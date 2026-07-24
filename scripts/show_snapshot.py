"""
Terminal Data Snapshot CLI Script (List Format)
Usage:
    python scripts/show_snapshot.py [--month 7] [--year 2026] [--bu BU_ELEVATOR] [--show-all]
"""
import os, sys, argparse
from datetime import datetime
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), '.venv', 'Lib', 'site-packages'))
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'report2026.settings')
django.setup()

from accounting.models import BUPerformance, BUTargetPlan, BusinessUnit

def fmt(val):
    if val is None or val == 0:
        return "0"
    return f"{float(val):,.0f}"

def fmt_pct(val):
    if val is None or val == 0:
        return "0.0%"
    return f"{float(val):.1f}%"

def main():
    parser = argparse.ArgumentParser(description="Terminal Data Snapshot Viewer for Dashboard Report 2026")
    parser.add_argument('--month', type=int, default=7, help="Month to view snapshot (default: 7)")
    parser.add_argument('--year', type=int, default=2026, help="Year to view snapshot (default: 2026)")
    parser.add_argument('--bu', type=str, default=None, help="Filter by specific Business Unit code (optional)")
    parser.add_argument('--show-all', action='store_true', help="Include inactive BUs where all metrics are 0")
    args = parser.parse_args()

    month = args.month
    year = args.year

    now_timestamp_str = datetime.now().strftime('%H:%M:%S %d/%m/%Y')

    out = []
    out.append("=========================================================================================")
    out.append(f"📊 DATA SNAPSHOT CƠ SỞ DỮ LIỆU - THÁNG {month:02d}/{year} (NGÀY CHỐT SỐ LIỆU: {now_timestamp_str})")
    out.append("=========================================================================================")

    # 1. TOTAL COMPANY (TOTAL_CORP / GLOBAL RECORD)
    glob = BUPerformance.objects.filter(business_unit__isnull=True, month=month, year=year).first()
    glob_target = BUTargetPlan.objects.filter(business_unit__isnull=True, month=month, year=year).first()

    # 2. BUSINESS UNITS PERFORMANCE
    qs = BUPerformance.objects.filter(month=month, year=year, business_unit__isnull=False).select_related('business_unit')
    if args.bu:
        qs = qs.filter(business_unit__code__iexact=args.bu.strip())

    bu_records = list(qs.order_by('business_unit__code'))

    out.append(f"\n🏢 1. CHI TIẾT DỮ LIỆU THEO TỪNG BỘ PHẬN (BUSINESS UNITS):")
    out.append("-" * 90)

    displayed_bu_count = 0
    for p in bu_records:
        bu_code = p.business_unit.code if p.business_unit else "N/A"
        bu_name = p.business_unit.name if p.business_unit and p.business_unit.name else ""
        tp = BUTargetPlan.objects.filter(business_unit=p.business_unit, month=month, year=year).first()

        # Doanh thu MTD / YTD Target & Actual
        rev_m_act = float(p.mtd_revenue_actual or 0)
        rev_m_tgt = float((tp.month_revenue_target if (tp and tp.month_revenue_target > 0) else p.mtd_revenue_plan) or 0)
        rev_m_pct = (rev_m_act / rev_m_tgt * 100) if rev_m_tgt > 0 else 0.0

        rev_y_act = float(p.ytd_revenue_actual or 0)
        rev_y_tgt = float((tp.year_revenue_target if (tp and tp.year_revenue_target > 0) else p.ytd_revenue_plan) or 0)
        rev_y_pct = (rev_y_act / rev_y_tgt * 100) if rev_y_tgt > 0 else 0.0

        # Thu tiền MTD / YTD Target & Actual
        coll_m_act = float(p.mtd_collection_actual or 0)
        coll_m_tgt = float((tp.month_collection_target if (tp and tp.month_collection_target > 0) else p.mtd_collection_plan) or 0)
        coll_m_pct = (coll_m_act / coll_m_tgt * 100) if coll_m_tgt > 0 else 0.0

        coll_y_act = float(p.ytd_collection_actual or 0)
        coll_y_tgt = float((tp.year_collection_target if (tp and tp.year_collection_target > 0) else p.ytd_collection_plan) or 0)
        coll_y_pct = (coll_y_act / coll_y_tgt * 100) if coll_y_tgt > 0 else 0.0

        # Các chỉ tiêu tài chính khác
        opex_act = float(p.opex_actual or 0)
        opex_tgt = float((tp.month_opex_target if (tp and tp.month_opex_target > 0) else p.opex_plan) or 0)
        opex_pct = (opex_act / opex_tgt * 100) if opex_tgt > 0 else 0.0

        inv = float(p.inventory_value_actual or 0)
        rec = float(p.receivable_total or 0)
        rec_ovd = float(p.receivable_overdue or 0)

        # Skip BUs where ALL values are 0 (unless --show-all is passed)
        if not args.show_all:
            if (rev_m_act == 0 and rev_m_tgt == 0 and rev_y_act == 0 and rev_y_tgt == 0 and 
                coll_m_act == 0 and coll_m_tgt == 0 and coll_y_act == 0 and coll_y_tgt == 0 and 
                opex_act == 0 and inv == 0 and rec == 0 and rec_ovd == 0):
                continue

        displayed_bu_count += 1
        out.append(f"📌 BỘ PHẬN: {bu_code} {f'({bu_name})' if bu_name else ''}")
        out.append(f"   • Doanh thu MTD thực tế      : {fmt(rev_m_act):>18} VNĐ  (Target: {fmt(rev_m_tgt):>18} VNĐ | Đạt: {fmt_pct(rev_m_pct)})")
        out.append(f"   • Doanh thu YTD thực tế      : {fmt(rev_y_act):>18} VNĐ  (Target: {fmt(rev_y_tgt):>18} VNĐ | Đạt: {fmt_pct(rev_y_pct)})")
        out.append(f"   • Thực thu MTD thực tế       : {fmt(coll_m_act):>18} VNĐ  (Target: {fmt(coll_m_tgt):>18} VNĐ | Đạt: {fmt_pct(coll_m_pct)})")
        out.append(f"   • Thực thu YTD thực tế       : {fmt(coll_y_act):>18} VNĐ  (Target: {fmt(coll_y_tgt):>18} VNĐ | Đạt: {fmt_pct(coll_y_pct)})")
        if opex_tgt > 0:
            out.append(f"   • Chi phí OPEX thực tế       : {fmt(opex_act):>18} VNĐ  (Target: {fmt(opex_tgt):>18} VNĐ | Chi: {fmt_pct(opex_pct)})")
        else:
            out.append(f"   • Chi phí OPEX thực tế       : {fmt(opex_act):>18} VNĐ")
        out.append(f"   • Giá trị Tồn kho            : {fmt(inv):>18} VNĐ")
        out.append(f"   • Dư nợ Phải thu             : {fmt(rec):>18} VNĐ  (Quá hạn: {fmt(rec_ovd):>18} VNĐ)")
        out.append("-" * 90)

    if displayed_bu_count == 0:
        out.append("   (Không có bộ phận nào phát sinh dữ liệu trong kỳ này)")
        out.append("-" * 90)

    if glob and not args.bu:
        g_rev_m_act = float(glob.mtd_revenue_actual or 0)
        g_rev_m_tgt = float((glob_target.month_revenue_target if (glob_target and glob_target.month_revenue_target > 0) else glob.mtd_revenue_plan) or 0)
        g_rev_m_pct = (g_rev_m_act / g_rev_m_tgt * 100) if g_rev_m_tgt > 0 else 0.0

        g_rev_y_act = float(glob.ytd_revenue_actual or 0)
        g_rev_y_tgt = float((glob_target.year_revenue_target if (glob_target and glob_target.year_revenue_target > 0) else glob.ytd_revenue_plan) or 0)
        g_rev_y_pct = (g_rev_y_act / g_rev_y_tgt * 100) if g_rev_y_tgt > 0 else 0.0

        g_coll_m_act = float(glob.mtd_collection_actual or 0)
        g_coll_m_tgt = float((glob_target.month_collection_target if (glob_target and glob_target.month_collection_target > 0) else glob.mtd_collection_plan) or 0)
        g_coll_m_pct = (g_coll_m_act / g_coll_m_tgt * 100) if g_coll_m_tgt > 0 else 0.0

        g_coll_y_act = float(glob.ytd_collection_actual or 0)
        g_coll_y_tgt = float((glob_target.year_collection_target if (glob_target and glob_target.year_collection_target > 0) else glob.ytd_collection_plan) or 0)
        g_coll_y_pct = (g_coll_y_act / g_coll_y_tgt * 100) if g_coll_y_tgt > 0 else 0.0

        g_opex_act = float(glob.opex_actual or 0)
        g_opex_tgt = float((glob_target.month_opex_target if (glob_target and glob_target.month_opex_target > 0) else glob.opex_plan) or 0)
        g_opex_pct = (g_opex_act / g_opex_tgt * 100) if g_opex_tgt > 0 else 0.0

        g_inv = float(glob.inventory_value_actual or 0)
        g_rec = float(glob.receivable_total or 0)
        g_rec_ovd = float(glob.receivable_overdue or 0)
        g_bank = float(glob.bank_debt_actual or 0)
        g_cash = float(glob.cash_balance_actual or 0)

        out.append(f"\n🏦 2. TỔNG CÔNG TY (GLOBAL FINANCIAL BALANCE & TOTAL CORP):")
        out.append("=" * 90)
        out.append(f"   • Doanh thu MTD thực tế (Global) : {fmt(g_rev_m_act):>18} VNĐ  (Target: {fmt(g_rev_m_tgt):>18} VNĐ | Đạt: {fmt_pct(g_rev_m_pct)})")
        out.append(f"   • Doanh thu YTD thực tế (Global) : {fmt(g_rev_y_act):>18} VNĐ  (Target: {fmt(g_rev_y_tgt):>18} VNĐ | Đạt: {fmt_pct(g_rev_y_pct)})")
        out.append(f"   • Thực thu MTD thực tế (Global)  : {fmt(g_coll_m_act):>18} VNĐ  (Target: {fmt(g_coll_m_tgt):>18} VNĐ | Đạt: {fmt_pct(g_coll_m_pct)})")
        out.append(f"   • Thực thu YTD thực tế (Global)  : {fmt(g_coll_y_act):>18} VNĐ  (Target: {fmt(g_coll_y_tgt):>18} VNĐ | Đạt: {fmt_pct(g_coll_y_pct)})")
        if g_opex_tgt > 0:
            out.append(f"   • Chi phí OPEX thực tế           : {fmt(g_opex_act):>18} VNĐ  (Target: {fmt(g_opex_tgt):>18} VNĐ | Chi: {fmt_pct(g_opex_pct)})")
        else:
            out.append(f"   • Chi phí OPEX thực tế           : {fmt(g_opex_act):>18} VNĐ")
        out.append(f"   • Giá trị Tồn kho                : {fmt(g_inv):>18} VNĐ")
        out.append(f"   • Dư nợ Phải thu                 : {fmt(g_rec):>18} VNĐ  (Quá hạn: {fmt(g_rec_ovd):>18} VNĐ)")
        out.append(f"   • Quỹ tiền mặt (Cash Balance)   : {fmt(g_cash):>18} VNĐ")
        out.append(f"   • Dư nợ Vay Ngân hàng (Bank Debt): {fmt(g_bank):>18} VNĐ")
        out.append("=" * 90)

    sys.stdout.buffer.write("\n".join(out).encode('utf-8'))

if __name__ == '__main__':
    main()
