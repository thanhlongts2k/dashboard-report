# -*- coding: utf-8 -*-
"""
Django Management Command: send_executive_dashboard
Gửi Email Báo Cáo Điều Hành Tổng Quan (Executive Dashboard) cho Ban Lãnh Đạo (BOD) & Quản lý cấp cao.

Cú pháp:
  # 1. Gửi báo cáo cho Ban Lãnh Đạo chốt ngày hôm qua (T-1):
  python manage.py send_executive_dashboard --to-email sep@haophuong.com

  # 2. Gửi test báo cáo chốt ngày cụ thể có kèm CC:
  python manage.py send_executive_dashboard --to-email test@haophuong.com --cc sep1@haophuong.com,sep2@haophuong.com --date 2026-08-24

  # 3. Chạy thử nghiệm (dry-run, chỉ in thống kê, không gửi mail thật):
  python manage.py send_executive_dashboard --to-email test@haophuong.com --date 2026-08-24 --dry-run
"""
import sys
from datetime import date, timedelta, datetime
from django.core.management.base import BaseCommand
from accounting.services.debt_mailer import send_executive_dashboard_email, collect_executive_dashboard_data


class Command(BaseCommand):
    help = "Gửi email Báo Cáo Điều Hành Tổng Quan (Executive Dashboard) cho BOD và Quản lý"

    def add_arguments(self, parser):
        parser.add_argument(
            '--to-email',
            type=str,
            required=True,
            help='Địa chỉ email người nhận (Ví dụ: sep@haophuong.com)'
        )
        parser.add_argument(
            '--cc',
            type=str,
            default=None,
            help='Danh sách email CC phân cách bằng dấu phẩy'
        )
        parser.add_argument(
            '--date',
            type=str,
            default=None,
            help='Ngày chốt báo cáo YYYY-MM-DD (Mặc định: ngày hôm qua T-1)'
        )
        parser.add_argument(
            '--period',
            type=str,
            default=None,
            help='Kỳ báo cáo YYYY-MM (Tùy chọn)'
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            default=False,
            help='Chạy thử nghiệm hiển thị thông số và render, không gửi email thực'
        )

    def handle(self, *args, **options):
        try:
            sys.stdout.reconfigure(encoding='utf-8')
        except Exception:
            pass

        to_email = (options.get('to_email') or '').strip()
        cc_raw = options.get('cc')
        cc_list = [e.strip() for e in cc_raw.split(',') if e.strip()] if cc_raw else []
        report_date_str = options.get('date')
        period = options.get('period')
        is_dry_run = options.get('dry_run', False)

        if not report_date_str and not period:
            # Mặc định lấy ngày làm việc hôm trước (T-1)
            from accounting.services.debt_mailer import get_previous_working_day
            prev_work_day = get_previous_working_day()
            report_date_str = prev_work_day.strftime('%Y-%m-%d')

        self.stdout.write("=" * 95)
        mode_str = "🧪 CHẾ ĐỘ THỬ NGHIỆM (DRY-RUN)" if is_dry_run else "🚨 GỬI EMAIL THỰC TẾ"
        self.stdout.write(self.style.WARNING(f"📊 TIẾN TRÌNH GỬI EMAIL EXECUTIVE DASHBOARD [{mode_str}]"))
        self.stdout.write(f"📧 Người nhận chính (To): {to_email}")
        if cc_list:
            self.stdout.write(f"👥 Danh sách CC: {', '.join(cc_list)}")
        if report_date_str:
            self.stdout.write(f"📅 Ngày chốt báo cáo: {report_date_str}")
        if period:
            self.stdout.write(f"🗓️ Kỳ báo cáo: {period}")
        self.stdout.write("=" * 95)

        try:
            # 1. Thu thập và in tóm tắt số liệu
            data = collect_executive_dashboard_data(report_date=report_date_str, period=period)
            
            self.stdout.write(self.style.SUCCESS(f"\n📈 [KHỐI 1] CHỈ SỐ TÀI CHÍNH & KINH DOANH CỐT LÕI (KỲ {data['period_display']}):"))
            for card in data['top_kpis']:
                self.stdout.write(
                    f"   + {card['title']:<18}: {card['actual_display']:>10} / {card['plan_display']:<14} | "
                    f"Tiến độ: {card['rate']:>6.2f}% | Lệch: {card['gap_display']:>10}"
                )

            self.stdout.write(self.style.SUCCESS(f"\n🌐 [KHỐI 2] TỶ TRỌNG DOANH THU OVERSEA & NỘI ĐỊA:"))
            for card in data['oversea_kpis']:
                self.stdout.write(
                    f"   + {card['title']:<38}: {card['actual_display']:>10} / {card['base_display']:<10} | "
                    f"Tỷ trọng: {card['share_rate']:>5.1f}%"
                )

            self.stdout.write(self.style.SUCCESS(f"\n📊 [KHỐI 3] BẢNG TỔNG HỢP HIỆU SUẤT 8 ĐƠN VỊ KINH DOANH (BU):"))
            self.stdout.write(f"{'STT':<4} | {'Mã BU':<16} | {'Tên Đơn Vị Kinh Doanh':<26} | {'Doanh Thu (Thực tế / KH)':<30} | {'Thu Tiền (Thực tế / KH)':<30} | {'Dư Nợ 1311':<14} | {'Nợ Quá Hạn':<18}")
            self.stdout.write("-" * 155)

            for idx, r in enumerate(data['bu_rows'], start=1):
                rev_str = f"{r['revenue_actual']:>12,.0f} / {r['revenue_plan']:>12,.0f} ({r['revenue_rate']:>5.1f}%)"
                col_str = f"{r['collection_actual']:>12,.0f} / {r['collection_plan']:>12,.0f} ({r['collection_rate']:>5.1f}%)"
                ovd_str = f"{r['overdue_debt']:>10,.0f} ({r['overdue_rate']:>4.1f}%)"
                self.stdout.write(
                    f"{idx:<4} | {r['bu_code']:<16} | {r['bu_name']:<26} | {rev_str:<30} | {col_str:<30} | "
                    f"{r['total_debt']:>14,.0f} | {ovd_str:<18}"
                )

            tot = data['total_summary']
            tot_rev_str = f"{tot['revenue_actual']:>12,.0f} / {tot['revenue_plan']:>12,.0f} ({tot['revenue_rate']:>5.1f}%)"
            tot_col_str = f"{tot['collection_actual']:>12,.0f} / {tot['collection_plan']:>12,.0f} ({tot['collection_rate']:>5.1f}%)"
            tot_ovd_str = f"{tot['overdue_debt']:>10,.0f} ({tot['overdue_rate']:>4.1f}%)"
            self.stdout.write("-" * 155)
            self.stdout.write(
                f"{'':<4} | {'TỔNG CỘNG (8 BU)':<45} | {tot_rev_str:<30} | {tot_col_str:<30} | "
                f"{tot['total_debt']:>14,.0f} | {tot_ovd_str:<18}"
            )
            self.stdout.write("=" * 155)

            # 2. Gửi email
            if is_dry_run:
                self.stdout.write(self.style.WARNING("ℹ️ [DRY-RUN] Bỏ qua bước phát tán email thật ra ngoài."))
            else:
                self.stdout.write(f"🚀 Đang tiến hành gửi email đến {to_email}...")
                ok, msg = send_executive_dashboard_email(
                    to_email=to_email,
                    cc_emails=cc_list,
                    report_date=report_date_str,
                    period=period,
                    dry_run=False
                )
                if ok:
                    self.stdout.write(self.style.SUCCESS(f"✅ GỬI EMAIL THÀNH CÔNG đến {to_email}!"))
                else:
                    self.stdout.write(self.style.ERROR(f"❌ GỬI EMAIL THẤT BẠI: {msg}"))

            self.stdout.write("=" * 95)

        except Exception as e:
            self.stdout.write(self.style.ERROR(f"❌ Xảy ra lỗi trong tiến trình: {str(e)}"))
            raise e
