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
    """
    reporting_period, target_date = get_target_date_for_period(reporting_period)
    logger.info(f"👉 Bắt đầu tính toán Công nợ Nhân viên & Quản lý cho kỳ {reporting_period} (Ngày chốt: {target_date})...")

    # -------------------------------------------------------------
    # BƯỚC 1: Lấy danh sách snapshot tuổi nợ trong kỳ (Lọc theo TK mục tiêu 1311)
    # -------------------------------------------------------------
    target_rec_accounts = getattr(settings, 'TARGET_RECEIVABLE_ACCOUNTS', ['1311'])
    ageing_filter = Q(reporting_period=reporting_period)
    if target_rec_accounts:
        ageing_filter &= Q(account_code__in=target_rec_accounts)

    ageing_records = ReceivablesAgeing.objects.filter(ageing_filter)
    
    # Map tổng hợp dư nợ theo từng Nhân viên (Direct Employee Debt or Assigned Sales)
    emp_own_debts = {}

    # Pre-cache mapping từ Mã NV (employee_code) -> Employee Object
    emp_code_map = {e.employee_code: e for e in Employee.objects.all() if e.employee_code}

    for rec in ageing_records:
        customer = rec.customer
        if not customer:
            continue
        
        target_emp_id = None

        # TH1: Mã Khách hàng khớp chính xác với Mã Nhân viên nội bộ (Customer IS Employee)
        if customer.code and customer.code in emp_code_map:
            target_emp_id = emp_code_map[customer.code].id
        # TH2: Khách hàng ngoài do Nhân viên Sales phụ trách (assigned_employee)
        elif customer.assigned_employee_id:
            target_emp_id = customer.assigned_employee_id

        if not target_emp_id:
            continue

        emp_id = target_emp_id
        if emp_id not in emp_own_debts:
            emp_own_debts[emp_id] = {
                'total': Decimal('0'),
                'due': Decimal('0'),
                'overdue': Decimal('0'),
                'overdue_60': Decimal('0'),
                'overdue_120': Decimal('0'),
            }

        data = emp_own_debts[emp_id]
        data['total'] += rec.total_debt or Decimal('0')
        data['due'] += rec.due_total or Decimal('0')
        data['overdue'] += rec.overdue_total or Decimal('0')
        
        # Nợ quá hạn >60 ngày = (overdue_61_90 + overdue_91_120 + overdue_above_120)
        overdue_60_val = (rec.overdue_61_90 or Decimal('0')) + (rec.overdue_91_120 or Decimal('0')) + (rec.overdue_above_120 or Decimal('0'))
        data['overdue_60'] += overdue_60_val
        data['overdue_120'] += rec.overdue_above_120 or Decimal('0')

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
            'total': Decimal('0'),
            'due': Decimal('0'),
            'overdue': Decimal('0'),
            'overdue_60': Decimal('0'),
            'overdue_120': Decimal('0'),
        })

        summary_map[emp.id] = {
            'employee': emp,
            'department': dept,
            'own_total_debt': own['total'],
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
        team_due = own_info['own_due_total']
        team_overdue = own_info['own_overdue_total']
        team_overdue_120 = own_info['own_overdue_above_120']

        for sub_id in sub_ids:
            if sub_id in summary_map:
                sub_own = summary_map[sub_id]
                team_total += sub_own['own_total_debt']
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
                'own_due_total': own_info['own_due_total'],
                'own_overdue_total': own_info['own_overdue_total'],
                'own_overdue_above_60': own_info['own_overdue_above_60'],
                'own_overdue_above_120': own_info['own_overdue_above_120'],
                'team_total_debt': team_total,
                'team_due_total': team_due,
                'team_overdue_total': team_overdue,
                'team_overdue_above_120': team_overdue_120,
                'subordinate_count': len(sub_ids),
            }
        )
        results.append(summary_obj)

    logger.info(f"✅ Hoàn tất tính toán công nợ cho {len(results)} nhân viên & quản lý kỳ {reporting_period}!")
    return f"Đã tính toán thành công công nợ cho {len(results)} nhân viên/quản lý kỳ {reporting_period}."
