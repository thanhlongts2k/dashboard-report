"""
Script Kích Hoạt Tiến Trình Gửi Email Nhắc Nợ Phân Cấp (CLI Tool)
Hỗ trợ cả chế độ Thử nghiệm (Dry-run) lẫn Gửi thực tế (Live).
"""
import os
import sys
import argparse
import django

sys.stdout.reconfigure(encoding='utf-8')
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE_DIR)

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'report2026.settings')
django.setup()

from accounting.services.debt_mailer import send_debt_reminders_process, get_target_period


def main():
    parser = argparse.ArgumentParser(
        description="Hệ thống tự động gửi email nhắc nợ phân cấp (Sales & Trưởng BU)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Ví dụ sử dụng:
  # 1. Chạy thử nghiệm thống kê (Mặc định dry-run an toàn):
  python scripts/send_live_debt_reminders.py --period 2026-08

  # 2. Chạy thử nghiệm gửi 1 email mẫu về email test cá nhân:
  python scripts/send_live_debt_reminders.py --period 2026-08 --test-email abc@haophuong.com

  # 3. KÍCH HOẠT GỬI THỰC TẾ (LIVE) CHO TOÀN BỘ 23 SALES & 6 TRƯỞNG BU:
  python scripts/send_live_debt_reminders.py --period 2026-08 --live

  # 4. Chỉ gửi thực tế cho riêng Trưởng BU:
  python scripts/send_live_debt_reminders.py --period 2026-08 --live --recipient-type MANAGERS

  # 5. Chỉ gửi thực tế cho 1 BU cụ thể (Ví dụ Thang Máy):
  python scripts/send_live_debt_reminders.py --period 2026-08 --live --bu BU_ELEVATOR
        """
    )
    parser.add_argument('--period', type=str, default=None, help='Kỳ báo cáo YYYY-MM (Mặc định: kỳ mới nhất)')
    parser.add_argument('--live', action='store_true', default=False, help='BẬT CHẾ ĐỘ GỬI THỰC TẾ (LIVE) đến email công ty của từng nhân viên')
    parser.add_argument('--test-email', type=str, default=None, help='Email nhận thử nghiệm khi chạy dry-run')
    parser.add_argument('--bu', type=str, default=None, help='Mã BU cụ thể (Ví dụ: BU_ELEVATOR, BU_IBIZ PREMIUM...)')
    parser.add_argument('--recipient-type', type=str, choices=['ALL', 'SALES', 'MANAGERS'], default='ALL', help='Đối tượng nhận (ALL, SALES, MANAGERS)')
    parser.add_argument('--yes', '-y', action='store_true', default=False, help='Tự động xác nhận bỏ qua prompt cảnh báo khi chạy --live')

    args = parser.parse_args()
    period = get_target_period(args.period)
    is_dry_run = not args.live

    print("=" * 85)
    if is_dry_run:
        print(f"🧪 TIẾN TRÌNH GỬI EMAIL NHẮC NỢ [CHẾ ĐỘ THỬ NGHIỆM - DRY-RUN] — KỲ {period}")
        if args.test_email:
            print(f"📧 Email nhận test chỉ định: {args.test_email}")
        else:
            print("ℹ️ Chỉ thống kê dữ liệu, KHÔNG gửi email thật ra ngoài.")
    else:
        print(f"🚨 TIẾN TRÌNH GỬI EMAIL NHẮC NỢ [CHẾ ĐỘ THỰC TẾ - LIVE PRODUCTION] — KỲ {period}")
        print("⚠️ CẢNH BÁO: Email sẽ được gửi trực tiếp đến hộp thư của Nhân viên Sales và Trưởng BU!")

        if not args.yes:
            confirm = input("\n👉 Bạn có chắc chắn muốn gửi email THỰC TẾ cho toàn bộ danh sách? (nhập 'yes' để xác nhận): ")
            if confirm.strip().lower() not in ['yes', 'y']:
                print("❌ Đã hủy bỏ tiến trình gửi thực tế.")
                return

    print("=" * 85)

    result = send_debt_reminders_process(
        period=period,
        dry_run=is_dry_run,
        test_email=args.test_email,
        bu_code=args.bu,
        recipient_type=args.recipient_type
    )

    print("\n" + "-" * 85)
    print("📊 BÁO CÁO TIẾN ĐỘ THỰC THI:")
    for log in result.get('logs', []):
        print(f"   {log}")

    sales_sum = result.get('sales_summary', {})
    bu_sum = result.get('bu_summary', {})

    print("-" * 85)
    print(f"📈 TỔNG HỢP KẾT QUẢ:")
    print(f"   + Cấp Sales   : Thành công={sales_sum.get('success', 0)}, Thất bại={sales_sum.get('failed', 0)}, Bỏ qua={sales_sum.get('skipped', 0)}")
    print(f"   + Cấp Trưởng BU: Thành công={bu_sum.get('success', 0)}, Thất bại={bu_sum.get('failed', 0)}, Bỏ qua={bu_sum.get('skipped', 0)}")
    print("=" * 85)


if __name__ == '__main__':
    main()
