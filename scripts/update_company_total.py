"""
Script Cập nhật Số liệu Tổng Toàn Công ty (TOTAL_CORP) từ các BU con linh hoạt
"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), '.venv', 'Lib', 'site-packages'))
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'report2026.settings')
django.setup()

from accounting.models import BUPerformance, BusinessUnit
from accounting.tasks import update_single_bu_performance
from datetime import datetime

def update_company_totals(month=None, year=None):
    today = datetime.now()
    month = month or today.month
    year = year or today.year

    out = [f"=== KÍCH HOẠT CẬP NHẬT SỐ LIỆU TỔNG TOÀN CÔNG TY (THÁNG {month}/{year}) ==="]
    
    # 1. Cập nhật tuần tự từ tháng 1 đến tháng chỉ định cho các BU cấp cao (tự động cộng dồn BU con)
    top_bus = list(BusinessUnit.objects.filter(parent__isnull=True))
    
    for m in range(1, month + 1):
        for bu in top_bus:
            update_single_bu_performance(bu.id, month=m, year=year)
        update_single_bu_performance(None, month=m, year=year)

    tot = BUPerformance.objects.filter(business_unit__isnull=True, month=month, year=year).first()
    if tot:
        rev = tot.mtd_revenue_actual or 0
        coll = tot.mtd_collection_actual or 0
        inv = tot.inventory_value_actual or 0
        cash = tot.cash_balance_actual or 0
        bank = tot.bank_debt_actual or 0
        opex = tot.opex_actual or 0
        opex_p = tot.opex_plan or 0

        out.append(f"✅ ĐÃ CẬP NHẬT THÀNH CÔNG SỐ LIỆU TỔNG CÔNG TY THÁNG {month}/{year}:")
        out.append(f"   - Doanh thu MTD   : {rev:18,.0f} VNĐ")
        out.append(f"   - Thu tiền MTD    : {coll:18,.0f} VNĐ")
        out.append(f"   - Chi phí VH MTD  : {opex:18,.0f} VNĐ (Kế hoạch: {opex_p:,.0f} VNĐ)")
        out.append(f"   - Tồn kho Cuối    : {inv:18,.0f} VNĐ")
        out.append(f"   - Tiền Cuối kỳ    : {cash:18,.0f} VNĐ")
        out.append(f"   - Nợ ngân hàng    : {bank:18,.0f} VNĐ")

    sys.stdout.buffer.write("\n".join(out).encode('utf-8'))

if __name__ == '__main__':
    m = int(sys.argv[1]) if len(sys.argv) > 1 else datetime.now().month
    y = int(sys.argv[2]) if len(sys.argv) > 2 else datetime.now().year
    update_company_totals(month=m, year=y)
