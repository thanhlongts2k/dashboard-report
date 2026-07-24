"""
Script tự động làm sạch (Clear Data) các giao dịch và chạy vòng lặp nạp lại dữ liệu báo cáo
từ Tháng 1 đến Tháng 7 năm 2026 từ MISA.

Các bước thực hiện:
1. Xóa dữ liệu phát sinh trong database (SalesTransaction, PurchaseDetail, AccountDetail,
   ReceivablesAgeing, SupplierDebt, InventorySummary, BankBalance, BUPerformanceDaily, BUPerformance).
2. Chạy vòng lặp từ Tháng 1 đến Tháng 7:
   - Tải báo cáo MISA theo kỳ 'Tháng {m}'
   - Nạp dữ liệu Excel từ media/auto_imports/ vào DB
   - Tính toán lại KPI (Doanh thu, OPEX, Tiền cuối kỳ...) cho Tháng {m}/2026
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

from django.conf import settings
from accounting.models import (
    SalesTransaction, PurchaseDetail, AccountDetail, ReceivablesAgeing,
    SupplierDebt, InventorySummary, BankBalance, BUPerformance, BUPerformanceDaily,
    BusinessUnit
)
from accounting.misa_tasks import run_misa_automation
from accounting.tasks import update_single_bu_performance, auto_import_excel_from_folder, sync_warehouse_inventory_data


def clear_transaction_data():
    print("=" * 80)
    print("🧹 BẮT ĐẦU DỌN SẠCH DỮ LIỆU CÁC BẢNG GIAO DỊCH VÀ KPI (CLEAR DATA)...")
    print("=" * 80)
    
    models_to_clear = [
        ("Chi tiết bán hàng (SalesTransaction)", SalesTransaction),
        ("Sổ chi tiết mua hàng (PurchaseDetail)", PurchaseDetail),
        ("Sổ chi tiết tài khoản (AccountDetail)", AccountDetail),
        ("Chi tiết tuổi nợ (ReceivablesAgeing)", ReceivablesAgeing),
        ("Công nợ nhà cung cấp (SupplierDebt)", SupplierDebt),
        ("Tồn kho (InventorySummary)", InventorySummary),
        ("Số dư ngân hàng (BankBalance)", BankBalance),
        ("KPI ngày (BUPerformanceDaily)", BUPerformanceDaily),
        ("KPI tháng (BUPerformance)", BUPerformance),
    ]
    
    for name, model in models_to_clear:
        count, _ = model.objects.all().delete()
        print(f"  - Đã xóa {count} bản ghi trong {name}")
        
    print("✅ Đã dọn sạch dữ liệu giao dịch và KPI thành công!\n")


def reimport_all_months():
    print("=" * 80)
    print("🚀 BẮT ĐẦU TIẾN TRÌNH TẢI VÀ NẠP LẠI BÁO CÁO TỪ THÁNG 1 ĐẾN THÁNG 7 / 2026")
    print("=" * 80)
    
    # 1. Clear data trước khi nạp lại
    clear_transaction_data()
    
    # 2. Vòng lặp từ tháng 1 đến tháng 7
    for m in range(1, 8):
        month_suffix = f"2026{m:02d}"
        period_str = f"Tháng {m}"
        print("\n" + "=" * 60)
        print(f"📅 [BƯỚC 1] BẮT ĐẦU TẢI BÁO CÁO MISA CHO {period_str.upper()} / 2026 (File: <PREFIX>_{month_suffix}.xlsx)...")
        print("=" * 60)
        
        try:
            # Chạy automation tải báo cáo MISA với tham số period_option = 'Tháng m' và tên file theo tháng
            result_msg = asyncio.run(run_misa_automation(period_option=period_str, custom_period_suffix=month_suffix))
            print(f"  -> Kết quả tải MISA {period_str}: {result_msg}")
        except Exception as e:
            print(f"  ❌ Lỗi khi tải báo cáo MISA cho {period_str}: {e}")
            
        print(f"\n📥 [BƯỚC 2] NẠP DỮ LIỆU EXCEL {period_str.upper()} VÀO DATABASE...")
        try:
            import_msg = auto_import_excel_from_folder()
            print(f"  -> Kết quả nạp Excel {period_str}: {import_msg}")
        except Exception as e:
            print(f"  ❌ Lỗi khi nạp Excel cho {period_str}: {e}")
            
        print(f"\n📊 [BƯỚC 3] TÍNH TOÁN LẠI KPI CHO THÁNG {m}/2026...")
        try:
            # Tính cho Tổng công ty
            msg_corp = update_single_bu_performance(bu_id=None, month=m, year=2026)
            print(f"  - Tổng công ty (Th{m}/2026): {msg_corp}")
            
            # Tính cho từng BU
            for bu in BusinessUnit.objects.all():
                msg_bu = update_single_bu_performance(bu_id=bu.id, month=m, year=2026)
                print(f"  - BU {bu.code} (Th{m}/2026): {msg_bu}")
        except Exception as e:
            print(f"  ❌ Lỗi khi tính toán KPI cho {period_str}: {e}")
            
        print(f"✅ Hoàn thành xử lý {period_str} / 2026.")

    # 3. Đồng bộ tồn kho sau cùng cho kỳ 2026-07
    print("\n" + "=" * 80)
    print("🔄 BẮT ĐẦU ĐỒNG BỘ TỒN KHO CUỐI CÙNG CHO KỲ 2026-07...")
    print("=" * 80)
    try:
        sync_warehouse_inventory_data('2026-07')
        print("  - Đồng bộ tồn kho kho: OK")
    except Exception as e:
        print(f"  ❌ Lỗi đồng bộ tồn kho kho: {e}")

    print("\n" + "=" * 80)
    print("🎉 HOÀN THÀNH TOÀN BỘ TIẾN TRÌNH NẠP LẠI DỮ LIỆU TỪ THÁNG 1 ĐẾN THÁNG 7 / 2026!")
    print("=" * 80)


if __name__ == '__main__':
    sys.stdout.reconfigure(encoding='utf-8')
    reimport_all_months()
