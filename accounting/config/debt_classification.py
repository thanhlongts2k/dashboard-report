"""
Cấu hình phân loại danh mục công nợ đặc biệt (Chuẩn Kế toán 2026):
1. Nhóm Nợ cũ khó đòi 2022-2024 (Historical Bad Debt): 4,365,519,339 VNĐ
2. Nhóm Nợ cũ năm 2025 (Old Debt 2025): 266,666,301 VNĐ (Lê Văn Tín 262.4M + Hoàng Triều 4.25M)
3. Nhóm Nợ năm 2026 (Active Operating Debt 2026): 59,066,876,095 VNĐ (Trong hạn: 36.19 tỷ, Quá hạn: 22.88 tỷ)
"""
from decimal import Decimal

# -----------------------------------------------------------------------------
# 1. Danh mục Nợ cũ khó đòi 2022-2024 (Chuẩn chốt theo Báo cáo Kế toán đến 05/09/2026)
# -----------------------------------------------------------------------------
HISTORICAL_BAD_DEBT_2022_2024 = [
    {
        'customer_name': '7 KHÁCH HÀNG CAMBODIA',
        'employee_code': '2001',
        'employee_name': 'NGÔ ĐÌNH TRUNG TÂN',
        'original_debt': Decimal('1394969434'),
        'recovered_ytd': Decimal('0'),
        'remaining_debt': Decimal('1394969434'),
        'note': '7 khách hàng Cambodia hải ngoại',
    },
    {
        'customer_name': 'CÔNG TY TNHH MTV THƯƠNG MẠI DỊCH VỤ KỸ THUẬT ĐẠI THÀNH',
        'employee_code': '9004',
        'employee_name': 'PHẠM VĂN MỪNG',
        'original_debt': Decimal('51710560'),
        'recovered_ytd': Decimal('0'),
        'remaining_debt': Decimal('51710560'),
        'note': 'Hiện tại đang đối chiếu công nợ với Đại Thành',
    },
    {
        'customer_name': 'CÔNG TY TNHH SẢN XUẤT KINH DOANH DỊCH VỤ TIÊN PHÁT',
        'employee_code': '3003',
        'employee_name': 'ĐÀO TIẾN DŨNG',
        'original_debt': Decimal('1379999994'),
        'recovered_ytd': Decimal('350000000'),
        'remaining_debt': Decimal('1029999994'),
        'note': 'Đã thu lũy kế 350 triệu trong năm 2026',
    },
    {
        'customer_name': 'CÔNG TY TNHH THANG MÁY KỸ THUẬT THIÊN HƯNG',
        'employee_code': '3003',
        'employee_name': 'ĐÀO TIẾN DŨNG',
        'original_debt': Decimal('954851411'),
        'recovered_ytd': Decimal('184534343'),
        'remaining_debt': Decimal('770317068'),
        'note': 'Đã thu lũy kế 184.5 triệu trong năm 2026',
    },
    {
        'customer_name': 'ELECTRICAL & MECHANICAL ENGINEERING SERVICE',
        'employee_code': '3003',
        'employee_name': 'ĐÀO TIẾN DŨNG',
        'original_debt': Decimal('29525837'),
        'recovered_ytd': Decimal('0'),
        'remaining_debt': Decimal('29525837'),
        'note': 'Khách hàng dự án cũ',
    },
    {
        'customer_name': 'MR. VANNAK',
        'employee_code': '3003',
        'employee_name': 'ĐÀO TIẾN DŨNG',
        'original_debt': Decimal('8194909'),
        'recovered_ytd': Decimal('0'),
        'remaining_debt': Decimal('8194909'),
        'note': 'Khách hàng cá nhân',
    },
    {
        'customer_name': 'CÔNG TY CỔ PHẦN KỸ THUẬT SAO NAM VIỆT',
        'employee_code': '3003',
        'employee_name': 'ĐÀO TIẾN DŨNG',
        'original_debt': Decimal('369000151'),
        'recovered_ytd': Decimal('229020352'),
        'remaining_debt': Decimal('139979799'),
        'note': 'Đã thu lũy kế 229 triệu trong năm 2026',
    },
    {
        'customer_name': 'CÔNG TY CỔ PHẦN TẬP ĐOÀN THANG MÁY MITSU LIFT',
        'employee_code': '3005',
        'employee_name': 'TRỊNH HOÀNG QUÂN',
        'original_debt': Decimal('330348145'),
        'recovered_ytd': Decimal('0'),
        'remaining_debt': Decimal('330348145'),
        'note': 'Tòa đã tuyên thắng kiện, đang chờ thi hành án',
    },
    {
        'customer_name': 'CÔNG TY TNHH THANG MÁY PHÚC THÀNH',
        'employee_code': '3003',
        'employee_name': 'ĐÀO TIẾN DŨNG',
        'original_debt': Decimal('121033937'),
        'recovered_ytd': Decimal('0'),
        'remaining_debt': Decimal('121033937'),
        'note': 'Đang khởi kiện',
    },
    {
        'customer_name': 'CÔNG TY TNHH KSP VIỆT NAM',
        'employee_code': '9004',
        'employee_name': 'PHẠM VĂN MỪNG',
        'original_debt': Decimal('116049998'),
        'recovered_ytd': Decimal('0'),
        'remaining_debt': Decimal('116049998'),
        'note': 'Đối tác dự án nông nghiệp/nhà xưởng',
    },
    {
        'customer_name': 'CÔNG TY CỔ PHẦN CÔNG NGHIỆP A ME CO',
        'employee_code': '2001',
        'employee_name': 'NGÔ ĐÌNH TRUNG TÂN',
        'original_debt': Decimal('89202659'),
        'recovered_ytd': Decimal('0'),
        'remaining_debt': Decimal('89202659'),
        'note': 'Đang làm hồ sơ khởi kiện',
    },
    {
        'customer_name': 'CÔNG TY CỔ PHẦN GIẢI PHÁP VÀ CÔNG NGHỆ ĐIỀU KHIỂN HỆ THỐNG',
        'employee_code': '2000058',
        'employee_name': 'NGUYỄN BÌNH MINH',
        'original_debt': Decimal('43900999'),
        'recovered_ytd': Decimal('15000000'),
        'remaining_debt': Decimal('28900999'),
        'note': 'Đã khởi kiện lần 1 nhưng tòa chưa xử lý hồ sơ. Chưa khởi kiện lại',
    },
    {
        'customer_name': 'CÔNG TY TNHH TM & KT GIA NGUYỄN',
        'employee_code': 'BEE',
        'employee_name': 'BEE',
        'original_debt': Decimal('64476000'),
        'recovered_ytd': Decimal('0'),
        'remaining_debt': Decimal('64476000'),
        'note': 'Đang kiện ra tòa nhưng chưa thụ lý được do tòa không liên hệ được với NCC',
    },
    {
        'customer_name': 'NGÔ ANH BÌNH - KHÁCH LẺ - BEE',
        'employee_code': 'BEE',
        'employee_name': 'BEE',
        'original_debt': Decimal('190810000'),
        'recovered_ytd': Decimal('0'),
        'remaining_debt': Decimal('190810000'),
        'note': 'Khách lẻ mảng Bee Solar/Energy',
    },
]

