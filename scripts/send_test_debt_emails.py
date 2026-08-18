import os
import sys
import django
import time
from datetime import datetime

# Cấu hình UTF-8 cho console
sys.stdout.reconfigure(encoding='utf-8')
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE_DIR)

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'report2026.settings')
django.setup()

from accounting.services.debt_mailer import (
    collect_sales_debt_data, collect_bu_manager_debt_data,
    send_sales_debt_email, send_bu_manager_debt_email
)


def main():
    period = '2026-08'
    print("=" * 85)
    print(f"📧 TIẾN TRÌNH GỬI THỰC TẾ 2 MẪU EMAIL NHẮC NỢ QUA SMTP (KỲ {period})")
    print("=" * 85)

    # -------------------------------------------------------------------------
    # 1. GỬI EMAIL NHẮC NỢ CHO SALES (MAI TIẾN DƯƠNG - 2000996)
    # -------------------------------------------------------------------------
    target_sales_code = '2000510'
    test_sales_email = 'thanhlongts2k@gmail.com'

    print(f"\n🔹 [1/2] Đang chuẩn bị dữ liệu và gửi Email Sales cho NV: {target_sales_code}...")
    sales_list = collect_sales_debt_data(period=period)
    target_sales = next((s for s in sales_list if str(s['employee_code']) == target_sales_code), None)

    if not target_sales:
        print(f"❌ Không tìm thấy dữ liệu công nợ cho Nhân viên có mã: {target_sales_code}!")
        return

    print(f"   + Nhân viên: {target_sales['full_name']} (Mã NV: {target_sales['employee_code']})")
    print(f"   + Email gốc nhân viên: {target_sales['email']}")
    print(f"   + Email nhận thử nghiệm (Override): {test_sales_email}")
    print(f"   + Số khách hàng nợ: {target_sales['customer_count']}")
    print(f"   + Tổng nợ: {target_sales['total_debt']:,.0f} đ | Trong hạn: {target_sales['due_total']:,.0f} đ | Quá hạn: {target_sales['overdue_total']:,.0f} đ ({target_sales['overdue_rate']}%)")
    for idx, c in enumerate(target_sales['customers'], 1):
        print(f"     {idx}. [{c['customer_code']}] {c['customer_name']} - Nợ: {c['total_debt']:,.0f} đ (Quá hạn: {c['overdue_total']:,.0f} đ)")

    start_time = time.time()
    ok_sales, msg_sales = send_sales_debt_email(
        target_sales,
        period=period,
        dry_run=True,
        test_email=test_sales_email
    )
    sales_duration = time.time() - start_time

    if ok_sales:
        print(f"   ✅ Gửi Email Sales THÀNH CÔNG đến [{test_sales_email}]! (Thời gian: {sales_duration:.2f}s, Lúc: {datetime.now().strftime('%H:%M:%S')})")
    else:
        print(f"   ❌ Gửi Email Sales THẤT BẠI: {msg_sales}")

    # -------------------------------------------------------------------------
    # 2. GỬI EMAIL BÁO CÁO TỔNG HỢP CHO TRƯỞNG BU (BU_ELEVATOR - ĐÀO TIẾN DŨNG)
    # -------------------------------------------------------------------------
    target_bu_code = 'BU_IBIZ VALUE'
    test_manager_email = 'thanhlongts2k@gmail.com'

    print(f"\n🔹 [2/2] Đang chuẩn bị dữ liệu và gửi Email Trưởng BU cho Khối: {target_bu_code}...")
    bu_list = collect_bu_manager_debt_data(period=period, bu_code=target_bu_code)
    target_bu = next((b for b in bu_list if b['bu_code'] == target_bu_code), None)

    if not target_bu:
        print(f"❌ Không tìm thấy dữ liệu công nợ cho BU: {target_bu_code}!")
        return

    print(f"   + Khối BU: {target_bu['bu_name']} ({target_bu['bu_code']})")
    print(f"   + Trưởng BU: {target_bu['manager_name']} (Email gốc: {target_bu['manager_email']})")
    print(f"   + Email nhận thử nghiệm (Override): {test_manager_email}")
    print(f"   + Tổng nợ Khối: {target_bu['total_debt']:,.0f} đ | Quá hạn: {target_bu['overdue_total']:,.0f} đ ({target_bu['overdue_rate']}%)")
    print(f"   + Số nhân sự quản lý nợ: {target_bu['sales_count']} nhân viên | Tổng khách hàng: {target_bu['customer_count']} KH")
    print(f"   + Top 3 KH quá hạn lớn nhất:")
    for idx, c in enumerate(target_bu['top_overdue_customers'][:3], 1):
        print(f"     {idx}. [{c['customer_code']}] {c['customer_name']} (Sales: {c['sales_name']}) - Quá hạn: {c['overdue_total']:,.0f} đ / Tổng: {c['total_debt']:,.0f} đ")

    start_time = time.time()
    ok_bu, msg_bu = send_bu_manager_debt_email(
        target_bu,
        period=period,
        dry_run=True,
        test_email=test_manager_email
    )
    bu_duration = time.time() - start_time

    if ok_bu:
        print(f"   ✅ Gửi Email Trưởng BU THÀNH CÔNG đến [{test_manager_email}]! (Thời gian: {bu_duration:.2f}s, Lúc: {datetime.now().strftime('%H:%M:%S')})")
    else:
        print(f"   ❌ Gửi Email Trưởng BU THẤT BẠI: {msg_bu}")

    # -------------------------------------------------------------------------
    # TỔNG KẾT
    # -------------------------------------------------------------------------
    print("\n" + "=" * 85)
    print(f"🏁 TỔNG KẾT: Sales Email -> {test_sales_email} ({'SUCCESS' if ok_sales else 'FAILED'}) | BU Email -> {test_manager_email} ({'SUCCESS' if ok_bu else 'FAILED'})")
    print("=" * 85)


if __name__ == '__main__':
    main()
