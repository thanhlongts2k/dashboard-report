"""
Script tự động dọn sạch CSDL (Clear Data), nạp trực tiếp toàn bộ các file Excel
báo cáo MISA đã tải về trong media/auto_imports/ (và media/auto_imports/success/)
theo tuần tự Tháng 1 đến Tháng 7/2026 và tính toán lại toàn bộ KPI (BUPerformance)
mà KHÔNG CẦN phải chạy lại Playwright tải từ MISA.

Các bước thực hiện:
1. Xóa toàn bộ dữ liệu giao dịch cũ trong database.
2. Quét và chuyển tất cả các file Excel đã tải về (bao gồm trong media/auto_imports/success/)
   quay lại folder media/auto_imports/ để sẵn sàng nạp.
3. Kích hoạt auto_import_excel_from_folder() để import tất cả dữ liệu giao dịch vào DB.
4. Chạy vòng lặp tính toán lại KPI (BUPerformance) tuần tự từ Tháng 1 đến Tháng 7 cho
   Tổng công ty và 22 Business Units.
5. Đồng bộ kho hàng cuối cùng cho kỳ 2026-07.
"""

import os
import sys
import shutil
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


def prepare_excel_files():
    """
    Thu gom tất cả các file Excel báo cáo từ folder success/ và các subfolder
    quay trở lại media/auto_imports/ để nạp lại vào CSDL.
    """
    auto_imports_dir = os.path.join(settings.BASE_DIR, 'media', 'auto_imports')
    success_dir = os.path.join(auto_imports_dir, 'success')
    
    print("=" * 80)
    print("📁 KIỂM TRA VÀ THU GOM TẤT CẢ FILE EXCEL VỀ FOLDER MEDIA/AUTO_IMPORTS/...")
    print("=" * 80)
    
    if os.path.exists(success_dir):
        # Quét tất cả file .xlsx trong success/ và các thư mục con (202601, 202602...)
        moved_count = 0
        for root, dirs, files in os.walk(success_dir):
            for file in files:
                if file.endswith('.xlsx') and not file.startswith('~$'):
                    src = os.path.join(root, file)
                    dst = os.path.join(auto_imports_dir, file)
                    try:
                        shutil.move(src, dst)
                        moved_count += 1
                    except Exception as e:
                        print(f"  - Không thể di chuyển {file}: {e}")
        print(f"  -> Đã di chuyển {moved_count} file Excel từ folder success/ quay lại auto_imports/.")
        
    # Đếm tổng số file Excel đang có trong auto_imports_dir
    files_in_imports = [f for f in os.listdir(auto_imports_dir) if f.endswith('.xlsx') and not f.startswith('~$')]
    print(f"  -> Tổng số file Excel sẵn sàng nạp: {len(files_in_imports)} file.")
    for f in sorted(files_in_imports):
        print(f"     • {f}")
    print()


def import_and_calculate_all(skip_clear=False):
    print("=" * 80)
    print("🚀 BẮT ĐẦU TIẾN TRÌNH NẠP FILE EXCEL VÀ TÍNH TOÁN KPI TỪ THÁNG 1 ĐẾN THÁNG 7 / 2026")
    print("=" * 80)
    
    # 1. Clear data cũ (nếu không truyền cờ --skip-clear)
    if not skip_clear:
        clear_transaction_data()
    else:
        print("ℹ️ Đã bỏ qua bước Clear Data (sử dụng dữ liệu CSDL vừa dọn/reset ở Bước 1).\n")
    
    # 2. Gom tất cả file Excel về folder auto_imports/
    prepare_excel_files()
    
    # 3. Nạp tất cả file Excel vào CSDL
    print("=" * 80)
    print("📥 BẮT ĐẦU NẠP DỮ LIỆU EXCEL VÀO DATABASE...")
    print("=" * 80)
    try:
        import_result = auto_import_excel_from_folder()
        print(f"  -> Kết quả import: {import_result}\n")
    except Exception as e:
        print(f"  ❌ Lỗi khi nạp dữ liệu Excel: {e}\n")

    # 4. Tính toán lại KPI tuần tự từ Tháng 1 đến Tháng 7
    print("=" * 80)
    print("📊 BẮT ĐẦU TÍNH TOÁN LẠI KPI (BUPERFORMANCE) THEO TUẦN TỰ THÁNG 1 -> 7...")
    print("=" * 80)
    
    for m in range(1, 8):
        print(f"\n--- TÍNH KPI THÁNG {m}/2026 ---")
        try:
            # Tính cho Tổng công ty
            msg_corp = update_single_bu_performance(bu_id=None, month=m, year=2026)
            print(f"  - Tổng công ty (Th{m}/2026): {msg_corp}")
            
            # Tính cho từng BU
            for bu in BusinessUnit.objects.all():
                msg_bu = update_single_bu_performance(bu_id=bu.id, month=m, year=2026)
                print(f"  - BU {bu.code} (Th{m}/2026): {msg_bu}")
            print(f"  ✅ Hoàn tất tính KPI Tháng {m}/2026.")
        except Exception as e:
            print(f"  ❌ Lỗi khi tính KPI Tháng {m}/2026: {e}")

    # 5. Đồng bộ kho hàng cuối cùng cho kỳ 2026-07
    print("\n" + "=" * 80)
    print("🔄 BẮT ĐẦU ĐỒNG BỘ TỒN KHO CUỐI CÙNG CHO KỲ 2026-07...")
    print("=" * 80)
    try:
        sync_warehouse_inventory_data('2026-07')
        print("  - Đồng bộ tồn kho kho: OK")
    except Exception as e:
        print(f"  ❌ Lỗi đồng bộ tồn kho kho: {e}")

    print("\n" + "=" * 80)
    print("🎉 HOÀN THÀNH TIẾN TRÌNH NẠP EXCEL VÀ CẬP NHẬT KPI TỪ THÁNG 1 ĐẾN THÁNG 7 / 2026!")
    print("=" * 80)


if __name__ == '__main__':
    sys.stdout.reconfigure(encoding='utf-8')
    skip_clear_flag = '--skip-clear' in sys.argv
    import_and_calculate_all(skip_clear=skip_clear_flag)