# -----------------------------------------------------------------------------
# 2. Danh mục Nợ cũ năm 2025 (Chuẩn Kế toán: 266,666,301 VNĐ)
# -----------------------------------------------------------------------------
OLD_DEBT_2025 = [
    {
        'customer_name': 'LÊ VĂN TÍN (NỢ CŨ 2025)',
        'employee_code': '7011',
        'employee_name': 'LÊ VĂN TÍN',
        'remaining_debt': Decimal('262409544'),
        'note': 'Nợ cũ năm 2025',
    },
    {
        'customer_name': 'CÔNG TY TNHH MTV THIẾT BỊ THANG MÁY HOÀNG TRIỀU',
        'employee_code': '3003',
        'employee_name': 'ĐÀO TIẾN DŨNG',
        'remaining_debt': Decimal('4256757'),
        'note': 'Phát sinh tồn dư năm 2025 (PAR2019/001687)',
    }
]

# -----------------------------------------------------------------------------
# 3. Các khoản bóc tách khỏi dữ liệu MISA TK 1311 để tránh tính trùng vào Nợ 2026
# (Do MISA ghi nhận vào tuổi nợ hiện hành nhưng Kế toán bóc riêng vào Nợ khó đòi hoặc Nợ 2025)
# -----------------------------------------------------------------------------
MISA_1311_EXCLUSIONS_OR_ADJUSTMENTS = {
    # Mã KH: (Trừ Trong hạn, Trừ Quá hạn, Ghi chú)
    'PAR2019/001561': (Decimal('0'), Decimal('89202659'), 'A Me Co (chuyển sang Nợ khó đòi 2022-2024)'),
    'KH2025/000427': (Decimal('0'), Decimal('1384931507'), 'Fuji Lift phần nợ Cambodia (chuyển sang 7 KH Cambodia khó đòi)'),
    'PAR2019/001594': (Decimal('0'), Decimal('108848424'), 'Sao Nam Việt (chuyển sang Nợ khó đòi 2022-2024)'),
    'PAR2021/000189': (Decimal('0'), Decimal('28900999'), 'Điều khiển hệ thống (chuyển sang Nợ khó đòi 2022-2024)'),
    'PAR2019/001687': (Decimal('0'), Decimal('4256757'), 'Hoàng Triều (chuyển sang Nợ cũ 2025)'),
    'KH2025/000411': (Decimal('0'), Decimal('262409544'), 'Agro Milk hóa đơn nợ cũ 2025 của Lê Văn Tín (chuyển sang Nợ cũ 2025)'),
}

