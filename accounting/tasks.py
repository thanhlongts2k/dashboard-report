import os
import re
import glob
import logging
from decimal import Decimal
import pandas as pd
from celery import shared_task
from django.db.models import Sum, Q
from .models import BusinessUnit, BUPerformance, InventorySummary, PurchaseDetail, ReceivablesAgeing, SalesTransaction, AccountDetail, BUPerformanceDaily, SupplierDebt, Warehouse, ImportLog, Customer, BankBalance, BUTargetPlan, ManualAdjustment, Department, JobTitle, Employee, EmployeeAssignment
from datetime import datetime, timedelta
import calendar
from .resources import (
    PurchaseDetailResource, SalesTransactionResource, SupplierDebtResource, 
    AccountDetailResource, ReceivablesAgeingResource, InventorySummaryResource, CustomerResource, BankBalanceResource,
    EmployeeResource
)
from django.conf import settings
from django.db import transaction
from django.utils import timezone
from tablib import Dataset
from .misa_tasks import download_misa_reports_task, misa_pipeline_master
from accounting.services import (
    detect_period_from_filename,
    sync_warehouse_inventory_data_logic,
    is_under_oversea,
    update_single_bu_performance as update_single_bu_performance_logic
)

logger = logging.getLogger(__name__)


def normalize_report_prefix(prefix):
    p = str(prefix).upper()
    if p in ['BAN_HANG', 'SO_CHI_TIET_BAN_HANG']: return 'BAN_HANG'
    if p in ['MUA_HANG', 'SO_CHI_TIET_MUA_HANG']: return 'MUA_HANG'
    if p in ['TON_KHO', 'TONG_HOP_TON_KHO']: return 'TON_KHO'
    if p in ['CONG_NO_NCC', 'TONG_HOP_CONG_NO_PHAI_TRA_NCC']: return 'CONG_NO_NCC'
    if p in ['TUOI_NO_KH', 'TONG_HOP_CONG_NO_PHAI_THU_KH', 'CONG_NO_KH']: return 'TUOI_NO_KH'
    if p in ['TAI_KHOAN_CT', 'SO_CHI_TIET_CAC_TAI_KHOAN', 'SO_CHI_TIET_TAI_KHOAN']: return 'TAI_KHOAN_CT'
    if p in ['SO_DU_NH', 'SO_DU_NGAN_HANG', 'BANG_KE_SO_DU_NGAN_HANG']: return 'SO_DU_NH'
    if p in ['DANH_SACH_NHAN_VIEN', 'NHAN_VIEN']: return 'DANH_SACH_NHAN_VIEN'
    if p in ['DANH_SACH_KHACH_HANG', 'KHACH_HANG']: return 'DANH_SACH_KHACH_HANG'
    return p


