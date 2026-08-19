"""
Management Command: sync_employee_users
Đồng bộ danh sách nhân viên (Employee) vào bảng tài khoản đăng nhập (User).
Hỗ trợ:
- Tự động gán quyền 4 Groups: BOD_ADMIN, BU_HEAD, SALES, VIEWER.
- Tách Họ & Tên chuẩn tiếng Việt.
- Tuỳ chọn --dry-run (chạy thử nghiệm an toàn).
- Tuỳ chọn --bu (lọc theo phòng ban/BU).
- Tuỳ chọn --email (lọc riêng 1 nhân viên).
"""

import sys
from django.core.management.base import BaseCommand
from django.db.models import Q
from accounting.models import Employee
from accounting.services.user_provisioner import (
    ensure_auth_groups_exist,
    provision_user_for_employee,
    AUTH_GROUPS
)


class Command(BaseCommand):
    help = 'Đồng bộ danh sách nhân viên (Employee) vào hệ thống tài khoản đăng nhập (User) cho Google SSO'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            dest='dry_run',
            default=False,
            help='Chạy thử nghiệm kiểm tra số lượng User sẽ tạo/cập nhật mà không ghi vào CSDL'
        )
        parser.add_argument(
            '--bu',
            type=str,
            dest='bu',
            default=None,
            help='Lọc theo mã phòng ban / BU (ví dụ: --bu BU_ELEVATOR)'
        )
        parser.add_argument(
            '--email',
            type=str,
            dest='email',
            default=None,
            help='Đồng bộ riêng cho 1 địa chỉ email (ví dụ: --email long.nguyen@haophuong.com)'
        )

    def handle(self, *args, **options):
        try:
            sys.stdout.reconfigure(encoding='utf-8')
        except (AttributeError, IOError):
            pass

        dry_run = options['dry_run']
        bu_filter = options['bu']
        email_filter = options['email']

        ensure_auth_groups_exist()

        mode_str = "🔍 [CHẾ ĐỘ THỬ NGHIỆM - DRY RUN]" if dry_run else "🚀 [CHẾ ĐỘ THỰC THI - LIVE]"
        self.stdout.write(self.style.MIGRATE_HEADING(f"\n=== ĐỒNG BỘ TÀI KHOẢN NHÂN VIÊN (EMPLOYEE USER PROVISIONING) {mode_str} ==="))

        # Lọc danh sách nhân viên có email
        employees_qs = Employee.objects.filter(is_active=True).exclude(email__isnull=True).exclude(email='')

        if bu_filter:
            employees_qs = employees_qs.filter(
                Q(assignments__department__department_code__icontains=bu_filter) |
                Q(assignments__department__department_name__icontains=bu_filter)
            ).distinct()
            self.stdout.write(f"🏢 Bộ lọc phòng ban/BU: '{bu_filter}'")

        if email_filter:
            employees_qs = employees_qs.filter(email__iexact=email_filter.strip())
            self.stdout.write(f"📧 Bộ lọc email: '{email_filter}'")

        total_count = employees_qs.count()
        self.stdout.write(f"📋 Tìm thấy tổng cộng {total_count} nhân viên có email hợp lệ.\n")

        if total_count == 0:
            self.stdout.write(self.style.WARNING("⚠️ Không tìm thấy nhân viên nào phù hợp điều kiện lọc."))
            return

        created_count = 0
        updated_count = 0
        skipped_count = 0
        group_stats = {g: 0 for g in AUTH_GROUPS.keys()}

        for idx, emp in enumerate(employees_qs, 1):
            res = provision_user_for_employee(emp, dry_run=dry_run)
            
            if not res['success']:
                skipped_count += 1
                self.stdout.write(self.style.WARNING(f"  [{idx:03d}/{total_count:03d}] ⚠️ BỎ QUA: {emp.full_name} ({emp.employee_code}) - {res.get('reason')}"))
                continue

            role_group = res.get('role_group', 'VIEWER')
            group_stats[role_group] = group_stats.get(role_group, 0) + 1

            action = res.get('action', 'CREATE')
            if action == 'CREATE':
                created_count += 1
                action_badge = "[TẠO MỚI]"
                color_func = self.style.SUCCESS
            else:
                updated_count += 1
                action_badge = "[CẬP NHẬT]"
                color_func = self.style.WARNING

            self.stdout.write(
                color_func(
                    f"  [{idx:03d}/{total_count:03d}] {action_badge:11s} {res['email']:<32s} | "
                    f"Tên: {res['last_name']} {res['first_name']} | Role: [{role_group:^9s}] | Chức danh: {res['title']}"
                )
            )

        # In bảng tổng kết
        self.stdout.write("\n" + "=" * 80)
        self.stdout.write(self.style.MIGRATE_HEADING("📊 BẢNG TỔNG KẾT KẾT QUẢ ĐỒNG BỘ:"))
        self.stdout.write(f"  - Tổng số nhân viên quét : {total_count}")
        self.stdout.write(f"  - Tạo tài khoản mới       : {created_count}")
        self.stdout.write(f"  - Cập nhật tài khoản cũ   : {updated_count}")
        self.stdout.write(f"  - Bỏ qua (không hợp lệ)   : {skipped_count}")
        self.stdout.write("-" * 80)
        self.stdout.write(self.style.MIGRATE_HEADING("👥 PHÂN BỔ THEO 4 DJANGO GROUPS:"))
        for g_name, g_desc in AUTH_GROUPS.items():
            count = group_stats.get(g_name, 0)
            pct = (count / total_count * 100) if total_count > 0 else 0
            self.stdout.write(f"  * [{g_name:^9s}]: {count:3d} tài khoản ({pct:5.1f}%) — {g_desc}")
        self.stdout.write("=" * 80 + "\n")

        if dry_run:
            self.stdout.write(self.style.NOTICE("💡 Chú ý: Đây là chạy thử nghiệm (--dry-run). Hãy bỏ cờ --dry-run để ghi thực tế vào CSDL.\n"))
        else:
            self.stdout.write(self.style.SUCCESS("🎉 Đồng bộ tài khoản người dùng thành công 100%!\n"))
