"""
Script phục hồi dữ liệu ReceivablesAgeing cho kỳ 2026-09 từ file đối soát chuẩn 100% (TUOI_NO_KH_202609.xlsx).
Đồng thời tính toán lại EmployeeReceivableSummary và BUPerformance cho Tháng 9/2026.
"""
import os
import sys
import shutil
from decimal import Decimal

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'report2026.settings')
django.setup()

from django.db import transaction
from django.utils import timezone
from django.db.models import Sum, Q
from tablib import Dataset

from accounting.models import (
    BusinessUnit, Customer, ReceivablesAgeing, ImportLog,
    EmployeeReceivableSummary, BUPerformance
)
from accounting.resources import ReceivablesAgeingResource
from accounting.tasks import load_and_clean_excel, update_single_bu_performance
from accounting.services.employee_debt_calculator import update_employee_receivable_summary
from accounting.services.debt_mailer import collect_bu_manager_debt_data

def run_restoration():
    print("=" * 80)
    print("🚀 BẮT ĐẦU TIẾN TRÌNH PHỤC HỒI DỮ LIỆU TUỔI NỢ CHUẨN KỲ 2026-09")
    print("=" * 80)

    clean_file = os.path.join('media', 'auto_imports', 'success', 'TUOI_NO_KH_202609.xlsx')
    corrupted_file = os.path.join('media', 'auto_imports', 'success', 'TUOI_NO_KH_20260908_070021.xlsx')
    backup_dir = os.path.join('media', 'auto_imports', 'backup')
    os.makedirs(backup_dir, exist_ok=True)

    if not os.path.exists(clean_file):
        print(f"❌ LỖI: Không tìm thấy file chuẩn '{clean_file}'!")
        return False

    # 1. Sao lưu file bị lỗi vào thư mục backup để phục vụ thanh tra/đối chiếu
    if os.path.exists(corrupted_file):
        backup_corrupted_path = os.path.join(backup_dir, 'TUOI_NO_KH_20260908_070021_corrupted_future_cutoff.xlsx')
        shutil.copy2(corrupted_file, backup_corrupted_path)
        print(f"📦 Đã sao lưu file lỗi sang: {backup_corrupted_path}")

    # 2. Thống kê trước khi phục hồi
    pre_agg = ReceivablesAgeing.objects.filter(reporting_period='2026-09').aggregate(
        tot=Sum('total_debt'),
        due=Sum('due_total'),
        ovd=Sum('overdue_total')
    )
    pre_count = ReceivablesAgeing.objects.filter(reporting_period='2026-09').count()
    print(f"\n📊 DỮ LIỆU HIỆN TẠI TRONG DB (TRƯỚC KHI SỬA):")
    print(f"  - Số dòng: {pre_count:,}")
    print(f"  - Tổng nợ: {pre_agg['tot'] or 0:,.0f} đ")
    print(f"  - Trong hạn: {pre_agg['due'] or 0:,.0f} đ")
    print(f"  - Nợ quá hạn: {pre_agg['ovd'] or 0:,.0f} đ (BỊ THỔI PHỒNG DO MỐC 30/09)")

    # 3. Đọc và nạp dữ liệu từ file chuẩn
    print(f"\n📖 Đọc file chuẩn: {clean_file}...")
    headers, cleaned_rows = load_and_clean_excel(clean_file, 'TUOI_NO_KH')
    total_excel_rows = len(cleaned_rows)
    print(f"  - Số dòng đọc được: {total_excel_rows:,}")

    start_time = timezone.now()
    resource = ReceivablesAgeingResource()

    with transaction.atomic():
        deleted_count = ReceivablesAgeing.objects.filter(
            Q(reporting_period='2026-09') | Q(reporting_period__isnull=True)
        ).delete()[0]
        print(f"  🗑️ Đã xóa {deleted_count:,} bản ghi cũ bị nhiễm mốc tương lai trong DB.")

        chunk_size = 1000
        imported_count = 0
        has_error = False
        error_details = []

        for i in range(0, total_excel_rows, chunk_size):
            chunk_data = cleaned_rows[i:i+chunk_size]
            chunk_dataset = Dataset()
            chunk_dataset.headers = headers
            for r in chunk_data:
                chunk_dataset.append([r[h] for h in headers])

            result = resource.import_data(chunk_dataset, dry_run=False, reporting_period='2026-09')
            if result.has_errors():
                has_error = True
                for row_num, errors in result.row_errors():
                    for error in errors:
                        error_details.append(f"Dòng {row_num + i}: {str(error.error)}")
                break
            imported_count += len(chunk_dataset)

        if has_error:
            raise Exception("Lỗi import ReceivablesAgeing: " + "\n".join(error_details))

        ImportLog.objects.create(
            file_name='TUOI_NO_KH_202609.xlsx',
            status='SUCCESS',
            message=f"Phục hồi thành công {imported_count} dòng ReceivablesAgeing kỳ 2026-09 từ file đối soát chuẩn 05/09/2026.",
            start_time=start_time,
            end_time=timezone.now()
        )
        print(f"  ✅ Đã import thành công {imported_count:,} dòng chuẩn vào ReceivablesAgeing!")

    # 4. Kích hoạt tính toán lại EmployeeReceivableSummary và BUPerformance
    print("\n🔄 Đang tính toán lại EmployeeReceivableSummary cho kỳ 2026-09...")
    emp_res = update_employee_receivable_summary('2026-09')
    print(f"  ✅ Hoàn tất tính toán công nợ theo nhân viên: {emp_res}")

    print("\n🔄 Đang tính toán lại BUPerformance cho kỳ 2026-09...")
    update_single_bu_performance(None, month=9, year=2026)
    for bu in BusinessUnit.objects.all():
        update_single_bu_performance(bu.id, month=9, year=2026)
    print("  ✅ Hoàn tất cập nhật BUPerformance!")

    # 5. Thống kê sau phục hồi
    post_agg = ReceivablesAgeing.objects.filter(reporting_period='2026-09').aggregate(
        tot=Sum('total_debt'),
        due=Sum('due_total'),
        ovd=Sum('overdue_total')
    )
    post_count = ReceivablesAgeing.objects.filter(reporting_period='2026-09').count()

    print(f"\n📊 DỮ LIỆU TOÀN CÔNG TY SAU KHI PHỤC HỒI CHUẨN:")
    print(f"  - Số dòng: {post_count:,}")
    print(f"  - Tổng nợ: {post_agg['tot'] or 0:,.0f} đ")
    print(f"  - Trong hạn: {post_agg['due'] or 0:,.0f} đ")
    print(f"  - Nợ quá hạn: {post_agg['ovd'] or 0:,.0f} đ (ĐÃ GIẢM {-((pre_agg['ovd'] or 0) - (post_agg['ovd'] or 0)):,.0f} đ VỀ GIÁ TRỊ THỰC)")

    # 6. Kiểm tra cụ thể 3 khách hàng BU IBIZ VALUE được người dùng báo cáo
    target_custs = [
        ('KH2026/000025', 'CÔNG TY TNHH THIÊN PHÚ ELECTRIC'),
        ('KH2026/000011', 'CÔNG TY TNHH SX TM DV XNK AUTOSS'),
        ('KH2025/000505', 'CÔNG TY TNHH KT & TM HOÀNG MINH'),
    ]

    print("\n" + "=" * 80)
    print("🎯 KIỂM TRA ĐẶC BIỆT 3 KHÁCH HÀNG BU IBIZ VALUE:")
    print("=" * 80)

    for code, expected_name in target_custs:
        cust = Customer.objects.filter(code=code).first()
        if not cust:
            print(f"  ❌ Không tìm thấy KH: {code}")
            continue

        records = ReceivablesAgeing.objects.filter(customer=cust, reporting_period='2026-09')
        c_tot = sum(r.total_debt or Decimal('0') for r in records)
        c_due = sum(r.due_total or Decimal('0') for r in records)
        c_ovd = sum(r.overdue_total or Decimal('0') for r in records)
        c_0_14 = sum(r.overdue_0_14 or Decimal('0') for r in records)

        print(f"\n📌 [{code}] {cust.name}")
        print(f"   - Tổng nợ:       {c_tot:,.0f} đ")
        print(f"   - Trong hạn:     {c_due:,.0f} đ")
        print(f"   - Quá hạn:       {c_ovd:,.0f} đ  {'🟢 CHUẨN 0 Đ (100% TRONG HẠN)' if c_ovd == 0 else ('🟢 CHUẨN (CÒN LẠI ĐỀU TRONG HẠN)' if c_ovd < 100000 else '⚠️ CÒN QUÁ HẠN')}")
        print(f"   - Quá hạn 0-14:  {c_0_14:,.0f} đ")

    # 7. Kiểm tra dữ liệu Top Khách hàng nợ quá hạn của BU IBIZ VALUE
    print("\n" + "=" * 80)
    print("🏢 KIỂM TRA BÁO CÁO BU MANAGER GỬI CHO MR. NGUYỄN NGỌC HUY PHONG (BU IBIZ VALUE):")
    print("=" * 80)
    ibiz_data = collect_bu_manager_debt_data(period='2026-09', bu_code='BU_IBIZ VALUE')
    if ibiz_data:
        ibiz = ibiz_data[0]
        print(f"  - BU: {ibiz['bu_display_code']} | Trưởng BU: {ibiz['manager_name']}")
        print(f"  - Tổng nợ BU: {ibiz['total_debt']:,.0f} đ")
        print(f"  - Trong hạn: {ibiz['due_total']:,.0f} đ")
        print(f"  - Quá hạn: {ibiz['overdue_total']:,.0f} đ")
        print(f"  - Tỷ lệ quá hạn: {ibiz['overdue_rate']}%")
        print(f"\n  📋 TOP KHÁCH HÀNG NỢ QUÁ HẠN CỦA BU IBIZ VALUE:")
        for idx, c in enumerate(ibiz['top_overdue_customers'][:10], 1):
            flag = "⚠️ LỖI NẾU XUẤT HIỆN" if c['customer_code'] in ['KH2026/000025', 'KH2026/000011'] else "✅"
            print(f"    {idx}. [{c['customer_code']}] {c['customer_name']} | Quá hạn: {c['overdue_total']:,.0f} đ | Tổng nợ: {c['total_debt']:,.0f} đ {flag}")
    else:
        print("  ⚠️ Không lấy được dữ liệu cho BU_IBIZ VALUE!")

    print("\n" + "=" * 80)
    print("🎉 HOÀN TẤT TIẾN TRÌNH PHỤC HỒI TOÀN BỘ CSDL VÀ BÁO CÁO CÔNG NỢ!")
    print("=" * 80)
    return True

if __name__ == '__main__':
    run_restoration()
