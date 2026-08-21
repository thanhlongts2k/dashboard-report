"""
Script chạy import thủ công một hoặc nhiều file Excel vào hệ thống. (Legacy)

Cách dùng:
    1. Import một file cụ thể:
       .venv\Scripts\python.exe scripts/legacy/run_import.py "<đường_dẫn_file>"

    2. Tự động quét và import toàn bộ các file trong thư mục `media/auto_imports`:
       .venv\Scripts\python.exe scripts/legacy/run_import.py

Ghi chú: Đã có lệnh tiêu chuẩn `python manage.py sync_misa --action=import` và `python import_specific_file.py` thay thế.
"""

import os
import sys

if hasattr(sys.stdout, 'reconfigure'):
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

# Setup Django Environment TRƯỚC KHI import bất kỳ module nào của Django
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, PROJECT_ROOT)

import django
if not django.apps.apps.ready:
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'report2026.settings')
    django.setup()

from import_specific_file import import_file, IMPORT_MAP


def get_priority(file_path):
    """Đảm bảo KHACH_HANG được import trước các file khác để tránh lỗi FK"""
    filename = os.path.basename(file_path).lower()
    if filename.startswith('khach_hang'):
        return 0
    return 1


def main():
    target_files = []

    # TH1: Chạy không tham số hoặc truyền đường dẫn thư mục -> Quét tất cả file hợp lệ
    if len(sys.argv) < 2 or os.path.isdir(sys.argv[1]):
        if len(sys.argv) >= 2 and os.path.isdir(sys.argv[1]):
            scan_dir = sys.argv[1]
        else:
            scan_dir = os.path.join(PROJECT_ROOT, 'media', 'auto_imports')

        scan_dir = os.path.normpath(scan_dir)
        print("=" * 60)
        print(f"🔍 Đang quét thư mục: {scan_dir}")
        print("=" * 60)

        if not os.path.exists(scan_dir):
            print(f"❌ Thư mục không tồn tại: {scan_dir}")
            sys.exit(1)

        # Quét tất cả file .xlsx và .xls
        all_files = []
        for f in os.listdir(scan_dir):
            if f.endswith('.xlsx') or f.endswith('.xls'):
                all_files.append(os.path.join(scan_dir, f))

        # Lọc ra các file có prefix hợp lệ trong IMPORT_MAP
        for fp in all_files:
            filename = os.path.basename(fp)
            for prefix in IMPORT_MAP.keys():
                if filename.lower().startswith(prefix.lower()):
                    target_files.append(fp)
                    break

        if not target_files:
            print("ℹ️ Không tìm thấy file Excel hợp lệ nào có prefix được hỗ trợ.")
            sys.exit(0)

        # Sắp xếp thứ tự ưu tiên (KHACH_HANG lên đầu)
        target_files.sort(key=get_priority)

        print(f"Tìm thấy {len(target_files)} file cần import:")
        for idx, fp in enumerate(target_files, 1):
            print(f"  {idx}. {os.path.basename(fp)}")
        print("=" * 60)

    # TH2: Truyền trực tiếp đường dẫn file
    else:
        file_path = sys.argv[1]
        if not os.path.isabs(file_path):
            file_path = os.path.normpath(os.path.join(PROJECT_ROOT, file_path))
        
        target_files.append(file_path)

    # Thực hiện import tuần tự các file
    success_count = 0
    imported_periods = set()
    from datetime import datetime
    from accounting.tasks import detect_period_from_filename

    for idx, fp in enumerate(target_files, 1):
        filename = os.path.basename(fp)
        print(f"\n[Tiến trình {idx}/{len(target_files)}] Bắt đầu xử lý file: {filename}")
        print("-" * 50)
        
        if not os.path.exists(fp):
            print(f"❌ Không tìm thấy file: {fp}")
            continue

        try:
            start_date, end_date, reporting_period, is_range = detect_period_from_filename(filename, fp)
            # Gọi import_file với recalculate=False để tránh lặp lại tính toán
            status_ok = import_file(fp, recalculate=False)
            if status_ok:
                success_count += 1
                # Lưu lại các kỳ cần tính toán lại
                current_dt = start_date
                while current_dt <= end_date:
                    imported_periods.add((current_dt.month, current_dt.year))
                    if current_dt.month == 12:
                        current_dt = datetime(current_dt.year + 1, 1, 1).date()
                    else:
                        current_dt = datetime(current_dt.year, current_dt.month + 1, 1).date()
            else:
                print(f"❌ Xử lý file {filename} có lỗi xảy ra.")
        except Exception as e:
            print(f"❌ Lỗi khi import file {filename}: {e}")

    # Sau khi tất cả các file đã được import xong, tiến hành tính toán lại KPI cho các kỳ
    if success_count > 0 and imported_periods:
        print("\n" + "=" * 60)
        print("📊 TIẾN HÀNH TÍNH TOÁN LẠI KPI CHO CÁC KỲ ĐÃ NẠP...")
        print("=" * 60)
        from accounting.tasks import update_single_bu_performance, sync_warehouse_inventory_data
        from accounting.models import BusinessUnit
        
        for m, y in sorted(list(imported_periods)):
            print(f"\n👉 Kích hoạt tính toán hiệu suất (KPI) cho kỳ {m}/{y}:")
            try:
                update_single_bu_performance(None, month=m, year=y)
                print("  - Tổng công ty: OK")
                for bu in BusinessUnit.objects.all():
                    update_single_bu_performance(bu.id, month=m, year=y)
                print("  - Tất cả các Business Unit: OK")
            except Exception as celery_err:
                print(f"  ❌ Lỗi khi tính toán KPI kỳ {m}/{y}: {celery_err}")

        # Tự động đồng bộ tồn kho vào Warehouse sau khi tính KPI
        latest_m, latest_y = max(imported_periods)
        latest_period = f"{latest_y:04d}-{latest_m:02d}"
        print(f"\n🔄 Đồng bộ dữ liệu tồn kho cho kỳ {latest_period}...")
        try:
            sync_warehouse_inventory_data(latest_period)
            print("  - Đồng bộ kho: OK")
        except Exception as err:
            print(f"  ❌ Lỗi đồng bộ kho: {err}")

    print("\n" + "=" * 60)
    print(f"🎉 Hoàn thành! Đã import thành công {success_count}/{len(target_files)} file.")
    print("=" * 60)


if __name__ == '__main__':
    main()
