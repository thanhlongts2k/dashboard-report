"""
Script độc lập [BƯỚC 1]: Dọn dẹp sạch dữ liệu phát sinh (Clear Data)
và Reset toàn bộ chuỗi ID tự tăng (Primary Key Sequences) về 1 trong CSDL PostgreSQL.

Các bảng được làm sạch và reset ID:
- SalesTransaction (Chi tiết bán hàng)
- PurchaseDetail (Sổ chi tiết mua hàng)
- AccountDetail (Sổ chi tiết tài khoản)
- ReceivablesAgeing (Chi tiết tuổi nợ)
- SupplierDebt (Công nợ nhà cung cấp)
- InventorySummary (Tồn kho)
- BankBalance (Số dư ngân hàng)
- BUPerformanceDaily (KPI ngày)
- BUPerformance (KPI tháng)
"""

import os
import sys

# Setup Django Environment
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'report2026.settings')

import django
django.setup()

from django.db import connection, transaction
from accounting.models import (
    SalesTransaction, PurchaseDetail, AccountDetail, ReceivablesAgeing,
    SupplierDebt, InventorySummary, BankBalance, BUPerformance, BUPerformanceDaily
)


def clear_and_reset_db():
    print("=" * 80)
    print("🧹 [BƯỚC 1] BẮT ĐẦU DỌN SẠCH DỮ LIỆU & RESET ID CÁC BẢNG VỀ 1...")
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
    
    with connection.cursor() as cursor:
        for name, model in models_to_clear:
            table_name = model._meta.db_table
            try:
                # Xóa dữ liệu và Reset ID tự tăng về 1 trong PostgreSQL
                cursor.execute(f"TRUNCATE TABLE \"{table_name}\" RESTART IDENTITY CASCADE;")
                print(f"  - Đã XÓA và RESET ID về 1 cho bảng {name} (table: {table_name})")
            except Exception as e:
                # Fallback nếu không phải PostgreSQL (ví dụ SQLite)
                count, _ = model.objects.all().delete()
                print(f"  - Đã xóa {count} bản ghi trong {name} (Fallback delete)")
                
    print("\n✅ ĐÃ DỌN TẠCH DỮ LIỆU VÀ RESET TOÀN BỘ ID BẢNG VỀ 1 THÀNH CÔNG!")
    print("👉 Anh có thể chuyển sang [BƯỚC 2] để nạp lại dữ liệu.")
    print("=" * 80)


if __name__ == '__main__':
    if hasattr(sys.stdout, 'reconfigure'):
        try:
            sys.stdout.reconfigure(encoding='utf-8')
        except Exception:
            pass
    clear_and_reset_db()
