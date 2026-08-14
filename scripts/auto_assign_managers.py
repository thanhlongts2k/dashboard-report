import os
import sys
from datetime import datetime
from django.db import transaction
from django.db.models import Q

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

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
    """
    Xếp hạng độ ưu tiên chức danh quản lý:
    Rank 1: Giám đốc (Giám đốc kinh doanh, Giám đốc vận hành, Giám đốc khối...)
    Rank 2: Trưởng BU (Trưởng BU elevator, Trưởng BU premium, Trưởng BU value, Trưởng BU manufacturing, Trưởng BU agritech - eco)
    Rank 3: Trưởng bộ phận, Trưởng đơn vị, Trưởng phòng, Head, Chủ nhiệm
    Rank 4: Trưởng nhóm, Quản lý kho, Leader, Supervisor
    Rank 5: Phó giám đốc, Phó phòng, Phó bộ phận, Phó BU
    Rank 6: Nhân viên
    """
    if not title_name:
        return 6
    t = title_name.lower().strip()
    if 'giám đốc' in t or 'director' in t:
        return 1
    if 'trưởng bu' in t or 'head of bu' in t:
        return 2
    if any(kw in t for kw in ['trưởng bộ phận', 'trưởng đơn vị', 'trưởng phòng', 'head', 'chủ nhiệm']):
        return 3
    if any(kw in t for kw in ['trưởng nhóm', 'quản lý', 'leader', 'supervisor']):
        return 4
    if any(kw in t for kw in ['phó giám đốc', 'phó phòng', 'phó bộ phận', 'phó bu']):
        return 5
    return 6