def load_and_clean_excel(file_path, prefix):
    # Read raw Excel file
    df = pd.read_excel(file_path, header=None)
    norm_prefix = normalize_report_prefix(prefix)
    
    # 1. Find header row
    header_idx = -1
    required_cols = []
    if norm_prefix in ['BAN_HANG', 'MUA_HANG', 'TAI_KHOAN_CT']:
        required_cols = ['Ngày hạch toán', 'Số chứng từ', 'Mã hàng']
    elif norm_prefix == 'TON_KHO':
        required_cols = ['Mã hàng', 'Mã kho']
    elif norm_prefix == 'CONG_NO_NCC':
        required_cols = ['Mã nhà cung cấp']
    elif norm_prefix == 'TUOI_NO_KH':
        required_cols = ['Mã khách hàng']
    elif norm_prefix == 'SO_DU_NH':
        required_cols = ['Tên ngân hàng']
    elif norm_prefix in ['DANH_SACH_NHAN_VIEN', 'NHAN_VIEN']:
        required_cols = ['Mã nhân viên', 'Tên nhân viên']
    elif norm_prefix in ['DANH_SACH_KHACH_HANG', 'KHACH_HANG']:
        required_cols = ['Mã khách hàng']

    for idx, row in df.iterrows():
        row_str = [str(cell).strip() if pd.notna(cell) else "" for cell in row.values]
        if any(col in row_str for col in required_cols):
            header_idx = idx
            break

    if header_idx == -1:
        raise ValueError(f"Không tìm thấy dòng tiêu đề cho {prefix} trong file Excel.")

    # 2. Clean headers based on prefix (mimicking resource.before_import)
    if norm_prefix == 'TON_KHO':
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
    elif norm_prefix == 'CONG_NO_NCC':
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
    elif norm_prefix == 'TUOI_NO_KH':
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
def auto_import_excel_from_folder(specific_file=None):
    # 1. Cấu hình đường dẫn
    BASE_IMPORT_PATH = os.path.join(settings.BASE_DIR, 'media', 'auto_imports')
    
    # 2. Mapping giữa Tiền tố File - Model - Resource (kèm Priority & Group)
    IMPORT_MAP = {
        'DANH_SACH_NHAN_VIEN': {'model': Employee, 'resource': EmployeeResource(), 'skip_delete': True, 'priority': 1, 'group': 'NHAN_VIEN'},
        'NHAN_VIEN': {'model': Employee, 'resource': EmployeeResource(), 'skip_delete': True, 'priority': 1, 'group': 'NHAN_VIEN'},
        'DANH_SACH_KHACH_HANG': {'model': Customer, 'resource': CustomerResource(), 'skip_delete': True, 'priority': 2, 'use_custom_importer': True, 'group': 'KHACH_HANG'},
        'KHACH_HANG': {'model': Customer, 'resource': CustomerResource(), 'skip_delete': True, 'priority': 2, 'use_custom_importer': True, 'group': 'KHACH_HANG'},
        'SO_CHI_TIET_BAN_HANG': {'model': SalesTransaction, 'resource': SalesTransactionResource(), 'priority': 3, 'group': 'BAN_HANG'},
        'BAN_HANG': {'model': SalesTransaction, 'resource': SalesTransactionResource(), 'priority': 3, 'group': 'BAN_HANG'},
        'SO_CHI_TIET_MUA_HANG': {'model': PurchaseDetail, 'resource': PurchaseDetailResource(), 'priority': 3, 'group': 'MUA_HANG'},
        'MUA_HANG': {'model': PurchaseDetail, 'resource': PurchaseDetailResource(), 'priority': 3, 'group': 'MUA_HANG'},
        'TONG_HOP_TON_KHO': {'model': InventorySummary, 'resource': InventorySummaryResource(), 'priority': 3, 'group': 'TON_KHO'},
        'TON_KHO': {'model': InventorySummary, 'resource': InventorySummaryResource(), 'priority': 3, 'group': 'TON_KHO'},
        'TONG_HOP_CONG_NO_PHAI_TRA_NCC': {'model': SupplierDebt, 'resource': SupplierDebtResource(), 'priority': 3, 'group': 'CONG_NO_NCC'},
        'CONG_NO_NCC': {'model': SupplierDebt, 'resource': SupplierDebtResource(), 'priority': 3, 'group': 'CONG_NO_NCC'},
        'TONG_HOP_CONG_NO_PHAI_THU_KH': {'model': ReceivablesAgeing, 'resource': ReceivablesAgeingResource(), 'priority': 3, 'group': 'TUOI_NO_KH'},
        'TUOI_NO_KH': {'model': ReceivablesAgeing, 'resource': ReceivablesAgeingResource(), 'priority': 3, 'group': 'TUOI_NO_KH'},
        'SO_CHI_TIET_CAC_TAI_KHOAN': {'model': AccountDetail, 'resource': AccountDetailResource(), 'priority': 3, 'group': 'TAI_KHOAN_CT'},
        'SO_CHI_TIET_TAI_KHOAN': {'model': AccountDetail, 'resource': AccountDetailResource(), 'priority': 3, 'group': 'TAI_KHOAN_CT'},
        'TAI_KHOAN_CT': {'model': AccountDetail, 'resource': AccountDetailResource(), 'priority': 3, 'group': 'TAI_KHOAN_CT'},
        'SO_DU_NH': {'model': BankBalance, 'resource': BankBalanceResource(), 'priority': 3, 'group': 'SO_DU_NH'},
        'SO_DU_NGAN_HANG': {'model': BankBalance, 'resource': BankBalanceResource(), 'priority': 3, 'group': 'SO_DU_NH'},
        'BANG_KE_SO_DU_NGAN_HANG': {'model': BankBalance, 'resource': BankBalanceResource(), 'priority': 3, 'group': 'SO_DU_NH'},
    }

    # 9 nhóm báo cáo chuẩn bắt buộc phải có trong thư mục auto_imports
    REQUIRED_REPORT_GROUPS = {
        'NHAN_VIEN': 'DANH_SACH_NHAN_VIEN (Danh sách nhân viên)',
        'KHACH_HANG': 'DANH_SACH_KHACH_HANG (Danh sách khách hàng)',
        'BAN_HANG': 'BAN_HANG (Sổ chi tiết bán hàng)',
        'MUA_HANG': 'MUA_HANG (Sổ chi tiết mua hàng)',
        'TON_KHO': 'TON_KHO (Tổng hợp tồn kho)',
        'CONG_NO_NCC': 'CONG_NO_NCC (Công nợ phải trả NCC)',
        'TUOI_NO_KH': 'TUOI_NO_KH (Tuổi nợ phải thu KH)',
        'TAI_KHOAN_CT': 'TAI_KHOAN_CT (Sổ chi tiết tài khoản)',
        'SO_DU_NH': 'SO_DU_NH (Bảng kê số dư ngân hàng)',
    }

    # Nếu specific_file được chỉ định → chỉ xử lý đúng 1 file đó (bỏ qua quét thư mục)
    if specific_file:
        all_files = [specific_file]
        logger.info(f"[specific_file mode] Processing only: {os.path.basename(specific_file)}")
    else:
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

    # Sắp xếp thứ tự nạp ưu tiên: Priority 1 (Nhân viên) -> Priority 2 (Khách hàng) -> Priority 3 (Báo cáo)
    sorted_prefix_items = sorted(
        prefix_to_files.items(), 
        key=lambda item: IMPORT_MAP[item[0]].get('priority', 3)
    )

    for prefix, files in sorted_prefix_items:
        if not files:
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

            # Xử lý nạp qua custom importer cho Customer Mapping
            if config.get('use_custom_importer'):
                try:
                    from scripts.import_customer_mapping import import_customer_sales_mapping
                    import_customer_sales_mapping(filepath, run_calculate=False)
                    move_to_processed(filepath, 'success')
                    msg = f"Đã nạp danh mục & mapping khách hàng từ file {os.path.basename(filepath)}"
                    report.append(msg)
                    ImportLog.objects.create(
                        file_name=os.path.basename(filepath),
                        status='SUCCESS',
                        message=msg,
                        start_time=start_time,
                        end_time=timezone.now()
                    )
                except Exception as cus_err:
                    msg = f"⚠️ Lỗi import mapping khách hàng: {str(cus_err)}"
                    logger.error(msg)
                    report.append(msg)
                    ImportLog.objects.create(
                        file_name=os.path.basename(filepath),
                        status='ERROR',
                        message=msg,
                        start_time=start_time,
                        end_time=timezone.now()
                    )
                continue
            
            try:
                with transaction.atomic():
                    deleted_count = 0
                    is_snapshot = config.get('model') in [InventorySummary, SupplierDebt, ReceivablesAgeing, BankBalance]
                    
                    # BƯỚC A: XÓA SẠCH DỮ LIỆU CŨ THEO PHÂN ĐOẠN (nếu không có skip_delete)
                    if not config.get('skip_delete', False):
                        if is_snapshot:
                            if config['model'] == BankBalance:
                                # Xóa theo tháng báo cáo cho số dư ngân hàng
                                deleted_count = config['model'].objects.filter(
                                    Q(reporting_month=reporting_period) | Q(reporting_month__isnull=True)
                                ).delete()[0]
                            else:
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
                            imported_count += result.totals.get('new', 0) + result.totals.get('update', 0)

                    if not has_error:
                        # BƯỚC D: DI CHUYỂN FILE VÀO THƯ MỤC SUCCESS
                        move_to_processed(filepath, 'success')
                        if imported_count == 0:
                            msg = f"Kỳ: {reporting_period}. Đã xóa {deleted_count} dòng cũ & File rỗng / Không phát sinh dữ liệu trong kỳ."
                        else:
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
                        if is_snapshot or not is_range:
                            # Đối với snapshot (Tuổi nợ, Tồn kho, Công nợ NCC, Số dư NH) hoặc file tháng đơn lẻ, chỉ tính KPI cho đúng kỳ báo cáo
                            if reporting_period and reporting_period != "N/A":
                                try:
                                    rp_y, rp_m = map(int, reporting_period.split('-'))
                                    imported_periods.add((rp_m, rp_y))
                                except Exception:
                                    imported_periods.add((end_date.month, end_date.year))
                            else:
                                imported_periods.add((end_date.month, end_date.year))
                        else:
                            # Chỉ lặp qua nhiều tháng khi file thực sự là dải tháng giao dịch (ví dụ BAN_HANG_202601-202605.xlsx)
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

    # Kiểm tra các nhóm báo cáo thực sự còn thiếu (tránh false-alarm do alias)
    if not specific_file:
        found_groups = set()
        for prefix, files in prefix_to_files.items():
            if files:
                found_groups.add(IMPORT_MAP[prefix].get('group', prefix))

        missing_groups = [desc for grp, desc in REQUIRED_REPORT_GROUPS.items() if grp not in found_groups]
        if len(missing_groups) > 0:
            files_list = '\n'.join([f'- {desc}' for desc in missing_groups])
            schedule_desc = getattr(settings, 'IMPORT_SCHEDULE_DESC', 'N/A')
            msg = f"Đã thực hiện import theo chu kỳ: {schedule_desc}\nKhông tìm thấy file:\n{files_list}"
            ImportLog.objects.create(
                file_name="N/A",
                status='NOTFOUND',
                message=msg,
                start_time=timezone.now(),
                end_time=timezone.now()
            )

    # BƯỚC D: SAU KHI IMPORT XONG, TÍNH TOÁN LẠI KPI CHO TOÀN BỘ BU & TOÀN CÔNG TY
    if not imported_periods:
        today = datetime.now()
        imported_periods.add((today.month, today.year))

    for m, y in sorted(list(imported_periods)):
        logger.info(f"Kích hoạt tính toán hiệu suất (KPI) cho kỳ {m}/{y}")
        # 1. Tính cho tất cả các BU con trước
        for bu in BusinessUnit.objects.all():
            try:
                update_single_bu_performance_logic(bu.id, month=m, year=y)
            except Exception as bu_calc_err:
                logger.error(f"Lỗi tính KPI BU {bu.code}: {bu_calc_err}")
        # 2. Tính Tổng Toàn Công Ty (business_unit=None) sau cùng để tổng hợp đầy đủ từ các BU
        try:
            update_single_bu_performance_logic(None, month=m, year=y)
        except Exception as corp_calc_err:
            logger.error(f"Lỗi tính KPI Toàn Công Ty: {corp_calc_err}")

    # Tự động đồng bộ tồn kho vào Warehouse sau khi tính KPI
    latest_period = None
    if imported_periods:
        latest_m, latest_y = max(imported_periods)
        latest_period = f"{latest_y:04d}-{latest_m:02d}"
        try:
            logger.info(f"Kích hoạt đồng bộ số liệu tồn kho vào Warehouse cho kỳ {latest_period}")
            sync_warehouse_inventory_data_logic(reporting_period=latest_period)
        except Exception as wh_err:
            logger.warning(f"Lỗi khi đồng bộ dữ liệu tồn kho kho hàng: {wh_err}")
        
    # Tự động tính toán và chốt số liệu công nợ Nhân viên & Quản lý nhóm (EmployeeReceivableSummary)
    try:
        from accounting.services.employee_debt_calculator import update_employee_receivable_summary
        for m, y in sorted(list(imported_periods)):
            p_str = f"{y:04d}-{m:02d}"
            logger.info(f"Kích hoạt tính toán công nợ Nhân viên & Quản lý cho kỳ {p_str}")
            update_employee_receivable_summary(p_str)
    except Exception as debt_err:
        logger.warning(f"Lỗi khi tự động tính toán công nợ Nhân viên & Quản lý: {debt_err}")

    return "\n".join(report)

