"""
Script tiêu chuẩn vận hành hằng ngày: Tải báo cáo MISA cho THÁNG HIỆN TẠI,
nạp thay thế dữ liệu riêng của Tháng hiện tại và cập nhật lại KPI cho các BU.

Lợi ích:
- KHÔNG dọn dẹp hay làm ảnh hưởng dữ liệu các tháng cũ.
- KHÔNG reset ID của các bảng (giữ nguyên ID liên tục).
- Tiết kiệm thời gian (chỉ tải và xử lý duy nhất 1 tháng).

Các bước thực hiện:
1. Gọi Playwright tải các báo cáo MISA cho 'Tháng này'.
2. Nạp dữ liệu Excel từ media/auto_imports/ vào DB (xóa thay thế phân đoạn tháng hiện tại).
3. Cập nhật lại KPI (BUPerformance) Tháng hiện tại cho Tổng công ty và 22 Business Units.
4. Đồng bộ tồn kho kho hàng.
"""

import os
import sys
import asyncio
from datetime import datetime

# Setup Django Environment
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'report2026.settings')

import django
django.setup()

from accounting.models import BusinessUnit
from accounting.misa_tasks import run_misa_automation
from accounting.tasks import update_single_bu_performance, auto_import_excel_from_folder, sync_warehouse_inventory_data


def sync_current_month():
    today = datetime.now()
    curr_month = today.month
    curr_year = today.year
    
    print("=" * 80)
    print(f"📅 BẮT ĐẦU TIẾN TRÌNH CẬP NHẬT DỮ LIỆU MISA CHO THÁNG HIỆN TẠI ({curr_month}/{curr_year})")
    print("=" * 80)
    
    # BƯỚC 1: TẢI BÁO CÁO MISA THÁNG HIỆN TẠI
    print(f"\n🌐 [BƯỚC 1] TẢI CÁC BÁO CÁO MISA CHO 'THÁNG NÀY' ({curr_month}/{curr_year})...")
    try:
        download_res = asyncio.run(run_misa_automation(period_option="Tháng này"))
        print(f"  -> Kết quả tải MISA: {download_res}")
    except Exception as e:
        print(f"  ❌ Lỗi khi tải báo cáo MISA Tháng hiện tại: {e}")
        
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
    print(f"🎉 HOÀN THÀNH TIẾN TRÌNH CẬP NHẬT CẬP NHẬT DỮ LIỆU THÁNG HIỆN TẠI ({curr_month}/{curr_year})!")
    print("=" * 80)


if __name__ == '__main__':
    if hasattr(sys.stdout, 'reconfigure'):
        try:
            sys.stdout.reconfigure(encoding='utf-8')
        except Exception:
            pass
    sync_current_month()
