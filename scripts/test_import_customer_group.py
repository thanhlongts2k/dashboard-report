import os
import sys

# Đảm bảo in ký tự tiếng Việt không bị lỗi cp1252 trên Windows Terminal
if hasattr(sys.stdout, 'reconfigure'):
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_ROOT)

if not django.apps.apps.ready:
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'report2026.settings')
    django.setup()

from accounting.resources import SalesTransactionResource
from accounting.models import Customer, CustomerGroup, Product, MaterialGroup

def main():
    print("=" * 60)
    print(" CHƯƠNG TRÌNH KIỂM THỬ TỰ ĐỘNG TẠO NHÓM KHÁCH HÀNG KHI IMPORT")
    print("=" * 60)

    # 1. Dọn dẹp dữ liệu cũ (nếu có) để đảm bảo môi trường sạch
    Customer.objects.filter(code='CUST_TEST_SOP').delete()
    CustomerGroup.objects.filter(code='GRP_TEST_SOP').delete()
    Product.objects.filter(code='PROD_TEST_SOP').delete()

    print("Step 1: Khởi tạo dữ liệu mock dòng giao dịch Excel...")
    row = {
        'Ngày hạch toán': '2026-07-15',
        'Số chứng từ': 'HD002',
        'Mã khách hàng': 'CUST_TEST_SOP',
        'Tên khách hàng': 'Công ty Cổ phần HAOPHUONG Test',
        'Mã hàng': 'PROD_TEST_SOP',
        'Tên hàng': 'Thiết bị Điện tự động hóa',
        'Mã nhóm khách hàng': 'GRP_TEST_SOP',
        'Tên nhóm khách hàng': 'Nhóm khách hàng VIP miền Nam',
        'Mã nhóm VTHH': 'VTHH_TEST_SOP',
        'Tên nhóm VTHH': 'Nhóm Thiết bị điện',
        'Mã kho': 'KHO_TEST_SOP',
        'Tên kho': 'Kho chính TP.HCM',
        'Chi nhánh': 'Chi nhánh miền Nam',
        'Mã nhân viên bán hàng': 'NV_TEST_SOP',
        'Tên nhân viên bán hàng': 'Nguyễn Văn A',
        'Mã thống kê': 'BU_TEST_SOP',
        'Tên thống kê': 'Business Unit Automation',
        'Tổng số lượng bán': 100,
        'Đơn giá': 15000,
        'Doanh số bán': 1500000,
        'TK Nợ': '131',
        'TK Có': '511',
        'Doanh số thực tế': 1500000
    }

    print("\nStep 2: Chạy trước xử lý dòng `before_import_row`...")
    resource = SalesTransactionResource()
    resource.before_import_row(row)

    print("\nStep 3: Kiểm chứng kết quả trong Cơ sở dữ liệu...")
    
    # Kiểm tra Nhóm khách hàng
    group = CustomerGroup.objects.filter(code='GRP_TEST_SOP').first()
    if group:
        print(f"  [OK] Đã tự tạo Nhóm khách hàng thành công:")
        print(f"       - Mã nhóm: {group.code}")
        print(f"       - Tên nhóm: {group.name}")
    else:
        print("  [ERROR] Không tìm thấy Nhóm khách hàng được tạo!")
        sys.exit(1)

    # Kiểm tra Khách hàng và liên kết nhóm
    customer = Customer.objects.filter(code='CUST_TEST_SOP').first()
    if customer:
        print(f"  [OK] Đã tự tạo Khách hàng thành công:")
        print(f"       - Mã KH: {customer.code}")
        print(f"       - Tên KH: {customer.name}")
        if customer.group == group:
            print(f"  [OK] Liên kết giữa Khách hàng và Nhóm khách hàng chính xác!")
        else:
            print(f"  [ERROR] Khách hàng chưa được liên kết đúng với Nhóm khách hàng!")
            sys.exit(1)
    else:
        print("  [ERROR] Không tìm thấy Khách hàng được tạo!")
        sys.exit(1)

    # Dọn dẹp dữ liệu kiểm thử
    Customer.objects.filter(code='CUST_TEST_SOP').delete()
    CustomerGroup.objects.filter(code='GRP_TEST_SOP').delete()
    Product.objects.filter(code='PROD_TEST_SOP').delete()

    print("\n" + "=" * 60)
    print(" KẾT QUẢ KIỂM THỬ: THÀNH CÔNG RỰC RỠ (PASS)!")
    print("=" * 60)

if __name__ == '__main__':
    main()