def move_to_processed(file_path, status):
    dest_dir = os.path.join(os.path.dirname(file_path), status)
    if not os.path.exists(dest_dir): os.makedirs(dest_dir)
    dest_path = os.path.join(dest_dir, os.path.basename(file_path))
    if os.path.exists(dest_path): os.remove(dest_path)
    os.rename(file_path, dest_path)

@shared_task
def update_single_bu_performance(bu_id, month=None, year=None, target_date_str=None):
    return update_single_bu_performance_logic(bu_id, month=month, year=year, target_date_str=target_date_str)


@shared_task
def recalculate_company_total_task(month=None, year=None):
    """
    Celery Task / Function cập nhật linh hoạt số liệu Tổng Toàn Công Ty bất cứ lúc nào.
    """
    today = datetime.now()
    month = int(month) if month else today.month
    year = int(year) if year else today.year
    
    for bu in BusinessUnit.objects.all():
        update_single_bu_performance_logic(bu.id, month=month, year=year)
        
    res = update_single_bu_performance_logic(None, month=month, year=year)
    return f"✅ Đã cập nhật xong Tổng Toàn Công Ty Th{month}/{year}: {res}"


@shared_task
def sync_warehouse_inventory_data(reporting_period=None):
    """
    Hàm này quét bảng InventorySummary của kỳ báo cáo chỉ định và cập nhật số tổng vào từng Warehouse tương ứng.
    """
    return sync_warehouse_inventory_data_logic(reporting_period=reporting_period)


