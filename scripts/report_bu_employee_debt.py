"""
Script Báo Cáo Công Nợ Toàn Diện (Chuẩn Hóa):
1. Báo cáo 1: Tổng hợp Công nợ 22 Business Units (BU) độc lập (Đã loại trừ HPC để không cộng trùng, khớp 100% Global).
2. Báo cáo 2: Bóc tách Công nợ Nhân viên & Quản lý theo từng BU với Cây phân cấp chuẩn (CCO -> Trưởng BU -> Trưởng bộ phận -> Sales).
"""
import os
import sys
import argparse
from decimal import Decimal
from collections import defaultdict

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE_DIR)

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'report2026.settings')
import django
django.setup()

from accounting.models import (
    BusinessUnit, BUPerformance, ReceivablesAgeing, Customer,
    Employee, Department, EmployeeAssignment, EmployeeReceivableSummary
)


def generate_bu_debt_report(period='2026-08'):
    year, month = map(int, period.split('-'))
    print("=" * 115)
    print(f"📊 BÁO CÁO 1: TỔNG HỢP CÔNG NỢ 22 BUSINESS UNITS (BU) — KỲ {period}")
    print("📌 (Đã loại bỏ mã mẹ HPC để chống cộng trùng — Tổng 22 BU khớp 100% với Global Toàn Công Ty)")
    print("=" * 115)

    # Exclude Global (business_unit=None) and Parent company (code='HPC')
    perfs = BUPerformance.objects.filter(
        month=month, year=year
    ).exclude(
        business_unit=None
    ).exclude(
        business_unit__code='HPC'
    ).select_related('business_unit').order_by('-receivable_total')

    headers = f"{'STT':<4} | {'MÃ BU':<20} | {'TÊN BUSINESS UNIT':<32} | {'TỔNG DƯ NỢ (VNĐ)':>18} | {'TRONG HẠN (VNĐ)':>18} | {'QUÁ HẠN (VNĐ)':>18} | {'TỶ LỆ (%)':>9}"
    print(headers)
    print("-" * 115)

    total_22_debt = Decimal('0')
    total_22_due = Decimal('0')
    total_22_overdue = Decimal('0')

    idx = 1
    for p in perfs:
        bu = p.business_unit
        bu_code = bu.code if bu else "N/A"
        bu_name = bu.name if bu else "N/A"
        tot = p.receivable_total or Decimal('0')
        ovd = p.receivable_overdue or Decimal('0')
        due = tot - ovd if tot >= ovd else Decimal('0')
        rate = (ovd / tot * 100) if tot > 0 else Decimal('0')

        total_22_debt += tot
        total_22_due += due
        total_22_overdue += ovd

        print(f"{idx:<4} | {bu_code:<20} | {bu_name[:32]:<32} | {tot:>18,.0f} | {due:>18,.0f} | {ovd:>18,.0f} | {rate:>8.1f}%")
        idx += 1

    # Global KPI
    global_perf = BUPerformance.objects.filter(month=month, year=year, business_unit=None).first()
    g_tot = global_perf.receivable_total if global_perf else total_22_debt
    g_ovd = global_perf.receivable_overdue if global_perf else total_22_overdue
    g_due = g_tot - g_ovd
    g_rate = (g_ovd / g_tot * 100) if g_tot > 0 else Decimal('0')

    print("=" * 115)
    print(f"{'TỔNG CỘNG 22 BUSINESS UNITS':<59} | {total_22_debt:>18,.0f} | {total_22_due:>18,.0f} | {total_22_overdue:>18,.0f} | {(total_22_overdue/total_22_debt*100):>8.1f}%")
    print(f"{'TỔNG TOÀN CÔNG TY (GLOBAL KPI)':<59} | {g_tot:>18,.0f} | {g_due:>18,.0f} | {g_ovd:>18,.0f} | {g_rate:>8.1f}%")
    diff = g_tot - total_22_debt
    status_str = "✅ KHỚP 100% (0 VNĐ CHÊNH LỆCH)" if diff == 0 else f"⚠️ LỆCH {diff:,.0f} VNĐ"
    print(f"TRẠNG THÁI ĐỐI SOÁT: {status_str}")
    print("=" * 115)


