import os
import django
import sys

# Reconfigure stdout to use UTF-8 encoding on Windows terminals
sys.stdout.reconfigure(encoding='utf-8')

# Setup Django Environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'report2026.settings')
django.setup()

from django.conf import settings
from django.db import transaction
from django.utils import timezone
from django.db.models import Q
from tablib import Dataset
from accounting.models import Customer, SalesTransaction, PurchaseDetail, InventorySummary, SupplierDebt, ReceivablesAgeing, AccountDetail, ImportLog
from accounting.resources import CustomerResource, SalesTransactionResource, PurchaseDetailResource, InventorySummaryResource, SupplierDebtResource, ReceivablesAgeingResource, AccountDetailResource
from accounting.tasks import (
    move_to_processed, 
    update_single_bu_performance, 
    detect_period_from_filename, 
    load_and_clean_excel
)

# Mapping Prefix -> Model, Resource
IMPORT_MAP = {
    'KHACH_HANG': {'model': Customer, 'resource': CustomerResource(), 'skip_delete': True},
    'BAN_HANG': {'model': SalesTransaction, 'resource': SalesTransactionResource()},
    'MUA_HANG': {'model': PurchaseDetail, 'resource': PurchaseDetailResource()},
    'TON_KHO': {'model': InventorySummary, 'resource': InventorySummaryResource()},
    'CONG_NO_NCC': {'model': SupplierDebt, 'resource': SupplierDebtResource()},
    'TUOI_NO_KH': {'model': ReceivablesAgeing, 'resource': ReceivablesAgeingResource()},
    'TAI_KHOAN_CT': {'model': AccountDetail, 'resource': AccountDetailResource()},
}

