"""
Script Báo Cáo Công Nợ Phân Cấp 3 Tầng Drilldown (Chuẩn Hóa):
[CẤP 1: BUSINESS UNIT] Mã BU, Tên BU, Trưởng BU, Tổng nợ BU, Trong hạn, Quá hạn
    ├── [NHÓM 1: KEY ACCOUNTS CẤP TỔNG (CCO)] Giám đốc KD phụ trách trực tiếp
    │       └── [CẤP 3: DETAILS] Danh sách Khách hàng của CCO
    └── [NHÓM 2: CÂY QUẢN LÝ BU] Trưởng BU -> Trưởng bộ phận MB/MN -> Sales
            └── [CẤP 3: DETAILS] Danh sách Khách hàng của từng Nhân sự
"""
import os
import sys
import argparse
from decimal import Decimal
from collections import defaultdict
from django.conf import settings

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE_DIR)

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'report2026.settings')
import django
django.setup()

from accounting.models import BusinessUnit, BUPerformance, ReceivablesAgeing, Customer, Employee, EmployeeAssignment
from django.db.models import Sum, Q


def print_single_bu_drilldown(bu, period='2026-08', limit_cust=10):
    year, month = map(int, period.split('-'))

    # Tier 1: BU KPI
    bu_perf = BUPerformance.objects.filter(business_unit=bu, month=month, year=year).first()
    tot_bu_debt = bu_perf.receivable_total if bu_perf else Decimal('0')
    ovd_bu_debt = bu_perf.receivable_overdue if bu_perf else Decimal('0')
    due_bu_debt = tot_bu_debt - ovd_bu_debt if tot_bu_debt >= ovd_bu_debt else Decimal('0')
    rate = (ovd_bu_debt / tot_bu_debt * 100) if tot_bu_debt > 0 else Decimal('0')

    mgr_name = bu.manager or "ĐÀO TIẾN DŨNG" if bu.code == 'BU_ELEVATOR' else (bu.manager or "Chưa cấu hình")

    print("\n" + "=" * 140)
    print(f"🏢 [CẤP 1: BUSINESS UNIT] [{bu.code}] - {bu.name.upper()}")
    print(f"   👤 Trưởng BU: {mgr_name:<25} | 💰 Tổng nợ BU: {tot_bu_debt:>16,.0f} VNĐ | Trong hạn: {due_bu_debt:>15,.0f} | Quá hạn: {ovd_bu_debt:>15,.0f} ({rate:.1f}%)")
    print("=" * 140)

    # Filter Oversea and Target Receivable Accounts (1311)
    oversea_groups = getattr(settings, 'OVERSEA_CUSTOMER_GROUP_CODES', ['Oversea'])
    target_rec_accounts = getattr(settings, 'TARGET_RECEIVABLE_ACCOUNTS', ['1311'])

    ageing_filter = Q(reporting_period=period, customer__business_unit=bu)
    if target_rec_accounts:
        ageing_filter &= Q(account_code__in=target_rec_accounts)

    if bu.code == 'Oversea':
        ageing_filter &= Q(customer__group__code__in=oversea_groups)
    else:
        ageing_filter &= ~Q(customer__group__code__in=oversea_groups)

    ageings = ReceivablesAgeing.objects.filter(ageing_filter).select_related('customer', 'customer__assigned_employee')

    if not ageings.exists():
        print("   ℹ️ Không có phát sinh công nợ trong kỳ báo cáo này.")
        return

    # Aggregate by customer first (to combine multiple ageing rows per customer)
    cust_agg = {}
    for a in ageings:
        c = a.customer
        sales = c.assigned_employee
        s_code = sales.employee_code if sales else "UNASSIGNED"
        s_name = sales.full_name if sales else "Khách hàng tự do / Chưa gán Sales"
        
        c_due = a.due_total or (a.total_debt - a.overdue_total)
        c_ovd = a.overdue_total or Decimal('0')
        c_tot = a.total_debt or Decimal('0')

        if c.code not in cust_agg:
            cust_agg[c.code] = {
                'name': c.name,
                'sales_code': s_code,
                'sales_name': s_name,
                'due': Decimal('0'),
                'overdue': Decimal('0'),
                'total': Decimal('0')
            }
        cust_agg[c.code]['due'] += c_due
        cust_agg[c.code]['overdue'] += c_ovd
        cust_agg[c.code]['total'] += c_tot

    # Group aggregated customers by Sales
    sales_map = defaultdict(lambda: {'name': '', 'due': Decimal('0'), 'overdue': Decimal('0'), 'total': Decimal('0'), 'custs': []})
    for c_code, c_data in cust_agg.items():
        s_code = c_data['sales_code']
        sales_map[s_code]['name'] = c_data['sales_name']
        sales_map[s_code]['due'] += c_data['due']
        sales_map[s_code]['overdue'] += c_data['overdue']
        sales_map[s_code]['total'] += c_data['total']
        sales_map[s_code]['custs'].append((c_code, c_data))

    # Helper function to print a table of customers
    def print_customer_table(cust_list, indent="      "):
        sorted_c = sorted(cust_list, key=lambda x: x[1]['total'], reverse=True)
        display_list = sorted_c[:limit_cust] if limit_cust > 0 else sorted_c

        print(f"{indent}┌{'─'*18}┬{'─'*46}┬{'─'*18}┬{'─'*18}┬{'─'*18}┐")
        print(f"{indent}│ {'MÃ KH':<16} │ {'TÊN KHÁCH HÀNG (CẤP 3: DETAILS)':<44} │ {'TRONG HẠN (VNĐ)':>16} │ {'QUÁ HẠN (VNĐ)':>16} │ {'TỔNG NỢ KH (VNĐ)':>16} │")
        print(f"{indent}├{'─'*18}┼{'─'*46}┼{'─'*18}┼{'─'*18}┼{'─'*18}┤")
        
        for c_code, c_info in display_list:
            print(f"{indent}│ {c_code:<16} │ {c_info['name'][:44]:<44} │ {c_info['due']:>16,.0f} │ {c_info['overdue']:>16,.0f} │ {c_info['total']:>16,.0f} │")

        if len(sorted_c) > len(display_list):
            rem_count = len(sorted_c) - len(display_list)
            rem_due = sum(c[1]['due'] for c in sorted_c[limit_cust:])
            rem_ovd = sum(c[1]['overdue'] for c in sorted_c[limit_cust:])
            rem_tot = sum(c[1]['total'] for c in sorted_c[limit_cust:])
            print(f"{indent}│ ... {rem_count} KH khác ... │ {'...':<44} │ {rem_due:>16,.0f} │ {rem_ovd:>16,.0f} │ {rem_tot:>16,.0f} │")

        print(f"{indent}└{'─'*18}┴{'─'*46}┴{'─'*18}┴{'─'*18}┴{'─'*18}┘")

    # Separate CCO Key Accounts vs BU Operational Tree
    total_rendered_debt = Decimal('0')

    # 1. CCO Key Accounts (if any)
    if '2001' in sales_map:
        cco_info = sales_map['2001']
        total_rendered_debt += cco_info['total']
        print(f"\n   ├── 👑 [NHÓM 1: KEY ACCOUNTS CẤP TỔNG] [2001] NGÔ ĐÌNH TRUNG TÂN (Giám đốc kinh doanh phụ trách trực tiếp)")
        print(f"   │      💰 Tổng nợ Key Accounts: {cco_info['total']:>16,.0f} VNĐ | Trong hạn: {cco_info['due']:>15,.0f} | Quá hạn: {cco_info['overdue']:>15,.0f} ({len(cco_info['custs'])} KH)")
        print_customer_table(cco_info['custs'], indent="   │      ")

    # 2. BU Operational Management Tree
    print(f"\n   └── 🏢 [NHÓM 2: CÂY QUẢN LÝ & VẬN HÀNH BU] (Trưởng BU -> Trưởng bộ phận MB/MN -> Sales)")
    
    # Order for BU_ELEVATOR
    if bu.code == 'BU_ELEVATOR':
        # Head: 3003
        if '3003' in sales_map:
            s_info = sales_map['3003']
            total_rendered_debt += s_info['total']
            print(f"\n          ├── 👑 [TRƯỞNG BU] [3003] ĐÀO TIẾN DŨNG (Phụ trách trực tiếp)")
            print(f"          │      💰 Tổng nợ: {s_info['total']:>16,.0f} VNĐ ({len(s_info['custs'])} KH)")
            print_customer_table(s_info['custs'], indent="          │      ")

        # MB Branch: 2000017 (Head) -> 2000609, 2000996 (Sales)
        print(f"\n          ├── ⭐ [TRƯỞNG BỘ PHẬN MB] [2000017] NGUYỄN ĐỨC THƯỞNG")
        if '2000017' in sales_map:
            s_info = sales_map['2000017']
            total_rendered_debt += s_info['total']
            print(f"          │      🔹 [Khách hàng do Sếp Thưởng chăm sóc trực tiếp] — Tổng nợ: {s_info['total']:>15,.0f} VNĐ ({len(s_info['custs'])} KH)")
            print_customer_table(s_info['custs'], indent="          │      ")

        for s_code in ['2000609', '2000996']:
            if s_code in sales_map:
                s_info = sales_map[s_code]
                total_rendered_debt += s_info['total']
                print(f"          │      └── 👤 [SALES MB] [{s_code}] {s_info['name']} — Tổng nợ: {s_info['total']:>15,.0f} VNĐ ({len(s_info['custs'])} KH)")
                print_customer_table(s_info['custs'], indent="          │             ")

        # MN Branch: 3005 (Head) -> 2000812, 9037 (Sales)
        print(f"\n          ├── ⭐ [TRƯỞNG BỘ PHẬN MN] [3005] TRỊNH HOÀNG QUÂN")
        if '3005' in sales_map:
            s_info = sales_map['3005']
            total_rendered_debt += s_info['total']
            print(f"          │      🔹 [Khách hàng do Sếp Quân chăm sóc trực tiếp] — Tổng nợ: {s_info['total']:>15,.0f} VNĐ ({len(s_info['custs'])} KH)")
            print_customer_table(s_info['custs'], indent="          │      ")

        for s_code in ['2000812', '9037']:
            if s_code in sales_map:
                s_info = sales_map[s_code]
                total_rendered_debt += s_info['total']
                print(f"          │      └── 👤 [SALES MN] [{s_code}] {s_info['name']} — Tổng nợ: {s_info['total']:>15,.0f} VNĐ ({len(s_info['custs'])} KH)")
                print_customer_table(s_info['custs'], indent="          │             ")

        # Unassigned / Others
        if 'UNASSIGNED' in sales_map:
            s_info = sales_map['UNASSIGNED']
            total_rendered_debt += s_info['total']
            print(f"\n          └── 👤 [KHÁCH HÀNG TỰ DO / CHƯA GÁN SALES] — Tổng nợ: {s_info['total']:>15,.0f} VNĐ ({len(s_info['custs'])} KH)")
            print_customer_table(s_info['custs'], indent="                 ")

    else:
        # Generic BU rendering
        for s_code, s_info in sorted(sales_map.items(), key=lambda x: x[1]['total'], reverse=True):
            if s_code == '2001':
                continue
            total_rendered_debt += s_info['total']
            print(f"\n          ├── 👤 [{s_code}] {s_info['name']} — Tổng nợ: {s_info['total']:>15,.0f} VNĐ ({len(s_info['custs'])} KH)")
            print_customer_table(s_info['custs'], indent="          │      ")

    # Reconciliation footer
    diff = tot_bu_debt - total_rendered_debt
    status_str = "✅ KHỚP 100% (0 VNĐ CHÊNH LỆCH)" if diff == 0 else f"⚠️ LỆCH {diff:,.0f} VNĐ"
    print("\n" + "=" * 140)
    print(f"📈 TỔNG NỢ TẤT CẢ KHÁCH HÀNG / SALES CỘNG LẠI: {total_rendered_debt:>18,.0f} VNĐ | TỔNG NỢ CẤP 1 BU: {tot_bu_debt:>18,.0f} VNĐ")
    print(f"🎯 TRẠNG THÁI ĐỐI SOÁT DRILLDOWN: {status_str}")
    print("=" * 140)


def main():
    parser = argparse.ArgumentParser(description="Báo cáo công nợ phân cấp 3 tầng chuẩn hóa")
    parser.add_argument('--bu', type=str, default='BU_ELEVATOR', help="Mã BU cần xuất (Mặc định: BU_ELEVATOR)")
    parser.add_argument('--period', type=str, default='2026-08', help="Kỳ báo cáo (YYYY-MM), mặc định: 2026-08")
    parser.add_argument('--limit-cust', type=int, default=10, help="Số khách hàng hiển thị tối đa mỗi Sales (Mặc định: 10, 0=Tất cả)")
    parser.add_argument('--all', action='store_true', help="Xuất báo cáo cho tất cả 22 Business Units")
    args = parser.parse_args()

    if args.all:
        bus = BusinessUnit.objects.exclude(code='HPC').order_by('code')
        for b in bus:
            print_single_bu_drilldown(b, period=args.period, limit_cust=args.limit_cust)
    else:
        bu = BusinessUnit.objects.filter(code=args.bu).first()
        if not bu:
            print(f"❌ Không tìm thấy Business Unit có mã: {args.bu}")
            return
        print_single_bu_drilldown(bu, period=args.period, limit_cust=args.limit_cust)


if __name__ == '__main__':
    main()
