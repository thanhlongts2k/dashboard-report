# -*- coding: utf-8 -*-
"""
Django Management Command: send_debt_reminders
Hệ thống gửi email nhắc nợ phân cấp tự động (Sales & Trưởng BU).
Hỗ trợ cả chế độ Thử nghiệm (Dry-run) và Gửi thực tế (Live Production).

Cú pháp:
  # 1. Chạy thử nghiệm (Dry-run mặc định):
  python manage.py send_debt_reminders --period 2026-08

  # 2. Gửi thử nghiệm 1 email mẫu:
  python manage.py send_debt_reminders --period 2026-08 --test-email abc@haophuong.com

  # 3. Gửi THỰC TẾ (Live):
  python manage.py send_debt_reminders --period 2026-08 --live --yes

  # 4. Chỉ gửi cho riêng Trưởng BU:
  python manage.py send_debt_reminders --period 2026-08 --live --recipient-type MANAGERS --yes

  # 5. Chỉ gửi cho 1 BU cụ thể:
  python manage.py send_debt_reminders --period 2026-08 --live --bu BU_ELEVATOR --yes
"""
import sys
from django.core.management.base import BaseCommand
from accounting.services.debt_mailer import send_debt_reminders_process, get_target_period


class Command(BaseCommand):
    help = "Hệ thống tự động gửi email nhắc nợ phân cấp (Sales & Trưởng BU)"

    def add_arguments(self, parser):
        parser.add_argument(
            '--period',
            type=str,
            default=None,
            help='Kỳ báo cáo YYYY-MM (Mặc định: kỳ mới nhất có phát sinh dữ liệu)'
        )
        parser.add_argument(
            '--live',
            action='store_true',
            default=False,
            help='BẬT CHẾ ĐỘ GỬI THỰC TẾ (LIVE) đến email công ty của từng nhân viên'
        )
        parser.add_argument(
            '--override-email',
            type=str,
            default=None,
            help='Chuyển hướng toàn bộ email nhắc nợ về địa chỉ test được chỉ định'
        )
        parser.add_argument(
            '--test-email',
            type=str,
            default=None,
            help='Alias của --override-email'
        )
        parser.add_argument(
            '--bu',
            type=str,
            default=None,
            help='Mã BU cụ thể (Ví dụ: BU_ELEVATOR, BU_IBIZ PREMIUM, Oversea...)'
        )
        parser.add_argument(
            '--recipients',
            '--recipient-type',
            dest='recipient_type',
            type=str,
            choices=['ALL', 'SALES', 'MANAGERS'],
            default='ALL',
            help='Đối tượng nhận (ALL, SALES, MANAGERS)'
        )
        parser.add_argument(
            '--cc',
            type=str,
            default=None,
            help='Danh sách email CC tùy chọn phân cách bằng dấu phẩy (ghi đè DEBT_REMINDER_CC_EMAILS)'
        )
        parser.add_argument(
            '--yes', '-y',
            action='store_true',
            default=False,
            help='Tự động xác nhận bỏ qua prompt cảnh báo khi chạy --live'
        )

    def handle(self, *args, **options):
        try:
            sys.stdout.reconfigure(encoding='utf-8')
        except Exception:
            pass

        period = get_target_period(options.get('period'))
        is_live = options.get('live', False)
        is_dry_run = not is_live
        override_email = options.get('override_email') or options.get('test_email')
        bu_code = options.get('bu')
        recipient_type = options.get('recipient_type', 'ALL')
        auto_yes = options.get('yes', False)
        cc_raw = options.get('cc')
        cc_list = [e.strip() for e in cc_raw.split(',') if e.strip()] if cc_raw else None

        self.stdout.write("=" * 85)
        if override_email:
            self.stdout.write(self.style.WARNING(
                f"🧪 TIẾN TRÌNH GỬI EMAIL NHẮC NỢ [CHẾ ĐỘ TEST CHUYỂN HƯỚNG] — KỲ {period}"
            ))
            self.stdout.write(f"📧 Toàn bộ email ({recipient_type}) sẽ được chuyển hướng về: {override_email}")
            if bu_code:
                self.stdout.write(f"🏢 Giới hạn phạm vi BU: {bu_code}")
        elif is_dry_run:
            self.stdout.write(self.style.WARNING(
                f"🧪 TIẾN TRÌNH GỬI EMAIL NHẮC NỢ [CHẾ ĐỘ THỬ NGHIỆM - DRY-RUN] — KỲ {period}"
            ))
            self.stdout.write("ℹ️ Chỉ thống kê dữ liệu, KHÔNG gửi email thật ra ngoài.")
        else:
            self.stdout.write(self.style.ERROR(
                f"🚨 TIẾN TRÌNH GỬI EMAIL NHẮC NỢ [CHẾ ĐỘ THỰC TẾ - LIVE PRODUCTION] — KỲ {period}"
            ))
            self.stdout.write(self.style.WARNING(
                "⚠️ CẢNH BÁO: Email sẽ được gửi trực tiếp đến hộp thư của Nhân viên Sales và Trưởng BU!"
            ))

            if not auto_yes:
                confirm = input("\n👉 Bạn có chắc chắn muốn gửi email THỰC TẾ cho toàn bộ danh sách? (nhập 'yes' để xác nhận): ")
                if confirm.strip().lower() not in ['yes', 'y']:
                    self.stdout.write(self.style.NOTICE("❌ Đã hủy bỏ tiến trình gửi thực tế."))
                    return

        self.stdout.write("=" * 85)

        try:
            result = send_debt_reminders_process(
                period=period,
                dry_run=is_dry_run,
                test_email=override_email,
                override_email=override_email,
                bu_code=bu_code,
                recipient_type=recipient_type,
                cc_emails=cc_list
            )

            self.stdout.write("\n" + "-" * 85)
            self.stdout.write("📊 BÁO CÁO TIẾN ĐỘ THỰC THI:")
            for log in result.get('logs', []):
                self.stdout.write(f"   {log}")

            sales_sum = result.get('sales_summary', {})
            bu_sum = result.get('bu_summary', {})

            self.stdout.write("-" * 85)
            self.stdout.write(self.style.SUCCESS("📈 TỔNG HỢP KẾT QUẢ:"))
            self.stdout.write(
                f"   + Cấp Sales   : Thành công={sales_sum.get('success', 0)}, "
                f"Thất bại={sales_sum.get('failed', 0)}, Bỏ qua={sales_sum.get('skipped', 0)}"
            )
            self.stdout.write(
                f"   + Cấp Trưởng BU: Thành công={bu_sum.get('success', 0)}, "
                f"Thất bại={bu_sum.get('failed', 0)}, Bỏ qua={bu_sum.get('skipped', 0)}"
            )
            self.stdout.write("=" * 85)

        except Exception as e:
            self.stdout.write(self.style.ERROR(f"❌ Xảy ra lỗi trong quá trình thực thi: {str(e)}"))
            raise e
