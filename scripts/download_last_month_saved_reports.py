"""
Script 1-Click: Tải trọn gói các Báo cáo MISA đã lưu (Saved Reports - Option 2) cho kỳ 'THÁNG TRƯỚC'
(hoặc kỳ tùy chỉnh), kết hợp tùy chọn tự động Import và tính toán lại KPI Dashboard.

Lợi ích:
- Kế thừa 100% định dạng mẫu chuẩn đã lưu trên MISA (cột, phân nhóm, mã nhân viên, BU).
- Tự động mở modal tham số và đổi Kỳ báo cáo sang 'Tháng trước'.
- Tùy chọn --auto-import để nạp dữ liệu và tính lại KPI cho Tháng trước mà không ảnh hưởng các tháng khác.

Cách sử dụng:
  # 1. Chỉ tải file Excel báo cáo Tháng trước về media/auto_imports/:
  python scripts/download_last_month_saved_reports.py

  # 2. Tải file Excel và tự động Import + Tính KPI Tháng trước:
  python scripts/download_last_month_saved_reports.py --auto-import

  # 3. Tải cho kỳ tùy chỉnh (ví dụ: 'Tháng 7', 'Tháng 07', 'Quý trước'...):
  python scripts/download_last_month_saved_reports.py --period "Tháng 7" --auto-import
"""

import os
import sys
import argparse
import asyncio
from datetime import datetime

# Setup Django Environment
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'report2026.settings')

import django
django.setup()

from accounting.models import BusinessUnit
from accounting.misa.automation import run_misa_automation
from accounting.tasks import update_single_bu_performance, auto_import_excel_from_folder, sync_warehouse_inventory_data


def get_last_month_and_year():
    today = datetime.now()
    if today.month == 1:
        return 12, today.year - 1
    else:
        return today.month - 1, today.year


def run_download_and_sync_last_month(period_str="Tháng trước", auto_import=False, prefix_filter=None):
    last_m, last_y = get_last_month_and_year()
    
    print("=" * 80)
    print(f"🚀 TIẾN TRÌNH TẢI BÁO CÁO MISA ĐÃ LƯU CHO KỲ: '{period_str.upper()}' (Tháng tham chiếu: {last_m}/{last_y})")
    print("=" * 80)
    
    # BƯỚC 1: TẢI BÁO CÁO MISA THEO MẪU ĐÃ LƯU
    print(f"\n🌐 [BƯỚC 1] Đang mở danh sách Báo cáo đã lưu trên MISA và đổi kỳ sang '{period_str}'...")
    try:
        download_res = asyncio.run(run_misa_automation(
            period_option=period_str,
            prefix_filter=prefix_filter,
            use_saved_reports=True
        ))
        print(f"  -> Kết quả tải MISA: {download_res}")
    except Exception as e:
        print(f"  ❌ Lỗi khi tải báo cáo MISA: {e}")
        return False
        
    if not auto_import:
        print("\n💡 File Excel đã được tải về thư mục 'media/auto_imports/'.")
        print("💡 Để tự động nạp vào DB và tính toán KPI, hãy thêm cờ: --auto-import")
        print("=" * 80)
        return True

    # BƯỚC 2: NẠP EXCEL VÀO DATABASE CHO THÁNG TRƯỚC
    print(f"\n📥 [BƯỚC 2] NẠP DỮ LIỆU EXCEL VÀO DATABASE (THAY THẾ THÁNG {last_m}/{last_y})...")
    try:
        import_res = auto_import_excel_from_folder()
        print(f"  -> Kết quả nạp Excel: {import_res}")
    except Exception as e:
        print(f"  ❌ Lỗi khi nạp dữ liệu Excel: {e}")
        return False

    # BƯỚC 3: TÍNH TOÁN LẠI KPI CHO THÁNG TRƯỚC
    print(f"\n📊 [BƯỚC 3] TÍNH TOÁN LẠI KPI CHO THÁNG {last_m}/{last_y}...")
    try:
        # Tính cho Tổng công ty
        msg_corp = update_single_bu_performance(bu_id=None, month=last_m, year=last_y)
        print(f"  - Tổng công ty (Th{last_m}/{last_y}): {msg_corp}")
        
        # Tính cho từng BU
        for bu in BusinessUnit.objects.all():
            msg_bu = update_single_bu_performance(bu_id=bu.id, month=last_m, year=last_y)
            print(f"  - BU {bu.code} (Th{last_m}/{last_y}): {msg_bu}")
        print(f"  ✅ Hoàn tất tính KPI Tháng {last_m}/{last_y}.")
    except Exception as e:
        print(f"  ❌ Lỗi khi tính KPI Tháng {last_m}/{last_y}: {e}")

    # BƯỚC 4: ĐỒNG BỘ TỒN KHO KHO HÀNG
    reporting_period = f"{last_y:04d}-{last_m:02d}"
    print(f"\n🔄 [BƯỚC 4] ĐỒNG BỘ TỒN KHO KHO HÀNG CHO KỲ {reporting_period}...")
    try:
        sync_warehouse_inventory_data(reporting_period)
        print("  - Đồng bộ tồn kho kho: OK")
    except Exception as e:
        print(f"  ❌ Lỗi đồng bộ tồn kho kho: {e}")

    print("\n" + "=" * 80)
    print(f"🎉 HOÀN THÀNH TIẾN TRÌNH TẢI & ĐỒNG BỘ DỮ LIỆU CHO KỲ '{period_str}' (Tháng {last_m}/{last_y})!")
    print("=" * 80)
    return True


def main():
    if hasattr(sys.stdout, 'reconfigure'):
        try:
            sys.stdout.reconfigure(encoding='utf-8')
        except Exception:
            pass

    parser = argparse.ArgumentParser(
        description="Script 1-Click tải các báo cáo MISA đã lưu cho 'Tháng trước' (hoặc kỳ tùy chỉnh) và tùy chọn nạp DB."
    )
    parser.add_argument(
        '--period',
        type=str,
        default="Tháng trước",
        help='Kỳ báo cáo cần tải (mặc định: "Tháng trước", có thể truyền "Tháng 7", "Tháng 07", "Quý trước"...)'
    )
    parser.add_argument(
        '--auto-import',
        action='store_true',
        help='Tự động nạp dữ liệu Excel vừa tải vào DB và tính toán lại KPI Dashboard cho tháng tương ứng'
    )
    parser.add_argument(
        '--prefix',
        type=str,
        default=None,
        help='Chỉ định tải riêng 1 loại báo cáo (ví dụ: BAN_HANG, TON_KHO...). Mặc định tải tất cả.'
    )

    args = parser.parse_args()
    run_download_and_sync_last_month(
        period_str=args.period,
        auto_import=args.auto_import,
        prefix_filter=args.prefix
    )


if __name__ == '__main__':
    main()
