"""
Service tính toán và tổng hợp Báo cáo Doanh thu theo Nhân viên Sales
Đa cấp: Công ty -> BU -> Miền / Nhóm -> Nhân viên kinh doanh
"""
from decimal import Decimal
from datetime import datetime, date
from django.db.models import Sum, Case, When, DecimalField, Q
from django.core.exceptions import PermissionDenied

from accounting.models import Employee, BusinessUnit, SalesTransaction, Customer, SalesTarget
from accounting.services.user_provisioner import get_user_role_info

def get_hisa_customer_ids():
    """Lấy ID của các khách hàng HiSa để loại trừ khỏi doanh thu."""
    return list(Customer.objects.filter(
        Q(name__icontains='HISA') | Q(code__icontains='HISA') | Q(code='PAR2019/000883')
    ).values_list('id', flat=True))

def compute_rate(actual, target):
    """Tính tỷ lệ % hoàn thành thực tế / kế hoạch."""
    if not target or target == 0:
        return 0.0
    return round(float(actual / target) * 100, 1)

def resolve_target_bu_codes(bu_code_input):
    """
    Chuẩn hóa chuỗi bu_code_input từ URL / API (slug, hoa/thường, space, underscore...)
    thành danh sách mã BusinessUnit trong DB.
    """
    if not bu_code_input or bu_code_input.upper() in ('ALL', 'ROOT', ''):
        return None

    clean = bu_code_input.strip().lower().replace('-', '').replace('_', '').replace(' ', '')

    if 'premium' in clean:
        return ['BU_IBIZ PREMIUM']
    if 'value' in clean:
        return ['BU_IBIZ VALUE']
    if 'elevator' in clean or 'thang' in clean:
        return ['BU_ELEVATOR']
    if clean in ('eco', 'bueco'):
        return ['BU_ECO', 'BU_AGRITECH', 'BU_SAB', 'SAB']
    if clean in ('agritech', 'buagritech'):
        return ['BU_AGRITECH']
    if clean in ('sab', 'busab'):
        return ['BU_SAB', 'SAB']
    if 'manufacturing' in clean or 'sanxuat' in clean:
        return ['BU_MANUFACTURING']
    if 'dtct' in clean or 'chothue' in clean:
        return ['ĐTCT', 'BU_DTCT']

    # Tìm gần đúng trong BusinessUnit
    matched = list(BusinessUnit.objects.filter(
        Q(code__iexact=bu_code_input) |
        Q(code__iexact=bu_code_input.replace('_', ' ')) |
        Q(code__iexact=bu_code_input.replace(' ', '_'))
    ).values_list('code', flat=True))

    return matched if matched else [bu_code_input]

