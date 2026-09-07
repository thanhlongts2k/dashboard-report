import logging
import calendar
from datetime import datetime
from decimal import Decimal
from django.db import transaction
from django.db.models import Q
from django.conf import settings
from accounting.models import (
    Employee, Department, EmployeeAssignment, Customer,
    ReceivablesAgeing, EmployeeReceivableSummary
)
from accounting.config.debt_classification import get_customer_debt_category

logger = logging.getLogger(__name__)


def get_target_date_for_period(reporting_period=None):
    """
    Chuyển 'YYYY-MM' thành ngày cuối tháng (hoặc ngày hôm nay nếu trùng tháng hiện tại)
    """
    today = datetime.now()
    if not reporting_period:
        reporting_period = f"{today.year:04d}-{today.month:02d}"
    
    parts = reporting_period.split('-')
    year = int(parts[0])
    month = int(parts[1])

    if year == today.year and month == today.month:
        target_date = today.date()
    else:
        last_day = calendar.monthrange(year, month)[1]
        target_date = datetime(year, month, last_day).date()
        
    return reporting_period, target_date


def get_employee_assignment_at_date(employee, target_date):
    """
    Tra cứu quá trình công tác active của nhân viên tại mốc thời gian target_date (chuẩn SCD Type 2)
    """
    return EmployeeAssignment.objects.filter(
        employee=employee,
        start_date__lte=target_date
    ).filter(
        Q(end_date__gte=target_date) | Q(end_date__isnull=True)
    ).first()


def get_direct_subordinate_ids(manager_employee, target_date):
    """
    Lấy danh sách ID các nhân viên do manager_employee trực tiếp quản lý tại mốc target_date
    """
    assignments = EmployeeAssignment.objects.filter(
        manager=manager_employee,
        start_date__lte=target_date
    ).filter(
        Q(end_date__gte=target_date) | Q(end_date__isnull=True)
    )
    return set(assignments.values_list('employee_id', flat=True))


def get_all_subordinate_ids_recursive(manager_employee, target_date, visited=None):
    """
    Đệ quy lấy toàn bộ ID cấp dưới (trực tiếp + gián tiếp) của một Trưởng nhóm / Trưởng phòng
    """
    if visited is None:
        visited = set()

    direct_ids = get_direct_subordinate_ids(manager_employee, target_date)
    subordinates = set()

    for sub_id in direct_ids:
        if sub_id not in visited:
            visited.add(sub_id)
            subordinates.add(sub_id)
            sub_emp = Employee.objects.filter(id=sub_id).first()
            if sub_emp:
                nested_subs = get_all_subordinate_ids_recursive(sub_emp, target_date, visited)
                subordinates.update(nested_subs)

    return subordinates


