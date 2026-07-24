"""
Script Reconcile YTD Revenue Department by Department (BU Grouping) vs Accountant Report Image
"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), '.venv', 'Lib', 'site-packages'))
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'report2026.settings')
django.setup()

import pandas as pd
from django.db.models import Sum, Q
from accounting.models import SalesTransaction, BusinessUnit

def reconcile_by_department():
    out = ["=== KẾT QUẢ ĐỐI CHẤT DOANH THU THEO TỪNG BỘ PHẬN (GROUP BY BU) TỚI 22/07/2026 ==="]

    excluded_bu_codes = ['ĐTCT']
    excluded_cust_group_codes = ['Internal', 'Nội bộ']

    # Get parent BUs (level 1 BUs)
    parent_bus = BusinessUnit.objects.filter(parent__isnull=True).exclude(code__in=excluded_bu_codes)

    report_image_targets = {
        'Oversea': 20172234903.0,
        'BU_AGRITECH': 3901753505.0,
        'BU_IBIZ VALUE': 3545466920.0,
        'BU_ECO': 5450120321.0,
        'BU_IBIZ PREMIUM': 92912721748.0,
        'BU_MANUFACTURING': 870740120.0,
        'BU_ELEVATOR': 152526645754.0,
    }

    base_qs = SalesTransaction.objects.filter(
        posting_date__year=2026,
        posting_date__lte='2026-07-22'
    ).exclude(
        business_unit__code__in=excluded_bu_codes
    ).exclude(
        customer__group__code__in=excluded_cust_group_codes
    )

    out.append(f"{'Mã Bộ Phận (BU)':<20} | {'Doanh Thu DB (VNĐ)':<20} | {'Báo Cáo Kế Toán':<20} | {'Chênh Lệch (VNĐ)':<20} | {'Tỷ Lệ Khớp':<10}")
    out.append("-" * 100)

    total_db_sum = 0
    total_img_sum = 0

    for bu in parent_bus:
        descendant_ids = bu.get_all_descendant_ids()
        bu_txs = base_qs.filter(business_unit_id__in=descendant_ids)
        db_ytd = float(bu_txs.aggregate(tot=Sum('actual_sales'))['tot'] or 0.0)
        
        img_target = report_image_targets.get(bu.code, 0.0)
        diff = db_ytd - img_target
        match_pct = (db_ytd / img_target * 100) if img_target > 0 else 0.0

        total_db_sum += db_ytd
        total_img_sum += img_target

        out.append(f"{bu.code:<20} | {db_ytd:20,.0f} | {img_target:20,.0f} | {diff:20,.0f} | {match_pct:9.1f}%")

    out.append("-" * 100)
    total_diff = total_db_sum - total_img_sum
    total_pct = (total_db_sum / total_img_sum * 100) if total_img_sum > 0 else 0.0
    out.append(f"{'TỔNG CỘNG (TOTAL)':<20} | {total_db_sum:20,.0f} | {total_img_sum:20,.0f} | {total_diff:20,.0f} | {total_pct:9.1f}%")

    sys.stdout.buffer.write("\n".join(out).encode('utf-8'))

if __name__ == '__main__':
    reconcile_by_department()
