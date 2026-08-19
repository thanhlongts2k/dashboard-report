"""
Module: user_provisioner.py
Dịch vụ Quản lý & Đồng bộ Tài khoản Người dùng (Employee User Provisioning & Google SSO IAM)
Hỗ trợ:
- Tự động tạo/cập nhật tài khoản User từ danh sách Employee.
- Phân quyền tự động vào 4 Groups: BOD_ADMIN, BU_HEAD, SALES, VIEWER.
- Tách Họ & Tên chuẩn tiếng Việt (first_name = Tên, last_name = Họ & Tên đệm).
- Just-In-Time (JIT) provisioning khi nhân viên đăng nhập Google SSO lần đầu.
"""

import logging
from django.contrib.auth.models import User, Group
from django.db import transaction
from accounting.models import Employee, EmployeeAssignment

logger = logging.getLogger(__name__)

# Danh sách 4 Django Groups chuẩn
AUTH_GROUPS = {
    'BOD_ADMIN': 'Ban Tổng Giám đốc / Quản trị viên cấp cao',
    'BU_HEAD': 'Trưởng Khối BU / Giám đốc Trung tâm / Trưởng bộ phận',
    'SALES': 'Nhân viên Kinh doanh / Chuyên viên Bán hàng',
    'VIEWER': 'Nhân viên nghiệp vụ / Xem báo cáo (Mặc định)',
}


def ensure_auth_groups_exist():
    """
    Đảm bảo 4 Django Groups luôn tồn tại trong hệ thống.
    """
    created_groups = []
    for group_name in AUTH_GROUPS.keys():
        group, created = Group.objects.get_or_create(name=group_name)
        if created:
            created_groups.append(group_name)
    if created_groups:
        logger.info(f"✅ Đã khởi tạo các Django Group mới: {created_groups}")
    return created_groups


def split_vietnamese_name(full_name: str):
    """
    Tách Họ & Tên theo chuẩn tiếng Việt:
    - first_name (Tên): Từ cuối cùng trong full_name.
    - last_name (Họ & Tên đệm): Các từ còn lại phía trước.
    Ví dụ: 'Nguyễn Thanh Long' -> first_name='Long', last_name='Nguyễn Thanh'
           'Long' -> first_name='Long', last_name=''
    """
    name = (full_name or '').strip()
    if not name:
        return '', ''
    
    parts = name.split()
    if len(parts) == 1:
        return parts[0], ''
    
    first_name = parts[-1]
    last_name = ' '.join(parts[:-1])
    return first_name, last_name


ROLE_PRIORITY = {
    'BOD_ADMIN': 4,
    'BU_HEAD': 3,
    'SALES': 2,
    'VIEWER': 1,
}

