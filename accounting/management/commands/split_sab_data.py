import logging
from django.core.management.base import BaseCommand
from django.db import transaction
from django.db.models import Q
from accounting.models import (
    BusinessUnit, Employee, EmployeeAssignment, Customer, 
    SalesTransaction, AccountDetail, ReceivablesAgeing, BUPerformance
)
from accounting.services.kpi_calculator import update_single_bu_performance
from accounting.services.user_provisioner import provision_user_for_employee

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Khởi tạo BU_SAB độc lập, tự động phân tách dữ liệu của anh TRẦN HỒNG QUÂN ra khỏi BU_AGRITECH và tính toán lại KPI 2026."

    def add_arguments(self, parser):
        parser.add_argument(
            '--year',
            type=int,
            default=2026,
            help='Năm cần tính toán lại KPI (mặc định: 2026)'
        )

    def handle(self, *args, **options):
        target_year = options['year']
        self.stdout.write(self.style.NOTICE(f"🚀 BẮT ĐẦU TIẾN TRÌNH TÁCH BU_SAB RA KHỎI BU_AGRITECH (NĂM {target_year})..."))

        with transaction.atomic():
            # 1. Khởi tạo/Cập nhật BusinessUnit BU_SAB
            sab_bu, created = BusinessUnit.objects.get_or_create(
                code='BU_SAB',
                defaults={
                    'name': 'Thủy sản thông minh (SAB)',
                    'is_main': True,
                    'manager': 'TRẦN HỒNG QUÂN',
                }
            )
            if not created:
                sab_bu.name = 'Thủy sản thông minh (SAB)'
                sab_bu.is_main = True
                sab_bu.manager = 'TRẦN HỒNG QUÂN'
                sab_bu.save()
            self.stdout.write(self.style.SUCCESS(f"✅ Đã cấu hình BusinessUnit: [{sab_bu.code}] - {sab_bu.name} (Manager: {sab_bu.manager})"))

            # Đảm bảo BU_AGRITECH có Trưởng BU là TRẦN DUY HIẾU
            agritech_bu = BusinessUnit.objects.filter(code='BU_AGRITECH').first()
            if agritech_bu:
                agritech_bu.manager = 'TRẦN DUY HIẾU'
                agritech_bu.save(update_fields=['manager'])

            # 2. Tìm nhân viên TRẦN HỒNG QUÂN (Mã 2000477)
            quan_emp = Employee.objects.filter(
                Q(employee_code='2000477') | Q(full_name__iexact='TRẦN HỒNG QUÂN')
            ).first()

            if quan_emp:
                self.stdout.write(self.style.SUCCESS(f"✅ Tìm thấy nhân viên: [{quan_emp.employee_code}] {quan_emp.full_name} ({quan_emp.email})"))
                from accounting.models import Department, JobTitle
                dept_sab, _ = Department.objects.get_or_create(
                    department_code='BU_SAB',
                    defaults={'department_name': 'Thủy sản thông minh (SAB)'}
                )
                title_head, _ = JobTitle.objects.get_or_create(
                    title_name='Trưởng bộ phận Thủy sản thông minh (SAB)'
                )
                # Gán Assignment BU_HEAD cho BU_SAB
                EmployeeAssignment.objects.update_or_create(
                    employee=quan_emp,
                    department=dept_sab,
                    defaults={
                        'title': title_head,
                        'start_date': '2026-01-01',
                    }
                )
            else:
                self.stdout.write(self.style.WARNING("⚠️ Không tìm thấy nhân viên TRẦN HỒNG QUÂN trong Employee model."))

            # 3. Cập nhật Khách hàng (Customer) của anh Hồng Quân -> BU_SAB
            cust_qs = Customer.objects.filter(
                Q(assigned_employee=quan_emp) | 
                Q(assigned_employee__employee_code='2000477') |
                Q(assigned_employee__full_name__icontains='HỒNG QUÂN')
            )
            cust_count = cust_qs.update(business_unit=sab_bu)
            self.stdout.write(self.style.SUCCESS(f"✅ Đã cập nhật {cust_count} khách hàng sang BU_SAB."))

            # 4. Cập nhật Giao dịch Bán hàng (SalesTransaction) -> BU_SAB
            sales_qs = SalesTransaction.objects.filter(
                Q(employee=quan_emp) |
                Q(employee__employee_code='2000477') |
                Q(employee__full_name__icontains='HỒNG QUÂN') |
                Q(customer__in=cust_qs)
            )
            sales_count = sales_qs.update(business_unit=sab_bu)
            self.stdout.write(self.style.SUCCESS(f"✅ Đã chuyển {sales_count} giao dịch bán hàng sang BU_SAB."))

            # 5. Cập nhật Sổ chi tiết tài khoản (AccountDetail) -> BU_SAB
            acc_qs = AccountDetail.objects.filter(
                Q(customer__in=cust_qs) |
                Q(business_unit__code__in=['BU_AGRITECH', 'AGRITECH'], customer__assigned_employee=quan_emp)
            )
            acc_count = acc_qs.update(business_unit=sab_bu)
            self.stdout.write(self.style.SUCCESS(f"✅ Đã chuyển {acc_count} chứng từ thu/chi chi tiết sang BU_SAB."))

        # 6. Tính toán lại KPI 12 tháng của năm target_year cho BU_AGRITECH, BU_SAB và TOTAL_CORP
        self.stdout.write(self.style.NOTICE(f"\n📊 Đang tính toán lại KPI 12 tháng năm {target_year}..."))
        for m in range(1, 13):
            # Tính BU_AGRITECH
            if agritech_bu:
                update_single_bu_performance(agritech_bu.id, month=m, year=target_year)
            # Tính BU_SAB
            update_single_bu_performance(sab_bu.id, month=m, year=target_year)
            # Tính TOTAL_CORP (toàn công ty)
            update_single_bu_performance(None, month=m, year=target_year)

        self.stdout.write(self.style.SUCCESS(f"✅ Đã tính toán lại KPI hoàn tất cho 12 tháng năm {target_year}."))

        # 7. Đồng bộ lại RBAC User Provisioning
        self.stdout.write(self.style.NOTICE("\n🔑 Đang đồng bộ lại quyền hạn người dùng (RBAC User Provisioning)..."))
        active_emps = Employee.objects.filter(is_active=True)
        for emp in active_emps:
            provision_user_for_employee(emp)
        self.stdout.write(self.style.SUCCESS(f"✅ Đã đồng bộ {active_emps.count()} tài khoản nhân sự."))

        self.stdout.write(self.style.SUCCESS("\n🎉 HOÀN TẤT TÁCH BU_SAB THÀNH CÔNG RỰC RỠ!"))
