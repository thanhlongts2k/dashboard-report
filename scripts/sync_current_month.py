"""
Script tiêu chuẩn vận hành: Tải báo cáo MISA cho THÁNG HIỆN TẠI (Tháng này),
nạp thay thế dữ liệu riêng của Tháng hiện tại và cập nhật lại KPI cho các BU.

Lợi ích:
- Kế thừa 100% định dạng mẫu báo cáo đã lưu (Saved Reports - Option 2) trên MISA Web.
- KHÔNG dọn dẹp hay làm ảnh hưởng dữ liệu các tháng cũ.
- KHÔNG reset ID của các bảng (giữ nguyên ID liên tục).
- Tiết kiệm thời gian (chỉ tải và xử lý duy nhất Tháng này).

Các bước thực hiện mặc định:
1. Gọi Playwright tải các báo cáo MISA đã lưu cho 'Tháng này'.
2. Nạp dữ liệu Excel từ media/auto_imports/ vào DB (xóa thay thế phân đoạn tháng hiện tại).
3. Cập nhật lại KPI (BUPerformance) Tháng hiện tại cho Tổng công ty và 22 Business Units.
4. Đồng bộ tồn kho kho hàng.

Cách sử dụng:
  # 1. Chạy 1-Click TRỌN GÓI (Tải + Nạp CSDL + Tính toàn bộ KPI Tháng này + Tồn kho):
  python scripts/sync_current_month.py

  # 2. Chỉ tính toán lại KPI Tháng này từ dữ liệu đã có trong DB:
  python scripts/sync_current_month.py --only-kpi

  # 3. Chỉ tải các file Excel báo cáo MISA Tháng này về media/auto_imports/:
  python scripts/sync_current_month.py --only-download

  # 4. Chỉ nạp Excel từ media/auto_imports/ vào DB và tính KPI Tháng này:
  python scripts/sync_current_month.py --only-import

  # 5. Chỉ tải và xử lý riêng 1 loại báo cáo cụ thể (ví dụ: BAN_HANG, TON_KHO...):
  python scripts/sync_current_month.py --prefix BAN_HANG
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


def sync_current_month(only_kpi=False, only_download=False, only_import=False, prefix_filter=None):
    today = datetime.now()
    curr_month = today.month
    curr_year = today.year
    
    print("=" * 80)
    print(f"📅 BẮT ĐẦU TIẾN TRÌNH ĐỒNG BỘ DỮ LIỆU MISA CHO THÁNG HIỆN TẠI ({curr_month}/{curr_year})")
    print("=" * 80)
    
    # KỊCH BẢN CHỈ TÍNH KPI
    if only_kpi:
        print(f"\n📊 CHẾ ĐỘ: CHỈ TÍNH TOÁN LẠI KPI CHO THÁNG HIỆN TẠI ({curr_month}/{curr_year})...")
        try:
            msg_corp = update_single_bu_performance(bu_id=None, month=curr_month, year=curr_year)
            print(f"  - Tổng công ty (Th{curr_month}/{curr_year}): {msg_corp}")
            for bu in BusinessUnit.objects.all():
                msg_bu = update_single_bu_performance(bu_id=bu.id, month=curr_month, year=curr_year)
                print(f"  - BU {bu.code} (Th{curr_month}/{curr_year}): {msg_bu}")
            print(f"  ✅ Hoàn tất tính toán KPI Tháng {curr_month}/{curr_year}!")
        except Exception as e:
            print(f"  ❌ Lỗi khi tính KPI Tháng {curr_month}/{curr_year}: {e}")
        print("=" * 80)
        return

    # BƯỚC 1: TẢI BÁO CÁO MISA THÁNG HIỆN TẠI (nếu không chọn only_import)
    if not only_import:
        filter_str = f" [Bộ lọc prefix: {prefix_filter}]" if prefix_filter else ""
        print(f"\n🌐 [BƯỚC 1] TẢI CÁC BÁO CÁO MISA ĐÃ LƯU CHO 'THÁNG NÀY' ({curr_month}/{curr_year}){filter_str}...")
        try:
            download_res = asyncio.run(run_misa_automation(
                period_option="Tháng này",
                prefix_filter=prefix_filter,
                use_saved_reports=True
            ))
            print(f"  -> Kết quả tải MISA: {download_res}")
        except Exception as e:
            print(f"  ❌ Lỗi khi tải báo cáo MISA Tháng hiện tại: {e}")
            if only_download:
                return

    if only_download:
        print("\n💡 Đã hoàn tất tải các tệp Excel về thư mục 'media/auto_imports/'.")
        print("💡 Để tự động nạp vào DB và cập nhật KPI, hãy chạy lệnh không kèm cờ --only-download hoặc thêm --only-import.")
        print("=" * 80)
        return

    # BƯỚC 2: NẠP EXCEL VÀ THAY THẾ DỮ LIỆU THÁNG HIỆN TẠI
    print(f"\n📥 [BƯỚC 2] NẠP DỮ LIỆU EXCEL VÀO DATABASE (THAY THẾ THÁNG {curr_month}/{curr_year})...")
    try:
        import_res = auto_import_excel_from_folder()
        print(f"  -> Kết quả nạp Excel: {import_res}")
    except Exception as e:
        print(f"  ❌ Lỗi khi nạp dữ liệu Excel: {e}")

    # BƯỚC 3: TÍNH TOÁN LẠI KPI THÁNG HIỆN TẠI
    print(f"\n📊 [BƯỚC 3] TÍNH TOÁN LẠI KPI CHO THÁNG HIỆN TẠI ({curr_month}/{curr_year})...")
    try:
        # Tính cho Tổng công ty
        msg_corp = update_single_bu_performance(bu_id=None, month=curr_month, year=curr_year)
        print(f"  - Tổng công ty (Th{curr_month}/{curr_year}): {msg_corp}")
        
        # Tính cho từng BU
        for bu in BusinessUnit.objects.all():
            msg_bu = update_single_bu_performance(bu_id=bu.id, month=curr_month, year=curr_year)
            print(f"  - BU {bu.code} (Th{curr_month}/{curr_year}): {msg_bu}")
        print(f"  ✅ Hoàn tất tính KPI Tháng {curr_month}/{curr_year}.")
    except Exception as e:
        print(f"  ❌ Lỗi khi tính KPI Tháng {curr_month}/{curr_year}: {e}")

    # BƯỚC 4: ĐỒNG BỘ TỒN KHO KHO HÀNG
    reporting_period = f"{curr_year:04d}-{curr_month:02d}"
    print(f"\n🔄 [BƯỚC 4] ĐỒNG BỘ TỒN KHO KHO HÀNG CHO KỲ {reporting_period}...")
    try:
        sync_warehouse_inventory_data(reporting_period)
        print("  - Đồng bộ tồn kho kho: OK")
    except Exception as e:
        print(f"  ❌ Lỗi đồng bộ tồn kho kho: {e}")

    print("\n" + "=" * 80)
    print(f"🎉 HOÀN THÀNH TIẾN TRÌNH ĐỒNG BỘ DỮ LIỆU THÁNG HIỆN TẠI ({curr_month}/{curr_year})!")
    print("=" * 80)


def main():
    if hasattr(sys.stdout, 'reconfigure'):
        try:
            sys.stdout.reconfigure(encoding='utf-8')
        except Exception:
            pass

    parser = argparse.ArgumentParser(
        description="Script 1-Click: Tải báo cáo MISA cho THÁNG HIỆN TẠI (Tháng này), nạp CSDL và cập nhật KPI Dashboard."
    )
    parser.add_argument(
        '--only-kpi',
        action='store_true',
        help='Chỉ tính toán lại KPI (BUPerformance + Global) cho Tháng này từ dữ liệu đã có trong DB.'
    )
    parser.add_argument(
        '--only-download',
        action='store_true',
        help='Chỉ tải các tệp Excel báo cáo MISA Tháng này về media/auto_imports/ (không import DB).'
    )
    parser.add_argument(
        '--only-import',
        action='store_true',
        help='Chỉ nạp các tệp Excel từ media/auto_imports/ vào DB và tính lại KPI Tháng này.'
    )
    parser.add_argument(
        '--prefix',
        type=str,
        default=None,
        help='Lọc chỉ tải và xử lý báo cáo có tiền tố cụ thể (ví dụ: BAN_HANG, TON_KHO, SO_DU_NH...).'
    )

    args = parser.parse_args()
    sync_current_month(
        only_kpi=args.only_kpi,
        only_download=args.only_download,
        only_import=args.only_import,
        prefix_filter=args.prefix
    )


if __name__ == '__main__':
    main()
