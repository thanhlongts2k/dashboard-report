import os
import sys
sys.stdout.reconfigure(encoding='utf-8')
from django.db import transaction

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_ROOT)
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'report2026.settings')

import django
django.setup()

from accounting.models import Customer, SalesTransaction, Employee

@transaction.atomic
def auto_assign_customer_sales():
    print("=" * 85)
    print("🚀 BẮT ĐẦU TỰ ĐỘNG GÁN NHÂN VIÊN SALES PHỤ TRÁCH CHO KHÁCH HÀNG TỪ SỔ BÁN HÀNG")
    print("=" * 85)

    # Lấy tất cả giao dịch bán hàng có Customer và Employee
    txs = SalesTransaction.objects.filter(
        customer__isnull=False, 
        employee__isnull=False
    ).values('customer_id', 'employee_id')

    # Thống kê tần suất giao dịch (Sales nào bán cho Khách hàng này nhiều nhất)
    customer_sales_freq = {} # {customer_id: {employee_id: count}}
    for tx in txs:
        c_id = tx['customer_id']
        e_id = tx['employee_id']
        if c_id not in customer_sales_freq:
            customer_sales_freq[c_id] = {}
        customer_sales_freq[c_id][e_id] = customer_sales_freq[c_id].get(e_id, 0) + 1

    updated_customers = []
    
    for c_id, emp_dict in customer_sales_freq.items():
        # Chọn Sales có số lần giao dịch bán hàng nhiều nhất cho khách này
        top_emp_id = max(emp_dict.items(), key=lambda item: item[1])[0]
        
        customer = Customer.objects.filter(id=c_id).first()
        if customer and customer.assigned_employee_id != top_emp_id:
            customer.assigned_employee_id = top_emp_id
            updated_customers.append(customer)

    if updated_customers:
        Customer.objects.bulk_update(updated_customers, ['assigned_employee'])
        print(f"✅ ĐÃ TỰ ĐỘNG GÁN THÀNH CÔNG NHÂN VIÊN SALES PHỤ TRÁCH CHO {len(updated_customers)} KHÁCH HÀNG!")
    else:
        print("ℹ️ Không có Khách hàng mới nào cần cập nhật.")

    print("=" * 85)

if __name__ == '__main__':
    auto_assign_customer_sales()
