"""
Script nạp Dữ liệu Mục tiêu Kế hoạch Sales (SalesTarget) Năm 2026 & Tháng 09/2026
Dựa trên BẢNG THEO DÕI MỤC TIÊU DOANH THU CÔNG TY HẢO PHƯƠNG 2026 (KHÔNG BAO GỒM DOANH THU NỘI BỘ VÀ HISA)
"""
import os
import sys
import argparse
from decimal import Decimal
import django

# Add project root to sys.path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'report2026.settings')
django.setup()

from accounting.models import Employee, BusinessUnit, SalesTarget

TARGETS_2026_09 = [
    # =========================================================================
    # 1. BU_ELEVATOR (Tổng Tháng 9: 24.700.000.000, Năm: 253.800.000.000, T1-T8: 142.100.000.000)
    # =========================================================================
    # Miền Bắc_Elevator (Tháng 9: 13.800.000.000, Năm: 142.100.000.000, T1-T8: 79.500.000.000)
    {
        'emp_code': '2000017', 'emp_name': 'Nguyễn Đức Thưởng',
        'bu_code': 'BU_ELEVATOR', 'region': 'Miền Bắc', 'sales_group': 'Miền Bắc_Elevator',
        'year_target': 63671423504, 'prev_target': 35626447435, 'month_target': 6187142857,
        'order': 1
    },
    {
        'emp_code': '2000609', 'emp_name': 'Phạm Văn Nghệ',
        'bu_code': 'BU_ELEVATOR', 'region': 'Miền Bắc', 'sales_group': 'Miền Bắc_Elevator',
        'year_target': 43806079171, 'prev_target': 24498641815, 'month_target': 4254285714,
        'order': 2
    },
    {
        'emp_code': '2000996', 'emp_name': 'Mai Tiến Dương',
        'bu_code': 'BU_ELEVATOR', 'region': 'Miền Bắc', 'sales_group': 'Miền Bắc_Elevator',
        'year_target': 34622497325, 'prev_target': 19374910749, 'month_target': 3358571429,
        'order': 3
    },
    # Miền Nam__Elevator (Tháng 9: 10.900.000.000, Năm: 111.700.000.000, T1-T8: 62.600.000.000)
    {
        'emp_code': '3003', 'emp_name': 'Đào Tiến Dũng',
        'bu_code': 'BU_ELEVATOR', 'region': 'Miền Nam', 'sales_group': 'Miền Nam__Elevator',
        'year_target': 64238322873, 'prev_target': 36037009196, 'month_target': 6252109181,
        'order': 4
    },
    {
        'emp_code': '3005', 'emp_name': 'Trịnh Hoàng Quân',
        'bu_code': 'BU_ELEVATOR', 'region': 'Miền Nam', 'sales_group': 'Miền Nam__Elevator',
        'year_target': 28074441303, 'prev_target': 15708440950, 'month_target': 2753101737,
        'order': 5
    },
    {
        'emp_code': '2000812', 'emp_name': 'Nguyễn Hoàng Dinh',
        'bu_code': 'BU_ELEVATOR', 'region': 'Miền Nam', 'sales_group': 'Miền Nam__Elevator',
        'year_target': 19387235824, 'prev_target': 10854549854, 'month_target': 1894789082,
        'order': 6
    },

    # =========================================================================
    # 2. BU_IBIZ PREMIUM (Tổng Tháng 9: 16.500.000.000, Năm: 175.600.000.000, T1-T8: 109.000.000.000)
    # =========================================================================
    # Miền Bắc_Premium (Tháng 9: 10.700.000.000, Năm: 113.700.000.000, T1-T8: 70.600.000.000)
    {
        'emp_code': '2000610', 'emp_name': 'Ngô Văn Hiếu',
        'bu_code': 'BU_IBIZ PREMIUM', 'region': 'Miền Bắc', 'sales_group': 'Miền Bắc_Premium',
        'year_target': 37533660131, 'prev_target': 23355555556, 'month_target': 3529084967,
        'order': 7
    },
    {
        'emp_code': '2000079', 'emp_name': 'Trần Thị Tuyến',
        'bu_code': 'BU_IBIZ PREMIUM', 'region': 'Miền Bắc', 'sales_group': 'Miền Bắc_Premium',
        'year_target': 60950544662, 'prev_target': 37783442266, 'month_target': 5734422658,
        'order': 8
    },
    {
        'emp_code': '2000058', 'emp_name': 'Nguyễn Bình Minh',
        'bu_code': 'BU_IBIZ PREMIUM', 'region': 'Miền Bắc', 'sales_group': 'Miền Bắc_Premium',
        'year_target': 7102015251, 'prev_target': 4412854031, 'month_target': 671187364,
        'order': 9
    },
    {
        'emp_code': '2000997', 'emp_name': 'Lê Tuấn Kiên',
        'bu_code': 'BU_IBIZ PREMIUM', 'region': 'Miền Bắc', 'sales_group': 'Miền Bắc_Premium',
        'year_target': 8113779956, 'prev_target': 5048148148, 'month_target': 765305011,
        'order': 10
    },
    # Miền Nam_Premium (Tháng 9: 5.800.000.000, Năm: 61.900.000.000, T1-T8: 38.400.000.000)
    {
        'emp_code': '2000593', 'emp_name': 'Nguyễn Xuân Tân',
        'bu_code': 'BU_IBIZ PREMIUM', 'region': 'Miền Nam', 'sales_group': 'Miền Nam_Premium',
        'year_target': 22425164835, 'prev_target': 13910329670, 'month_target': 2095970696,
        'order': 11
    },
    {
        'emp_code': '2000588', 'emp_name': 'Nguyễn Hoàng Tân',
        'bu_code': 'BU_IBIZ PREMIUM', 'region': 'Miền Nam', 'sales_group': 'Miền Nam_Premium',
        'year_target': 32678351648, 'prev_target': 20276703297, 'month_target': 3070054945,
        'order': 12
    },
    {
        'emp_code': '9010', 'emp_name': 'Đào Lê Hoàng Thiện',
        'bu_code': 'BU_IBIZ PREMIUM', 'region': 'Miền Nam', 'sales_group': 'Miền Nam_Premium',
        'year_target': 6796483516, 'prev_target': 4212967033, 'month_target': 633974359,
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
    # 3. BU_IBIZ VALUE (Tổng Tháng 9: 1.400.000.000, Năm: 15.000.000.000, T1-T8: 10.875.000.000)
    # =========================================================================
    # Miền Bắc_Value (Tháng 9: 500.000.000, Năm: 4.000.000.000, T1-T8: 1.525.000.000)
    {
        'emp_code': '2000798', 'emp_name': 'Nguyễn Văn Hữu_Sale',
        'bu_code': 'BU_IBIZ VALUE', 'region': 'Miền Bắc', 'sales_group': 'Miền Bắc_Value',
        'year_target': 4000000000, 'prev_target': 1200000000, 'month_target': 300000000,
        'order': 17
    },
    {
        'emp_code': '2001004', 'emp_name': 'Nguyễn Trung Kiên',
        'bu_code': 'BU_IBIZ VALUE', 'region': 'Miền Bắc', 'sales_group': 'Miền Bắc_Value',
        'year_target': 0, 'prev_target': 325000000, 'month_target': 200000000,
        'order': 18
    },
    # Miền Nam_Value (Tháng 9: 900.000.000, Năm: 11.000.000.000, T1-T8: 9.350.000.000)
    {
        'emp_code': '2000793', 'emp_name': 'Nguyễn Huy Phong',
        'bu_code': 'BU_IBIZ VALUE', 'region': 'Miền Nam', 'sales_group': 'Miền Nam_Value',
        'year_target': 2360000000, 'prev_target': 4250000000, 'month_target': 0,
        'order': 19
    },
    {
        'emp_code': '7607', 'emp_name': 'Nguyễn Công Trạng',
        'bu_code': 'BU_IBIZ VALUE', 'region': 'Miền Nam', 'sales_group': 'Miền Nam_Value',
        'year_target': 2880000000, 'prev_target': 1700000000, 'month_target': 300000000,
        'order': 20
    },
    {
        'emp_code': '9037', 'emp_name': 'Võ Tấn Hiệp',
        'bu_code': 'BU_IBIZ VALUE', 'region': 'Miền Nam', 'sales_group': 'Miền Nam_Value',
        'year_target': 2880000000, 'prev_target': 1700000000, 'month_target': 300000000,
        'order': 21
    },
    {
        'emp_code': '2001027', 'emp_name': 'Lâm Duy Nhật',
        'bu_code': 'BU_IBIZ VALUE', 'region': 'Miền Nam', 'sales_group': 'Miền Nam_Value',
        'year_target': 2880000000, 'prev_target': 1700000000, 'month_target': 300000000,
        'order': 22
    },
    {
        'emp_code': '2000530', 'emp_name': 'Lý Anh Vũ',
        'bu_code': 'BU_IBIZ VALUE', 'region': 'Miền Nam', 'sales_group': 'Miền Nam_Value',
        'year_target': 0, 'prev_target': 0, 'month_target': 0,
        'order': 23
    },

    # =========================================================================
    # 4. TỔNG ECO+AGRITECH (Tháng 9: 2.450.000.000, Năm: 25.100.000.000, T1-T8: 15.300.000.000)
    # =========================================================================
    # BU ECO (Tháng 9: 1.500.000.000, Năm: 15.900.000.000, T1-T8: 9.900.000.000)
    {
        'emp_code': '9004', 'emp_name': 'Phạm Văn Mừng',
        'bu_code': 'BU_ECO', 'region': 'Tổng BU ECO', 'sales_group': 'BU ECO',
        'year_target': 13300000000, 'prev_target': 9500000000, 'month_target': 1100000000,
        'order': 24
    },
    {
        'emp_code': '2000510', 'emp_name': 'Phan Thái Vũ',
        'bu_code': 'BU_ECO', 'region': 'Tổng BU ECO', 'sales_group': 'BU ECO',
        'year_target': 1300000000, 'prev_target': 200000000, 'month_target': 200000000,
        'order': 25
    },
    {
        'emp_code': '2000471', 'emp_name': 'Nguyễn Quốc Huy',
        'bu_code': 'BU_ECO', 'region': 'Tổng BU ECO', 'sales_group': 'BU ECO',
        'year_target': 1300000000, 'prev_target': 200000000, 'month_target': 200000000,
        'order': 26
    },
    # BU AGRITECH (Tháng 9: 500.000.000, Năm: 5.400.000.000, T1-T8: 3.400.000.000)
    {
        'emp_code': '7503', 'emp_name': 'Lý Kế Phú',
        'bu_code': 'BU_AGRITECH', 'region': 'BU AGRITECH', 'sales_group': 'BU AGRITECH',
        'year_target': 5400000000, 'prev_target': 3400000000, 'month_target': 500000000,
        'order': 27
    },
    # Đơn vị SAB (Tháng 9: 450.000.000, Năm: 3.800.000.000, T1-T8: 2.000.000.000)
    {
        'emp_code': '2000477', 'emp_name': 'Trần Hồng Quân',
        'bu_code': 'BU_SAB', 'region': 'Đơn vị SAB', 'sales_group': 'Đơn vị SAB',
        'year_target': 3800000000, 'prev_target': 2000000000, 'month_target': 450000000,
        'order': 28
    },

    # =========================================================================
    # 5. TỔNG MANUFACTURING (Tháng 9: 0, Năm: 5.405.000.000, T1-T8: 767.920.600)
    # =========================================================================
    {
        'emp_code': '9038', 'emp_name': 'Hồ Xuân Quang',
        'bu_code': 'BU_MANUFACTURING', 'region': 'BU MANUFACTURING', 'sales_group': 'BU MANUFACTURING',
        'year_target': 5405000000, 'prev_target': 767920600, 'month_target': 0,
        'order': 29
    }
]

TARGETS_2026_08 = [
    # Elevators
    {'emp_code': '2000017', 'emp_name': 'Nguyễn Đức Thưởng', 'bu_code': 'BU_ELEVATOR', 'region': 'Miền Bắc', 'sales_group': 'Miền Bắc_Elevator', 'year_target': 63130239315, 'prev_target': 29980488766, 'month_target': 5645958669, 'order': 1},
    {'emp_code': '2000609', 'emp_name': 'Phạm Văn Nghệ', 'bu_code': 'BU_ELEVATOR', 'region': 'Miền Bắc', 'sales_group': 'Miền Bắc_Elevator', 'year_target': 43435626443, 'prev_target': 20614808829, 'month_target': 3883832986, 'order': 2},
    {'emp_code': '2000996', 'emp_name': 'Mai Tiến Dương', 'bu_code': 'BU_ELEVATOR', 'region': 'Miền Bắc', 'sales_group': 'Miền Bắc_Elevator', 'year_target': 34334134242, 'prev_target': 16304702404, 'month_target': 3070208345, 'order': 3},
    {'emp_code': '3003', 'emp_name': 'Đào Tiến Dũng', 'bu_code': 'BU_ELEVATOR', 'region': 'Miền Nam', 'sales_group': 'Miền Nam__Elevator', 'year_target': 63682586484, 'prev_target': 30340636403, 'month_target': 5696372792, 'order': 4},
    {'emp_code': '3005', 'emp_name': 'Trịnh Hoàng Quân', 'bu_code': 'BU_ELEVATOR', 'region': 'Miền Nam', 'sales_group': 'Miền Nam__Elevator', 'year_target': 27808520462, 'prev_target': 13221260054, 'month_target': 2487180896, 'order': 5},
    {'emp_code': '2000812', 'emp_name': 'Nguyễn Hoàng Dinh', 'bu_code': 'BU_ELEVATOR', 'region': 'Miền Nam', 'sales_group': 'Miền Nam__Elevator', 'year_target': 19208893054, 'prev_target': 9138103542, 'month_target': 1716446312, 'order': 6},
    # iBiz Premium
    {'emp_code': '2000610', 'emp_name': 'Ngô Văn Hiếu', 'bu_code': 'BU_IBIZ PREMIUM', 'region': 'Miền Bắc', 'sales_group': 'Miền Bắc_Premium', 'year_target': 37297212418, 'prev_target': 20062418301, 'month_target': 3293137255, 'order': 7},
    {'emp_code': '2000079', 'emp_name': 'Trần Thị Tuyến', 'bu_code': 'BU_IBIZ PREMIUM', 'region': 'Miền Bắc', 'sales_group': 'Miền Bắc_Premium', 'year_target': 60589978214, 'prev_target': 32409586057, 'month_target': 5373856209, 'order': 8},
    {'emp_code': '2000058', 'emp_name': 'Nguyễn Bình Minh', 'bu_code': 'BU_IBIZ PREMIUM', 'region': 'Miền Bắc', 'sales_group': 'Miền Bắc_Premium', 'year_target': 7053213508, 'prev_target': 3790468410, 'month_target': 622385621, 'order': 9},
    {'emp_code': '2000997', 'emp_name': 'Lê Tuấn Kiên', 'bu_code': 'BU_IBIZ PREMIUM', 'region': 'Miền Bắc', 'sales_group': 'Miền Bắc_Premium', 'year_target': 8059095861, 'prev_target': 4337527233, 'month_target': 710620915, 'order': 10},
    {'emp_code': '2000593', 'emp_name': 'Nguyễn Xuân Tân', 'bu_code': 'BU_IBIZ PREMIUM', 'region': 'Miền Nam', 'sales_group': 'Miền Nam_Premium', 'year_target': 22328058608, 'prev_target': 11911465201, 'month_target': 1998864469, 'order': 11},
    {'emp_code': '2000588', 'emp_name': 'Nguyễn Hoàng Tân', 'bu_code': 'BU_IBIZ PREMIUM', 'region': 'Miền Nam', 'sales_group': 'Miền Nam_Premium', 'year_target': 32499890110, 'prev_target': 17385109890, 'month_target': 2891593407, 'order': 12},
    {'emp_code': '9010', 'emp_name': 'Đào Lê Hoàng Thiện', 'bu_code': 'BU_IBIZ PREMIUM', 'region': 'Miền Nam', 'sales_group': 'Miền Nam_Premium', 'year_target': 6772051282, 'prev_target': 3603424908, 'month_target': 609542125, 'order': 13},
    {'emp_code': '10039', 'emp_name': 'Nguyễn Thị Mỹ Hòa', 'bu_code': 'BU_IBIZ PREMIUM', 'region': 'Miền Nam', 'sales_group': 'Miền Nam_Premium', 'year_target': 0, 'prev_target': 0, 'month_target': 0, 'order': 14},
    {'emp_code': '2000499', 'emp_name': 'Nguyễn Thị Oanh', 'bu_code': 'BU_IBIZ PREMIUM', 'region': 'Miền Nam', 'sales_group': 'Miền Nam_Premium', 'year_target': 0, 'prev_target': 0, 'month_target': 0, 'order': 15},
    {'emp_code': '2001016', 'emp_name': 'Dương Đức Mạnh', 'bu_code': 'BU_IBIZ PREMIUM', 'region': 'Miền Bắc', 'sales_group': 'Miền Bắc_Premium', 'year_target': 0, 'prev_target': 0, 'month_target': 0, 'order': 16},
    # iBiz Value
    {'emp_code': '2000798', 'emp_name': 'Nguyễn Văn Hữu_Sale', 'bu_code': 'BU_IBIZ VALUE', 'region': 'Miền Bắc', 'sales_group': 'Miền Bắc_Value', 'year_target': 4000000000, 'prev_target': 800000000, 'month_target': 400000000, 'order': 17},
    {'emp_code': '2001004', 'emp_name': 'Nguyễn Trung Kiên', 'bu_code': 'BU_IBIZ VALUE', 'region': 'Miền Bắc', 'sales_group': 'Miền Bắc_Value', 'year_target': 0, 'prev_target': 325000000, 'month_target': 0, 'order': 18},
    {'emp_code': '2000793', 'emp_name': 'Nguyễn Huy Phong', 'bu_code': 'BU_IBIZ VALUE', 'region': 'Miền Nam', 'sales_group': 'Miền Nam_Value', 'year_target': 2360000000, 'prev_target': 4250000000, 'month_target': 0, 'order': 19},
    {'emp_code': '7607', 'emp_name': 'Nguyễn Công Trạng', 'bu_code': 'BU_IBIZ VALUE', 'region': 'Miền Nam', 'sales_group': 'Miền Nam_Value', 'year_target': 2880000000, 'prev_target': 1400000000, 'month_target': 300000000, 'order': 20},
    {'emp_code': '9037', 'emp_name': 'Võ Tấn Hiệp', 'bu_code': 'BU_IBIZ VALUE', 'region': 'Miền Nam', 'sales_group': 'Miền Nam_Value', 'year_target': 2880000000, 'prev_target': 1400000000, 'month_target': 300000000, 'order': 21},
    {'emp_code': '2001027', 'emp_name': 'Lâm Duy Nhật', 'bu_code': 'BU_IBIZ VALUE', 'region': 'Miền Nam', 'sales_group': 'Miền Nam_Value', 'year_target': 2880000000, 'prev_target': 1400000000, 'month_target': 300000000, 'order': 22},
    {'emp_code': '2000530', 'emp_name': 'Lý Anh Vũ', 'bu_code': 'BU_IBIZ VALUE', 'region': 'Miền Nam', 'sales_group': 'Miền Nam_Value', 'year_target': 0, 'prev_target': 0, 'month_target': 0, 'order': 23},
    # ECO+AgriTech+SAB
    {'emp_code': '9004', 'emp_name': 'Phạm Văn Mừng', 'bu_code': 'BU_ECO', 'region': 'Tổng BU ECO', 'sales_group': 'BU ECO', 'year_target': 13300000000, 'prev_target': 8400000000, 'month_target': 1100000000, 'order': 24},
    {'emp_code': '2000510', 'emp_name': 'Phan Thái Vũ', 'bu_code': 'BU_ECO', 'region': 'Tổng BU ECO', 'sales_group': 'BU ECO', 'year_target': 1300000000, 'prev_target': 0, 'month_target': 200000000, 'order': 25},
    {'emp_code': '2000471', 'emp_name': 'Nguyễn Quốc Huy', 'bu_code': 'BU_ECO', 'region': 'Tổng BU ECO', 'sales_group': 'BU ECO', 'year_target': 1300000000, 'prev_target': 0, 'month_target': 200000000, 'order': 26},
    {'emp_code': '7503', 'emp_name': 'Lý Kế Phú', 'bu_code': 'BU_AGRITECH', 'region': 'BU AGRITECH', 'sales_group': 'BU AGRITECH', 'year_target': 5400000000, 'prev_target': 3813204500, 'month_target': 500000000, 'order': 27},
    {'emp_code': '2000477', 'emp_name': 'Trần Hồng Quân', 'bu_code': 'BU_SAB', 'region': 'Đơn vị SAB', 'sales_group': 'Đơn vị SAB', 'year_target': 3800000000, 'prev_target': 2000000000, 'month_target': 0, 'order': 28},
    # Manufacturing
    {'emp_code': '9038', 'emp_name': 'Hồ Xuân Quang', 'bu_code': 'BU_MANUFACTURING', 'region': 'BU MANUFACTURING', 'sales_group': 'BU MANUFACTURING', 'year_target': 5405000000, 'prev_target': 767920600, 'month_target': 0, 'order': 29}
]

DATASETS = {
    '2026-08': TARGETS_2026_08,
    '2026-09': TARGETS_2026_09,
}

def seed_sales_targets_2026(period='2026-09'):
    targets_data = DATASETS.get(period, TARGETS_2026_09)

    print(f"=== BẮT ĐẦU NẠP DỮ LIỆU CHỈ TIÊU SALES (KỲ {period}) ===")
    created_count = 0
    updated_count = 0

    total_month = Decimal('0')
    total_prev = Decimal('0')
    total_year = Decimal('0')

    bu_totals = {}

    for item in targets_data:
        emp = Employee.objects.filter(employee_code=item['emp_code']).first()
        if not emp:
            print(f"❌ Không tìm thấy Employee với mã: {item['emp_code']} ({item['emp_name']})")
            continue

        bu = BusinessUnit.objects.filter(code=item['bu_code']).first()
        if not bu:
            print(f"❌ Không tìm thấy BusinessUnit với mã: {item['bu_code']}")
            continue

        m_tgt = Decimal(str(item['month_target']))
        p_tgt = Decimal(str(item['prev_target']))
        y_tgt = Decimal(str(item['year_target']))

        total_month += m_tgt
        total_prev += p_tgt
        total_year += y_tgt

        bu_key = item['bu_code']
        if bu_key not in bu_totals:
            bu_totals[bu_key] = {'month': Decimal('0'), 'year': Decimal('0')}
        bu_totals[bu_key]['month'] += m_tgt
        bu_totals[bu_key]['year'] += y_tgt

        obj, created = SalesTarget.objects.update_or_create(
            employee=emp,
            business_unit=bu,
            period=period,
            defaults={
                'region': item['region'],
                'sales_group': item['sales_group'],
                'year_target': y_tgt,
                'prev_target': p_tgt,
                'month_target': m_tgt,
                'display_order': item['order'],
                'is_active': True,
            }
        )
        if created:
            created_count += 1
            print(f"  [TẠO MỚI] {item['order']:02d}. {emp.full_name} ({item['sales_group']}): Tháng={m_tgt:,.0f} | Năm={y_tgt:,.0f}")
        else:
            updated_count += 1
            print(f"  [CẬP NHẬT] {item['order']:02d}. {emp.full_name} ({item['sales_group']}): Tháng={m_tgt:,.0f} | Năm={y_tgt:,.0f}")

    print(f"\n=== HOÀN TẤT: Tạo mới {created_count}, Cập nhật {updated_count} bản ghi SalesTarget (Kỳ {period}) ===")
    print("--- TỔNG KẾT THEO BU ---")
    for b, vals in bu_totals.items():
        print(f"  * {b:<20}: Tháng={vals['month']:>15,.0f} đ | Năm={vals['year']:>17,.0f} đ")
    print(f"  => TỔNG TOÀN CÔNG TY: Tháng={total_month:>15,.0f} đ | T1-T8={total_prev:>17,.0f} đ | Năm={total_year:>17,.0f} đ")

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="Seed sales targets for specified period.")
    parser.add_argument('--period', type=str, default='2026-09', help="Target period (YYYY-MM), default: 2026-09")
    args = parser.parse_args()
    seed_sales_targets_2026(period=args.period)
