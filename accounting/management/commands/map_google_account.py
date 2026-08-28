import logging
from django.core.management.base import BaseCommand, CommandError
from django.db.models import Q
from accounting.models import Employee
from accounting.services.user_provisioner import provision_user_for_employee, get_user_role_info

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Liên kết hoặc gỡ bỏ Email Google cá nhân (Gmail) cho nhân sự (Employee)"

    def add_arguments(self, parser):
        parser.add_argument(
            '--code',
            type=str,
            help='Mã nhân viên (Employee Code, ví dụ: 3003, 2001)'
        )
        parser.add_argument(
            '--email',
            type=str,
            help='Email công ty của nhân viên (ví dụ: dung.daotien@haophuong.com)'
        )
        parser.add_argument(
            '--gmail',
            type=str,
            help='Địa chỉ Gmail cá nhân cần liên kết (ví dụ: dungdt88@gmail.com)'
        )
        parser.add_argument(
            '--remove',
            action='store_true',
            help='Gỡ bỏ Gmail cá nhân khỏi hồ sơ nhân sự'
        )
        parser.add_argument(
            '--list',
            action='store_true',
            help='Liệt kê danh sách tất cả nhân viên đã liên kết Gmail cá nhân'
        )

    def handle(self, *args, **options):
        # 1. Liệt kê danh sách nếu có cờ --list
        if options.get('list'):
            linked_employees = Employee.objects.filter(
                google_sso_email__isnull=False
            ).exclude(google_sso_email='').order_by('employee_code')

            self.stdout.write(self.style.SUCCESS("\n======================================================================"))
            self.stdout.write(self.style.SUCCESS("DANH SÁCH NHÂN SỰ ĐÃ LIÊN KẾT GMAIL CÁ NHÂN"))
            self.stdout.write(self.style.SUCCESS("======================================================================"))
            
            if not linked_employees.exists():
                self.stdout.write(self.style.WARNING("Chưa có nhân sự nào được liên kết Gmail cá nhân."))
                return

            for emp in linked_employees:
                role_info = get_user_role_info(emp.user) if emp.user else {}
                role_name = role_info.get('primary_role', '—')
                status_icon = "🟢" if emp.is_active else "🔴"
                self.stdout.write(
                    f" {status_icon} [{emp.employee_code}] {emp.full_name} | Role: [{role_name}]\n"
                    f"    - Email công ty : {emp.email or '—'}\n"
                    f"    - Gmail cá nhân : {emp.google_sso_email}\n"
                )
            return

        code = options.get('code')
        email = options.get('email')
        gmail = options.get('gmail')
        remove = options.get('remove')

        if not code and not email:
            raise CommandError("Vui lòng cung cấp --code <Mã NV> hoặc --email <Email công ty>!")

        # 2. Tìm nhân viên
        query = Q()
        if code:
            query |= Q(employee_code__iexact=code.strip())
        if email:
            query |= Q(email__iexact=email.strip())

        employee = Employee.objects.filter(query).first()
        if not employee:
            raise CommandError(f"Không tìm thấy nhân viên với điều kiện: code={code}, email={email}")

        # 3. Gỡ bỏ Gmail nếu có cờ --remove
        if remove:
            if not gmail:
                old_gmail = employee.google_sso_email
                employee.google_sso_email = None
                employee.save(update_fields=['google_sso_email'])
                self.stdout.write(self.style.SUCCESS(
                    f"✅ Đã gỡ bỏ toàn bộ Gmail cá nhân '{old_gmail}' khỏi nhân viên [{employee.employee_code}] {employee.full_name}."
                ))
            else:
                target_g = gmail.strip().lower()
                current_list = [
                    e.strip()
                    for e in (employee.google_sso_email or '').replace(';', ',').split(',')
                    if e.strip() and e.strip().lower() != target_g
                ]
                employee.google_sso_email = ', '.join(current_list) if current_list else None
                employee.save(update_fields=['google_sso_email'])
                self.stdout.write(self.style.SUCCESS(
                    f"✅ Đã gỡ bỏ Gmail '{target_g}' khỏi nhân viên [{employee.employee_code}] {employee.full_name}."
                ))
            return

        # 4. Thêm / Cập nhật Gmail
        if not gmail:
            raise CommandError("Vui lòng cung cấp --gmail <Địa chỉ Gmail cá nhân> để liên kết!")

        target_g = gmail.strip().lower()

        # Kiểm tra xem Gmail này đã được gán cho nhân viên khác chưa
        existing = Employee.objects.filter(
            google_sso_email__icontains=target_g
        ).exclude(id=employee.id).first()

        if existing:
            self.stdout.write(self.style.WARNING(
                f"⚠️ Cảnh báo: Gmail '{target_g}' hiện cũng đang được gán cho nhân viên [{existing.employee_code}] {existing.full_name}."
            ))

        current_list = [
            e.strip()
            for e in (employee.google_sso_email or '').replace(';', ',').split(',')
            if e.strip()
        ]

        if target_g not in [e.lower() for e in current_list]:
            current_list.append(target_g)

        employee.google_sso_email = ', '.join(current_list)
        employee.save(update_fields=['google_sso_email'])

        # Tự động đồng bộ User
        provision_user_for_employee(employee)

        self.stdout.write(self.style.SUCCESS("\n======================================================================"))
        self.stdout.write(self.style.SUCCESS(f"✅ LIÊN KẾT GMAIL THÀNH CÔNG CHO: {employee.full_name}"))
        self.stdout.write(self.style.SUCCESS("======================================================================"))
        self.stdout.write(f"  * Mã nhân viên   : {employee.employee_code}")
        self.stdout.write(f"  * Email công ty  : {employee.email or '—'}")
        self.stdout.write(f"  * Gmail cá nhân  : {employee.google_sso_email}")
        self.stdout.write(f"  * Tài khoản User : {employee.user.username if employee.user else '—'}")
        self.stdout.write("----------------------------------------------------------------------")
        self.stdout.write(">> Nhân viên có thể dùng Gmail trên để đăng nhập Google SSO ngay lập tức!\n")
