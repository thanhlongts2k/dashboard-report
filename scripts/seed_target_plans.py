"""
Script nạp Dữ liệu Mục tiêu Kế hoạch (BUTargetPlan) theo Báo cáo Kế toán
Hỗ trợ các kỳ: Tháng 07/2026, Tháng 08/2026, Tháng 09/2026 (Mặc định)
"""
import os
import sys
import argparse
import django

# Setup path và encoding
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), '.venv', 'Lib', 'site-packages'))
if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'report2026.settings')
django.setup()

from accounting.models import BusinessUnit, BUTargetPlan
from accounting.tasks import update_single_bu_performance

TARGET_PLANS_BY_MONTH = {
    # =========================================================================
    # KẾ HOẠCH THÁNG 09/2026 (Báo cáo Kế toán ngày 07/09/2026)
    # Tổng DT Tháng: 68,417,883,530 | Thu tiền Tháng: 54,867,543,092
    # Tổng DT Cả Năm: 723,408,013,496 | Thu tiền Cả Năm: 594,258,344,410
    # =========================================================================
    9: [
        {
            'bu_code': None, # TOTAL_CORP
            'manager': 'BOD & Kế toán (Ms Thảo/Diễm)',
            'year_rev': 723408013496, 'month_rev': 68417883530,
            'year_coll': 594258344410, 'month_coll': 54867543092,
            'year_inv': 200000000000, 'month_inv': 200000000000, # Ms Diễm
            'year_cash': 30000000000, 'month_cash': 30000000000, # Ms Thảo AC
            'year_bank': 160000000000, 'month_bank': 175000000000, # Ms Thảo AC
            'year_opex': 70650000000, 'month_opex': 6606411962, # Ms Thảo AC
            'note': 'Chỉ tiêu Kế hoạch Tổng Công Ty chốt từ Báo cáo Kế toán 07/09/2026'
        },
        {
            'bu_code': 'BU_ELEVATOR',
            'manager': 'Mr Tiến Dũng',
            'year_rev': 472500000000, 'month_rev': 45125000000,
            'year_coll': 355675634835, 'month_coll': 28974659562,
            'note': 'Mục tiêu Thang máy: Elevator (24.7 tỷ DT, 22 tỷ TT), Hisa (4.7 tỷ DT HPC + 14.225 tỷ DT FJT, 5.4746 tỷ TT), 5EX (1.5 tỷ DT, 1.5 tỷ TT)'
        },
        {
            'bu_code': 'BU_IBIZ PREMIUM',
            'manager': 'Mr Nhật Minh',
            'year_rev': 174600000000, 'month_rev': 16500000000,
            'year_coll': 162274696079, 'month_coll': 19000000000,
            'note': 'Mục tiêu Thiết bị điện cao cấp iBiz Premium'
        },
        {
            'bu_code': 'BU_IBIZ VALUE',
            'manager': 'Mr Huy Phong',
            'year_rev': 15000000000, 'month_rev': 1400000000,
            'year_coll': 15000000000, 'month_coll': 1500000000,
            'note': 'Mục tiêu Thiết bị điện phổ thông iBiz Value'
        },
        {
            'bu_code': 'BU_ECO',
            'manager': 'Mr Duy Hiếu',
            'year_rev': 15900000000, 'month_rev': 1500000000,
            'year_coll': 15900000000, 'month_coll': 1500000000,
            'note': 'Mục tiêu ECO Solar'
        },
        {
            'bu_code': 'BU_AGRITECH',
            'manager': 'Mr Duy Hiếu',
            'year_rev': 5400000000, 'month_rev': 500000000,
            'year_coll': 5400000000, 'month_coll': 500000000,
            'note': 'Mục tiêu AgriTech Nông nghiệp công nghệ cao'
        },
        {
            'bu_code': 'BU_SAB',
            'manager': 'Mr Hồng Quân',
            'year_rev': 3800000000, 'month_rev': 450000000,
            'year_coll': 3800000000, 'month_coll': 450000000,
            'note': 'Mục tiêu SAB Thủy sản thông minh'
        },
        {
            'bu_code': 'SAB',
            'manager': 'Mr Hồng Quân',
            'year_rev': 3800000000, 'month_rev': 450000000,
            'year_coll': 3800000000, 'month_coll': 450000000,
            'note': 'Mục tiêu SAB Thủy sản thông minh (Alias BU 79)'
        },
        {
            'bu_code': 'BU_MANUFACTURING',
            'manager': 'Mr Quang',
            'year_rev': 5405000000, 'month_rev': 0,
            'year_coll': 5405000000, 'month_coll': 0,
            'note': 'Mục tiêu Sản xuất - Nhà máy'
        },
        {
            'bu_code': 'ĐTCT',
            'manager': 'Mr Tiến / Khối Đầu tư cho thuê',
            'year_rev': 30803013496, 'month_rev': 2942883530,
            'year_coll': 30803013496, 'month_coll': 2942883530,
            'note': 'Mục tiêu Cho thuê Solar: 11 hệ (2.082.025.293 đ) + 6 hệ (860.858.237 đ)'
        },
        {
            'bu_code': 'Oversea',
            'manager': 'Oversea Lead',
            'year_rev': 0, 'month_rev': 0,
            'year_coll': 0, 'month_coll': 0,
            'note': 'Mục tiêu Oversea'
        }
    ],

    # =========================================================================
    # KẾ HOẠCH THÁNG 08/2026
    # =========================================================================
    8: [
        {
            'bu_code': None, # TOTAL_CORP
            'manager': 'Ban Điều Hành',
            'year_rev': 724025300000, 'month_rev': 47200000000,
            'year_coll': 594875630914, 'month_coll': 56414659562,
            'year_inv': 200000000000, 'month_inv': 200000000000,
            'year_cash': 30000000000, 'month_cash': 30000000000,
            'year_bank': 160000000000, 'month_bank': 175000000000,
            'year_opex': 70650000000, 'month_opex': 4851250000,
            'note': 'Chỉ tiêu Kế hoạch Tổng Công Ty chốt Tháng 08/2026'
        },
        {
            'bu_code': 'BU_ELEVATOR',
            'manager': 'Mr Tiến Dũng',
            'year_rev': 499000000000, 'month_rev': 27200000000,
            'year_coll': 382175634835, 'month_coll': 30314659562,
            'note': 'Mục tiêu Thang máy Tháng 08/2026'
        },
        {
            'bu_code': 'BU_IBIZ PREMIUM',
            'manager': 'Mr Nhật Minh',
            'year_rev': 174600000000, 'month_rev': 15500000000,
            'year_coll': 162274696079, 'month_coll': 21400000000,
            'note': 'Mục tiêu Thiết bị điện cao cấp iBiz Premium Tháng 08/2026'
        },
        {
            'bu_code': 'BU_IBIZ VALUE',
            'manager': 'Mr Huy Phong',
            'year_rev': 15000000000, 'month_rev': 1300000000,
            'year_coll': 15000000000, 'month_coll': 1500000000,
            'note': 'Mục tiêu Thiết bị điện phổ thông iBiz Value Tháng 08/2026'
        },
        {
            'bu_code': 'BU_ECO',
            'manager': 'Mr Duy Hiếu',
            'year_rev': 16400000000, 'month_rev': 1600000000,
            'year_coll': 16400000000, 'month_coll': 1600000000,
            'note': 'Mục tiêu ECO Solar Tháng 08/2026'
        },
        {
            'bu_code': 'BU_AGRITECH',
            'manager': 'Mr Duy Hiếu',
            'year_rev': 13620300000, 'month_rev': 500000000,
            'year_coll': 13620300000, 'month_coll': 500000000,
            'note': 'Mục tiêu AgriTech Tháng 08/2026'
        },
        {
            'bu_code': 'SAB',
            'manager': 'Mr. Hồng Quân',
            'year_rev': 3800000000, 'month_rev': 1100000000,
            'year_coll': 3800000000, 'month_coll': 1100000000,
            'note': 'Mục tiêu SAB Tôm Tháng 08/2026'
        },
        {
            'bu_code': 'BU_MANUFACTURING',
            'manager': 'Mr. Quang',
            'year_rev': 5405000000, 'month_rev': 0,
            'year_coll': 5405000000, 'month_coll': 0,
            'note': 'Mục tiêu Sản xuất - Nhà máy'
        },
        {
            'bu_code': 'Oversea',
            'manager': 'Oversea Lead',
            'year_rev': 0, 'month_rev': 0,
            'year_coll': 0, 'month_coll': 0,
            'note': 'Mục tiêu Oversea'
        }
    ],

    # =========================================================================
    # KẾ HOẠCH THÁNG 07/2026
    # =========================================================================
    7: [
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
}

def seed_target_plans(month=9, year=2026):
    targets_data = TARGET_PLANS_BY_MONTH.get(month)
    if not targets_data:
        print(f"❌ Không tìm thấy bộ dữ liệu mục tiêu cho Tháng {month}/{year} trong TARGET_PLANS_BY_MONTH!")
        return

    print(f"\n=======================================================================")
    print(f"   NẠP DỮ LIỆU MỤC TIÊU VÀO BUTARGETPLAN THÁNG {month:02d}/{year}")
    print(f"=======================================================================")

    count_success = 0
    for item in targets_data:
        bu_code = item['bu_code']
        bu_obj = BusinessUnit.objects.filter(code=bu_code).first() if bu_code else None
        
        if bu_code and not bu_obj:
            print(f"⚠️ [CẢNH BÁO] Không tìm thấy BU có code '{bu_code}' trong CSDL! Bỏ qua bản ghi này.")
            continue

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
        count_success += 1
        code_str = bu_code if bu_code else "TOTAL_CORP"
        status = "TẠO MỚI" if created else "CẬP NHẬT"
        print(f"✅ [{status:<7}] {code_str:<18} | Quản lý: {plan.manager:<30} | DT Tháng: {plan.month_revenue_target:14,.0f} | TT Tháng: {plan.month_collection_target:14,.0f}")

    print(f"\n-> Đã nạp thành công {count_success} bản ghi BUTargetPlan cho kỳ {month:02d}/{year}!")

    # Trigger calculation
    print(f"\n=======================================================================")
    print(f"   KÍCH HOẠT TÍNH TOÁN LẠI CHỈ SỐ HIỆU SUẤT (BUPERFORMANCE)")
    print(f"=======================================================================")
    bus = BusinessUnit.objects.all().order_by('id')
    for b in bus:
        update_single_bu_performance(b.id, month=month, year=year)
    update_single_bu_performance(None, month=month, year=year)
    print("✅ Đã cập nhật xong tất cả BUPerformance và Total Corp cho kỳ Tháng {0:02d}/{1}!\n".format(month, year))

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="Seed BUTargetPlan and recalculate BUPerformance.")
    parser.add_argument('--month', type=int, default=9, help="Tháng cần nạp (mặc định: 9)")
    parser.add_argument('--year', type=int, default=2026, help="Năm cần nạp (mặc định: 2026)")
    args = parser.parse_args()

    seed_target_plans(month=args.month, year=args.year)