# 1. CENTRALIZED BU DEFINITIONS (Single Source of Truth)
BU_DEFINITIONS = {
    'BU_ELEVATOR': {
        'code': 'BU_ELEVATOR',
        'name': 'Thang máy',
        'frontend_key': 'elevator',
        'is_commercial': True,
        'keywords': ['elevator', 'thang máy', 'bu_elevator']
    },
    'BU_IBIZ PREMIUM': {
        'code': 'BU_IBIZ PREMIUM',
        'name': 'Thiết bị điện cao cấp',
        'frontend_key': 'ibizPremium',
        'is_commercial': True,
        'keywords': ['premium', 'bu_premium', 'ibiz premium']
    },
    'BU_IBIZ VALUE': {
        'code': 'BU_IBIZ VALUE',
        'name': 'Thiết bị điện phổ thông',
        'frontend_key': 'ibizValue',
        'is_commercial': True,
        'keywords': ['value', 'bu_value', 'ibiz value']
    },
    'BU_AGRITECH': {
        'code': 'BU_AGRITECH',
        'name': 'Nông nghiệp công nghệ cao',
        'frontend_key': 'agritech',
        'is_commercial': True,
        'keywords': ['agritech', 'bu_agritech']
    },
    'BU_ECO': {
        'code': 'BU_ECO',
        'name': 'ECO (Solar)',
        'frontend_key': 'eco',
        'is_commercial': True,
        'keywords': ['eco', 'bu_eco', 'solar']
    },
    'BU_MANUFACTURING': {
        'code': 'BU_MANUFACTURING',
        'name': 'Sản xuất - Nhà máy',
        'frontend_key': 'manufacturing',
        'is_commercial': True,
        'keywords': ['manufacturing', 'sản xuất', 'nhà máy', 'bu_manufacturing', 'bu manufacturing']
    },
    'ĐTCT': {
        'code': 'ĐTCT',
        'name': 'đầu tư cho thuê / ĐTCT',
        'frontend_key': 'dtct',
        'is_commercial': True,
        'keywords': ['đtct', 'dtct', 'cho thuê', 'đầu tư cho thuê', 'đầu tư cho thuê', 'đối tác', 'đầu tư cho thuê', 'bu_dtct', 'bu_đtct']
    },
    'Oversea': {
        'code': 'Oversea',
        'name': 'Oversea',
        'frontend_key': 'oversea',
        'is_commercial': True,
        'keywords': ['oversea', 'campuchia']
    },
}

# 2. DEPARTMENT -> BUSINESS UNIT REGISTRY (Ánh xạ trực tiếp từ CSDL, hỗ trợ case-insensitive)
DEPARTMENT_BU_REGISTRY = {
    'BU_ELEVATOR': ['BU_ELEVATOR'],
    'BU_PREMIUM': ['BU_IBIZ PREMIUM'],
    'BU_IBIZ PREMIUM': ['BU_IBIZ PREMIUM'],
    'BU_IBIZ_PREMIUM': ['BU_IBIZ PREMIUM'],
    'BU_VALUE': ['BU_IBIZ VALUE'],
    'BU_IBIZ VALUE': ['BU_IBIZ VALUE'],
    'BU_IBIZ_VALUE': ['BU_IBIZ VALUE'],
    'BU_MANUFACTURING': ['BU_MANUFACTURING'],
    'BU_AGRITECH-ECO': ['BU_AGRITECH', 'BU_ECO'],
    'BU_AGRITECH_ECO': ['BU_AGRITECH', 'BU_ECO'],
    'BU_AGRITECH - ECO': ['BU_AGRITECH', 'BU_ECO'],
    'BU_AGRITECH': ['BU_AGRITECH'],
    'BU_ECO': ['BU_ECO'],
    'DA_KD2': ['BU_MANUFACTURING'],
    'DA_QLDA&SX': ['BU_MANUFACTURING'],
    'DA_NCPT': ['BU_MANUFACTURING'],
    'KD_BH1MN': ['BU_IBIZ VALUE'],
    'CA_KGH': ['Oversea'],
    'OVERSEA': ['Oversea'],
    'ĐTCT': ['ĐTCT'],
    'DTCT': ['ĐTCT'],
    'BU_DTCT': ['ĐTCT'],
    'BU_ĐTCT': ['ĐTCT'],
}

BOD_TITLES = [
    'ban giám đốc', 'tổng giám đốc', 'chủ tịch', 'giám đốc vận hành',
    'giám đốc tài chính', 'giám đốc sản xuất và kỹ thuật', 'kế toán trưởng',
    'ban tổng giám đốc', 'hội đồng quản trị', 'cco'
]

BU_HEAD_TITLES = [
    'trưởng bu', 'trưởng bộ phận', 'tbp', 'trưởng đơn vị',
    'giám đốc kinh doanh', 'giám đốc kdtb', 'gđ chi nhánh',
    'quản lý kinh doanh', 'quản lý bán hàng', 'trưởng bp',
    'trưởng nhóm', 'site manager', 'tp quản lý dự án', 'quản lý dự án',
    'giám sát dự án', 'quản lý nhà máy'
]

