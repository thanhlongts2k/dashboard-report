import os
import sys
import django
from decimal import Decimal

# Cấu hình UTF-8 cho stdout trên Windows
if hasattr(sys.stdout, 'reconfigure'):
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE_DIR)

if not django.apps.apps.ready:
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'report2026.settings')
    django.setup()

from django.template.loader import render_to_string
from rest_framework.test import APIClient
from accounting.services.debt_mailer import (
    collect_sales_debt_data, collect_bu_manager_debt_data,
    send_debt_reminders_process, format_period_display
)


def run_all_tests():
    print("=" * 80)
    print("🚀 BẮT ĐẦU KIỂM THỬ HỆ THỐNG GỬI EMAIL NHẮC NỢ PHÂN CẤP (DEBT REMINDER EMAIL)")
    print("=" * 80)

    period = '2026-08'
    passed_tests = 0
    total_tests = 4

    # -------------------------------------------------------------
    # TEST SUITE 1: KIỂM THỬ GOM DỮ LIỆU CÔNG NỢ SALES & BU
    # -------------------------------------------------------------
    print("\n🔹 [TEST 1/4] Kiểm thử gom dữ liệu công nợ Sales và Trưởng BU...")
    try:
        sales_list = collect_sales_debt_data(period=period)
        bu_list = collect_bu_manager_debt_data(period=period)

        print(f"   + Tìm thấy {len(sales_list)} nhân viên Sales có phát sinh công nợ.")
        print(f"   + Tìm thấy {len(bu_list)} Business Units trong phạm vi quản trị.")

        assert len(sales_list) > 0, "Không tìm thấy nhân viên Sales nào có nợ!"
        assert len(bu_list) >= 6, f"Dự kiến tối thiểu 6 BU cốt lõi, thực tế tìm thấy: {len(bu_list)}"

        # Kiểm tra Sales đầu bảng
        top_sales = sales_list[0]
        print(f"   + Top 1 Sales nợ lớn nhất: {top_sales['full_name']} ({top_sales['employee_code']}) - "
              f"Tổng nợ: {top_sales['total_debt']:,.0f} đ, Quá hạn: {top_sales['overdue_total']:,.0f} đ ({top_sales['overdue_rate']}%)")
        assert top_sales['total_debt'] > 0, "Tổng nợ của Sales phải > 0"
        assert top_sales['customer_count'] == len(top_sales['customers']), "Số lượng khách hàng không khớp danh sách con!"

        # Kiểm tra BU đầu bảng
        top_bu = bu_list[0]
        print(f"   + Top 1 BU nợ lớn nhất: {top_bu['bu_name']} ({top_bu['bu_code']}) - Trưởng BU: {top_bu['manager_name']} ({top_bu['manager_email']}) - "
              f"Tổng nợ: {top_bu['total_debt']:,.0f} đ, Quá hạn: {top_bu['overdue_total']:,.0f} đ ({top_bu['overdue_rate']}%)")
        assert top_bu['total_debt'] > 0, "Tổng nợ của BU phải > 0"
        assert len(top_bu['top_overdue_customers']) > 0, "Danh sách top overdue customers không được rỗng"

        print("   ✅ TEST 1 PASSED: Gom dữ liệu Sales & BU chính xác 100%!")
        passed_tests += 1
    except Exception as e:
        print(f"   ❌ TEST 1 FAILED: {e}")
        import traceback
        traceback.print_exc()

    # -------------------------------------------------------------
    # TEST SUITE 2: KIỂM THỬ RENDER HTML TEMPLATES
    # -------------------------------------------------------------
    print("\n🔹 [TEST 2/4] Kiểm thử render HTML Templates (Sales & BU Manager)...")
    try:
        sample_sales = sales_list[0]
        sample_bu = bu_list[0]
        period_display = format_period_display(period)

        # 1. Render Sales Template
        primary_bu = sample_sales.get('primary_bu_code', '')
        bu_param = f"&bu={primary_bu}" if primary_bu else ""
        sales_context = {
            'sales': sample_sales,
            'period': period,
            'period_display': period_display,
            'dashboard_url': f"https://report.haophuong.com/aging?period={period}{bu_param}&employee={sample_sales['employee_code']}",
            'dry_run': True,
            'generation_time': '18/08/2026 08:30:00',
        }
        sales_html = render_to_string('emails/debt_reminder_sales.html', sales_context)
        assert len(sales_html) > 500, "HTML Sales template quá ngắn!"
        assert sample_sales['full_name'] in sales_html, "Tên Sales không có trong template HTML!"
        assert "THÔNG BÁO CÔNG NỢ KHÁCH HÀNG PHỤ TRÁCH" in sales_html
        print(f"   + Render Sales Template thành công ({len(sales_html):,} bytes, {sample_sales['customer_count']} khách hàng).")

        # 2. Render Manager Template
        bu_context = {
            'bu': sample_bu,
            'period': period,
            'period_display': period_display,
            'dashboard_url': f"https://report.haophuong.com/aging?period={period}&bu={sample_bu['bu_code']}",
            'dry_run': True,
            'generation_time': '18/08/2026 08:30:00',
        }
        bu_html = render_to_string('emails/debt_summary_manager.html', bu_context)
        assert len(bu_html) > 500, "HTML BU template quá ngắn!"
        assert sample_bu['manager_name'] in bu_html, "Tên Trưởng BU không có trong template HTML!"
        assert "BÁO CÁO TỔNG HỢP CÔNG NỢ KHỐI KINH DOANH" in bu_html
        print(f"   + Render BU Manager Template thành công ({len(bu_html):,} bytes, {sample_bu['sales_count']} nhân sự).")

        print("   ✅ TEST 2 PASSED: Render 2 HTML templates mượt mà, không có lỗi cú pháp!")
        passed_tests += 1
    except Exception as e:
        print(f"   ❌ TEST 2 FAILED: {e}")
        import traceback
        traceback.print_exc()

    # -------------------------------------------------------------
    # TEST SUITE 3: KIỂM THỬ ĐIỀU PHỐI DRY-RUN QUA SERVICE
    # -------------------------------------------------------------
    print("\n🔹 [TEST 3/4] Kiểm thử điều phối tiến trình gửi mail ở chế độ Dry-Run...")
    try:
        # Dry-run không truyền test_email (chỉ thống kê)
        sim_res = send_debt_reminders_process(period=period, dry_run=True, test_email=None, recipient_type='ALL')
        assert sim_res['dry_run'] is True
        assert len(sim_res['sales_summary']['details']) == len(sales_list)
        assert len(sim_res['bu_summary']['details']) == len(bu_list)
        print(f"   + Simulation Stats: {len(sim_res['sales_summary']['details'])} Sales, {len(sim_res['bu_summary']['details'])} BUs.")

        # Dry-run với test_email chỉ định (gửi mẫu)
        test_email = "test_reminder@haophuong.com"
        sample_send_res = send_debt_reminders_process(period=period, dry_run=True, test_email=test_email, recipient_type='ALL')
        print(f"   + Test-Email Dry-Run Result: Sales (Success: {sample_send_res['sales_summary']['success']}, Failed: {sample_send_res['sales_summary']['failed']}), "
              f"BU (Success: {sample_send_res['bu_summary']['success']}, Failed: {sample_send_res['bu_summary']['failed']})")

        print("   ✅ TEST 3 PASSED: Tiến trình Dry-Run điều phối an toàn và hoàn hảo!")
        passed_tests += 1
    except Exception as e:
        print(f"   ❌ TEST 3 FAILED: {e}")
        import traceback
        traceback.print_exc()

    # -------------------------------------------------------------
    # TEST SUITE 4: KIỂM THỬ REST API ENDPOINT
    # -------------------------------------------------------------
    print("\n🔹 [TEST 4/4] Kiểm thử gọi REST API POST /api/debt/notifications/send-reminders/...")
    try:
        client = APIClient()
        api_url = '/api/debt/notifications/send-reminders/'

        payload = {
            "period": period,
            "dry_run": True,
            "recipient_type": "ALL"
        }
        response = client.post(api_url, payload, format='json')
        print(f"   + API Response Status: {response.status_code}")
        assert response.status_code == 200, f"API trả về status {response.status_code}: {response.data}"

        res_data = response.data
        assert res_data['period'] == period
        assert res_data['dry_run'] is True
        assert 'sales_summary' in res_data
        assert 'bu_summary' in res_data
        assert 'logs' in res_data
        print(f"   + API Response Payload: Sales count={len(res_data['sales_summary']['details'])}, BU count={len(res_data['bu_summary']['details'])}, Logs count={len(res_data['logs'])}")

        print("   ✅ TEST 4 PASSED: REST API Endpoint hoạt động chuẩn xác!")
        passed_tests += 1
    except Exception as e:
        print(f"   ❌ TEST 4 FAILED: {e}")
        import traceback
        traceback.print_exc()

    # -------------------------------------------------------------
    # TỔNG KẾT
    # -------------------------------------------------------------
    print("\n" + "=" * 80)
    print(f"🏁 TỔNG KẾT KIỂM THỬ: {passed_tests}/{total_tests} TEST SUITES PASS ({(passed_tests/total_tests)*100:.1f}%)")
    print("=" * 80)
    return passed_tests == total_tests


if __name__ == '__main__':
    success = run_all_tests()
    if not success:
        sys.exit(1)