# -----------------------------------------------------------------------------
# 4. Gán bổ sung / Điều chỉnh Nhân viên phụ trách theo đúng chuẩn Báo cáo Kế toán
# -----------------------------------------------------------------------------
REPORT_EMPLOYEE_OVERRIDES = {
    # Khách hàng AGRO MILK TÂY NINH -> Gán cho LÊ VĂN TÍN (7011) ở mảng Sản xuất
    'KH2025/000411': '7011',
    # Khách hàng CÔNG TY CỔ PHẦN NHỰA ĐẠI LIÊN -> Gán cho NGUYỄN ĐỨC THƯỞNG (2000017)
    'PAR2024/001743': '2000017',
}

# Backward compatibility definitions
HISTORICAL_BAD_DEBT_KEYWORDS = [
    "CAMBODIA", "TIÊN PHÁT", "THIÊN HƯNG", "ELECTRICAL & MECHANICAL",
    "VANNAK", "SAO NAM VIỆT", "MITSU LIFT", "PHÚC THÀNH", "KSP VIỆT NAM",
    "A ME CO", "ĐIỀU KHIỂN HỆ THỐNG", "GIA NGUYỄN", "BEE"
]

HISTORICAL_BAD_DEBT_CUSTOMER_CODES = [
    "PAR2019/001547", "PAR2022/002753", "PAR2023/006728", "PAR2023/000141",
    "PAR2022/002180", "PAR2019/001634", "PAR2019/002636", "PAR2019/001594",
    "KH2025/000099", "PAR2019/002444", "PAR2019/002016", "PAR2019/001568",
    "PAR2019/000028", "PAR2020/003100", "PAR2023/007181", "PAR2019/001569",
    "PAR2022/002492", "PAR2022/001620", "PAR2019/001561", "PAR2021/000189",
    "PAR2019/001129", "KH2025/000556", "PAR2023/000820"
]

OLD_DEBT_2025_CUSTOMER_CODES = ["7011"]


def get_customer_debt_category(customer):
    if not customer:
        return 'CURRENT_2026'
    code = (customer.code or '').strip()
    name_upper = (customer.name or '').upper()
    if code in OLD_DEBT_2025_CUSTOMER_CODES or 'LÊ VĂN TÍN' in name_upper:
        return 'OLD_DEBT_2025'
    if code in HISTORICAL_BAD_DEBT_CUSTOMER_CODES:
        return 'BAD_DEBT_2022_2024'
    for kw in HISTORICAL_BAD_DEBT_KEYWORDS:
        if kw in name_upper:
            return 'BAD_DEBT_2022_2024'
    return 'CURRENT_2026'


def get_historical_bad_debt_items():
    return HISTORICAL_BAD_DEBT_2022_2024


def get_old_debt_2025_items():
    return OLD_DEBT_2025


def get_bad_debt_for_employee(employee_code):
    if not employee_code:
        return Decimal('0')
    code_clean = str(employee_code).strip()
    total = Decimal('0')
    for item in HISTORICAL_BAD_DEBT_2022_2024:
        if str(item.get('employee_code', '')).strip() == code_clean:
            total += item['remaining_debt']
    return total


def get_old_debt_2025_for_employee(employee_code):
    if not employee_code:
        return Decimal('0')
    code_clean = str(employee_code).strip()
    total = Decimal('0')
    for item in OLD_DEBT_2025:
        if str(item.get('employee_code', '')).strip() == code_clean:
            total += item['remaining_debt']
    return total
