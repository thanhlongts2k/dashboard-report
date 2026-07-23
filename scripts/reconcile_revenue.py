"""
Script đối soát Doanh thu MTD / YTD giữa Báo cáo Kế toán và Database BUPerformance
"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), '.venv', 'Lib', 'site-packages'))
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'report2026.settings')
django.setup()

from accounting.models import BUPerformance

def run_reconciliation(month=7, year=2026):
    snapshot_list = BUPerformance.objects.filter(month=month, year=year).select_related('business_unit').order_by('-mtd_revenue_actual')
    print(f"=== SNAPSHOT DOANH THU & THỰC THU THÁNG {month}/{year} ===")
    for p in snapshot_list:
        bu_code = p.business_unit.code if p.business_unit else "TOTAL_CORP"
        bu_name = p.business_unit.name if p.business_unit else "TỔNG TOÀN CÔNG TY"
        print(f"[{bu_code:<18}]: DT MTD = {p.mtd_revenue_actual:15,.0f} | DT YTD = {p.ytd_revenue_actual:15,.0f} | Thu MTD = {p.mtd_collection_actual:15,.0f}")

if __name__ == '__main__':
    run_reconciliation()
