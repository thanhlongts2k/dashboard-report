import os
import glob
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

@shared_task
def auto_import_excel_from_folder():
    # 1. Cấu hình đường dẫn
    BASE_IMPORT_PATH = os.path.join(settings.BASE_DIR, 'media', 'auto_imports')
    
    # 2. Mapping giữa Tiền tố File - Model - Resource
    IMPORT_MAP = {
        'KHACH_HANG': {'model': Customer, 'resource': CustomerResource(), 'skip_delete': True},

        # Cùng loại SalesTransaction
        'So_chi_tiet_ban_hang': {'model': SalesTransaction, 'resource': SalesTransactionResource()},
        'BAN_HANG': {'model': SalesTransaction, 'resource': SalesTransactionResource()},
        
        # Cùng loại PurchaseDetail
        'So_chi_tiet_mua_hang': {'model': PurchaseDetail, 'resource': PurchaseDetailResource()},
        'MUA_HANG': {'model': PurchaseDetail, 'resource': PurchaseDetailResource()},
        
        'TON_KHO': {'model': InventorySummary, 'resource': InventorySummaryResource()},
        'CONG_NO_NCC': {'model': SupplierDebt, 'resource': SupplierDebtResource()},
        'TUOI_NO_KH': {'model': ReceivablesAgeing, 'resource': ReceivablesAgeingResource()},
        'SO_CHI_TIET_TAI_KHOAN': {'model': AccountDetail, 'resource': AccountDetailResource()},
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

    msgFileNotFound = []

    for prefix, files in prefix_to_files.items():
        if not files:
            msgFileNotFound.append(prefix)
            continue

        config = IMPORT_MAP[prefix]
        # Lấy file mới nhất nếu có nhiều file cùng tiền tố
        latest_file = max(files, key=os.path.getctime)
        start_time = timezone.now()
        
        try:
            with transaction.atomic():
                deleted_count = 0
                # BƯỚC A: XÓA SẠCH DỮ LIỆU CŨ CỦA MODEL NÀY (nếu không có skip_delete)
                if not config.get('skip_delete', False):
                    deleted_count = config['model'].objects.count()
                    config['model'].objects.all().delete()
                
                # BƯỚC B: ĐỌC VÀ IMPORT DỮ LIỆU MỚI
                dataset = Dataset()
                with open(latest_file, 'rb') as f:
                    dataset.load(f.read(), format='xlsx')
                
                result = config['resource'].import_data(dataset, dry_run=False)

                if not result.has_errors():
                    # BƯỚC C: DI CHUYỂN FILE VÀO THƯ MỤC SUCCESS
                    move_to_processed(latest_file, 'success')
                    msg = f"Đã xóa {deleted_count} dòng cũ & Import mới {len(dataset)} dòng."
                    report.append(msg)
                    ImportLog.objects.create(
                        file_name=os.path.basename(latest_file),
                        status='SUCCESS',
                        message=msg,
                        start_time=start_time,
                        end_time=timezone.now()
                    )
                else:
                    error_details = []
                    if result.base_errors:
                        for error in result.base_errors:
                            error_details.append(f"Lỗi chung: {str(error.error)}")
                    if result.row_errors():
                        for row_num, errors in result.row_errors():
                            for error in errors:
                                error_details.append(f"Dòng {row_num}: {str(error.error)}")
                    
                    err_msg = "\n".join(error_details)
                    msg = f"Lỗi dữ liệu file.\nChi tiết lỗi:\n{err_msg}"
                    report.append(msg)
                    ImportLog.objects.create(
                        file_name=os.path.basename(latest_file),
                        status='ERROR',
                        message=msg,
                        start_time=start_time,
                        end_time=timezone.now()
                    )
                    # Transaction sẽ rollback, dữ liệu cũ không bị mất nếu import lỗi

        except Exception as e:
            msg = f"⚠️ Lỗi hệ thống {str(e)}"
            report.append(msg)
            ImportLog.objects.create(
                file_name=os.path.basename(latest_file) if 'latest_file' in locals() else prefix,
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

    # BƯỚC D: SAU KHI IMPORT XONG, TÍNH TOÁN LẠI KPI CHO TOÀN BỘ BU
    # Cập nhật cho Tổng công ty
    update_single_bu_performance.delay(None)
    # Cập nhật cho từng BU lẻ
    for bu in BusinessUnit.objects.all():
        update_single_bu_performance.delay(bu.id)

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

    # --- 2. XÁC ĐỊNH PHẠM VI (GLOBAL / SUB-BU) ---
    is_global = False
    if bu_id is None:
        is_global = True
    else:
        bu = BusinessUnit.objects.filter(id=bu_id).first()
        if bu and bu.parent_id is None:
            is_global = True

    customer_rev_filter = Q(customer__has_revenue=True)

    # --- 3. TÍNH DOANH THU & THỰC THU (LŨY KẾ THÁNG) ---
    base_filter = Q(posting_date__month=month, posting_date__year=year) & customer_rev_filter

    inventory_filter = Q(created_at__month=month, created_at__year=year)
    if not is_global:
        inventory_filter &= Q(warehouse__business_unit_id=bu_id)

    # Tồn kho tháng (tính tổng theo filter, nếu là global thì lấy tất cả, nếu là sub-BU thì lọc theo BU)
    inv_data = InventorySummary.objects.filter(inventory_filter).aggregate(
        opening=Sum('opening_value'),
        in_val=Sum('in_value'),
        out_val=Sum('out_value'),
        closing=Sum('closing_value')
    )
    # print(f"Inventory Data for BU {bu_id} - Month {month}/{year}: {inv_data}")
    
    inventory_actual = inv_data['closing'] or 0

    if not is_global:
        base_filter &= Q(business_unit_id=bu_id)

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
    # Thiết lập filter cho Ageing
    ageing_filter = Q()
    if not is_global:
        # Lọc theo khách hàng thuộc BU đó quản lý
        ageing_filter &= Q(customer__business_unit_id=bu_id)
    
    # Tính toán các chỉ số nợ
    rec_data = ReceivablesAgeing.objects.filter(ageing_filter).aggregate(
        total=Sum('total_debt'),
        overdue=Sum('overdue_total'),
        due_now=Sum('due_total'), # Đã thu (đến hạn)
    )
    receivable_total = rec_data['total'] or 0
    receivable_overdue = rec_data['overdue'] or 0
    collection_due_actual = rec_data['due_now'] or 0
    # Thu trong hạn + COD = Tổng nợ - Nợ quá hạn
    collection_in_term_cod = receivable_total - receivable_overdue

    # --- 4. CẬP NHẬT DATABASE (BẢNG THÁNG) ---
    performance, _ = BUPerformance.objects.update_or_create(
        business_unit_id=bu_id,
        month=month,
        year=year,
        defaults={
            'mtd_revenue_actual': rev_actual,
            'mtd_collection_actual': coll_actual,
            'collection_due_actual': collection_due_actual,    # Đã thu đến hạn
            'collection_in_term_cod': collection_in_term_cod, # Thu trong hạn + COD
            'receivable_total': receivable_total,   # Dư nợ cần thu
            'receivable_overdue': receivable_overdue, # Nợ quá hạn
            'inventory_opening_value': inv_data['opening'] or 0,
            'inventory_in_value': inv_data['in_val'] or 0,
            'inventory_out_value': inv_data['out_val'] or 0,
            'inventory_value_actual': inventory_actual,
        }
    )

    # --- 5. TÍNH VÀ CẬP NHẬT CHO TẤT CẢ CÁC NGÀY TRONG THÁNG (DAILY ACTUAL) ---
    # Chạy vòng lặp từ ngày 1 đến target_date
    current_date = datetime(year, month, 1).date()
    
    while current_date <= target_date:
        daily_filter = Q(posting_date=current_date)
        if not is_global:
            daily_filter &= Q(business_unit_id=bu_id)
        
        # Doanh thu ngày (áp dụng customer_rev_filter tương tự như tháng)
        daily_rev = SalesTransaction.objects.filter(daily_filter & customer_rev_filter).aggregate(
            total=Sum('sales_amount')
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
        # Tăng lên 1 ngày
        current_date += timedelta(days=1)
    
    bu_name = "TỔNG CÔNG TY" if is_global else f"Business Unit {bu_id}"
    return f"Updated {bu_name}: Month Rev={rev_actual} | All days up to {target_date} updated"


@shared_task
def sync_warehouse_inventory_data():
    """
    Hàm này quét bảng InventorySummary và cập nhật số tổng vào từng Warehouse tương ứng.
    """
    warehouses = Warehouse.objects.all()
    
    for wh in warehouses:
        # Tính toán từ bảng InventorySummary vừa mới import
        data = InventorySummary.objects.filter(warehouse=wh).aggregate(
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

    return f"Đã cập nhật số liệu tồn kho cho {warehouses.count()} kho."