@transaction.atomic
def update_employee_receivable_summary(reporting_period=None):
    """
    Động cơ chính tính toán và cập nhật Bảng tổng hợp công nợ Nhân viên & Quản lý nhóm (Phase 2)
    Bóc tách 3 nhóm nợ chuẩn Kế toán (Mốc chốt 05/09/2026):
      1. Nợ hoạt động năm 2026 (current_year_debt: ~59.07 tỷ)
      2. Nợ cũ năm 2025 (debt_2025: 266,666,301 đ)
      3. Nợ cũ khó đòi 2022-2024 (bad_debt_historical: 4,365,519,339 đ)
    """
    from accounting.config.debt_classification import (
        MISA_1311_EXCLUSIONS_OR_ADJUSTMENTS,
        REPORT_EMPLOYEE_OVERRIDES,
        get_bad_debt_for_employee,
        get_old_debt_2025_for_employee,
    )

    reporting_period, target_date = get_target_date_for_period(reporting_period)
    logger.info(f"👉 Bắt đầu tính toán Công nợ Nhân viên & Quản lý cho kỳ {reporting_period} (Ngày chốt: {target_date})...")

    # Đảm bảo nhân sự đại diện BEE tồn tại trong bảng Employee
    Employee.objects.get_or_create(
        employee_code='BEE',
        defaults={'full_name': 'BEE (KHÁCH LẺ & DỰ ÁN CŨ)', 'is_active': True}
    )

    # -------------------------------------------------------------
    # BƯỚC 1: Lấy danh sách snapshot tuổi nợ trong kỳ (Lọc theo TK mục tiêu 1311)
    # -------------------------------------------------------------
    target_rec_accounts = getattr(settings, 'TARGET_RECEIVABLE_ACCOUNTS', ['1311'])
    ageing_filter = Q(reporting_period=reporting_period)
    if target_rec_accounts:
        ageing_filter &= Q(account_code__in=target_rec_accounts)

    ageing_records = ReceivablesAgeing.objects.filter(ageing_filter).select_related('customer')
    
    # 1.1 Tổng hợp theo từng Khách hàng trước để áp dụng bóc tách nợ cũ/khó đòi chính xác
    cust_totals = {}
    for rec in ageing_records:
        cust = rec.customer
        if not cust:
            continue
        c_code = (cust.code or '').strip()
        if c_code not in cust_totals:
            cust_totals[c_code] = {
                'customer': cust,
                'due': Decimal('0'),
                'overdue': Decimal('0'),
                'overdue_60': Decimal('0'),
                'overdue_above_120': Decimal('0'),
                'total': Decimal('0'),
            }
        due = rec.due_total or Decimal('0')
        ov = rec.overdue_total or Decimal('0')
        ov60 = (rec.overdue_61_90 or Decimal('0')) + (rec.overdue_91_120 or Decimal('0')) + (rec.overdue_above_120 or Decimal('0'))
        ov120 = rec.overdue_above_120 or Decimal('0')
        
        cust_totals[c_code]['due'] += due
        cust_totals[c_code]['overdue'] += ov
        cust_totals[c_code]['overdue_60'] += ov60
        cust_totals[c_code]['overdue_above_120'] += ov120
        cust_totals[c_code]['total'] += (due + ov)

    # 1.2 Áp dụng bóc tách các khoản nợ cũ / khó đòi đã kết xuất trong MISA 1311
    for c_code, deduct in MISA_1311_EXCLUSIONS_OR_ADJUSTMENTS.items():
        if c_code in cust_totals:
            d_due, d_ov, _ = deduct
            c_data = cust_totals[c_code]
            c_data['due'] = max(Decimal('0'), c_data['due'] - d_due)
            c_data['overdue'] = max(Decimal('0'), c_data['overdue'] - d_ov)
            c_data['overdue_60'] = max(Decimal('0'), c_data['overdue_60'] - d_ov)
            c_data['overdue_above_120'] = max(Decimal('0'), c_data['overdue_above_120'] - d_ov)
            c_data['total'] = c_data['due'] + c_data['overdue']

    # 1.3 Phân bổ nợ 2026 cho từng Nhân viên
    emp_code_map = {e.employee_code: e for e in Employee.objects.all() if e.employee_code}
    emp_own_debts = {}

    for c_code, c_data in cust_totals.items():
        cust = c_data['customer']
        target_emp_id = None
        
        # Ưu tiên 1: Gán điều chỉnh theo Báo cáo Kế toán
        if c_code in REPORT_EMPLOYEE_OVERRIDES:
            override_code = REPORT_EMPLOYEE_OVERRIDES[c_code]
            if override_code in emp_code_map:
                target_emp_id = emp_code_map[override_code].id
        # Ưu tiên 2: Khách hàng nội bộ trùng mã Nhân viên
        elif c_code and c_code in emp_code_map:
            target_emp_id = emp_code_map[c_code].id
        # Ưu tiên 3: Sales phụ trách trực tiếp
        elif cust.assigned_employee_id:
            target_emp_id = cust.assigned_employee_id

        if not target_emp_id:
            continue

        if target_emp_id not in emp_own_debts:
            emp_own_debts[target_emp_id] = {
                'current_year_debt': Decimal('0'),
                'due': Decimal('0'),
                'overdue': Decimal('0'),
                'overdue_60': Decimal('0'),
                'overdue_120': Decimal('0'),
            }

        data = emp_own_debts[target_emp_id]
        data['current_year_debt'] += c_data['total']
        data['due'] += c_data['due']
        data['overdue'] += c_data['overdue']
        data['overdue_60'] += c_data['overdue_60']
        data['overdue_120'] += c_data['overdue_above_120']

    # -------------------------------------------------------------
    # BƯỚC 2: Lấy tất cả nhân viên active hoặc có phát sinh nợ
    # -------------------------------------------------------------
    all_employees = list(Employee.objects.filter(is_active=True))
    extra_emp_ids = set(emp_own_debts.keys()) - set(e.id for e in all_employees)
    if extra_emp_ids:
        all_employees.extend(list(Employee.objects.filter(id__in=extra_emp_ids)))

    # Map lưu thông tin summary tạm thời của từng NV
    summary_map = {}

    for emp in all_employees:
        assignment = get_employee_assignment_at_date(emp, target_date)
        dept = assignment.department if assignment else None
        
        own = emp_own_debts.get(emp.id, {
            'current_year_debt': Decimal('0'),
            'due': Decimal('0'),
            'overdue': Decimal('0'),
            'overdue_60': Decimal('0'),
            'overdue_120': Decimal('0'),
        })

        # Gán nợ cũ 2025 & nợ khó đòi 2022-2024 theo danh mục kế toán
        bad_debt = get_bad_debt_for_employee(emp.employee_code)
        old_2025 = get_old_debt_2025_for_employee(emp.employee_code)
        curr_2026 = own['current_year_debt']
        total_all_debt = curr_2026 + old_2025 + bad_debt

        summary_map[emp.id] = {
            'employee': emp,
            'department': dept,
            'own_total_debt': total_all_debt,
            'current_year_debt': curr_2026,
            'debt_2025': old_2025,
            'bad_debt_historical': bad_debt,
            'own_due_total': own['due'],
            'own_overdue_total': own['overdue'],
            'own_overdue_above_60': own['overdue_60'],
            'own_overdue_above_120': own['overdue_120'],
        }

    # -------------------------------------------------------------
    # BƯỚC 3: Duyệt cây quản lý Bottom-Up để tính nợ nhóm (team_*)
    # -------------------------------------------------------------
    results = []

    for emp in all_employees:
        own_info = summary_map[emp.id]
        
        # Lấy danh sách toàn bộ cấp dưới đệ quy tại target_date
        sub_ids = get_all_subordinate_ids_recursive(emp, target_date)
        is_mgr = len(sub_ids) > 0

        team_total = own_info['own_total_debt']
        team_curr = own_info['current_year_debt']
        team_2025 = own_info['debt_2025']
        team_bad = own_info['bad_debt_historical']
        team_due = own_info['own_due_total']
        team_overdue = own_info['own_overdue_total']
        team_overdue_120 = own_info['own_overdue_above_120']

        for sub_id in sub_ids:
            if sub_id in summary_map:
                sub_own = summary_map[sub_id]
                team_total += sub_own['own_total_debt']
                team_curr += sub_own['current_year_debt']
                team_2025 += sub_own['debt_2025']
                team_bad += sub_own['bad_debt_historical']
                team_due += sub_own['own_due_total']
                team_overdue += sub_own['own_overdue_total']
                team_overdue_120 += sub_own['own_overdue_above_120']

        # Update hoặc Create bản ghi EmployeeReceivableSummary
        summary_obj, _ = EmployeeReceivableSummary.objects.update_or_create(
            employee=emp,
            reporting_period=reporting_period,
            defaults={
                'department': own_info['department'],
                'is_manager': is_mgr,
                'own_total_debt': own_info['own_total_debt'],
                'current_year_debt': own_info['current_year_debt'],
                'debt_2025': own_info['debt_2025'],
                'bad_debt_historical': own_info['bad_debt_historical'],
                'own_due_total': own_info['own_due_total'],
                'own_overdue_total': own_info['own_overdue_total'],
                'own_overdue_above_60': own_info['own_overdue_above_60'],
                'own_overdue_above_120': own_info['own_overdue_above_120'],
                'team_total_debt': team_total,
                'team_current_year_debt': team_curr,
                'team_debt_2025': team_2025,
                'team_bad_debt_historical': team_bad,
                'team_due_total': team_due,
                'team_overdue_total': team_overdue,
                'team_overdue_above_120': team_overdue_120,
                'subordinate_count': len(sub_ids),
            }
        )
        results.append(summary_obj)

    logger.info(f"✅ Hoàn tất tính toán công nợ cho {len(results)} nhân viên & quản lý kỳ {reporting_period}!")
    return f"Đã tính toán thành công công nợ cho {len(results)} nhân viên/quản lý kỳ {reporting_period}."
