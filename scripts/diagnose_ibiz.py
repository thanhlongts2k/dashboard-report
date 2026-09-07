import os, sys
sys.stdout.reconfigure(encoding='utf-8')
sys.stderr.reconfigure(encoding='utf-8')
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'report2026.settings')
import django
django.setup()

from accounting.models import BusinessUnit, SalesTarget, SalesTransaction, Customer, Employee

print("=== BUSINESS UNITS IN DB ===")
for bu in BusinessUnit.objects.all().order_by('code'):
    print(f"code: '{bu.code}' | name: '{bu.name}' | is_main: {bu.is_main}")

print("\n=== SALES TARGETS IN DB ===")
for st in SalesTarget.objects.filter(period='2026-08').select_related('business_unit', 'employee').order_by('business_unit__code', 'display_order'):
    print(f"BU: '{st.business_unit.code}' | Region: '{st.region}' | Sales: '{st.employee.full_name}' ({st.employee.employee_code}) | MonthTarget: {st.month_target}")

print("\n=== TRANSACTIONS FOR IBIZ IN AUGUST 2026 ===")
from datetime import date
txs = SalesTransaction.objects.filter(posting_date__gte=date(2026, 8, 1), posting_date__lte=date(2026, 8, 31))
print("Total tx in Aug 2026:", txs.count())
bu_tx_counts = {}
for bu_code in txs.values_list('business_unit__code', flat=True):
    bu_tx_counts[bu_code] = bu_tx_counts.get(bu_code, 0) + 1
print("Tx count by BU:", bu_tx_counts)

print("\n=== CHECK CUSTOMERS WITH ASSIGNED EMPLOYEES ===")
ibiz_emps = Employee.objects.filter(salestarget__isnull=False).distinct()
print("Employees with SalesTarget:", [(e.employee_code, e.full_name) for e in ibiz_emps])

cust_with_emp = Customer.objects.filter(assigned_employee__in=ibiz_emps)
print("Customers assigned to these sales:", cust_with_emp.count())
for c in cust_with_emp[:20]:
    print(f"Customer {c.code} - {c.name} -> Sales: {c.assigned_employee.full_name} ({c.assigned_employee.employee_code})")
