import os
import sys
from datetime import datetime
from django.db import transaction
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
    name_lower = title_name.lower()
    return any(kw in name_lower for kw in MANAGER_KEYWORDS)

def get_title_rank(title_name):
    """Xếp hạng độ ưu tiên chức danh quản lý (Trưởng/Giám đốc > Phó/Leader)"""
    name_lower = title_name.lower()
    if any(kw in name_lower for kw in ['giám đốc', 'director']):
        return 1
    if any(kw in name_lower for kw in ['trưởng phòng', 'trưởng đơn vị', 'trưởng bộ phận', 'head', 'chủ nhiệm']):
        return 2
    if any(kw in name_lower for kw in ['trưởng nhóm', 'leader', 'quản lý', 'manager']):
        return 3
    if any(kw in name_lower for kw in ['phó giám đốc', 'phó phòng', 'phó bộ phận']):
        return 4
    return 5

@transaction.atomic
def auto_assign_department_managers(dry_run=False):
    today = datetime.now().date()
    print("=" * 85)
    print("🚀 BẮT ĐẦU TIẾN TRÌNH TỰ ĐỘNG GÁN QUẢN LÝ (MANAGER) CHO NHÂN VIÊN THEO PHÒNG BAN")
    print("=" * 85)

    departments = Department.objects.all().order_by('department_code')
    dept_head_map = {} # {department_code: Employee}

    print("\n--- BƯỚC 1: XÁC ĐỊNH TRƯỞNG BỘ PHẬN / QUẢN LÝ CHO TỪNG PHÒNG BAN ---")
    
    for dept in departments:
        active_assignments = EmployeeAssignment.objects.filter(
            department=dept,
            employee__is_active=True
        ).filter(
            Q(end_date__gte=today) | Q(end_date__isnull=True)
        ).select_related('employee', 'title')

        manager_assigns = []
        for assign in active_assignments:
            if is_manager_title(assign.title.title_name):
                manager_assigns.append(assign)

        if manager_assigns:
            # Sắp xếp theo cấp bậc chức danh (Giám đốc/Trưởng phòng ưu tiên hơn Phó phòng)
            manager_assigns.sort(key=lambda a: get_title_rank(a.title.title_name))
            top_mgr_assign = manager_assigns[0]
            dept_head_map[dept.department_code] = top_mgr_assign.employee
            print(f"🏢 [{dept.department_code}] {dept.department_name:<40} -> Quản lý Trưởng: {top_mgr_assign.employee.full_name} ({top_mgr_assign.title.title_name})")
        else:
            print(f"🏢 [{dept.department_code}] {dept.department_name:<40} -> ⚠️ [Chưa tìm thấy Trưởng phòng/Quản lý]")

    print("\n--- BƯỚC 2: GÁN QUẢN LÝ TRỰC TIẾP CHO TẤT CẢ NHÂN VIÊN TRONG PHÒNG BAN ---")
    
    assigned_staff_count = 0
    updated_staff_assignments = []

    for dept in departments:
        dept_head = dept_head_map.get(dept.department_code)
        if not dept_head:
            continue

        staff_assignments = EmployeeAssignment.objects.filter(
            department=dept,
            employee__is_active=True
        ).filter(
            Q(end_date__gte=today) | Q(end_date__isnull=True)
        ).exclude(employee=dept_head)

        for assign in staff_assignments:
            if assign.manager != dept_head:
                old_mgr_str = assign.manager.full_name if assign.manager else "Chưa gán"
                assign.manager = dept_head
                updated_staff_assignments.append(assign)
                assigned_staff_count += 1
                print(f"  + NV: {assign.employee.full_name:<25} ({dept.department_code}) | Cũ: {old_mgr_str:<20} -> Mới: {dept_head.full_name}")

    print("\n--- BƯỚC 3: GÁN QUẢN LÝ CẤP TRÊN CHO CÁC TRƯỞNG PHÒNG (THEO CÂY PHÒNG BAN CHA - CON) ---")
    
    assigned_mgr_count = 0
    for dept in departments:
        dept_head = dept_head_map.get(dept.department_code)
        if not dept_head or not dept.parent_department:
            continue

        parent_dept = dept.parent_department
        parent_dept_head = dept_head_map.get(parent_dept.department_code)

        if parent_dept_head and parent_dept_head != dept_head:
            head_assignments = EmployeeAssignment.objects.filter(
                employee=dept_head,
                department=dept
            ).filter(
                Q(end_date__gte=today) | Q(end_date__isnull=True)
            )

            for assign in head_assignments:
                if assign.manager != parent_dept_head:
                    assign.manager = parent_dept_head
                    updated_staff_assignments.append(assign)
                    assigned_mgr_count += 1
                    print(f"  👑 Trưởng phòng: {dept_head.full_name:<20} ({dept.department_code}) -> Quản lý cấp trên: {parent_dept_head.full_name} ({parent_dept.department_code})")

    if not dry_run and updated_staff_assignments:
        print("\n💾 Đang lưu thay đổi vào Cơ sở dữ liệu...")
        EmployeeAssignment.objects.bulk_update(updated_staff_assignments, ['manager'])
        print(f"✅ ĐÃ CẬP NHẬT THÀNH CÔNG MANAGER CHO {len(updated_staff_assignments)} NHÂN VIÊN & QUẢN LÝ!")
    elif dry_run:
        print("\nℹ️ Đang chạy ở chế độ DRY-RUN (không lưu vào DB).")

    print("=" * 85)
    return len(updated_staff_assignments)

if __name__ == '__main__':
    auto_assign_department_managers(dry_run=False)
