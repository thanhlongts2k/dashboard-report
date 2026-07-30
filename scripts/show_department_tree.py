import os
import sys
import argparse
from datetime import datetime
from django.db.models import Q

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_ROOT)
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'report2026.settings')

import django
django.setup()

from accounting.models import Department, JobTitle, Employee, EmployeeAssignment

MANAGER_KEYWORDS = [
    'trưởng', 'chủ nhiệm', 'giám đốc', 'quản lý', 'phó', 'phó phòng', 
    'leader', 'manager', 'director', 'head', 'supervisor', 'điều hành'
]

def is_manager_title(title_name):
    if not title_name:
        return False
    return any(kw in title_name.lower() for kw in MANAGER_KEYWORDS)

def parse_code_key(code):
    if not code:
        return (1, "")
    code_str = str(code).strip()
    if code_str.isdigit():
        return (0, int(code_str))
    return (1, code_str)

def get_sort_key(assignment, sort_by):
    emp = assignment.employee
    title = assignment.title

    if sort_by in ('title', 'title_name'):
        t_name = title.title_name if title else ""
        return (t_name, parse_code_key(emp.employee_code))
    elif sort_by == 'title_id':
        t_id = title.title_id if (title and title.title_id) else 0
        return (t_id, parse_code_key(emp.employee_code))
    elif sort_by == 'name':
        return (emp.full_name or "", parse_code_key(emp.employee_code))
    else:  # default 'code'
        return parse_code_key(emp.employee_code)

def show_department_tree(sort_by='code'):
    today = datetime.now().date()
    sort_labels = {
        'code': 'Mã Nhân viên (Tăng dần)',
        'title': 'Tên Chức danh (A-Z)',
        'title_name': 'Tên Chức danh (A-Z)',
        'title_id': 'ID Chức danh (Tăng dần)',
        'name': 'Họ và tên (A-Z)',
    }
    sort_desc = sort_labels.get(sort_by, sort_by)

    print("=" * 90)
    print(f"🏢 BÁO CÁO CÂY PHÒNG BAN, TRƯỞNG BỘ PHẬN & DANH SÁCH NHÂN VIÊN TRỰC THUỘC")
    print(f"📌 Chế độ sắp xếp Danh sách Nhân viên: [{sort_desc}]")
    print("=" * 90)

    departments = Department.objects.all().order_by('department_code')
    total_depts = departments.count()
    print(f"Tổng số Đơn vị / Phòng ban: {total_depts}\n")

    for idx, dept in enumerate(departments, 1):
        parent_str = f" [Thuộc: {dept.parent_department.department_name}]" if dept.parent_department else ""
        print(f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
        print(f"🏢 {idx:02d}. [{dept.department_code}] {dept.department_name.upper()}{parent_str}")
        print(f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")

        # 1. Tìm Trưởng bộ phận (Manager / Head) của phòng ban
        active_assigns = EmployeeAssignment.objects.filter(
            department=dept,
            employee__is_active=True
        ).filter(
            Q(end_date__gte=today) | Q(end_date__isnull=True)
        ).select_related('employee', 'title', 'manager')

        head_assigns = [a for a in active_assigns if is_manager_title(a.title.title_name)]
        dept_head = head_assigns[0].employee if head_assigns else None

        if head_assigns:
            for h in head_assigns:
                head_emp = h.employee
                parent_mgr_str = f" (Báo cáo Quản lý cấp trên: {h.manager.full_name})" if h.manager else ""
                print(f"  👑 TRƯỞNG BỘ PHẬN: {head_emp.full_name} (Mã: {head_emp.employee_code}) | Chức danh: {h.title.title_name}{parent_mgr_str}")
        else:
            print(f"  ⚠️ TRƯỞNG BỘ PHẬN: [Chưa tìm thấy / Chưa gán]")

        # 2. Tìm danh sách Nhân viên trong phòng ban
        staff_assigns = [a for a in active_assigns if a.employee != dept_head]
        staff_assigns.sort(key=lambda a: get_sort_key(a, sort_by))

        print(f"  👥 DANH SÁCH NHÂN VIÊN TRỰC THUỘC ({len(staff_assigns)} Nhân viên):")
        if staff_assigns:
            seen_emp = set()
            staff_idx = 1
            for a in staff_assigns:
                emp = a.employee
                if emp.id in seen_emp:
                    continue
                seen_emp.add(emp.id)

                mgr_str = f" -> Quản lý: {a.manager.full_name}" if a.manager else " -> Quản lý: [Chưa gán]"
                print(f"     {staff_idx:02d}. {emp.full_name:<28} (Mã: {emp.employee_code:<7}) | Chức danh: {a.title.title_name:<32}{mgr_str}")
                staff_idx += 1
        else:
            print("     (Không có nhân viên trực thuộc)")

        print()

    print("=" * 90)

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="Hiển thị cây phòng ban và danh sách nhân viên trực thuộc.")
    parser.add_argument(
        '--sort-by', '-s',
        choices=['code', 'title', 'title_id', 'title_name', 'name'],
        default='code',
        help="Tuỳ chọn sắp xếp danh sách nhân viên: 'code' (Mã NV), 'title' (Tên chức danh), 'title_id' (ID Chức danh), 'name' (Họ tên)."
    )
    args = parser.parse_args()
    show_department_tree(sort_by=args.sort_by)