SALES_TITLES = [
    'kinh doanh', 'bán hàng', 'sale', 'sales', ' kd', 'kd ',
    'bh project', 'phát triển thị trường', 'sale admin'
]

DEFAULT_ROLE_TABS = {
    'BOD_ADMIN': ['dashboard', 'bu_detail', 'inventory', 'debt_collection', 'aging'],
    'BU_HEAD': ['bu_detail', 'inventory', 'debt_collection', 'aging'],
    'SALES': ['aging'],
    'VIEWER': ['aging'],
}


def is_commercial_department(department, code_override=None, name_override=None):
    """
    Kiểm tra phòng ban có thuộc các BU kinh doanh thương mại hay không.
    Trả về: (is_commercial: bool, bu_code: str, bu_name: str, frontend_key: str)
    """
    if not department and not code_override and not name_override:
        return False, None, None, None
    
    code = (code_override or (department.department_code if department else '') or '').strip()
    norm_code = code.upper()
    if norm_code in DEPARTMENT_BU_REGISTRY:
        first_bu_code = DEPARTMENT_BU_REGISTRY[norm_code][0]
        bu_def = BU_DEFINITIONS.get(first_bu_code, {})
        return True, bu_def.get('code', first_bu_code), bu_def.get('name', first_bu_code), bu_def.get('frontend_key')
    
    # Fuzzy keyword fallback
    combined = f"{code} {name_override or (department.department_name if department else '')}".lower()
    for bu_code, info in BU_DEFINITIONS.items():
        if any(kw in combined for kw in info['keywords']):
            return True, info['code'], info['name'], info.get('frontend_key')
            
    return False, code or (department.department_code if department else None), name_override or (department.department_name if department else None), None


