import os, sys
sys.stdout.reconfigure(encoding='utf-8')
sys.stderr.reconfigure(encoding='utf-8')
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'report2026.settings')
import django
django.setup()

from accounting.models import BusinessUnit, SalesTarget, SalesTransaction, Customer, Employee
from django.db.models import Sum, Q

print("=== CHECK ACTUAL REVENUE FOR IBIZ PREMIUM (BU_IBIZ PREMIUM) ===")
bu_prem = BusinessUnit.objects.filter(code='BU_IBIZ PREMIUM').first()
if bu_prem:
    tx_prem = SalesTransaction.objects.filter(
        business_unit=bu_prem,
        posting_date__year=2026,
        posting_date__month=8
    )
    print("Total transactions for BU_IBIZ PREMIUM in 08/2026:", tx_prem.count())
    print("Total amount in 08/2026:", tx_prem.aggregate(s=Sum('actual_sales'))['s'])

    # Check how many transactions have customer with assigned_employee
    tx_with_emp = tx_prem.filter(customer__assigned_employee__isnull=False)
    print("Transactions with customer.assigned_employee:", tx_with_emp.count())
    print("Amount with customer.assigned_employee:", tx_with_emp.aggregate(s=Sum('actual_sales'))['s'])

    # What employees are assigned?
    emp_stats = tx_with_emp.values(
        'customer__assigned_employee__employee_code',
        'customer__assigned_employee__full_name'
    ).annotate(total=Sum('actual_sales')).order_by('-total')
    print("\nEmployees breakdown for BU_IBIZ PREMIUM:")
    for e in emp_stats:
        print(f"  {e['customer__assigned_employee__employee_code']} - {e['customer__assigned_employee__full_name']}: {e['total']:,}")

    # Check transactions WITHOUT assigned employee
    tx_no_emp = tx_prem.filter(customer__assigned_employee__isnull=True)
    if tx_no_emp.exists():
        print(f"\nWARNING: {tx_no_emp.count()} transactions have NO customer.assigned_employee!")
        print("Unassigned amount:", tx_no_emp.aggregate(s=Sum('actual_sales'))['s'])
        # Show top customers without assigned employee
        top_custs = tx_no_emp.values('customer__code', 'customer__name').annotate(total=Sum('actual_sales')).order_by('-total')[:10]
        for c in top_custs:
            print(f"    Cust: {c['customer__code']} - {c['customer__name']}: {c['total']:,}")

print("\n=== CHECK ACTUAL REVENUE FOR IBIZ VALUE (BU_IBIZ VALUE) ===")
bu_val = BusinessUnit.objects.filter(code='BU_IBIZ VALUE').first()
if bu_val:
    tx_val = SalesTransaction.objects.filter(
        business_unit=bu_val,
        posting_date__year=2026,
        posting_date__month=8
    )
    print("Total transactions for BU_IBIZ VALUE in 08/2026:", tx_val.count())
    print("Total amount in 08/2026:", tx_val.aggregate(s=Sum('actual_sales'))['s'])

    tx_val_emp = tx_val.filter(customer__assigned_employee__isnull=False)
    print("Transactions with customer.assigned_employee:", tx_val_emp.count())
    print("Amount with customer.assigned_employee:", tx_val_emp.aggregate(s=Sum('actual_sales'))['s'])

    emp_stats_val = tx_val_emp.values(
        'customer__assigned_employee__employee_code',
        'customer__assigned_employee__full_name'
    ).annotate(total=Sum('actual_sales')).order_by('-total')
    print("\nEmployees breakdown for BU_IBIZ VALUE:")
    for e in emp_stats_val:
        print(f"  {e['customer__assigned_employee__employee_code']} - {e['customer__assigned_employee__full_name']}: {e['total']:,}")

    tx_val_no_emp = tx_val.filter(customer__assigned_employee__isnull=True)
    if tx_val_no_emp.exists():
        print(f"\nWARNING: {tx_val_no_emp.count()} transactions have NO customer.assigned_employee!")
        print("Unassigned amount:", tx_val_no_emp.aggregate(s=Sum('actual_sales'))['s'])