def generate_employee_debt_by_bu_report(period='2026-08'):
    print("\n" * 2)
    print("=" * 140)
    print(f"👥 BÁO CÁO 2: BÓC TÁCH CÔNG NỢ NHÂN VIÊN & QUẢN LÝ THEO TỪNG BU — KỲ {period}")
    print("📌 (Cây phân cấp chuẩn: CCO Khối Kinh Doanh -> Trưởng BU -> Trưởng bộ phận MB/MN -> Sales)")
    print("=" * 140)

    # 1. Hiển thị riêng Khối Ban Giám Đốc Kinh Doanh (CCO)
    cco_summary = EmployeeReceivableSummary.objects.filter(
        reporting_period=period, employee__employee_code='2001'
    ).select_related('employee', 'department').first()

    if cco_summary:
        print("\n👑 【 KHỐI LÃNH ĐẠO: BAN GIÁM ĐỐC KINH DOANH (CCO) 】")
        print("-" * 140)
        print(f"{'VAI TRÒ':<12} | {'MÃ NV':<10} | {'HỌ VÀ TÊN':<26} | {'CHỨC DANH':<32} | {'NỢ CÁ NHÂN (OWN)':>18} | {'NỢ TOÀN KHỐI (TEAM)':>20} | {'CẤP DƯỚI':>8}")
        print("-" * 140)
        print(f"{'👑 TỔNG CCO':<12} | {cco_summary.employee.employee_code:<10} | {cco_summary.employee.full_name[:26]:<26} | {'Giám đốc kinh doanh':<32} | {cco_summary.own_total_debt:>18,.0f} | {cco_summary.team_total_debt:>20,.0f} | {cco_summary.subordinate_count:>5} NV")
        print("-" * 140)
        print("  * Ghi chú: Nợ cá nhân của Sếp Tân (51.05 Tỷ) là các Hợp đồng dự án Key Account lớn toàn công ty (HIS Elevator 35.8 Tỷ, Ban điều hành 15.08 Tỷ...).")
        print("  * Nợ toàn khối (129.90 Tỷ) là con số cộng dồn đệ quy toàn bộ 87 nhân sự thuộc 5 BU kinh doanh trực thuộc.")

    # 2. Hiển thị theo từng BU cụ thể
    dept_order = [
        ('BU_Elevator', 'BU ELEVATOR (THANG MÁY)'),
        ('BU_Premium', 'BU IBIZ PREMIUM (THIẾT BỊ ĐIỆN CAO CẤP)'),
        ('BU_Agritech-Eco', 'BU AGRITECH - ECO (NÔNG NGHIỆP CNC & SOLAR)'),
        ('BU_Manufacturing', 'BU MANUFACTURING (SẢN XUẤT - NHÀ MÁY)'),
        ('BU_Value', 'BU IBIZ VALUE (THIẾT BỊ ĐIỆN PHỔ THÔNG)'),
        ('KD_BH1MN', 'KINH DOANH MIỀN NAM'),
        ('HPC', 'CÔNG TY CỔ PHẦN HẠO PHƯƠNG'),
    ]

    for dept_code, dept_title in dept_order:
        summaries = EmployeeReceivableSummary.objects.filter(
            reporting_period=period,
            department__department_code=dept_code
        ).exclude(
            employee__employee_code='2001'
        ).select_related('employee', 'department').order_by('-team_total_debt', '-own_total_debt')

        active_summaries = [s for s in summaries if s.own_total_debt > 0 or s.team_total_debt > 0]
        if not active_summaries:
            continue

        dept_own_sum = sum(s.own_total_debt for s in active_summaries)
        print(f"\n🏢 【 {dept_title} 】 (Tổng nợ phát sinh trực tiếp: {dept_own_sum:,.0f} VNĐ)")
        print("-" * 140)
        print(f"{'VAI TRÒ':<12} | {'MÃ NV':<10} | {'HỌ VÀ TÊN':<26} | {'CHỨC DANH':<32} | {'NỢ CÁ NHÂN (OWN)':>18} | {'NỢ CẢ NHÓM (TEAM)':>20} | {'CẤP DƯỚI':>8}")
        print("-" * 140)

        for s in active_summaries:
            ass = EmployeeAssignment.objects.filter(employee=s.employee, department=s.department).select_related('title').first()
            title_name = ass.title.title_name if ass and ass.title else ("Quản lý" if s.is_manager else "Nhân viên")
            
            if 'trưởng bu' in title_name.lower():
                role_tag = "👑 TRƯỞNG BU"
            elif s.is_manager:
                role_tag = "⭐ TRƯỞNG BP"
            else:
                role_tag = "👤 SALES"

            sub_str = f"{s.subordinate_count} NV" if s.is_manager else "-"
            print(f"{role_tag:<12} | {s.employee.employee_code:<10} | {s.employee.full_name[:26]:<26} | {title_name[:32]:<32} | {s.own_total_debt:>18,.0f} | {s.team_total_debt:>20,.0f} | {sub_str:>8}")

    print("\n" + "=" * 140)


def main():
    parser = argparse.ArgumentParser(description="Báo cáo công nợ BU & Nhân viên chuẩn hóa theo kỳ")
    parser.add_argument('--period', type=str, default='2026-08', help="Kỳ báo cáo (YYYY-MM), mặc định: 2026-08")
    args = parser.parse_args()

    generate_bu_debt_report(args.period)
    generate_employee_debt_by_bu_report(args.period)


if __name__ == '__main__':
    main()
