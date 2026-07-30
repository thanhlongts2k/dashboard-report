import os
import sys
from datetime import datetime
from django.db.models import Q

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_ROOT)
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'report2026.settings')

import django
django.setup()

from accounting.models import JobTitle, EmployeeAssignment, Employee, Department

def detect_manager_titles():
    print("=" * 85)
    print("🔍 DANH SÁCH CHỨC DANH & SỐ LƯỢNG NHÂN VIÊN THỰC TẾ (ACTIVE UNIQUE EMPLOYEES)")
    print("=" * 85)
    
    today = datetime.now().date()
    all_titles = JobTitle.objects.all().order_by('title_name')
    print(f"Tổng số chức danh trong danh mục: {all_titles.count()}\n")

    # Từ khóa nhận diện chức danh Quản lý / Trưởng bộ phận
    MANAGER_KEYWORDS = [
        'trưởng', 'chủ nhiệm', 'giám đốc', 'quản lý', 'phó', 'phó phòng', 
        'leader', 'manager', 'director', 'head', 'supervisor', 'điều hành'
    ]

    manager_titles = []
    other_titles = []

    for t in all_titles:
        name_lower = t.title_name.lower()
        if any(kw in name_lower for kw in MANAGER_KEYWORDS):
            manager_titles.append(t)
        else:
            other_titles.append(t)

    # 1. CHỨC DANH QUẢN LÝ
    print(f"👑 1. CHỨC DANH QUẢN LÝ / TRƯỞNG BỘ PHẬN ({len(manager_titles)}):")
    for t in manager_titles:
        active_assignments = EmployeeAssignment.objects.filter(
            title=t,
            employee__is_active=True
        ).filter(
            Q(end_date__gte=today) | Q(end_date__isnull=True)
        )
        unique_emp_count = active_assignments.values('employee_id').distinct().count()
        total_rows = active_assignments.count()
        
        note_str = f" (Tổng {total_rows} dòng hợp đồng)" if total_rows != unique_emp_count else ""
        print(f"  [QUẢN LÝ] ID {t.title_id:<2}: {t.title_name:<45} -> {unique_emp_count} Nhân viên thực tế{note_str}")

    # 2. CÁC CHỨC DANH KHÁC PHÂN THEO ĐƠN VỊ / PHÒNG BAN
    print(f"\n👔 2. CÁC CHỨC DANH KHÁC THUỘC CÁC ĐƠN VỊ / PHÒNG BAN ({len(other_titles)} Chức danh):")

    other_assignments = EmployeeAssignment.objects.filter(
        title__in=other_titles,
        employee__is_active=True
    ).filter(
        Q(end_date__gte=today) | Q(end_date__isnull=True)
    ).select_related('department', 'title', 'employee')

    dept_map = {}
    for assign in other_assignments:
        dept_name = assign.department.department_name if assign.department else "[Chưa phân phòng ban]"
        if dept_name not in dept_map:
            dept_map[dept_name] = {}
        
        t = assign.title
        if t not in dept_map[dept_name]:
            dept_map[dept_name][t] = set()
        
        dept_map[dept_name][t].add(assign.employee_id)

    for dept_name in sorted(dept_map.keys()):
        print(f"\n🏢 {dept_name}:")
        titles_in_dept = dept_map[dept_name]
        for t in sorted(titles_in_dept.keys(), key=lambda x: x.title_name):
            emp_ids = titles_in_dept[t]
            print(f"    - ID {t.title_id:<2}: {t.title_name:<42} -> {len(emp_ids)} Nhân viên thực tế")

    # 3. DANH SÁCH CHI TIẾT CÁC QUẢN LÝ
    print("\n" + "=" * 85)
    print("👥 3. DANH SÁCH CÁC QUẢN LÝ / TRƯỞNG BỘ PHẬN ĐANG ACTIVE TRONG HỆ THỐNG:")
    print("=" * 85)

    mgr_assignments = EmployeeAssignment.objects.filter(
        title__in=manager_titles,
        employee__is_active=True
    ).filter(
        Q(end_date__gte=today) | Q(end_date__isnull=True)
    ).select_related('employee', 'department', 'title').order_by('department__department_name', 'employee__full_name')

    seen_employees = set()
    counter = 1

    for assign in mgr_assignments:
        emp = assign.employee
        if emp.id in seen_employees:
            continue
        seen_employees.add(emp.id)

        dept_str = assign.department.department_name if assign.department else "N/A"
        mgr_str = f" -> Quản lý: {assign.manager.full_name} ({assign.manager.employee_code})" if assign.manager else " -> Quản lý: [Chưa gán]"
        print(f"  {counter:02d}. {emp.full_name:<25} (Mã: {emp.employee_code:<7}) | Chức danh: {assign.title.title_name:<30} | Phòng: {dept_str}{mgr_str}")
        counter += 1

    print("=" * 85)

if __name__ == '__main__':
    detect_manager_titles()
