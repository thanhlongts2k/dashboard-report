"""
Script nạp Dữ liệu Mục tiêu Kế hoạch (BUTargetPlan) Tháng 7/2026 từ Báo cáo Kế toán
"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), '.venv', 'Lib', 'site-packages'))
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'report2026.settings')
django.setup()

from accounting.models import BusinessUnit, BUTargetPlan
from accounting.tasks import update_single_bu_performance

def seed_target_plans(month=7, year=2026):
    targets_data = [
        {
            'bu_code': None, # TOTAL_CORP
            'manager': 'BOD & Kế toán (Ms Thảo/Diễm)',
            'year_rev': 724025300000, 'month_rev': 65605000000,
            'year_coll': 594875630914, 'month_coll': 64528882442,
            'year_inv': 200000000000, 'month_inv': 200000000000,
            'year_cash': 30000000000, 'month_cash': 30000000000,
            'year_bank': 160000000000, 'month_bank': 175000000000,
            'year_opex': 70650000000, 'month_opex': 4851250000,
            'note': 'Chỉ tiêu Kế hoạch Tổng Công Ty chốt từ Báo cáo Kế toán 22/07/2026'
        },
        {
            'bu_code': 'BU_ELEVATOR',
            'manager': 'Mr Tiến Dũng',
            'year_rev': 499000000000, 'month_rev': 46205000000,
            'year_coll': 382175634835, 'month_coll': 37769065278,
            'note': 'Mục tiêu Thang máy (Elevator, Hisa, 5EX, FJT)'
        },
        {
            'bu_code': 'BU_IBIZ PREMIUM',
            'manager': 'Mr Nhật Minh',
            'year_rev': 174600000000, 'month_rev': 15500000000,
            'year_coll': 162274696079, 'month_coll': 21440495726,
            'note': 'Mục tiêu Thiết bị điện cao cấp iBiz Premium'
        },
        {
            'bu_code': 'BU_IBIZ VALUE',
            'manager': 'Mr Huy Phong',
            'year_rev': 15000000000, 'month_rev': 1300000000,
            'year_coll': 15000000000, 'month_coll': 1300000000,
            'note': 'Mục tiêu Thiết bị điện phổ thông iBiz Value'
        },
        {
            'bu_code': 'BU_ECO',
            'manager': 'Mr Duy Hiếu',
            'year_rev': 16400000000, 'month_rev': 1600000000,
            'year_coll': 16400000000, 'month_coll': 2443047838,
            'note': 'Mục tiêu ECO Solar'
        },
        {
            'bu_code': 'BU_AGRITECH',
            'manager': 'Mr Duy Hiếu & Mr Hồng Quân',
            'year_rev': 13620300000, 'month_rev': 1000000000,
            'year_coll': 13620300000, 'month_coll': 1576273600,
            'note': 'Mục tiêu AgriTech (500M DT + 788.1M TT) và SAB Tôm (500M DT + 788.1M TT)'
        },
        {
            'bu_code': 'BU_MANUFACTURING',
            'manager': 'Mr. Quang',
            'year_rev': 5405000000, 'month_rev': 0,
            'year_coll': 5405000000, 'month_coll': 0,
            'note': 'Mục tiêu Sản xuất - Nhà máy'
        }
    ]

    out = [f"=== NẠP DỮ LIỆU MỤC TIÊU VÀO BUTARGETPLAN THÁNG {month}/{year} ==="]

    for item in targets_data:
        bu_code = item['bu_code']
        bu_obj = BusinessUnit.objects.filter(code=bu_code).first() if bu_code else None
        
        plan, created = BUTargetPlan.objects.update_or_create(
            business_unit=bu_obj,
            month=month,
            year=year,
            defaults={
                'manager': item.get('manager', ''),
                'year_revenue_target': item.get('year_rev', 0),
                'month_revenue_target': item.get('month_rev', 0),
                'year_collection_target': item.get('year_coll', 0),
                'month_collection_target': item.get('month_coll', 0),
                'year_inventory_target': item.get('year_inv', 0),
                'month_inventory_target': item.get('month_inv', 0),
                'year_cash_target': item.get('year_cash', 0),
                'month_cash_target': item.get('month_cash', 0),
                'year_bank_debt_target': item.get('year_bank', 0),
                'month_bank_debt_target': item.get('month_bank', 0),
                'year_opex_target': item.get('year_opex', 0),
                'month_opex_target': item.get('month_opex', 0),
                'note': item.get('note', '')
            }
        )
        code_str = bu_code if bu_code else "TOTAL_CORP"
        status = "Tạo mới" if created else "Cập nhật"
        out.append(f"✅ [{status}] {code_str:<20} | Quản lý: {plan.manager:<30} | DT Tháng Plan: {plan.month_revenue_target:15,.0f} | TT Tháng Plan: {plan.month_collection_target:15,.0f}")

    # Trigger calculation
    out.append("\n=== CẬP NHẬT LẠI HỆ THỐNG PERFORMANCE SỬ DỤNG TARGET MỚI ===")
    bus = BusinessUnit.objects.all()
    for b in bus:
        update_single_bu_performance(b.id, month=month, year=year)
    update_single_bu_performance(None, month=month, year=year)
    out.append("✅ Đã cập nhật xong tất cả BUPerformance!")

    sys.stdout.buffer.write("\n".join(out).encode('utf-8'))

if __name__ == '__main__':
    seed_target_plans(7, 2026)
