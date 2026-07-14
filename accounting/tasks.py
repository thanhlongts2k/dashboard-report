import os
import re
import glob
import logging
import pandas as pd
from celery import shared_task
from django.db.models import Sum, Q
from .models import BusinessUnit, BUPerformance, InventorySummary, PurchaseDetail, ReceivablesAgeing, SalesTransaction, AccountDetail, BUPerformanceDaily, SupplierDebt, Warehouse, ImportLog, Customer
from datetime import datetime, timedelta
import calendar
from .resources import (
    PurchaseDetailResource, SalesTransactionResource, SupplierDebtResource, 
    AccountDetailResource, ReceivablesAgeingResource, InventorySummaryResource, CustomerResource
)
from django.conf import settings
from django.db import transaction
from django.utils import timezone
from tablib import Dataset
from .misa_tasks import download_misa_reports_task, misa_pipeline_master

logger = logging.getLogger(__name__)

def detect_period_from_filename(filename, file_path):
    # 1. Check định dạng Quãng: ví dụ BAN_HANG_202601-202605.xlsx
    range_match = re.search(r'(\d{4})(\d{2})-(\d{4})(\d{2})', filename)
    if range_match:
        start_y, start_m, end_y, end_m = map(int, range_match.groups())
        start_date = datetime(start_y, start_m, 1).date()
        last_day = calendar.monthrange(end_y, end_m)[1]
        end_date = datetime(end_y, end_m, last_day).date()
        reporting_period = f"{end_y:04d}-{end_m:02d}"
        logger.info(f"Detected range period from filename {filename}: {start_date} to {end_date}, period: {reporting_period}")
        return start_date, end_date, reporting_period, True

    # 2. Check định dạng Ngày/Tháng thông thường: ví dụ BAN_HANG_20260630_163003.xlsx
    single_match = re.search(r'_(\d{4})(\d{2})(\d{2})_', filename)
    if single_match:
        y, m, d = map(int, single_match.groups())
        start_date = datetime(y, m, 1).date()
        last_day = calendar.monthrange(y, m)[1]
        end_date = datetime(y, m, last_day).date()
        reporting_period = f"{y:04d}-{m:02d}"
        logger.info(f"Detected single period from filename {filename}: {start_date} to {end_date}, period: {reporting_period}")
        return start_date, end_date, reporting_period, False

    # 3. Check định dạng Tháng: ví dụ BAN_HANG_202606.xlsx
    month_match = re.search(r'(?<!\d)(\d{4})(\d{2})(?!\d)', filename)
    if month_match:
        y, m = map(int, month_match.groups())
        if 1 <= m <= 12 and 2000 <= y <= 2100:
            start_date = datetime(y, m, 1).date()
            last_day = calendar.monthrange(y, m)[1]
            end_date = datetime(y, m, last_day).date()
            reporting_period = f"{y:04d}-{m:02d}"
            logger.info(f"Detected monthly period from filename {filename}: {start_date} to {end_date}, period: {reporting_period}")
            return start_date, end_date, reporting_period, False

    # 4. Fallback: Đọc lướt nội dung file tìm cột ngày hạch toán/chứng từ
    try:
        df = pd.read_excel(file_path, nrows=50, header=None)
        header_row_idx = -1
        date_col_idx = -1
        
        for idx, row in df.iterrows():
            for c_idx, val in enumerate(row.values):
                val_str = str(val).strip() if pd.notna(val) else ""
                if val_str in ["Ngày hạch toán", "Ngày chứng từ"]:
                    header_row_idx = idx
                    date_col_idx = c_idx
                    break
            if header_row_idx >= 0:
                break

        if header_row_idx >= 0 and date_col_idx >= 0:
            for r_idx in range(header_row_idx + 1, len(df)):
                val = df.iloc[r_idx, date_col_idx]
                if pd.notna(val):
                    try:
                        dt = pd.to_datetime(val)
                        if not pd.isna(dt):
                            start_date = datetime(dt.year, dt.month, 1).date()
                            last_day = calendar.monthrange(dt.year, dt.month)[1]
                            end_date = datetime(dt.year, dt.month, last_day).date()
                            reporting_period = f"{dt.year:04d}-{dt.month:02d}"
                            logger.info(f"Detected period by peeking excel {filename}: {start_date} to {end_date}, period: {reporting_period}")
                            return start_date, end_date, reporting_period, False
                    except Exception:
                        pass
    except Exception as e:
        logger.error(f"Error peeking excel file {filename}: {e}")

    # 4. Fallback cuối cùng: Lấy tháng hiện tại
    today = datetime.now()
    start_date = datetime(today.year, today.month, 1).date()
    last_day = calendar.monthrange(today.year, today.month)[1]
    end_date = datetime(today.year, today.month, last_day).date()
    reporting_period = f"{today.year:04d}-{today.month:02d}"
    logger.info(f"Fallback to current period for {filename}: {start_date} to {end_date}, period: {reporting_period}")
    return start_date, end_date, reporting_period, False