@shared_task(bind=True)
def send_debt_reminders_task(self, period=None, dry_run=True, test_email=None, bu_code=None, recipient_type='ALL'):
    """
    Celery Task tự động hóa gửi email nhắc nợ phân cấp (Sales & Trưởng BU).
    - period: YYYY-MM (Mặc định: kỳ mới nhất)
    - dry_run: bool (Mặc định True để an toàn)
    - test_email: email nhận mẫu khi dry_run=True
    - bu_code: chỉ gửi cho 1 BU chỉ định (Tùy chọn)
    - recipient_type: 'ALL', 'SALES', 'MANAGERS'
    """
    from accounting.services.debt_mailer import send_debt_reminders_process
    logger.info(f"👉 [Celery Task] Kích hoạt send_debt_reminders_task (period={period}, dry_run={dry_run}, test_email={test_email}, bu_code={bu_code}, recipient_type={recipient_type})")
    
    result = send_debt_reminders_process(
        period=period,
        dry_run=dry_run,
        test_email=test_email,
        bu_code=bu_code,
        recipient_type=recipient_type
    )
    return result


@shared_task(bind=True)
def send_executive_dashboard_task(self, to_email=None, cc_emails=None, report_date=None, period=None, dry_run=False):
    """
    Celery Task tự động hóa gửi email Báo Cáo Điều Hành (Executive Dashboard) cho Ban Lãnh Đạo (BOD).
    - to_email: Email người nhận chính
    - cc_emails: Danh sách email nhận CC
    - report_date: YYYY-MM-DD (Mặc định: ngày hiện tại)
    - period: YYYY-MM (Mặc định: tháng hiện tại)
    - dry_run: bool (Mặc định: False để gửi thật khi đã cấu hình)
    """
    from accounting.services.debt_mailer import send_executive_dashboard_email
    logger.info(f"👉 [Celery Task] Kích hoạt send_executive_dashboard_task (to_email={to_email}, cc_emails={cc_emails}, report_date={report_date}, period={period}, dry_run={dry_run})")
    
    success, msg = send_executive_dashboard_email(
        to_email=to_email,
        cc_emails=cc_emails,
        report_date=report_date,
        period=period,
        dry_run=dry_run
    )
    return {
        'success': success,
        'message': msg
    }