def resolve_user_rbac(employee: Employee):
    """
    ENGINE PHÂN QUYỀN HỆ THỐNG HÓA DỰA TRÊN DỮ LIỆU CSDL (Data-Driven RBAC Engine).
    Thuật toán phân giải tổng quát:
    1. Quét toàn bộ active EmployeeAssignment của nhân sự.
    2. Ánh xạ trực tiếp Department -> BusinessUnit qua DEPARTMENT_BU_REGISTRY.
    3. Tra cứu BusinessUnit.manager trực tiếp từ CSDL để gom các BU quản lý đứng tên.
    4. Xác định vai trò cho từng BU và tính toán primary_role cao nhất.
    5. BOD_ADMIN tự động được cấp toàn quyền trên 8 Commercial BUs.
    """
    if not employee:
        return {
            'primary_role': 'VIEWER',
            'role': 'VIEWER',
            'allowed_tabs': ['aging'],
            'managed_bus': [],
            'assigned_bus': [],
            'managed_bu_keys': [],
            'assigned_bu_keys': [],
            'assignments': [],
            'primary_bu_code': None,
            'primary_bu_name': None,
            'primary_title': None,
            'primary_department': None,
            'is_commercial': False,
        }

    from django.db.models import Q
    from django.utils import timezone
    today = timezone.now().date()

    assignments_qs = employee.assignments.filter(
        Q(end_date__isnull=True) | Q(end_date__gte=today)
    ).order_by('-start_date')

    if not assignments_qs.exists():
        assignments_qs = employee.assignments.order_by('-start_date').all()

    assignments_detail = []
    highest_role = 'VIEWER'
    highest_score = 1
    managed_bus = []
    assigned_bus = []
    managed_bu_keys = []
    assigned_bu_keys = []
    primary_assignment = None

    # Step 1: Quét toàn bộ các phân công công tác
    for ass in assignments_qs:
        title_name = ass.title.title_name if ass.title else ''
        title_lower = title_name.lower().strip()
        dept_code = ass.department.department_code if ass.department else ''
        dept_name = ass.department.department_name if ass.department else ''
        combined = f"{title_lower} {dept_name.lower()}"

        # 1.1 Xác định vai trò nghiệp vụ (Role Classification)
        if any(k in combined for k in BOD_TITLES) or any(k in title_lower for k in BOD_TITLES) or employee.employee_code == '2001':
            ass_role = 'BOD_ADMIN'
        elif any(k in title_lower for k in BU_HEAD_TITLES):
            ass_role = 'BU_HEAD'
        elif any(k in title_lower for k in SALES_TITLES):
            ass_role = 'SALES'
        else:
            ass_role = 'VIEWER'

        # 1.2 Ánh xạ Phòng ban sang danh sách BU
        norm_dept_code = (dept_code or '').strip().upper()
        bu_codes = DEPARTMENT_BU_REGISTRY.get(norm_dept_code, [])
        if not bu_codes and norm_dept_code in BU_DEFINITIONS:
            bu_codes = [norm_dept_code]
        is_commercial = len(bu_codes) > 0

        if not is_commercial:
            actual_role = ass_role if ass_role == 'BOD_ADMIN' else 'VIEWER'
            detail_item = {
                'bu_code': dept_code,
                'bu_name': dept_name,
                'frontend_key': None,
                'is_commercial': False,
                'role': actual_role,
                'title': title_name,
                'department': dept_name,
                'start_date': str(ass.start_date) if ass.start_date else None,
                'end_date': str(ass.end_date) if ass.end_date else None,
            }
            assignments_detail.append(detail_item)
            if not primary_assignment:
                primary_assignment = detail_item

            score = ROLE_PRIORITY.get(actual_role, 1)
            if score > highest_score:
                highest_score = score
                highest_role = actual_role
        else:
            for b_code in bu_codes:
                bu_def = BU_DEFINITIONS[b_code]
                f_key = bu_def['frontend_key']
                b_name = bu_def['name']

                detail_item = {
                    'bu_code': b_code,
                    'bu_name': b_name,
                    'frontend_key': f_key,
                    'is_commercial': True,
                    'role': ass_role,
                    'title': title_name,
                    'department': dept_name,
                    'start_date': str(ass.start_date) if ass.start_date else None,
                    'end_date': str(ass.end_date) if ass.end_date else None,
                }
                assignments_detail.append(detail_item)
                if not primary_assignment:
                    primary_assignment = detail_item

                if b_code not in assigned_bus:
                    assigned_bus.append(b_code)
                if f_key and f_key not in assigned_bu_keys:
                    assigned_bu_keys.append(f_key)

                if ass_role in ['BU_HEAD', 'BOD_ADMIN']:
                    if b_code not in managed_bus:
                        managed_bus.append(b_code)
                    if f_key and f_key not in managed_bu_keys:
                        managed_bu_keys.append(f_key)

                score = ROLE_PRIORITY.get(ass_role, 1)
                if score > highest_score:
                    highest_score = score
                    highest_role = ass_role

    # Step 2: Quét BusinessUnit.manager trực tiếp từ CSDL (Layer 2: Management)
    from accounting.models import BusinessUnit
    try:
        bu_managed_qs = BusinessUnit.objects.filter(
            Q(manager__iexact=employee.full_name) |
            Q(manager__icontains=employee.full_name) |
            Q(manager__icontains=employee.employee_code)
        )
        for bu in bu_managed_qs:
            b_code = bu.code
            b_name = bu.name
            b_def = BU_DEFINITIONS.get(b_code)
            f_key = b_def['frontend_key'] if b_def else ('dtct' if 'đtct' in b_code.lower() or 'thuê' in b_name.lower() else b_code.lower())
            if b_def:
                b_name = b_def['name']

            if b_code not in managed_bus:
                managed_bus.append(b_code)
            if b_code not in assigned_bus:
                assigned_bus.append(b_code)
            if f_key and f_key not in managed_bu_keys:
                managed_bu_keys.append(f_key)
            if f_key and f_key not in assigned_bu_keys:
                assigned_bu_keys.append(f_key)

            if highest_role in ['VIEWER', 'SALES']:
                highest_role = 'BU_HEAD'
                highest_score = ROLE_PRIORITY['BU_HEAD']

            if not any(a.get('bu_code') == b_code for a in assignments_detail):
                assignments_detail.append({
                    'bu_code': b_code,
                    'bu_name': b_name,
                    'frontend_key': f_key,
                    'is_commercial': True,
                    'role': 'BU_HEAD',
                    'title': f'Trưởng {b_name}',
                    'department': b_name,
                    'start_date': str(today),
                    'end_date': None,
                })
    except Exception as e:
        logger.warning(f"Lỗi tra cứu BusinessUnit manager cho NV {employee.employee_code}: {e}")

    # Step 3: Quét Danh mục Khách hàng phân công phụ trách (Layer 3: Customer Portfolio)
    from accounting.models import Customer
    try:
        cust_bus_qs = Customer.objects.filter(
            assigned_employee=employee,
            business_unit__isnull=False
        ).values_list('business_unit__code', flat=True).distinct()

        for b_raw_code in cust_bus_qs:
            norm_b_code = (b_raw_code or '').strip()
            if norm_b_code.upper() in DEPARTMENT_BU_REGISTRY:
                matched_codes = DEPARTMENT_BU_REGISTRY[norm_b_code.upper()]
            elif norm_b_code in BU_DEFINITIONS:
                matched_codes = [norm_b_code]
            else:
                matched_codes = []

            for b_code in matched_codes:
                bu_def = BU_DEFINITIONS[b_code]
                f_key = bu_def['frontend_key']
                b_name = bu_def['name']

                if b_code not in assigned_bus:
                    assigned_bus.append(b_code)
                if f_key and f_key not in assigned_bu_keys:
                    assigned_bu_keys.append(f_key)

                if highest_role == 'VIEWER':
                    highest_role = 'SALES'
                    highest_score = ROLE_PRIORITY['SALES']

                if not any(a.get('bu_code') == b_code for a in assignments_detail):
                    assignments_detail.append({
                        'bu_code': b_code,
                        'bu_name': b_name,
                        'frontend_key': f_key,
                        'is_commercial': True,
                        'role': 'SALES',
                        'title': f'Phụ trách Khách hàng ({b_name})',
                        'department': b_name,
                        'start_date': str(today),
                        'end_date': None,
                    })
    except Exception as e:
        logger.warning(f"Lỗi tra cứu Customer portfolio cho NV {employee.employee_code}: {e}")

    # Step 4: Quét Giao dịch Doanh số thực tế (Layer 4: Sales Operations)
    from accounting.models import SalesTransaction
    try:
        sales_bus_qs = SalesTransaction.objects.filter(
            employee=employee,
            business_unit__isnull=False
        ).values_list('business_unit__code', flat=True).distinct()

        for b_raw_code in sales_bus_qs:
            norm_b_code = (b_raw_code or '').strip()
            if norm_b_code.upper() in DEPARTMENT_BU_REGISTRY:
                matched_codes = DEPARTMENT_BU_REGISTRY[norm_b_code.upper()]
            elif norm_b_code in BU_DEFINITIONS:
                matched_codes = [norm_b_code]
            else:
                matched_codes = []

            for b_code in matched_codes:
                bu_def = BU_DEFINITIONS[b_code]
                f_key = bu_def['frontend_key']
                b_name = bu_def['name']

                if b_code not in assigned_bus:
                    assigned_bus.append(b_code)
                if f_key and f_key not in assigned_bu_keys:
                    assigned_bu_keys.append(f_key)

                if highest_role == 'VIEWER':
                    highest_role = 'SALES'
                    highest_score = ROLE_PRIORITY['SALES']

                if not any(a.get('bu_code') == b_code for a in assignments_detail):
                    assignments_detail.append({
                        'bu_code': b_code,
                        'bu_name': b_name,
                        'frontend_key': f_key,
                        'is_commercial': True,
                        'role': 'SALES',
                        'title': f'Kinh doanh ({b_name})',
                        'department': b_name,
                        'start_date': str(today),
                        'end_date': None,
                    })
    except Exception as e:
        logger.warning(f"Lỗi tra cứu Sales transactions cho NV {employee.employee_code}: {e}")

    # Step 5: BOD_ADMIN tự động có toàn quyền 8 Commercial BUs
    if highest_role == 'BOD_ADMIN':
        for b_code, b_def in BU_DEFINITIONS.items():
            if b_code not in assigned_bus:
                assigned_bus.append(b_code)
            if b_code not in managed_bus:
                managed_bus.append(b_code)
            f_key = b_def['frontend_key']
            if f_key and f_key not in assigned_bu_keys:
                assigned_bu_keys.append(f_key)
            if f_key and f_key not in managed_bu_keys:
                managed_bu_keys.append(f_key)

    # Chọn primary_assignment tốt nhất: Ưu tiên vai trò cao nhất, nếu cùng mức vai trò thì ưu tiên BU thương mại (is_commercial = True)
    best_assignment = None
    best_assign_score = -1
    for a in assignments_detail:
        score = ROLE_PRIORITY.get(a.get('role'), 0) * 10 + (2 if a.get('is_commercial') else 0)
        if score > best_assign_score:
            best_assign_score = score
            best_assignment = a

    primary_assignment = best_assignment or (assignments_detail[0] if assignments_detail else None)

    allowed_tabs = DEFAULT_ROLE_TABS.get(highest_role, ['aging'])

    return {
        'primary_role': highest_role,
        'role': highest_role,
        'allowed_tabs': allowed_tabs,
        'managed_bus': managed_bus,
        'assigned_bus': assigned_bus,
        'managed_bu_keys': managed_bu_keys,
        'assigned_bu_keys': assigned_bu_keys,
        'assignments': assignments_detail,
        'primary_bu_code': primary_assignment.get('bu_code') if primary_assignment else None,
        'primary_bu_name': primary_assignment.get('bu_name') if primary_assignment else None,
        'primary_title': primary_assignment.get('title') if primary_assignment else None,
        'primary_department': primary_assignment.get('department') if primary_assignment else None,
        'is_commercial': primary_assignment.get('is_commercial', False) if primary_assignment else False,
    }


