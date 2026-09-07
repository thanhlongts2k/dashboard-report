import os, sys
sys.stdout.reconfigure(encoding='utf-8')
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'report2026.settings')
import django
django.setup()

from accounting.models import SalesTransaction, Customer
from django.db.models import Sum, Q

hisa_ids = list(Customer.objects.filter(
    Q(name__icontains='HISA') | Q(code__icontains='HISA') | Q(code='PAR2019/000883')
).values_list('id', flat=True))

txs = SalesTransaction.objects.filter(
    posting_date='2026-08-31',
    customer__has_revenue=True
).exclude(
    customer_id__in=hisa_ids
).exclude(
    customer__group__code='Internal'
)

print('Total 2026-08-31 revenue:', txs.aggregate(s=Sum('actual_sales'))['s'])

bu_sums = txs.values('business_unit__code', 'business_unit__name').annotate(total=Sum('actual_sales')).order_by('-total')
for b in bu_sums:
    print(f"{b['business_unit__code']} - {b['business_unit__name']}: {b['total']}")

print("\n--- Detailed Customers on 31/08/2026 for BU_IBIZ VALUE ---")
val_txs = txs.filter(business_unit__code='BU_IBIZ VALUE')
for t in val_txs:
    print(f"  {t.doc_id} | {t.customer.code} - {t.customer.name} | Sales assigned: {t.customer.assigned_employee} | Amount: {t.actual_sales}")