def import_file(file_path):
    if not os.path.exists(file_path):
        print(f"Error: File '{file_path}' does not exist.")
        return
        
    filename = os.path.basename(file_path)
    
    # Identify prefix (longest match)
    matched_prefix = None
    sorted_prefixes = sorted(IMPORT_MAP.keys(), key=len, reverse=True)
    for prefix in sorted_prefixes:
        if filename.lower().startswith(prefix.lower()):
            matched_prefix = prefix
            break
            
    if not matched_prefix:
        print(f"Error: File name '{filename}' does not match any prefix (e.g. BAN_HANG, MUA_HANG, TON_KHO, etc.).")
        return
        
    config = IMPORT_MAP[matched_prefix]
    start_time = timezone.now()
    print(f"[{matched_prefix}] Starting import for file: {filename}")
    
    try:
        import_success = False
        msg = ""
        
        # 1. Nhận diện kỳ báo cáo từ tên file
        start_date, end_date, reporting_period, is_range = detect_period_from_filename(filename, file_path)
        print(f"[{matched_prefix}] Detected period: {start_date} to {end_date}, period: {reporting_period}")
        
        with transaction.atomic():
            deleted_count = 0
            # 2. Xóa phân đoạn dữ liệu cũ
            if not config.get('skip_delete', False):
                is_snapshot = config['model'] in [InventorySummary, SupplierDebt, ReceivablesAgeing]
                if is_snapshot:
                    deleted_count = config['model'].objects.filter(
                        Q(reporting_period=reporting_period) | Q(reporting_period__isnull=True)
                    ).delete()[0]
                else:
                    deleted_count = config['model'].objects.filter(
                        posting_date__range=[start_date, end_date]
                    ).delete()[0]
                print(f"Deleted {deleted_count} old records for model {config['model'].__name__}...")
                
            # 3. Đọc và làm sạch dữ liệu Excel
            headers, cleaned_rows = load_and_clean_excel(file_path, matched_prefix)
            
            # 4. Nạp dữ liệu theo lô (Chunk 1000 dòng)
            chunk_size = 1000
            total_rows = len(cleaned_rows)
            imported_count = 0
            has_error = False
            error_details = []
            
            for i in range(0, total_rows, chunk_size):
                chunk_data = cleaned_rows[i:i+chunk_size]
                chunk_dataset = Dataset()
                chunk_dataset.headers = headers
                for r in chunk_data:
                    chunk_dataset.append([r[h] for h in headers])
                
                result = config['resource'].import_data(
                    chunk_dataset, 
                    dry_run=False, 
                    reporting_period=reporting_period
                )
                
                if result.has_errors():
                    has_error = True
                    if result.base_errors:
                         for error in result.base_errors:
                             error_details.append(f"Lỗi chung: {str(error.error)}")
                    if result.row_errors():
                         for row_num, errors in result.row_errors():
                             for error in errors:
                                 error_details.append(f"Dòng {row_num + i}: {str(error.error)}")
                    break
                else:
                    imported_count += len(chunk_dataset)
            
            if not has_error:
                msg = f"Đã xóa {deleted_count} dòng cũ & Import mới {imported_count} dòng cho kỳ {reporting_period} (chạy thủ công)."
                ImportLog.objects.create(
                    file_name=filename,
                    status='SUCCESS',
                    message=msg,
                    start_time=start_time,
                    end_time=timezone.now()
                )
                import_success = True
            else:
                err_msg = "\n".join(error_details)
                msg = f"Lỗi dữ liệu file.\nChi tiết lỗi:\n{err_msg}"
                print(f"ERROR: {msg}")
                ImportLog.objects.create(
                    file_name=filename,
                    status='ERROR',
                    message=msg,
                    start_time=start_time,
                    end_time=timezone.now()
                )
                
        if import_success:
            print(f"SUCCESS: {msg}")
            
            # Move to success folder (run outside transaction)
            try:
                move_to_processed(file_path, 'success')
                print(f"Moved imported file to processed folder.")
            except Exception as fe:
                print(f"Warning: Failed to move file to success folder: {fe}")
                
            # Recalculate KPIs (run outside transaction)
            try:
                print("Recalculating KPI performance for all Business Units...")
                from accounting.models import BusinessUnit
                update_single_bu_performance(None)
                for bu in BusinessUnit.objects.all():
                    update_single_bu_performance(bu.id)
                print("KPI calculation completed.")
                
                # Tự động đồng bộ tồn kho vào Warehouse sau khi tính KPI
                print("Syncing warehouse inventory data...")
                from accounting.tasks import sync_warehouse_inventory_data
                sync_warehouse_inventory_data()
                print("Warehouse sync completed.")
            except Exception as ke:
                print(f"Warning: Failed to recalculate KPIs or sync Warehouse: {ke}")
                
    except Exception as e:
        msg = f"⚠️ Lỗi hệ thống: {str(e)}"
        print(f"SYSTEM ERROR: {msg}")
        ImportLog.objects.create(
            file_name=filename,
            status='ERROR',
            message=msg,
            start_time=start_time,
            end_time=timezone.now()
        )


if __name__ == '__main__':
    if len(sys.argv) < 2:
        import_dir = os.path.join(settings.BASE_DIR, 'media', 'auto_imports')
        excel_files = []
        if os.path.exists(import_dir):
            for f in os.listdir(import_dir):
                if f.lower().endswith('.xlsx') and not f.startswith('~$'):
                    excel_files.append(f)
                    
        if not excel_files:
            print("Usage: .venv\\Scripts\\python.exe import_specific_file.py <filename>")
            print(f"No excel files found in {import_dir}")
            sys.exit(1)
            
        print("Available excel files in auto_imports directory:")
        for idx, filename in enumerate(excel_files, 1):
            print(f"  [{idx}] {filename}")
        print("\nPlease run the command with a filename. E.g.:")
        print(f"  .venv\\Scripts\\python.exe import_specific_file.py {excel_files[0]}")
    else:
        target_file = sys.argv[1]
        # Resolve path if only filename is provided
        if not os.path.exists(target_file):
            target_file = os.path.join(settings.BASE_DIR, 'media', 'auto_imports', target_file)
            
        import_file(target_file)
