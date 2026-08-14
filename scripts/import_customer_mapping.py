import os
import sys
import argparse
import logging
from decimal import Decimal

# Setup Django Environment
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'report2026.settings')
sys.stdout.reconfigure(encoding='utf-8')

import django
django.setup()

import pandas as pd
from django.db import transaction
from accounting.models import Customer, Employee, EmployeeAssignment, EmployeeReceivableSummary
from accounting.services.employee_debt_calculator import update_employee_receivable_summary

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


def import_customer_sales_mapping(excel_path=None, run_calculate=True, reporting_period="2026-08"):
    if not excel_path:
        excel_path = os.path.join(PROJECT_ROOT, "media", "auto_imports", "Danh_sach_khach_hang.xlsx")

    if not os.path.exists(excel_path):
        print(f"❌ Không tìm thấy file Excel: {excel_path}")
        return False

    print("=" * 85)
    print(f"🚀 BẮT ĐẦU IMPORT MAPPING KHÁCH HÀNG - SALES TỪ: {os.path.basename(excel_path)}")
    print("=" * 85)

    # 1. Đọc file Excel từ dòng header (Header tại dòng 3 -> header=2)
    print("⏳ Đang đọc file Excel...")
    df = pd.read_excel(excel_path, header=2)
    total_excel_rows = len(df)
    print(f"📊 Tổng số dòng trong file Excel: {total_excel_rows:,}")

    # Lọc các dòng hợp lệ có 'Mã khách hàng'
    df_valid = df[df['Mã khách hàng'].notna()].copy()
    df_valid['Mã khách hàng'] = df_valid['Mã khách hàng'].astype(str).str.strip()
    df_valid['Tên khách hàng'] = df_valid['Tên khách hàng'].fillna('').astype(str).str.strip()
    df_valid['Địa chỉ'] = df_valid['Địa chỉ'].fillna('').astype(str).str.strip() if 'Địa chỉ' in df.columns else ''

    # 2. Xử lý danh mục Nhân viên (Employee)
    emp_code_col = 'Nhân viên'
    emp_name_col = 'Tên nhân viên'

    if emp_code_col in df_valid.columns:
        df_valid[emp_code_col] = df_valid[emp_code_col].fillna('').astype(str).str.strip()
        df_valid[emp_name_col] = df_valid[emp_name_col].fillna('').astype(str).str.strip()
    else:
        df_valid[emp_code_col] = ''
        df_valid[emp_name_col] = ''

    # Pre-populate Employee nếu có mã mới
    distinct_emps = df_valid[df_valid[emp_code_col] != ''][[emp_code_col, emp_name_col]].drop_duplicates()
    
    new_emp_count = 0
    with transaction.atomic():
        for _, row in distinct_emps.iterrows():
            raw_code = row[emp_code_col]
            name = (row[emp_name_col] or raw_code)[:100]
            code = raw_code[:20]
            if code and code not in ['None', 'nan']:
                _, created = Employee.objects.get_or_create(
                    employee_code=code,
                    defaults={'full_name': name, 'is_active': True}
                )
                if created:
                    new_emp_count += 1

    if new_emp_count > 0:
        print(f"👤 Đã tự động tạo mới {new_emp_count} nhân viên Sales từ danh mục.")

    # Tạo map Employee Code -> Employee ID (hỗ trợ cả raw code và truncated code)
    emp_map = {}
    for e in Employee.objects.all():
        if e.employee_code:
            emp_map[e.employee_code] = e.id
    # Bổ sung mapping cho các raw code dài
    for _, row in distinct_emps.iterrows():
        raw_c = row[emp_code_col]
        if raw_c and raw_c[:20] in emp_map:
            emp_map[raw_c] = emp_map[raw_c[:20]]

    # 3. Nạp và Cập nhật Customer
    existing_customers = {c.code: c for c in Customer.objects.all()}
    
    customers_to_update = []
    customers_to_create = []
    seen_codes = set()

    for _, row in df_valid.iterrows():
        cust_code = row['Mã khách hàng'][:50]
        cust_name = row['Tên khách hàng'][:255]
        cust_addr = row['Địa chỉ'] if 'Địa chỉ' in row else ''
        sales_code = row[emp_code_col]

        if not cust_code or cust_code in ['None', 'nan'] or cust_code in seen_codes:
            continue
        seen_codes.add(cust_code)

        target_emp_id = emp_map.get(sales_code) if sales_code else None

        if cust_code in existing_customers:
            cust = existing_customers[cust_code]
            need_save = False
            if cust.assigned_employee_id != target_emp_id:
                cust.assigned_employee_id = target_emp_id
                need_save = True
            if cust_name and cust.name != cust_name:
                cust.name = cust_name
                need_save = True
            if cust_addr and not cust.address:
                cust.address = cust_addr
                need_save = True
            
            if need_save:
                customers_to_update.append(cust)
        else:
            customers_to_create.append(
                Customer(
                    code=cust_code,
                    name=cust_name or cust_code,
                    address=cust_addr,
                    assigned_employee_id=target_emp_id,
                    has_revenue=True
                )
            )

    # Thực hiện Bulk Upsert
    with transaction.atomic():
        if customers_to_create:
            Customer.objects.bulk_create(customers_to_create, batch_size=1000)
            print(f"✨ Đã tạo mới: {len(customers_to_create):,} Khách hàng.")

        if customers_to_update:
            Customer.objects.bulk_update(
                customers_to_update,
                fields=['assigned_employee', 'name', 'address'],
                batch_size=1000
            )
            print(f"🔄 Đã cập nhật Sales phụ trách cho: {len(customers_to_update):,} Khách hàng.")

    total_customers_db = Customer.objects.count()
    assigned_count = Customer.objects.filter(assigned_employee__isnull=False).count()
    print(f"✅ Tổng số Khách hàng hiện tại trong DB: {total_customers_db:,}")
    print(f"🎯 Số Khách hàng đã được gán Sales phụ trách: {assigned_count:,} ({assigned_count/total_customers_db*100:.1f}%)")

    # 4. Tính toán và chốt số liệu công nợ EmployeeReceivableSummary
    if run_calculate:
        print("\n" + "=" * 85)
        print(f"⚙️ BẮT ĐẦU CHỐT SỐ LIỆU CÔNG NỢ NHÂN VIÊN & QUẢN LÝ KỲ {reporting_period}...")
        print("=" * 85)
        res = update_employee_receivable_summary(reporting_period)
        print(f"📋 Kết quả: {res}")

        # In báo cáo Top Quản lý
        print("\n🏆 TOP 3 QUẢN LÝ / TRƯỞNG PHÒNG CÓ DƯ NỢ NHÓM LỚN NHẤT KỲ " + reporting_period + ":")
        top_managers = EmployeeReceivableSummary.objects.filter(
            reporting_period=reporting_period,
            is_manager=True
        ).order_by('-team_total_debt')[:3]

        if not top_managers:
            # Fallback nếu chưa có is_manager=True, lấy top nhân viên/quản lý có team_total_debt lớn nhất
            top_managers = EmployeeReceivableSummary.objects.filter(
                reporting_period=reporting_period
            ).order_by('-team_total_debt')[:3]

        print("-" * 105)
        print(f"{'STT':<4} | {'Mã NV':<10} | {'Họ Tên Quản Lý':<28} | {'Phòng Ban':<25} | {'Nợ Cả Nhóm (VNĐ)':<20} | {'Nợ Cá Nhân (VNĐ)':<18}")
        print("-" * 105)
        for idx, m in enumerate(top_managers, 1):
            dept_name = m.department.department_name if m.department else "N/A"
            print(f"{idx:<4} | {m.employee.employee_code:<10} | {m.employee.full_name:<28} | {dept_name:<25} | {m.team_total_debt:>18,.0f} | {m.own_total_debt:>16,.0f}")
        print("-" * 105)

    print("\n🎉 HOÀN TẤT TIẾN TRÌNH IMPORT & CHỐT SỐ LIỆU CÔNG NỢ!")
    return True


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="Import Customer - Sales mapping from Excel")
    parser.add_argument('--file', type=str, default=None, help="Đường dẫn file Excel Danh mục khách hàng")
    parser.add_argument('--period', type=str, default="2026-08", help="Kỳ báo cáo cần chốt (YYYY-MM)")
    parser.add_argument('--no-calc', action='store_true', help="Bỏ qua bước tính toán chốt nợ")

    args = parser.parse_args()
    import_customer_sales_mapping(
        excel_path=args.file,
        run_calculate=not args.no_calc,
        reporting_period=args.period
    )