def get_employee_assignments_info(employee: Employee):
    """
    Wrapper gọi hàm phân giải Data-Driven RBAC Engine.
    """
    return resolve_user_rbac(employee)


def determine_employee_role(employee: Employee):
    """
    Xác định vai trò (Group) chính của nhân viên dựa trên Data-Driven RBAC Engine.
    """
    info = resolve_user_rbac(employee)
    return info['primary_role'], info['primary_title'] or 'Nhân viên'


def provision_user_for_employee(employee: Employee, dry_run: bool = False):
    """
    Đồng bộ hoặc tạo mới User cho 1 nhân viên cụ thể.
    """
    email = (employee.email or '').strip().lower()
    if not email:
        return {
            'success': False,
            'reason': f'Nhân viên [{employee.employee_code}] - {employee.full_name} không có email.'
        }

    role_group_name, title_name = determine_employee_role(employee)
    first_name, last_name = split_vietnamese_name(employee.full_name)

    if dry_run:
        return {
            'success': True,
            'dry_run': True,
            'email': email,
            'first_name': first_name,
            'last_name': last_name,
            'role_group': role_group_name,
            'title': title_name,
            'employee_code': employee.employee_code,
            'full_name': employee.full_name
        }

    with transaction.atomic():
        ensure_auth_groups_exist()
        target_group = Group.objects.get(name=role_group_name)

        user, is_created = User.objects.get_or_create(
            username=email,
            defaults={
                'email': email,
                'first_name': first_name,
                'last_name': last_name,
                'is_active': True
            }
        )

        user.first_name = first_name
        user.last_name = last_name
        user.email = email
        user.is_active = True
        user.set_unusable_password()
        user.save()

        all_app_groups = Group.objects.filter(name__in=AUTH_GROUPS.keys())
        for g in all_app_groups:
            if g.name != role_group_name:
                user.groups.remove(g)

        user.groups.add(target_group)

        if employee.user_id != user.id:
            employee.user = user
            employee.save(update_fields=['user'])

        logger.info(f"✅ Provisioning thành công User [{email}] ({role_group_name}) cho NV [{employee.employee_code}] - {employee.full_name}")

        return {
            'success': True,
            'dry_run': False,
            'action': 'CREATE' if is_created else 'UPDATE',
            'user_id': user.id,
            'username': user.username,
            'email': user.email,
            'first_name': user.first_name,
            'last_name': user.last_name,
            'role_group': role_group_name,
            'title': title_name,
            'employee_code': employee.employee_code,
            'full_name': employee.full_name
        }


