import os, sys
sys.stdout.reconfigure(encoding='utf-8')
sys.stderr.reconfigure(encoding='utf-8')
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'report2026.settings')
import django
django.setup()

from accounting.services.sales_performance_service import get_sales_performance_data

bus_to_test = ['BU_ELEVATOR', 'BU_IBIZ PREMIUM', 'BU_IBIZ_PREMIUM', 'ibiz-premium', 'BU_IBIZ VALUE', 'BU_IBIZ_VALUE', 'ibiz-value', 'ALL']

for bu_input in bus_to_test:
    print(f"\n=======================================================")
    print(f"TESTING WITH bu_code = '{bu_input}'")
    print(f"=======================================================")
    res = get_sales_performance_data(target_date='2026-08-31', period='2026-08', bu_code=bu_input)
    print(f"Success: {res['success']} | Date: {res['date']} | Period: {res['period']}")
    tree = res.get('tree', [])
    print(f"Tree nodes count: {len(tree)}")
    for bu_node in tree:
        m = bu_node['metrics']
        print(f"-> BU: {bu_node['code']} - {bu_node['name']}")
        print(f"   Lũy kế Năm: KH={m['year_target']:,.0f} | TT={m['year_actual']:,.0f} | %={m['year_rate']}%")
        print(f"   Lũy kế T1-T7: KH={m['prev_target']:,.0f} | TT={m['prev_actual']:,.0f} | %={m['prev_rate']}%")
        print(f"   Tháng 8: KH={m['month_target']:,.0f} | TT={m['month_actual']:,.0f} | %={m['month_rate']}%")
        print(f"   Ngày 31/08: DT={m['day_revenue']:,.0f}")
        for reg in bu_node.get('children', []):
            rm = reg['metrics']
            print(f"   -- Region: {reg['name']} ({len(reg.get('children', []))} sales) -> Ngày 31/08: {rm['day_revenue']:,.0f} | Tháng 8: {rm['month_actual']:,.0f}")
            for emp in reg.get('children', []):
                em = emp['metrics']
                if em['day_revenue'] > 0 or em['month_actual'] > 0:
                    print(f"      * {emp['name']} ({emp['employee_code']}): Ngày 31/08={em['day_revenue']:,.0f} | Tháng 8={em['month_actual']:,.0f}")
