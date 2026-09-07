"""
Script nạp Dữ liệu Mục tiêu Kế hoạch Sales (SalesTarget) Năm 2026 & Tháng 08/2026
Dựa trên BẢNG THEO DÕI MỤC TIÊU DOANH THU CÔNG TY HẢO PHƯƠNG 2026
"""
import os
import sys
import django

# Add project root to sys.path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'report2026.settings')
django.setup()

from accounting.models import Employee, BusinessUnit, SalesTarget

def seed_sales_targets_2026(period='2026-08'):
    targets_data = [
        # =========================================================================
        # 1. BU_ELEVATOR
        # =========================================================================
        # Miền Bắc_Elevator
        {
            'emp_code': '2000017', 'emp_name': 'Nguyễn Đức Thưởng',
            'bu_code': 'BU_ELEVATOR', 'region': 'Miền Bắc', 'sales_group': 'Miền Bắc_Elevator',
            'year_target': 63130239315, 'prev_target': 29980488766, 'month_target': 5645958669,
            'order': 1
        },
        {
            'emp_code': '2000609', 'emp_name': 'Phạm Văn Nghệ',
            'bu_code': 'BU_ELEVATOR', 'region': 'Miền Bắc', 'sales_group': 'Miền Bắc_Elevator',
            'year_target': 43435626443, 'prev_target': 20614808829, 'month_target': 3883832986,
            'order': 2
        },
        {
            'emp_code': '2000996', 'emp_name': 'Mai Tiến Dương',
            'bu_code': 'BU_ELEVATOR', 'region': 'Miền Bắc', 'sales_group': 'Miền Bắc_Elevator',
            'year_target': 34334134242, 'prev_target': 16304702404, 'month_target': 3070208345,
            'order': 3
        },
        # Miền Nam__Elevator
        {
            'emp_code': '3003', 'emp_name': 'Đào Tiến Dũng',
            'bu_code': 'BU_ELEVATOR', 'region': 'Miền Nam', 'sales_group': 'Miền Nam__Elevator',
            'year_target': 63682586484, 'prev_target': 30340636403, 'month_target': 5696372792,
            'order': 4
        },
        {
            'emp_code': '3005', 'emp_name': 'Trịnh Hoàng Quân',
            'bu_code': 'BU_ELEVATOR', 'region': 'Miền Nam', 'sales_group': 'Miền Nam__Elevator',
            'year_target': 27808520462, 'prev_target': 13221260054, 'month_target': 2487180896,
            'order': 5
        },
        {
            'emp_code': '2000812', 'emp_name': 'Nguyễn Hoàng Dinh',
            'bu_code': 'BU_ELEVATOR', 'region': 'Miền Nam', 'sales_group': 'Miền Nam__Elevator',
            'year_target': 19208893054, 'prev_target': 9138103542, 'month_target': 1716446312,
            'order': 6
        },

        # =========================================================================
        # 2. BU_IBIZ PREMIUM
        # =========================================================================
        # Miền Bắc_Premium
        {
            'emp_code': '2000610', 'emp_name': 'Ngô Văn Hiếu',
            'bu_code': 'BU_IBIZ PREMIUM', 'region': 'Miền Bắc', 'sales_group': 'Miền Bắc_Premium',
            'year_target': 37297212418, 'prev_target': 20062418301, 'month_target': 3293137255,
            'order': 7
        },
        {
            'emp_code': '2000079', 'emp_name': 'Trần Thị Tuyến',
            'bu_code': 'BU_IBIZ PREMIUM', 'region': 'Miền Bắc', 'sales_group': 'Miền Bắc_Premium',
            'year_target': 60589978214, 'prev_target': 32409586057, 'month_target': 5373856209,
            'order': 8
        },
        {
            'emp_code': '2000058', 'emp_name': 'Nguyễn Bình Minh',
            'bu_code': 'BU_IBIZ PREMIUM', 'region': 'Miền Bắc', 'sales_group': 'Miền Bắc_Premium',
            'year_target': 7053213508, 'prev_target': 3790468410, 'month_target': 622385621,
            'order': 9
        },
        {
            'emp_code': '2000997', 'emp_name': 'Lê Tuấn Kiên',
            'bu_code': 'BU_IBIZ PREMIUM', 'region': 'Miền Bắc', 'sales_group': 'Miền Bắc_Premium',
            'year_target': 8059095861, 'prev_target': 4337527233, 'month_target': 710620915,
            'order': 10
        },
        # Miền Nam_Premium
        {
            'emp_code': '2000593', 'emp_name': 'Nguyễn Xuân Tân',
            'bu_code': 'BU_IBIZ PREMIUM', 'region': 'Miền Nam', 'sales_group': 'Miền Nam_Premium',
            'year_target': 22328058608, 'prev_target': 11911465201, 'month_target': 1998864469,
            'order': 11
        },
        {
            'emp_code': '2000588', 'emp_name': 'Nguyễn Hoàng Tân',
            'bu_code': 'BU_IBIZ PREMIUM', 'region': 'Miền Nam', 'sales_group': 'Miền Nam_Premium',
            'year_target': 32499890110, 'prev_target': 17385109890, 'month_target': 2891593407,
            'order': 12
        },
        {
            'emp_code': '9010', 'emp_name': 'Đào Lê Hoàng Thiện',
            'bu_code': 'BU_IBIZ PREMIUM', 'region': 'Miền Nam', 'sales_group': 'Miền Nam_Premium',
            'year_target': 6772051282, 'prev_target': 3603424908, 'month_target': 609542125,
            'order': 13
        },
        {
            'emp_code': '10039', 'emp_name': 'Nguyễn Thị Mỹ Hòa',
            'bu_code': 'BU_IBIZ PREMIUM', 'region': 'Miền Nam', 'sales_group': 'Miền Nam_Premium',
            'year_target': 0, 'prev_target': 0, 'month_target': 0,
            'order': 14
        },
        {
            'emp_code': '2000499', 'emp_name': 'Nguyễn Thị Oanh',
            'bu_code': 'BU_IBIZ PREMIUM', 'region': 'Miền Nam', 'sales_group': 'Miền Nam_Premium',
            'year_target': 0, 'prev_target': 0, 'month_target': 0,
            'order': 15
        },
        {
            'emp_code': '2001016', 'emp_name': 'Dương Đức Mạnh',
            'bu_code': 'BU_IBIZ PREMIUM', 'region': 'Miền Bắc', 'sales_group': 'Miền Bắc_Premium',
            'year_target': 0, 'prev_target': 0, 'month_target': 0,
            'order': 16
        },

        # =========================================================================
        # 3. BU_IBIZ VALUE
        # =========================================================================
        # Miền Bắc_Value
        {
            'emp_code': '2000798', 'emp_name': 'Nguyễn Văn Hữu_Sale',
            'bu_code': 'BU_IBIZ VALUE', 'region': 'Miền Bắc', 'sales_group': 'Miền Bắc_Value',
            'year_target': 4000000000, 'prev_target': 800000000, 'month_target': 400000000,
            'order': 17
        },
        {
            'emp_code': '2001004', 'emp_name': 'Nguyễn Trung Kiên',
            'bu_code': 'BU_IBIZ VALUE', 'region': 'Miền Bắc', 'sales_group': 'Miền Bắc_Value',
            'year_target': 0, 'prev_target': 325000000, 'month_target': 0,
            'order': 18
        },
        # Miền Nam_Value
        {
            'emp_code': '2000793', 'emp_name': 'Nguyễn Huy Phong',
            'bu_code': 'BU_IBIZ VALUE', 'region': 'Miền Nam', 'sales_group': 'Miền Nam_Value',
            'year_target': 2360000000, 'prev_target': 4250000000, 'month_target': 0,
            'order': 19
        },
        {
            'emp_code': '7607', 'emp_name': 'Nguyễn Công Trạng',
            'bu_code': 'BU_IBIZ VALUE', 'region': 'Miền Nam', 'sales_group': 'Miền Nam_Value',
            'year_target': 2880000000, 'prev_target': 1400000000, 'month_target': 300000000,
            'order': 20
        },
        {
            'emp_code': '9037', 'emp_name': 'Võ Tấn Hiệp',
            'bu_code': 'BU_IBIZ VALUE', 'region': 'Miền Nam', 'sales_group': 'Miền Nam_Value',
            'year_target': 2880000000, 'prev_target': 1400000000, 'month_target': 300000000,
            'order': 21
        },
        {
            'emp_code': '2001027', 'emp_name': 'Lâm Duy Nhật',
            'bu_code': 'BU_IBIZ VALUE', 'region': 'Miền Nam', 'sales_group': 'Miền Nam_Value',
            'year_target': 2880000000, 'prev_target': 1400000000, 'month_target': 300000000,
            'order': 22
        },
        {
            'emp_code': '2000530', 'emp_name': 'Lý Anh Vũ',
            'bu_code': 'BU_IBIZ VALUE', 'region': 'Miền Nam', 'sales_group': 'Miền Nam_Value',
            'year_target': 0, 'prev_target': 0, 'month_target': 0,
            'order': 23
        },

        # =========================================================================
        # 4. TỔNG ECO+AGRITECH
        # =========================================================================
        # BU ECO
        {
            'emp_code': '9004', 'emp_name': 'Phạm Văn Mừng',
            'bu_code': 'BU_ECO', 'region': 'Tổng BU ECO', 'sales_group': 'BU ECO',
            'year_target': 13300000000, 'prev_target': 8400000000, 'month_target': 1100000000,
            'order': 22
        },
        {
            'emp_code': '2000510', 'emp_name': 'Phan Thái Vũ',
            'bu_code': 'BU_ECO', 'region': 'Tổng BU ECO', 'sales_group': 'BU ECO',
            'year_target': 1300000000, 'prev_target': 0, 'month_target': 200000000,
            'order': 23
        },
        {
            'emp_code': '2000471', 'emp_name': 'Nguyễn Quốc Huy',
            'bu_code': 'BU_ECO', 'region': 'Tổng BU ECO', 'sales_group': 'BU ECO',
            'year_target': 1300000000, 'prev_target': 0, 'month_target': 200000000,
            'order': 24
        },
        # BU AGRITECH
        {
            'emp_code': '7503', 'emp_name': 'Lý Kế Phú',
            'bu_code': 'BU_AGRITECH', 'region': 'BU AGRITECH', 'sales_group': 'BU AGRITECH',
            'year_target': 5400000000, 'prev_target': 3813204500, 'month_target': 500000000,
            'order': 25
        },
        # Đơn vị SAB
        {
            'emp_code': '2000477', 'emp_name': 'Trần Hồng Quân',
            'bu_code': 'BU_SAB', 'region': 'Đơn vị SAB', 'sales_group': 'Đơn vị SAB',
            'year_target': 3800000000, 'prev_target': 2000000000, 'month_target': 0,
            'order': 26
        },

        # =========================================================================
        # 5. TỔNG MANUFACTURING
        # =========================================================================
        # BU MANUFACTURING
        {
            'emp_code': '9038', 'emp_name': 'Hồ Xuân Quang',
            'bu_code': 'BU_MANUFACTURING', 'region': 'BU MANUFACTURING', 'sales_group': 'BU MANUFACTURING',
            'year_target': 5405000000, 'prev_target': 767920600, 'month_target': 0,
            'order': 27
        }
    ]

    print(f"=== BẮT ĐẦU NẠP DỮ LIỆU CHỈ TIÊU SALES (KỲ {period}) ===")
    created_count = 0
    updated_count = 0

    for item in targets_data:
        emp = Employee.objects.filter(employee_code=item['emp_code']).first()
        if not emp:
            print(f"❌ Không tìm thấy Employee với mã: {item['emp_code']} ({item['emp_name']})")
            continue

        bu = BusinessUnit.objects.filter(code=item['bu_code']).first()
        if not bu:
            print(f"❌ Không tìm thấy BusinessUnit với mã: {item['bu_code']}")
            continue

        obj, created = SalesTarget.objects.update_or_create(
            employee=emp,
            business_unit=bu,
            period=period,
            defaults={
                'region': item['region'],
                'sales_group': item['sales_group'],
                'year_target': item['year_target'],
                'prev_target': item['prev_target'],
                'month_target': item['month_target'],
                'display_order': item['order'],
                'is_active': True,
            }
        )
        if created:
            created_count += 1
            print(f"  [TẠO MỚI] {item['order']:02d}. {emp.full_name} ({item['sales_group']}): Tháng={item['month_target']:,.0f} | Năm={item['year_target']:,.0f}")
        else:
            updated_count += 1
            print(f"  [CẬP NHẬT] {item['order']:02d}. {emp.full_name} ({item['sales_group']}): Tháng={item['month_target']:,.0f} | Năm={item['year_target']:,.0f}")

    print(f"=== HOÀN TẤT: Tạo mới {created_count}, Cập nhật {updated_count} bản ghi SalesTarget ===")

if __name__ == '__main__':
    seed_sales_targets_2026()