def get_sales_performance_data(target_date=None, period=None, bu_code=None, user=None):
    """
    Tính toán hiệu suất bán hàng theo nhân viên và tổng hợp cây phân cấp.
    :param target_date: date hoặc str (YYYY-MM-DD), mặc định hôm nay hoặc ngày có data cuối
    :param period: str (YYYY-MM), mặc định theo target_date
    :param bu_code: str mã BU (hoặc 'ALL' / None)
    :param user: User object hiện tại để kiểm tra RBAC
    """
    # 1. Chuẩn hóa ngày và kỳ báo cáo
    if isinstance(target_date, str):
        try:
            parsed_date = datetime.strptime(target_date, '%Y-%m-%d').date()
        except ValueError:
            parsed_date = date.today()
    elif isinstance(target_date, date):
        parsed_date = target_date
    else:
        # Lấy ngày giao dịch gần nhất
        latest_tx = SalesTransaction.objects.order_by('-posting_date').first()
        parsed_date = latest_tx.posting_date if latest_tx else date.today()

    if not period:
        period = parsed_date.strftime('%Y-%m')
    else:
        # Nếu period được truyền vào, kiểm tra nếu parsed_date không thuộc period thì chỉnh về cuối tháng của period
        if parsed_date.strftime('%Y-%m') != period:
            p_year, p_month = map(int, period.split('-'))
            import calendar
            last_day = calendar.monthrange(p_year, p_month)[1]
            parsed_date = date(p_year, p_month, last_day)

    curr_year = parsed_date.year
    curr_month = parsed_date.month
    start_of_month = parsed_date.replace(day=1)
    start_of_year = date(curr_year, 1, 1)

    # 2. Chuẩn hóa danh sách mã BU mục tiêu
    resolved_bu_codes = resolve_target_bu_codes(bu_code)

    # 3. Kiểm tra Phân quyền RBAC
    allowed_bus = None
    is_bod = True
    if user and user.is_authenticated:
        role_info = get_user_role_info(user)
        primary_role = role_info.get('primary_role')
        if not (user.is_superuser or primary_role == 'BOD_ADMIN'):
            is_bod = False
            managed_bus = role_info.get('managed_bus', [])
            allowed_bus = managed_bus
            # Nếu user yêu cầu bu_code cụ thể nhưng không có quyền
            if resolved_bu_codes:
                if not any(c in allowed_bus for c in resolved_bu_codes):
                    raise PermissionDenied("Bạn không có quyền xem báo cáo của Đơn vị kinh doanh này.")
            else:
                resolved_bu_codes = allowed_bus

    # 4. Truy vấn các mục tiêu kế hoạch (SalesTarget) của kỳ
    exact_targets = SalesTarget.objects.filter(period=period, is_active=True).select_related('employee', 'business_unit')
    is_exact_period = exact_targets.exists()

    if is_exact_period:
        targets_qs = exact_targets
    else:
        # Fallback lấy mục tiêu gần nhất nếu period hiện tại chưa được seed (ví dụ xem 2026-09)
        latest_target = SalesTarget.objects.filter(is_active=True).order_by('-period').first()
        if latest_target:
            targets_qs = SalesTarget.objects.filter(period=latest_target.period, is_active=True).select_related('employee', 'business_unit')
        else:
            targets_qs = SalesTarget.objects.none()

    if resolved_bu_codes:
        targets_qs = targets_qs.filter(business_unit__code__in=resolved_bu_codes)

    targets_list = list(targets_qs.order_by('business_unit__code', 'display_order', 'id'))

    # 5. Truy vấn Doanh thu thực tế (SalesTransaction)
    hisa_ids = get_hisa_customer_ids()
    internal_groups = ['Internal']

    # Filter transactions trong năm tính đến target_date
    tx_filter = Q(
        posting_date__gte=start_of_year,
        posting_date__lte=parsed_date,
        customer__has_revenue=True
    )
    if hisa_ids:
        tx_filter &= ~Q(customer_id__in=hisa_ids)
    if internal_groups:
        tx_filter &= ~Q(customer__group__code__in=internal_groups)

    if resolved_bu_codes:
        tx_filter &= Q(business_unit__code__in=resolved_bu_codes)

    # 1 Query duy nhất với conditional aggregation tối ưu
    dec_field = DecimalField(max_digits=18, decimal_places=2)
    aggregations = SalesTransaction.objects.filter(tx_filter).values(
        'business_unit__code',
        'customer__assigned_employee_id'
    ).annotate(
        day_actual=Sum(
            Case(
                When(posting_date=parsed_date, then='actual_sales'),
                default=Decimal('0'),
                output_field=dec_field
            )
        ),
        month_actual=Sum(
            Case(
                When(posting_date__gte=start_of_month, posting_date__lte=parsed_date, then='actual_sales'),
                default=Decimal('0'),
                output_field=dec_field
            )
        ),
        year_actual=Sum('actual_sales')
    )

    # Map số liệu thực tế theo (bu_code, employee_id)
    actuals_map = {}
    for row in aggregations:
        key = (row['business_unit__code'], row['customer__assigned_employee_id'])
        actuals_map[key] = {
            'day_actual': row['day_actual'] or Decimal('0'),
            'month_actual': row['month_actual'] or Decimal('0'),
            'year_actual': row['year_actual'] or Decimal('0'),
        }

    # 5. Xây dựng Cây Phân Cấp (Tree Hierarchy)
    # Cấu trúc: Group -> Region -> Sales
    # Đảm bảo hiển thị cả khối ECO + AGRITECH theo đúng mẫu kế toán nếu có
    bu_nodes = {}

    def empty_metrics():
        return {
            'year_target': Decimal('0'),
            'year_actual': Decimal('0'),
            'year_rate': 0.0,
            'prev_target': Decimal('0'),
            'prev_actual': Decimal('0'),
            'prev_rate': 0.0,
            'month_target': Decimal('0'),
            'month_actual': Decimal('0'),
            'month_rate': 0.0,
            'day_revenue': Decimal('0'),
        }

    def add_metrics(parent_m, child_m):
        parent_m['year_target'] += child_m['year_target']
        parent_m['year_actual'] += child_m['year_actual']
        parent_m['prev_target'] += child_m['prev_target']
        parent_m['prev_actual'] += child_m['prev_actual']
        parent_m['month_target'] += child_m['month_target']
        parent_m['month_actual'] += child_m['month_actual']
        parent_m['day_revenue'] += child_m['day_revenue']

    def finalize_rates(m):
        m['year_rate'] = compute_rate(m['year_actual'], m['year_target'])
        m['prev_rate'] = compute_rate(m['prev_actual'], m['prev_target'])
        m['month_rate'] = compute_rate(m['month_actual'], m['month_target'])

    BU_DISPLAY_NAMES = {
        'BU_ELEVATOR': 'Thang máy (Elevator)',
        'BU_IBIZ PREMIUM': 'Thiết bị điện cao cấp (iBiz Premium)',
        'BU_IBIZ VALUE': 'Thiết bị điện phổ thông (iBiz Value)',
        'TOTAL_ECO_AGRITECH': 'Tổng khối ECO + AgriTech + SAB',
        'BU_ECO': 'ECO (Solar)',
        'BU_AGRITECH': 'Nông nghiệp công nghệ cao (AgriTech)',
        'BU_SAB': 'Thủy sản thông minh (SAB)',
        'BU_MANUFACTURING': 'Sản xuất - Nhà máy',
        'ĐTCT': 'Đầu tư cho thuê (ĐTCT)',
    }

    handled_keys = set()
    for t in targets_list:
        b_code = t.business_unit.code
        emp = t.employee
        handled_keys.add((b_code, emp.id))

        # Lấy thực tế từ actuals_map
        act = actuals_map.get((b_code, emp.id), {
            'day_actual': Decimal('0'),
            'month_actual': Decimal('0'),
            'year_actual': Decimal('0'),
        })

        day_rev = act['day_actual']
        m_act = act['month_actual']
        y_act = act['year_actual']
        p_act = y_act - m_act

        if is_exact_period:
            m_target = t.month_target
            p_target = t.prev_target
        else:
            # Kỳ xem chưa có target tháng cụ thể (ví dụ xem tháng 9) -> month_target = 0
            m_target = Decimal('0')
            p_target = (t.prev_target or Decimal('0')) + (t.month_target or Decimal('0'))

        s_metrics = {
            'year_target': t.year_target,
            'year_actual': y_act,
            'year_rate': compute_rate(y_act, t.year_target),
            'prev_target': p_target,
            'prev_actual': p_act,
            'prev_rate': compute_rate(p_act, p_target),
            'month_target': m_target,
            'month_actual': m_act,
            'month_rate': compute_rate(m_act, m_target),
            'day_revenue': day_rev,
        }

        # Xác định vai trò Trưởng nhóm / Quản lý
        is_leader = bool(t.display_order in [1, 4, 7, 11, 17, 19])

        sales_item = {
            'id': f"emp_{emp.employee_code}",
            'type': 'EMPLOYEE',
            'employee_code': emp.employee_code,
            'name': emp.full_name,
            'is_leader': is_leader,
            'sales_group': t.sales_group,
            'region': t.region,
            'display_order': t.display_order,
            'metrics': s_metrics
        }

        # Khởi tạo BU Node nếu chưa có
        # Gom nhóm BU ECO, AGRITECH, SAB thành khối TỔNG ECO+AGRITECH nếu xem ALL hoặc nhiều BU
        group_bu_code = b_code
        group_bu_name = BU_DISPLAY_NAMES.get(group_bu_code, f"Đơn vị {group_bu_code}")
        if b_code in ['BU_ECO', 'BU_AGRITECH', 'BU_SAB'] and (not resolved_bu_codes or len(resolved_bu_codes) > 1):
            group_bu_code = 'TOTAL_ECO_AGRITECH'
            group_bu_name = BU_DISPLAY_NAMES['TOTAL_ECO_AGRITECH']

        if group_bu_code not in bu_nodes:
            bu_nodes[group_bu_code] = {
                'id': f"bu_{group_bu_code.lower().replace(' ', '_')}",
                'type': 'BU',
                'code': group_bu_code,
                'name': group_bu_name,
                'metrics': empty_metrics(),
                'regions': {}
            }

        bu_entry = bu_nodes[group_bu_code]

        # Khởi tạo Region Node trong BU
        reg_key = t.region
        if reg_key not in bu_entry['regions']:
            bu_entry['regions'][reg_key] = {
                'id': f"reg_{group_bu_code.lower().replace(' ', '_')}_{len(bu_entry['regions'])+1}",
                'type': 'REGION',
                'name': f"Tổng {reg_key}" if not reg_key.startswith('Tổng') and not reg_key.startswith('BU') and not reg_key.startswith('Đơn vị') else reg_key,
                'region_name': reg_key,
                'sales_group': t.sales_group,
                'metrics': empty_metrics(),
                'children': []
            }

        reg_entry = bu_entry['regions'][reg_key]
        reg_entry['children'].append(sales_item)
        add_metrics(reg_entry['metrics'], s_metrics)
        add_metrics(bu_entry['metrics'], s_metrics)

    # Thêm các nhân sự có doanh thu thực tế nhưng chưa được giao chỉ tiêu trong SalesTarget
    for (b_code, emp_id), act in actuals_map.items():
        if (b_code, emp_id) in handled_keys:
            continue
        if not emp_id:
            continue
        if act['year_actual'] == 0 and act['month_actual'] == 0 and act['day_actual'] == 0:
            continue
        emp = Employee.objects.filter(id=emp_id).first()
        if not emp:
            continue

        day_rev = act['day_actual']
        m_act = act['month_actual']
        y_act = act['year_actual']
        p_act = y_act - m_act

        s_metrics = {
            'year_target': Decimal('0'),
            'year_actual': y_act,
            'year_rate': 0.0,
            'prev_target': Decimal('0'),
            'prev_actual': p_act,
            'prev_rate': 0.0,
            'month_target': Decimal('0'),
            'month_actual': m_act,
            'month_rate': 0.0,
            'day_revenue': day_rev,
        }

        reg_name = 'Miền Nam'
        assign = emp.assignments.first()
        if assign and ('bắc' in assign.department.department_name.lower() or 'mb' in assign.title.title_name.lower()):
            reg_name = 'Miền Bắc'

        sales_item = {
            'id': f"emp_{emp.employee_code}",
            'type': 'EMPLOYEE',
            'employee_code': emp.employee_code,
            'name': emp.full_name,
            'sales_group': f"{reg_name}_{b_code}",
            'region': reg_name,
            'display_order': 99,
            'metrics': s_metrics
        }

        group_bu_code = b_code
        group_bu_name = BU_DISPLAY_NAMES.get(group_bu_code, f"Đơn vị {group_bu_code}")
        if b_code in ['BU_ECO', 'BU_AGRITECH', 'BU_SAB'] and (not resolved_bu_codes or len(resolved_bu_codes) > 1):
            group_bu_code = 'TOTAL_ECO_AGRITECH'
            group_bu_name = BU_DISPLAY_NAMES['TOTAL_ECO_AGRITECH']

        if group_bu_code not in bu_nodes:
            bu_nodes[group_bu_code] = {
                'id': f"bu_{group_bu_code.lower().replace(' ', '_')}",
                'type': 'BU',
                'code': group_bu_code,
                'name': group_bu_name,
                'metrics': empty_metrics(),
                'regions': {}
            }
        bu_entry = bu_nodes[group_bu_code]

        if reg_name not in bu_entry['regions']:
            bu_entry['regions'][reg_name] = {
                'id': f"reg_{group_bu_code.lower().replace(' ', '_')}_{len(bu_entry['regions'])+1}",
                'type': 'REGION',
                'name': f"Tổng {reg_name}",
                'region_name': reg_name,
                'sales_group': f"{reg_name}_{b_code}",
                'metrics': empty_metrics(),
                'children': []
            }
        reg_entry = bu_entry['regions'][reg_name]
        reg_entry['children'].append(sales_item)
        add_metrics(reg_entry['metrics'], s_metrics)
        add_metrics(bu_entry['metrics'], s_metrics)

    # 6. Tính toán rates cho các node cấp trên & Tổng cộng công ty
    company_summary = empty_metrics()
    tree_list = []

    # Định nghĩa thứ tự ưu tiên hiển thị BU theo mẫu kế toán
    bu_priority = {
        'BU_ELEVATOR': 1,
        'BU_IBIZ PREMIUM': 2,
        'BU_IBIZ VALUE': 3,
        'TOTAL_ECO_AGRITECH': 4,
        'BU_ECO': 4,
        'BU_AGRITECH': 5,
        'BU_SAB': 6,
        'BU_MANUFACTURING': 7
    }

    sorted_bu_keys = sorted(
        bu_nodes.keys(),
        key=lambda k: bu_priority.get(k, 99)
    )

    for b_key in sorted_bu_keys:
        b_node = bu_nodes[b_key]
        finalize_rates(b_node['metrics'])
        add_metrics(company_summary, b_node['metrics'])

        # Chuyển regions dict thành children list
        reg_list = []
        for r_node in b_node['regions'].values():
            finalize_rates(r_node['metrics'])
            # Sắp xếp sales trong region theo display_order
            r_node['children'].sort(key=lambda x: x['display_order'])
            reg_list.append(r_node)

        b_node['children'] = reg_list
        del b_node['regions']
        tree_list.append(b_node)

    finalize_rates(company_summary)

    return {
        'success': True,
        'date': parsed_date.strftime('%Y-%m-%d'),
        'period': period,
        'bu_code': bu_code or 'ALL',
        'is_bod': is_bod,
        'summary': company_summary,
        'tree': tree_list
    }