def load_and_clean_excel(file_path, prefix):
    # Read raw Excel file
    df = pd.read_excel(file_path, header=None)
    
    # 1. Find header row
    header_idx = -1
    required_cols = []
    if prefix in ['BAN_HANG', 'MUA_HANG', 'TAI_KHOAN_CT']:
        required_cols = ['Ngày hạch toán', 'Số chứng từ', 'Mã hàng']
    elif prefix == 'TON_KHO':
        required_cols = ['Mã hàng', 'Mã kho']
    elif prefix == 'CONG_NO_NCC':
        required_cols = ['Mã nhà cung cấp']
    elif prefix == 'TUOI_NO_KH':
        required_cols = ['Mã khách hàng']

    for idx, row in df.iterrows():
        row_str = [str(cell).strip() if pd.notna(cell) else "" for cell in row.values]
        if any(col in row_str for col in required_cols):
            header_idx = idx
            break

    if header_idx == -1:
        raise ValueError(f"Không tìm thấy dòng tiêu đề cho {prefix} trong file Excel.")

    # 2. Clean headers based on prefix (mimicking resource.before_import)
    if prefix == 'TON_KHO':
        main_h = df.iloc[header_idx]
        sub_h = df.iloc[header_idx + 1]
        new_headers = []
        current_main = ""
        for m, s in zip(main_h, sub_h):
            m_s = str(m).strip() if pd.notna(m) else ""
            s_s = str(s).strip() if pd.notna(s) else ""
            if m_s in ["Đầu kỳ", "Nhập kho", "Xuất kho", "Cuối kỳ"]:
                current_main = m_s
            if s_s in ["Số lượng", "Giá trị", "SL mua hàng", "Giá trị mua hàng", "SL bán hàng", "Giá trị bán hàng"]:
                new_headers.append(f"{current_main}_{s_s}")
            else:
                val = m_s if m_s else s_s
                new_headers.append(val)
                if m_s not in ["", "Đầu kỳ", "Nhập kho", "Xuất kho", "Cuối kỳ"]:
                    current_main = ""
        headers = new_headers
        data_start_idx = header_idx + 2
    elif prefix == 'CONG_NO_NCC':
        main_headers = df.iloc[header_idx]
        sub_headers = df.iloc[header_idx + 1]
        new_headers = []
        current_prefix = ""
        for m, s in zip(main_headers, sub_headers):
            m_str = str(m).strip() if pd.notna(m) else ""
            s_str = str(s).strip() if pd.notna(s) else ""
            if "Số dư đầu kỳ" in m_str: current_prefix = "Đầu kỳ"
            elif "Phát sinh" in m_str: current_prefix = "Phát sinh"
            elif "Số dư cuối kỳ" in m_str: current_prefix = "Cuối kỳ"
            if s_str in ["Nợ", "Có"]:
                new_headers.append(f"{current_prefix}_{s_str}")
            else:
                new_headers.append(m_str if m_str else s_str)
        headers = new_headers
        data_start_idx = header_idx + 2
    elif prefix == 'TUOI_NO_KH':
        h_main = df.iloc[header_idx]
        h_sub = df.iloc[header_idx + 1]
        new_headers = []
        prefix_str = ""
        for m, s in zip(h_main, h_sub):
            m_s = str(m).strip() if pd.notna(m) else ""
            s_s = str(s).strip() if pd.notna(s) else ""
            if "Nợ trước hạn" in m_s: prefix_str = "Nợ trước hạn_"
            elif "Nợ quá hạn" in m_s: prefix_str = "Nợ quá hạn_"
            elif m_s != "": prefix_str = ""
            new_headers.append(f"{prefix_str}{s_s}" if prefix_str and s_s else (m_s if m_s else s_s))
        headers = new_headers
        data_start_idx = header_idx + 2
    else: # BAN_HANG, MUA_HANG, TAI_KHOAN_CT
        headers = [str(h).replace('\ufeff', '').strip().replace('\n', ' ') if pd.notna(h) else "" for h in df.iloc[header_idx]]
        headers = [re.sub(' +', ' ', h) for h in headers]
        data_start_idx = header_idx + 1

    # 3. Slice data and drop empty or summary rows
    df_data = df.iloc[data_start_idx:].copy()
    df_data.columns = headers
    
    filtered_rows = []
    for _, row in df_data.iterrows():
        row_str = [str(val).strip() for val in row.values if pd.notna(val)]
        if not row_str:
            continue
        first_val = str(row.values[0]).strip() if pd.notna(row.values[0]) else ""
        if "Tổng" in first_val or "Cộng" in first_val or first_val == "None":
            continue
        row_content = "".join([str(c) for c in row.values if pd.notna(c)])
        if "Tổng" in row_content or "Cộng" in row_content or not row_content:
            continue
            
        row_dict = {}
        for h, val in zip(headers, row.values):
            if pd.isna(val):
                row_dict[h] = None
            else:
                if isinstance(val, (pd.Timestamp, datetime)):
                    row_dict[h] = val.strftime('%Y-%m-%d')
                else:
                    row_dict[h] = val
        filtered_rows.append(row_dict)
        
    return headers, filtered_rows

