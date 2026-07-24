"""
Script Audit All 8 Financial Sections (Database vs Accountant Report)
"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), '.venv', 'Lib', 'site-packages'))
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'report2026.settings')
django.setup()

from accounting.models import BUPerformance, InventorySummary, SupplierDebt, ReceivablesAgeing
from django.db.models import Sum

def run_audit():
    glob = BUPerformance.objects.filter(business_unit__isnull=True, month=7, year=2026).first()

    inv_tot = InventorySummary.objects.filter(reporting_period='2026-07').aggregate(total=Sum('closing_value'))['total'] or 0
    sup_debt_tot = SupplierDebt.objects.filter(reporting_period='2026-07').aggregate(total=Sum('closing_credit'))['total'] or 0
    rec_tot = ReceivablesAgeing.objects.filter(reporting_period='2026-07').aggregate(
        total=Sum('total_debt'), due=Sum('due_total'), overdue=Sum('overdue_total')
    )

    rev_act = glob.mtd_revenue_actual if glob and glob.mtd_revenue_actual else 0
    coll_act = glob.mtd_collection_actual if glob and glob.mtd_collection_actual else 0
    inv_act = glob.inventory_value_actual if glob and glob.inventory_value_actual else 0
    cash_act = glob.cash_balance_actual if glob and glob.cash_balance_actual else 0
    bank_act = glob.bank_debt_actual if glob and glob.bank_debt_actual else 0
    opex_act = glob.opex_actual if glob and glob.opex_actual else 0

    out = ["========================================================================================="]
    out.append("📊 BÁO CÁO RÀ SOÁT TOÀN BỘ 8 MỤC TÀI CHÍNH TỔNG CÔNG TY (DB VS BÁO CÁO KẾ TOÁN)")
    out.append("=========================================================================================")
    out.append(f"1. Doanh thu (MTD Exclude Oversea): DB = {rev_act:18,.0f} VNĐ | Kế toán = 23,733,391,374 VNĐ")
    out.append(f"2. Tiền thu (MTD Collection)      : DB = {coll_act:18,.0f} VNĐ | Kế toán = 35,463,556,589 VNĐ")
    out.append(f"3. Tồn kho (Inventory Value)      : DB = {inv_act:18,.0f} VNĐ | Kế toán = 143,267,000,000 VNĐ (Thực tế kho = {inv_tot:,.0f} VNĐ)")
    out.append(f"4. Dư nợ Phải trả NCC (Supplier)  : DB = {sup_debt_tot:18,.0f} VNĐ | Kế toán = 186,854,000,000 VNĐ")
    out.append(f"5. Dư nợ Phải thu KH (Receivables): DB Total = {rec_tot.get('total') or 0:18,.0f} VNĐ (Trong hạn: {rec_tot.get('due') or 0:,.0f} | Quá hạn: {rec_tot.get('overdue') or 0:,.0f})")
    out.append(f"6. Quỹ tiền mặt (Cash Balance)   : DB = {cash_act:18,.0f} VNĐ | Kế toán = 444,000,000 VNĐ")
    out.append(f"7. Dư nợ Vay Ngân hàng (Bank Debt): DB = {bank_act:18,.0f} VNĐ | Kế toán = 127,117,000,000 VNĐ")
    out.append(f"8. Chi phí Quản lý OPEX (Actual)  : DB = {opex_act:18,.0f} VNĐ | Kế toán Target Plan = 4,851,250,000 VNĐ")
    out.append("=========================================================================================")

    sys.stdout.buffer.write("\n".join(out).encode('utf-8'))

if __name__ == '__main__':
    run_audit()
