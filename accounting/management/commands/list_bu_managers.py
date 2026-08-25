# -*- coding: utf-8 -*-
"""
Django Management Command: list_bu_managers
Liệt kê danh sách Trưởng Khối (BU Managers) và Email nhận báo cáo điều hành.

Cú pháp:
  python manage.py list_bu_managers
"""
from django.core.management.base import BaseCommand
from django.conf import settings
from accounting.models import BusinessUnit
from accounting.services.debt_mailer import get_bu_manager_info, is_bu_code_excluded


class Command(BaseCommand):
    help = "Liệt kê danh sách Trưởng Đơn vị Kinh doanh (BU Managers) và Email nhận báo cáo"

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS("=" * 125))
        self.stdout.write(self.style.SUCCESS("  📋 DANH SÁCH TRƯỞNG ĐƠN VỊ KINH DOANH (BU MANAGERS) & TRẠNG THÁI GỬI EMAIL NHẮC NỢ"))
        self.stdout.write(self.style.SUCCESS("=" * 125))

        exclude_bu_codes = getattr(settings, 'DEBT_REMINDER_EXCLUDE_BU_CODES', ['ĐTCT', 'BU_DTCT'])
        exclude_emails_raw = getattr(settings, 'DEBT_REMINDER_EXCLUDE_EMAILS', [])
        exclude_emails = set(e.strip().lower() for e in exclude_emails_raw if e and isinstance(e, str) and e.strip())

        # Lấy tất cả BU thương mại hoặc BU chính
        bus = BusinessUnit.objects.filter(is_main=True).order_by('code')
        if not bus.exists():
            bus = BusinessUnit.objects.all().order_by('code')

        rows = []
        for idx, bu in enumerate(bus, 1):
            info = get_bu_manager_info(bu)
            email = (info.get("email") or "").strip()

            # Xác định trạng thái gửi mail
            if is_bu_code_excluded(bu.code, exclude_bu_codes):
                status_text = "[BỎ QUA - BU LOẠI TRỪ]"
                status_tone = "exclude_bu"
            elif email and email.lower() in exclude_emails:
                status_text = "[BỎ QUA - EMAIL BLACKLIST]"
                status_tone = "blacklist"
            elif not email or '@' not in email:
                status_text = "[BỎ QUA - THIẾU EMAIL]"
                status_tone = "missing_email"
            else:
                status_text = "[SẴN SÀNG GỬI]"
                status_tone = "ready"

            rows.append({
                "stt": idx,
                "bu_code": bu.code,
                "bu_name": bu.name or bu.code,
                "emp_code": info.get("employee_code") or "—",
                "manager_name": info.get("name") or "Chưa cấu hình",
                "email": email or "Chưa có email",
                "status_text": status_text,
                "status_tone": status_tone,
            })

        # In Header
        header = f"{'STT':<4} | {'Mã BU':<18} | {'Tên Đơn vị Kinh doanh (BU)':<28} | {'Mã NV':<8} | {'Trưởng BU':<20} | {'Email Nhận Báo Cáo':<28} | {'Trạng Thái Gửi Mail':<24}"
        separator = "-" * len(header)
        self.stdout.write(header)
        self.stdout.write(separator)

        ready_count = 0
        exclude_bu_count = 0
        missing_email_count = 0
        blacklist_count = 0

        # In Rows
        for r in rows:
            line = f"{r['stt']:<4} | {r['bu_code']:<18} | {r['bu_name'][:28]:<28} | {r['emp_code']:<8} | {r['manager_name'][:20]:<20} | {r['email']:<28} | {r['status_text']:<24}"
            if r['status_tone'] == "ready":
                ready_count += 1
                self.stdout.write(self.style.SUCCESS(line))
            elif r['status_tone'] == "exclude_bu":
                exclude_bu_count += 1
                self.stdout.write(self.style.WARNING(line))
            elif r['status_tone'] == "blacklist":
                blacklist_count += 1
                self.stdout.write(self.style.ERROR(line))
            else:
                missing_email_count += 1
                self.stdout.write(self.style.NOTICE(line))

        self.stdout.write(separator)
        self.stdout.write(
            f"📊 Thống kê: Tổng BU={len(rows)} | Sẵn sàng gửi={ready_count} | BU loại trừ={exclude_bu_count} | "
            f"Thiếu email={missing_email_count} | Email Blacklist={blacklist_count}"
        )
        self.stdout.write(self.style.SUCCESS("=" * 125))