@shared_task
def auto_import_excel_from_folder():
    # 1. Cấu hình đường dẫn
    BASE_IMPORT_PATH = os.path.join(settings.BASE_DIR, 'media', 'auto_imports')
    
    # 2. Mapping giữa Tiền tố File - Model - Resource
    IMPORT_MAP = {
        'BAN_HANG': {'model': SalesTransaction, 'resource': SalesTransactionResource()},
        'MUA_HANG': {'model': PurchaseDetail, 'resource': PurchaseDetailResource()},
        'TON_KHO': {'model': InventorySummary, 'resource': InventorySummaryResource()},
        'CONG_NO_NCC': {'model': SupplierDebt, 'resource': SupplierDebtResource()},
        'TUOI_NO_KH': {'model': ReceivablesAgeing, 'resource': ReceivablesAgeingResource()},
        'TAI_KHOAN_CT': {'model': AccountDetail, 'resource': AccountDetailResource()},
    }

    # Quét tất cả các file excel trong thư mục auto_imports
    all_files = []
    if os.path.exists(BASE_IMPORT_PATH):
        for f in os.listdir(BASE_IMPORT_PATH):
            if f.lower().endswith('.xlsx') and not f.startswith('~$'):
                all_files.append(os.path.join(BASE_IMPORT_PATH, f))

    # Gom nhóm các file theo tiền tố phù hợp nhất (lấy prefix dài nhất khớp)
    prefix_to_files = {p: [] for p in IMPORT_MAP.keys()}
    sorted_prefixes = sorted(IMPORT_MAP.keys(), key=len, reverse=True)

    for filepath in all_files:
        filename = os.path.basename(filepath)
        for prefix in sorted_prefixes:
            if filename.lower().startswith(prefix.lower()):
                prefix_to_files[prefix].append(filepath)
                break

    report = []
    imported_periods = set()
    msgFileNotFound = []

    for prefix, files in prefix_to_files.items():
        if not files:
            msgFileNotFound.append(prefix)
            continue

        config = IMPORT_MAP[prefix]
        
        # 1. Trích xuất thông tin kỳ và sắp xếp thứ tự các file theo thời gian tăng dần
        parsed_files = []
        for filepath in files:
            try:
                start_date, end_date, reporting_period, is_range = detect_period_from_filename(
                    os.path.basename(filepath), filepath
                )
                ctime = os.path.getctime(filepath)
                parsed_files.append((start_date, filepath, end_date, reporting_period, is_range, ctime))
            except Exception as e:
                logger.error(f"Error parsing period for sorting file {filepath}: {e}")
                parsed_files.append((datetime.min.date(), filepath, datetime.min.date(), "N/A", False, 0))

        # Sắp xếp theo start_date -> end_date -> ctime (tệp cũ hơn chạy trước, tệp mới chạy sau ghi đè)
        parsed_files.sort(key=lambda x: (x[0], x[2], x[5]))

        for start_date, filepath, end_date, reporting_period, is_range, ctime in parsed_files:
            if not os.path.exists(filepath):
                logger.warning(f"[{prefix}] File {os.path.basename(filepath)} no longer exists. It may have been processed by another concurrent task.")
                continue
                
            start_time = timezone.now()
            logger.info(f"[{prefix}] Bắt đầu import từ file: {os.path.basename(filepath)}")
            
            try:
                with transaction.atomic():
                    deleted_count = 0
                    # BƯỚC A: XÓA SẠCH DỮ LIỆU CŨ THEO PHÂN ĐOẠN (nếu không có skip_delete)
                    if not config.get('skip_delete', False):
                        is_snapshot = config['model'] in [InventorySummary, SupplierDebt, ReceivablesAgeing]
                        if is_snapshot:
                            # Xóa phân đoạn của kỳ hiện tại và bất kỳ dữ liệu cũ bị NULL
                            deleted_count = config['model'].objects.filter(
                                Q(reporting_period=reporting_period) | Q(reporting_period__isnull=True)
                            ).delete()[0]
                        else:
                            deleted_count = config['model'].objects.filter(
                                posting_date__range=[start_date, end_date]
                            ).delete()[0]
                    
                    # BƯỚC B: ĐỌC VÀ LÀM SẠCH FILE EXCEL
                    headers, cleaned_rows = load_and_clean_excel(filepath, prefix)
                    
                    # BƯỚC C: NẠP THEO CHUNK (LÔ 1000 DÒNG)
                    chunk_size = 1000
                    total_rows = len(cleaned_rows)
                    has_error = False
                    err_msg = ""
                    imported_count = 0
                    
                    for i in range(0, total_rows, chunk_size):
                        chunk_data = cleaned_rows[i:i+chunk_size]
                        chunk_dataset = Dataset()
                        chunk_dataset.headers = headers
                        for r in chunk_data:
                            chunk_dataset.append([r[h] for h in headers])
                        
                        # Gọi import_data của Resource với reporting_period
                        result = config['resource'].import_data(
                            chunk_dataset, 
                            dry_run=False, 
                            reporting_period=reporting_period
                        )
                        
                        if result.has_errors():
                            has_error = True
                            error_details = []
                            if result.base_errors:
                                for error in result.base_errors:
                                    error_details.append(f"Lỗi chung: {str(error.error)}")
                            if result.row_errors():
                                for row_num, errors in result.row_errors():
                                    for error in errors:
                                        error_details.append(f"Dòng {row_num + i}: {str(error.error)}")
                            err_msg = "\n".join(error_details)
                            break
                        else:
                            imported_count += len(chunk_data)

                    if not has_error:
                        # BƯỚC D: DI CHUYỂN FILE VÀO THƯ MỤC SUCCESS
                        move_to_processed(filepath, 'success')
                        msg = f"Kỳ: {reporting_period}. Đã xóa {deleted_count} dòng cũ & Import mới {imported_count} dòng."
                        report.append(msg)
                        ImportLog.objects.create(
                            file_name=os.path.basename(filepath),
                            status='SUCCESS',
                            message=msg,
                            start_time=start_time,
                            end_time=timezone.now()
                        )
                        
                        # Lưu lại các kỳ đã nạp thành công để tính lại KPI sau này
                        current_dt = start_date
                        while current_dt <= end_date:
                            imported_periods.add((current_dt.month, current_dt.year))
                            if current_dt.month == 12:
                                current_dt = datetime(current_dt.year + 1, 1, 1).date()
                            else:
                                current_dt = datetime(current_dt.year, current_dt.month + 1, 1).date()
                    else:
                        msg = f"Lỗi dữ liệu file tại lô dòng {imported_count + 1}...\nChi tiết lỗi:\n{err_msg}"
                        report.append(msg)
                        ImportLog.objects.create(
                            file_name=os.path.basename(filepath),
                            status='ERROR',
                            message=msg,
                            start_time=start_time,
                            end_time=timezone.now()
                        )
                        raise Exception(msg)
                
                logger.info(f"[{prefix}] Hoàn tất import. Đã ghi log.")

            except Exception as e:
                msg = f"⚠️ Lỗi hệ thống {str(e)}"
                report.append(msg)
                ImportLog.objects.create(
                    file_name=os.path.basename(filepath) if 'filepath' in locals() else prefix,
                    status='ERROR',
                    message=msg,
                    start_time=start_time if 'start_time' in locals() else timezone.now(),
                    end_time=timezone.now()
                )

    if len(msgFileNotFound) > 0:
        files_list = '\n'.join([f'- {prefix}' for prefix in msgFileNotFound])
        schedule_desc = getattr(settings, 'IMPORT_SCHEDULE_DESC', 'N/A')
        msg = f"Đã thực hiện import theo chu kỳ: {schedule_desc}\nKhông tìm thấy file:\n{files_list}"
        ImportLog.objects.create(
            file_name="N/A",
            status='NOTFOUND',
            message=msg,
            start_time=timezone.now(),
            end_time=timezone.now()
        )

    # BƯỚC D: SAU KHI IMPORT XONG, TÍNH TOÁN LẠI KPI CHO TOÀN BỘ BU THEO CÁC KỲ ĐÃ NẠP
    if not imported_periods:
        today = datetime.now()
        imported_periods.add((today.month, today.year))

    for m, y in sorted(list(imported_periods)):
        logger.info(f"Kích hoạt tính toán hiệu suất (KPI) cho kỳ {m}/{y}")
        try:
            update_single_bu_performance.delay(None, month=m, year=y)
            for bu in BusinessUnit.objects.all():
                update_single_bu_performance.delay(bu.id, month=m, year=y)
        except Exception as celery_err:
            logger.warning(f"Không thể kết nối đến Redis/Celery ({celery_err}). Thực hiện tính toán KPI đồng bộ...")
            update_single_bu_performance(None, month=m, year=y)
            for bu in BusinessUnit.objects.all():
                update_single_bu_performance(bu.id, month=m, year=y)

    # Tự động đồng bộ tồn kho vào Warehouse sau khi tính KPI
    latest_period = None
    if imported_periods:
        latest_m, latest_y = max(imported_periods)
        latest_period = f"{latest_y:04d}-{latest_m:02d}"
        
    try:
        sync_warehouse_inventory_data.delay(latest_period)
    except Exception as celery_err:
        logger.warning(f"Không thể kết nối đến Redis/Celery ({celery_err}). Thực hiện đồng bộ tồn kho kho hàng đồng bộ...")
        sync_warehouse_inventory_data(latest_period)

    return "\n".join(report)