@transaction.atomic
def auto_assign_department_managers(dry_run=False):
    today = datetime.now().date()
    print("=" * 85)
    print("🚀 BẮT ĐẦU TIẾN TRÌNH TỰ ĐỘNG GÁN QUẢN LÝ (MANAGER) THEO CÂY TỔ CHỨC ĐA CẤP")
    print("=" * 85)

    # 1. Top Executives (CCO, COO)
    emp_cco = Employee.objects.filter(employee_code='2001').first() # Ngô Đình Trung Tân (Giám đốc kinh doanh)
    emp_coo = Employee.objects.filter(employee_code='2000807').first() # Phạm Định (Giám đốc vận hành)

    if emp_cco:
        for a in emp_cco.assignments.all():
            a.manager = None
            if not dry_run:
                a.save()
        print(f"👑 CCO [{emp_cco.employee_code}] {emp_cco.full_name} -> Quản lý: None (Lãnh đạo Khối Kinh doanh)")

    if emp_coo:
        for a in emp_coo.assignments.all():
            a.manager = None
            if not dry_run:
                a.save()
        print(f"👑 COO [{emp_coo.employee_code}] {emp_coo.full_name} -> Quản lý: None (Lãnh đạo Khối Vận hành)")

    # 2. BU Elevator (Đào Tiến Dũng -> Nguyễn Đức Thưởng MB / Trịnh Hoàng Quân MN -> Staff)
    dept_elev = Department.objects.filter(department_code='BU_Elevator').first()
    head_elev = Employee.objects.filter(employee_code='3003').first() # Đào Tiến Dũng
    mgr_mb_elev = Employee.objects.filter(employee_code='2000017').first() # Nguyễn Đức Thưởng
    mgr_mn_elev = Employee.objects.filter(employee_code='3005').first() # Trịnh Hoàng Quân

    if head_elev and dept_elev:
        a_head = EmployeeAssignment.objects.filter(employee=head_elev, department=dept_elev).first()
        if a_head:
            a_head.manager = emp_cco
            if not dry_run:
                a_head.save()
            print(f"🏢 Trưởng BU Elevator [{head_elev.employee_code}] {head_elev.full_name} -> Báo cáo: {emp_cco.full_name}")

        for sub_m in [mgr_mb_elev, mgr_mn_elev]:
            if sub_m:
                a_sub = EmployeeAssignment.objects.filter(employee=sub_m, department=dept_elev).first()
                if a_sub:
                    a_sub.manager = head_elev
                    if not dry_run:
                        a_sub.save()
                    print(f"  + Trưởng BP [{sub_m.employee_code}] {sub_m.full_name} -> Báo cáo: {head_elev.full_name}")

        for a in EmployeeAssignment.objects.filter(department=dept_elev).exclude(employee__in=[head_elev, mgr_mb_elev, mgr_mn_elev]):
            t_name = a.title.title_name.lower()
            if 'mb' in t_name and mgr_mb_elev:
                a.manager = mgr_mb_elev
            elif 'mn' in t_name and mgr_mn_elev:
                a.manager = mgr_mn_elev
            else:
                a.manager = head_elev
            if not dry_run:
                a.save()

    # 3. BU Premium (Hồ Tôn Nhật Minh / Nguyễn Bình Minh MB / Đào Lê Hoàng Thiện MN -> Staff)
    dept_prem = Department.objects.filter(department_code='BU_Premium').first()
    head_prem = Employee.objects.filter(employee_code='2000012').first()
    mgr_mb_prem = Employee.objects.filter(employee_code='2000058').first()
    mgr_mn_prem = Employee.objects.filter(employee_code='9010').first()
    top_prem = head_prem or mgr_mb_prem

    if dept_prem and top_prem:
        a_top = EmployeeAssignment.objects.filter(employee=top_prem, department=dept_prem).first()
        if a_top:
            a_top.manager = emp_cco
            if not dry_run:
                a_top.save()
            print(f"🏢 Trưởng BU Premium [{top_prem.employee_code}] {top_prem.full_name} -> Báo cáo: {emp_cco.full_name}")

        if head_prem and mgr_mb_prem and head_prem != mgr_mb_prem:
            a_mb = EmployeeAssignment.objects.filter(employee=mgr_mb_prem, department=dept_prem).first()
            if a_mb:
                a_mb.manager = head_prem
                if not dry_run:
                    a_mb.save()

        if mgr_mn_prem:
            a_mn = EmployeeAssignment.objects.filter(employee=mgr_mn_prem, department=dept_prem).first()
            if a_mn:
                a_mn.manager = top_prem
                if not dry_run:
                    a_mn.save()

        for a in EmployeeAssignment.objects.filter(department=dept_prem).exclude(employee__in=[top_prem, mgr_mb_prem, mgr_mn_prem]):
            t_name = a.title.title_name.lower()
            if 'mb' in t_name and mgr_mb_prem:
                a.manager = mgr_mb_prem
            elif 'mn' in t_name and mgr_mn_prem:
                a.manager = mgr_mn_prem
            else:
                a.manager = top_prem
            if not dry_run:
                a.save()

    # 4. BU Value (Nguyễn Ngọc Huy Phong / Nguyễn Văn Hữu_SALE -> Staff)
    dept_val = Department.objects.filter(department_code='BU_Value').first()
    head_val = Employee.objects.filter(employee_code='2000793').first()
    mgr_mb_val = Employee.objects.filter(employee_code='2000798').first()
    top_val = head_val or mgr_mb_val

    if dept_val and top_val:
        a_top = EmployeeAssignment.objects.filter(employee=top_val, department=dept_val).first()
        if a_top:
            a_top.manager = emp_cco
            if not dry_run:
                a_top.save()
            print(f"🏢 Trưởng BU Value [{top_val.employee_code}] {top_val.full_name} -> Báo cáo: {emp_cco.full_name}")

        if head_val and mgr_mb_val and head_val != mgr_mb_val:
            a_mb = EmployeeAssignment.objects.filter(employee=mgr_mb_val, department=dept_val).first()
            if a_mb:
                a_mb.manager = head_val
                if not dry_run:
                    a_mb.save()

        for a in EmployeeAssignment.objects.filter(department=dept_val).exclude(employee__in=[top_val, mgr_mb_val]):
            a.manager = mgr_mb_val or top_val
            if not dry_run:
                a.save()

    # 5. BU Manufacturing (Hồ Xuân Quang / Tô Quốc Thuấn -> Staff)
    dept_mfg = Department.objects.filter(department_code='BU_Manufacturing').first()
    head_mfg = Employee.objects.filter(employee_code='9038').first()
    mgr_qlda = Employee.objects.filter(employee_code='2000169').first()
    top_mfg = head_mfg or mgr_qlda

    if dept_mfg and top_mfg:
        a_top = EmployeeAssignment.objects.filter(employee=top_mfg, department=dept_mfg).first()
        if a_top:
            a_top.manager = emp_cco
            if not dry_run:
                a_top.save()
            print(f"🏢 Trưởng BU Manufacturing [{top_mfg.employee_code}] {top_mfg.full_name} -> Báo cáo: {emp_cco.full_name}")

        if head_mfg and mgr_qlda and head_mfg != mgr_qlda:
            a_qlda = EmployeeAssignment.objects.filter(employee=mgr_qlda, department=dept_mfg).first()
            if a_qlda:
                a_qlda.manager = head_mfg
                if not dry_run:
                    a_qlda.save()

        for a in EmployeeAssignment.objects.filter(department=dept_mfg).exclude(employee__in=[top_mfg, mgr_qlda]):
            a.manager = mgr_qlda or top_mfg
            if not dry_run:
                a.save()

    # 6. BU Agritech-Eco (Trần Duy Hiếu / Phạm Văn Mừng / Trần Hồng Quân -> Staff)
    dept_agri = Department.objects.filter(department_code='BU_Agritech-Eco').first()
    head_agri = Employee.objects.filter(employee_code='7511').first()
    mgr_agri = Employee.objects.filter(employee_code='9004').first()
    mgr_aqua = Employee.objects.filter(employee_code='2000477').first()
    top_agri = head_agri or mgr_agri or mgr_aqua

    if dept_agri and top_agri:
        a_top = EmployeeAssignment.objects.filter(employee=top_agri, department=dept_agri).first()
        if a_top:
            a_top.manager = emp_cco
            if not dry_run:
                a_top.save()
            print(f"🏢 Trưởng BU Agritech-Eco [{top_agri.employee_code}] {top_agri.full_name} -> Báo cáo: {emp_cco.full_name}")

        if head_agri:
            for sub_m in [mgr_agri, mgr_aqua]:
                if sub_m:
                    a_sub = EmployeeAssignment.objects.filter(employee=sub_m, department=dept_agri).first()
                    if a_sub:
                        a_sub.manager = head_agri
                        if not dry_run:
                            a_sub.save()

        for a in EmployeeAssignment.objects.filter(department=dept_agri).exclude(employee__in=[head_agri, mgr_agri, mgr_aqua]):
            a.manager = top_agri
            if not dry_run:
                a.save()

    # 7. Auto assign remaining departments (SSC SCM, HCNS, Kế toán, TechCenter...) to COO (Phạm Định) or their heads
    other_depts = Department.objects.exclude(department_code__in=['BU_Elevator', 'BU_Premium', 'BU_Value', 'BU_Manufacturing', 'BU_Agritech-Eco'])
    for d in other_depts:
        assigns = EmployeeAssignment.objects.filter(department=d, employee__is_active=True).select_related('employee', 'title')
        mgrs = [a for a in assigns if is_manager_title(a.title.title_name)]
        if mgrs:
            mgrs.sort(key=lambda a: get_title_rank(a.title.title_name))
            top_d_mgr = mgrs[0]
            if top_d_mgr.employee != emp_coo and top_d_mgr.employee != emp_cco:
                top_d_mgr.manager = emp_coo
                if not dry_run:
                    top_d_mgr.save()

            for a in assigns.exclude(employee=top_d_mgr.employee):
                if a.employee not in [emp_cco, emp_coo]:
                    a.manager = top_d_mgr.employee
                    if not dry_run:
                        a.save()

    print("✅ ĐÃ CHUẨN HÓA VÀ CẬP NHẬT CÂY QUẢN LÝ THÀNH CÔNG!")


if __name__ == '__main__':
    auto_assign_department_managers(dry_run=False)