def get_user_role_info(user: User):
    """
    Lấy thông tin quyền hạn và profile mở rộng của User để trả về cho Frontend khi đăng nhập thành công.
    """
    groups = list(user.groups.values_list('name', flat=True))
    employee = getattr(user, 'employee_profile', None)

    info = resolve_user_rbac(employee)
    primary_role = info['primary_role']

    if user.is_superuser or 'BOD_ADMIN' in groups:
        primary_role = 'BOD_ADMIN'
    elif 'BU_HEAD' in groups and ROLE_PRIORITY.get(primary_role, 1) < ROLE_PRIORITY['BU_HEAD']:
        primary_role = 'BU_HEAD'
    elif 'SALES' in groups and ROLE_PRIORITY.get(primary_role, 1) < ROLE_PRIORITY['SALES']:
        primary_role = 'SALES'

    managed_bus = list(info['managed_bus'])
    assigned_bus = list(info['assigned_bus'])
    managed_bu_keys = list(info['managed_bu_keys'])
    assigned_bu_keys = list(info['assigned_bu_keys'])

    if primary_role == 'BOD_ADMIN':
        for b_code, b_def in BU_DEFINITIONS.items():
            if b_code not in assigned_bus:
                assigned_bus.append(b_code)
            if b_code not in managed_bus:
                managed_bus.append(b_code)
            f_key = b_def['frontend_key']
            if f_key and f_key not in assigned_bu_keys:
                assigned_bu_keys.append(f_key)
            if f_key and f_key not in managed_bu_keys:
                managed_bu_keys.append(f_key)

    allowed_tabs = DEFAULT_ROLE_TABS.get(primary_role, ['aging'])

    return {
        'id': user.id,
        'user_id': user.id,
        'username': user.username,
        'email': user.email,
        'full_name': employee.full_name if employee else f"{user.last_name} {user.first_name}".strip() or user.username,
        'first_name': user.first_name,
        'last_name': user.last_name,
        'is_active': user.is_active,
        'is_superuser': user.is_superuser,
        'role': primary_role,
        'primary_role': primary_role,
        'groups': groups,
        'employee_code': employee.employee_code if employee else None,
        'bu_code': info['primary_bu_code'],
        'bu_name': info['primary_bu_name'],
        'is_commercial': info['is_commercial'],
        'department': info['primary_department'],
        'title': info['primary_title'],
        'allowed_tabs': allowed_tabs,
        'managed_bus': managed_bus,
        'assigned_bus': assigned_bus,
        'managed_bu_keys': managed_bu_keys,
        'assigned_bu_keys': assigned_bu_keys,
        'assignments': info['assignments'],
    }