def move_to_processed(file_path, status):
    dest_dir = os.path.join(os.path.dirname(file_path), status)
    if not os.path.exists(dest_dir): os.makedirs(dest_dir)
    dest_path = os.path.join(dest_dir, os.path.basename(file_path))
    if os.path.exists(dest_path): os.remove(dest_path)
    os.rename(file_path, dest_path)

@shared_task
def update_single_bu_performance(bu_id, month=None, year=None, target_date_str=None):
    # --- 1. XỬ LÝ THỜI GIAN ---
    today = datetime.now()
    month = int(month) if month else today.month
    year = int(year) if year else today.year
    
    if target_date_str:
        target_date = datetime.strptime(target_date_str, '%Y-%m-%d').date()
    else:
        if month == today.month and year == today.year:
            target_date = today.date()
        else:
            last_day = calendar.monthrange(year, month)[1]
            target_date = datetime(year, month, last_day).date()

    # --- 2. XÁC ĐỊNH PHẠM VI (GLOBAL / SUB-BU) & LOẠI TRỪ ---
    # Lấy cấu hình loại trừ từ settings
    excluded_bu_codes = getattr(settings, 'EXCLUDED_BU_CODES', [])
    excluded_bu_ids = []
    if excluded_bu_codes:
        excluded_bus = BusinessUnit.objects.filter(code__in=excluded_bu_codes)
        for ex_bu in excluded_bus:
            excluded_bu_ids.extend(ex_bu.get_all_descendant_ids())

    is_global = False
    bu_ids = []
    if bu_id is None:
        is_global = True
    else:
        bu = BusinessUnit.objects.filter(id=bu_id).first()
        if bu:
            is_global = False
            bu_ids = bu.get_all_descendant_ids()
            # Loại bỏ các BU bị loại trừ khỏi danh sách bu_ids
            bu_ids = [bid for bid in bu_ids if bid not in excluded_bu_ids]

    # Bộ lọc khách hàng: Ghi nhận doanh thu và loại bỏ các nhóm khách hàng loại trừ từ settings
    excluded_cust_group_codes = getattr(settings, 'EXCLUDED_CUSTOMER_GROUP_CODES', [])
    customer_rev_filter = Q(customer__has_revenue=True)
    if excluded_cust_group_codes:
        customer_rev_filter &= ~Q(customer__group__code__in=excluded_cust_group_codes)

    # --- 3. TÍNH DOANH THU & THỰC THU (LŨY KẾ THÁNG) ---
    base_filter = Q(posting_date__month=month, posting_date__year=year) & customer_rev_filter

    # Lọc Tồn kho theo kỳ báo cáo cụ thể
    inventory_filter = Q(reporting_period=f"{year:04d}-{month:02d}")
    if is_global:
        if excluded_bu_ids:
            inventory_filter &= ~Q(warehouse__business_unit_id__in=excluded_bu_ids)
    else:
        inventory_filter &= Q(warehouse__business_unit_id__in=bu_ids)

    # Tồn kho tháng
    inv_data = InventorySummary.objects.filter(inventory_filter).aggregate(
        opening=Sum('opening_value'),
        in_val=Sum('in_value'),
        out_val=Sum('out_value'),
        closing=Sum('closing_value')
    )
    
    inventory_actual = inv_data['closing'] or 0

    if is_global:
        if excluded_bu_ids:
            base_filter &= ~Q(business_unit_id__in=excluded_bu_ids)
    else:
        base_filter &= Q(business_unit_id__in=bu_ids)

    # Doanh thu tháng
    sales_qs = SalesTransaction.objects.filter(base_filter)
    rev_actual = sales_qs.aggregate(total=Sum('actual_sales'))['total'] or 0

    # Thực thu tháng
    account_qs = AccountDetail.objects.filter(base_filter)
    cash_cond = Q(account_number__startswith='111') | Q(account_number__startswith='112')
    offset_cond = Q(offset_account__startswith='1311') | Q(offset_account__startswith='1312')
    
    match_qs = account_qs.filter(cash_cond & offset_cond)
    sums = match_qs.aggregate(d=Sum('debit_amount'), c=Sum('credit_amount'))
    coll_actual = (sums['d'] or 0) - (sums['c'] or 0)

    # --- BỔ SUNG TÍNH TOÁN CÔNG NỢ & THU TIỀN ---
    # Lọc Ageing theo kỳ báo cáo cụ thể
    ageing_filter = Q(reporting_period=f"{year:04d}-{month:02d}")
    if excluded_cust_group_codes:
        ageing_filter &= ~Q(customer__group__code__in=excluded_cust_group_codes)

    if is_global:
        if excluded_bu_ids:
            ageing_filter &= ~Q(customer__business_unit_id__in=excluded_bu_ids)
    else:
        ageing_filter &= Q(customer__business_unit_id__in=bu_ids)
    
    # Tính toán các chỉ số dư nợ và nợ quá hạn cuối kỳ từ ReceivablesAgeing
    rec_data = ReceivablesAgeing.objects.filter(ageing_filter).aggregate(
        total=Sum('total_debt'),
        overdue=Sum('overdue_total'),
    )
    receivable_total = rec_data['total'] or 0
    receivable_overdue = rec_data['overdue'] or 0

    # Tính Đã thu (đến hạn) cấp tháng: Tổng số tiền thực thu từ các khách hàng có nợ quá hạn
    overdue_customers = ReceivablesAgeing.objects.filter(
        ageing_filter, 
        overdue_total__gt=0
    ).values_list('customer_id', flat=True)

    month_due_qs = AccountDetail.objects.filter(
        base_filter,
        customer_id__in=overdue_customers
    ).filter(cash_cond & offset_cond)
    sums_due = month_due_qs.aggregate(d=Sum('debit_amount'), c=Sum('credit_amount'))
    collection_due_actual = (sums_due['d'] or 0) - (sums_due['c'] or 0)

    # Thu trong hạn + COD = Tổng thực thu - Đã thu đến hạn
    collection_in_term_cod = coll_actual - collection_due_actual

    # --- 3.6. TÍNH TOÁN TIỀN CUỐI KỲ & NỢ NGÂN HÀNG THỰC TẾ (LŨY KẾ THÁNG) ---
    ledger_filter = Q(posting_date__month=month, posting_date__year=year)
    if is_global:
        if excluded_bu_ids:
            ledger_filter &= ~Q(business_unit_id__in=excluded_bu_ids)
    else:
        ledger_filter &= Q(business_unit_id__in=bu_ids)

    # Tiền cuối kỳ thực tế: Dư Nợ dòng cuối cùng tài khoản 111 và 112 cộng lại
    last_111 = AccountDetail.objects.filter(ledger_filter, account_number='111').order_by('posting_date', 'id').last()
    last_112 = AccountDetail.objects.filter(ledger_filter, account_number='112').order_by('posting_date', 'id').last()
    
    cash_bal_111 = last_111.balance_debit if last_111 else 0
    cash_bal_112 = last_112.balance_debit if last_112 else 0
    cash_balance_actual = cash_bal_111 + cash_bal_112

    # Nợ ngân hàng thực tế: Dư Có dòng cuối cùng tài khoản 341
    last_341 = AccountDetail.objects.filter(ledger_filter, account_number='341').order_by('posting_date', 'id').last()
    bank_debt_actual = last_341.balance_credit if last_341 else 0

    # --- 4. CẬP NHẬT DATABASE (BẢNG THÁNG) ---
    performance, _ = BUPerformance.objects.update_or_create(
        business_unit_id=bu_id,
        month=month,
        year=year,
        defaults={
            'mtd_revenue_actual': rev_actual,                  # Doanh thu thực tế lũy kế tháng (MTD)
            'mtd_collection_actual': coll_actual,              # Thực thu thực tế lũy kế tháng (Dòng tiền thu về)
            'collection_due_actual': collection_due_actual,    # Số tiền nợ quá hạn thực tế đã thu được trong tháng
            'collection_in_term_cod': collection_in_term_cod,  # Số tiền thu nợ trong hạn + COD thực tế thu được
            'receivable_total': receivable_total,              # Tổng số dư nợ phải thu của khách hàng tại thời điểm cuối kỳ
            'receivable_overdue': receivable_overdue,          # Tổng số dư nợ quá hạn của khách hàng tại thời điểm cuối kỳ
            'inventory_opening_value': inv_data['opening'] or 0, # Giá trị tồn kho đầu kỳ báo cáo
            'inventory_in_value': inv_data['in_val'] or 0,     # Tổng giá trị nhập kho phát sinh trong kỳ
            'inventory_out_value': inv_data['out_val'] or 0,   # Tổng giá trị xuất kho phát sinh trong kỳ
            'inventory_value_actual': inventory_actual,        # Giá trị tồn kho thực tế cuối kỳ báo cáo
            'cash_balance_actual': cash_balance_actual,        # Tổng số dư tiền mặt và tiền gửi ngân hàng thực tế cuối kỳ
            'bank_debt_actual': bank_debt_actual,              # Tổng số dư nợ vay ngân hàng (TK 341) thực tế cuối kỳ
        }
    )

    # --- 4.5. TÍNH CHỈ SỐ YTD (LŨY KẾ NĂM) & PROPAGATION ---
    prev_perf = None
    if month > 1:
        prev_perf = BUPerformance.objects.filter(
            business_unit_id=bu_id,
            month=month - 1,
            year=year
        ).first()

    performance.ytd_revenue_actual = (prev_perf.ytd_revenue_actual if prev_perf else 0) + performance.mtd_revenue_actual
    performance.ytd_revenue_plan = (prev_perf.ytd_revenue_plan if prev_perf else 0) + performance.mtd_revenue_plan
    performance.ytd_collection_actual = (prev_perf.ytd_collection_actual if prev_perf else 0) + performance.mtd_collection_actual
    performance.ytd_collection_plan = (prev_perf.ytd_collection_plan if prev_perf else 0) + performance.mtd_collection_plan
    performance.ytd_opex_actual = (prev_perf.ytd_opex_actual if prev_perf else 0) + performance.opex_actual
    performance.ytd_opex_plan = (prev_perf.ytd_opex_plan if prev_perf else 0) + performance.opex_plan
    performance.save()

    # Lan truyền sang các tháng tiếp theo của năm đó
    next_month = month + 1
    while next_month <= 12:
        next_perf = BUPerformance.objects.filter(
            business_unit_id=bu_id,
            month=next_month,
            year=year
        ).first()
        if next_perf:
            curr_perf = BUPerformance.objects.filter(
                business_unit_id=bu_id,
                month=next_month - 1,
                year=year
            ).first()
            if curr_perf:
                next_perf.ytd_revenue_actual = curr_perf.ytd_revenue_actual + next_perf.mtd_revenue_actual
                next_perf.ytd_revenue_plan = curr_perf.ytd_revenue_plan + next_perf.mtd_revenue_plan
                next_perf.ytd_collection_actual = curr_perf.ytd_collection_actual + next_perf.mtd_collection_actual
                next_perf.ytd_collection_plan = curr_perf.ytd_collection_plan + next_perf.mtd_collection_plan
                next_perf.ytd_opex_actual = curr_perf.ytd_opex_actual + next_perf.opex_actual
                next_perf.ytd_opex_plan = curr_perf.ytd_opex_plan + next_perf.opex_plan
                next_perf.save()
            next_month += 1
        else:
            break

    # --- 5. TÍNH VÀ CẬP NHẬT CHO TẤT CẢ CÁC NGÀY TRONG THÁNG (DAILY ACTUAL) ---
    # Chạy vòng lặp từ ngày 1 đến target_date
    current_date = datetime(year, month, 1).date()
    
    while current_date <= target_date:
        daily_filter = Q(posting_date=current_date)
        if is_global:
            if excluded_bu_ids:
                daily_filter &= ~Q(business_unit_id__in=excluded_bu_ids)
        else:
            daily_filter &= Q(business_unit_id__in=bu_ids)
        
        # Doanh thu ngày (áp dụng actual_sales thay vì sales_amount để đồng bộ dữ liệu)
        daily_rev = SalesTransaction.objects.filter(daily_filter & customer_rev_filter).aggregate(
            total=Sum('actual_sales')
        )['total'] or 0

        # Thực thu ngày
        daily_acc_qs = AccountDetail.objects.filter(daily_filter & customer_rev_filter).filter(cash_cond & offset_cond)
        daily_sums = daily_acc_qs.aggregate(d=Sum('debit_amount'), c=Sum('credit_amount'))
        daily_coll = (daily_sums['d'] or 0) - (daily_sums['c'] or 0)

        # Cập nhật bảng Daily
        BUPerformanceDaily.objects.update_or_create(
            performance_month=performance,
            date=current_date,
            defaults={
                'daily_revenue': daily_rev,
                'daily_collection': daily_coll,
            }
        )
        current_date += timedelta(days=1)
    
    bu_name = "TỔNG CÔNG TY" if is_global else f"Business Unit {bu_id}"
    return f"Updated {bu_name}: Month Rev={rev_actual} | All days up to {target_date} updated"


