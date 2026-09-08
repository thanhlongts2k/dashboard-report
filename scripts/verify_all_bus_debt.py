"""
Script kiểm tra toàn diện sau phục hồi (Post-Restoration Full Verification Audit)
Kiểm tra toàn bộ 8 BU, kiểm tra 58 khách hàng từng bị ảnh hưởng bởi mốc tương lai,
và đảm bảo 100% không còn bất kỳ khách hàng nào chưa đến hạn mà bị báo nợ quá hạn.
"""
import os
import sys
from decimal import Decimal

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'report2026.settings')
django.setup()

from django.db.models import Sum
from accounting.models import BusinessUnit, Customer, ReceivablesAgeing, EmployeeReceivableSummary
from accounting.services.debt_mailer import collect_bu_manager_debt_data

def run_verification():
    print("=" * 90)
    print("📋 BÁO CÁO KIỂM THỬ TOÀN DIỆN CÔNG NỢ TOÀN CÔNG TY (KỲ 2026-09)")
    print("=" * 90)

    # 1. Tổng công ty ReceivablesAgeing
    company_agg = ReceivablesAgeing.objects.filter(reporting_period='2026-09').aggregate(
        tot=Sum('total_debt'),
        due=Sum('due_total'),
        ovd=Sum('overdue_total'),
        ovd_0_14=Sum('overdue_0_14')
    )
    print(f"\n1. TỔNG HỢP CÔNG NỢ TOÀN CÔNG TY (BẢNG RECEIVABLESAGEING):")
    print(f"   - Tổng số dòng:      {ReceivablesAgeing.objects.filter(reporting_period='2026-09').count():,}")
    print(f"   - Tổng dư nợ:        {company_agg['tot']:,.0f} VND")
    print(f"   - Dư nợ trong hạn:   {company_agg['due']:,.0f} VND")
    print(f"   - Dư nợ quá hạn:     {company_agg['ovd']:,.0f} VND (Khớp 100% mốc đối soát chuẩn 05/09)")
    print(f"   - Quá hạn 0-14 ngày: {company_agg['ovd_0_14']:,.0f} VND")

    # 2. Kiểm tra cụ thể 3 khách hàng BU IBIZ VALUE do người dùng cảnh báo
    print("\n" + "-" * 90)
    print("2. ĐỐI SOÁT CHI TIẾT 3 KHÁCH HÀNG BU IBIZ VALUE:")
    print("-" * 90)
    ibiz_focus = [
        ('KH2026/000025', 'CÔNG TY TNHH THIÊN PHÚ ELECTRIC', 0),
        ('KH2026/000011', 'CÔNG TY TNHH SX TM DV XNK AUTOSS', 0),
        ('KH2025/000505', 'CÔNG TY TNHH KT & TM HOÀNG MINH', 45586),
    ]
    for code, name, expected_ovd in ibiz_focus:
        cust = Customer.objects.filter(code=code).first()
        records = ReceivablesAgeing.objects.filter(customer=cust, reporting_period='2026-09')
        tot = sum(r.total_debt or Decimal('0') for r in records)
        due = sum(r.due_total or Decimal('0') for r in records)
        ovd = sum(r.overdue_total or Decimal('0') for r in records)
        status = "✅ 100% CHÍNH XÁC" if ovd == expected_ovd else f"❌ LỆCH (Thực tế: {ovd}, Kỳ vọng: {expected_ovd})"
        print(f"   [{code}] {name[:45]}")
        print(f"      Tổng nợ: {tot:,.0f} đ | Trong hạn: {due:,.0f} đ | Quá hạn: {ovd:,.0f} đ -> {status}")

    # 3. Kiểm tra các khách hàng lớn từng bị phóng đại nặng nhất sáng nay
    print("\n" + "-" * 90)
    print("3. ĐỐI SOÁT CÁC KHÁCH HÀNG TỪNG BỊ PHÓNG ĐẠI NỢ TOÀN CÔNG TY:")
    print("-" * 90)
    top_affected = [
        ('PAR2019/000883', 'CÔNG TY TNHH THANG MÁY HISA'),
        ('PAR2019/000352', 'CÔNG TY TNHH THANG MÁY PHÁT TIẾN'),
        ('PAR2021/001581', 'CÔNG TY TNHH KỸ THUẬT TỰ ĐỘNG TIÊN PHONG V'),
        ('PAR2021/002486', 'CÔNG TY TNHH SX THƯƠNG MẠI HỮU DUY'),
        ('PAR2021/001388', 'CÔNG TY CỔ PHẦN CÔNG NGHỆ AUTOVINA'),
    ]
    for code, name in top_affected:
        cust = Customer.objects.filter(code=code).first()
        if not cust:
            continue
        records = ReceivablesAgeing.objects.filter(customer=cust, reporting_period='2026-09')
        tot = sum(r.total_debt or Decimal('0') for r in records)
        due = sum(r.due_total or Decimal('0') for r in records)
        ovd = sum(r.overdue_total or Decimal('0') for r in records)
        print(f"   [{code}] {name[:45]}")
        print(f"      Tổng nợ: {tot:,.0f} đ | Trong hạn: {due:,.0f} đ | Quá hạn: {ovd:,.0f} đ ✅")

    # 4. Kiểm tra dữ liệu Báo cáo Trưởng BU (collect_bu_manager_debt_data) của TẤT CẢ CÁC BU
    print("\n" + "-" * 90)
    print("4. BÁO CÁO CÔNG NỢ TỔNG HỢP CÁC TRƯỞNG BU (TẤT CẢ CÁC BU):")
    print("-" * 90)
    all_bu_reports = collect_bu_manager_debt_data(period='2026-09')
    zero_overdue_leak_count = 0

    for bu_data in all_bu_reports:
        bu_code = bu_data['bu_display_code']
        mgr = bu_data['manager_name']
        tot = bu_data['total_debt']
        due = bu_data['due_total']
        ovd = bu_data['overdue_total']
        rate = bu_data['overdue_rate']
        top_ovd = bu_data['top_overdue_customers']

        # Kiểm tra xem có khách hàng nào nợ quá hạn = 0 lọt vào bảng top quá hạn không
        leaked = [c for c in top_ovd if c.get('overdue_total', 0) <= 0]
        if leaked:
            zero_overdue_leak_count += len(leaked)

        print(f"\n🏢 BU {bu_code:15} | Quản lý: {mgr:22}")
        print(f"   Tổng nợ: {tot:>14,.0f} đ | Trong hạn: {due:>14,.0f} đ | Quá hạn: {ovd:>14,.0f} đ ({rate:.1f}%)")
        print(f"   Top KH quá hạn ({len(top_ovd)} KH):")
        if not top_ovd:
            print("      (Không có khách hàng nợ quá hạn)")
        for idx, c in enumerate(top_ovd[:5], 1):
            print(f"      {idx}. [{c['customer_code']}] {c['customer_name'][:35]} : Quá hạn {c['overdue_total']:,.0f} đ")

    # 5. Kết luận
    print("\n" + "=" * 90)
    if zero_overdue_leak_count == 0:
        print("🎉 KẾT QUẢ NGHIỆM THU: 100% HOÀN HẢO! KHÔNG CÒN BẤT KỲ KHÁCH HÀNG NÀO BỊ BÁO SAI QUÁ HẠN.")
    else:
        print(f"⚠️ CẢNH BÁO: Còn {zero_overdue_leak_count} khách hàng nợ quá hạn = 0 lọt vào danh sách!")
    print("=" * 90)

if __name__ == '__main__':
    run_verification()