@shared_task
def sync_warehouse_inventory_data(reporting_period=None):
    """
    Hàm này quét bảng InventorySummary của kỳ báo cáo chỉ định và cập nhật số tổng vào từng Warehouse tương ứng.
    """
    if not reporting_period:
        # Tìm kỳ mới nhất trong cơ sở dữ liệu nếu không chỉ định
        latest_item = InventorySummary.objects.order_by('-reporting_period').first()
        if latest_item:
            reporting_period = latest_item.reporting_period
        else:
            today = datetime.now()
            reporting_period = f"{today.year:04d}-{today.month:02d}"

    logger.info(f"Đang đồng bộ dữ liệu tồn kho cho các kho theo kỳ: {reporting_period}")
    warehouses = Warehouse.objects.all()
    
    for wh in warehouses:
        # Tính toán từ bảng InventorySummary thuộc kỳ báo cáo chỉ định
        data = InventorySummary.objects.filter(
            warehouse=wh,
            reporting_period=reporting_period
        ).aggregate(
            opening=Sum('opening_value'),
            in_val=Sum('in_value'),
            out_val=Sum('out_value'),
            closing=Sum('closing_value')
        )

        # Cập nhật vào bảng Warehouse
        wh.inventory_opening_value = data['opening'] or 0
        wh.inventory_in_value = data['in_val'] or 0
        wh.inventory_out_value = data['out_val'] or 0
        wh.inventory_value_actual = data['closing'] or 0
        wh.save()

    return f"Đã cập nhật số liệu tồn kho cho {warehouses.count()} kho theo kỳ {reporting_period}."