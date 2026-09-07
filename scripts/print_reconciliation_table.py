import os
import sys

sys.stdout.reconfigure(encoding='utf-8')
sys.stderr.reconfigure(encoding='utf-8')
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'report2026.settings')
import django

django.setup()

from accounting.services.sales_performance_service import get_sales_performance_data

bus = ['BU_ELEVATOR', 'BU_IBIZ PREMIUM', 'BU_IBIZ VALUE']
print(
    f'| BU | Ten BU | KH Năm 2026 | TT Năm 2026 (% Đạt) | KH T1-T7 | TT T1-T7 (% Đạt) | KH Tháng 8 | TT Tháng 8 (% Đạt) | DT Ngày 31/08 |'
)
print(
    '|:---|:---|:---:|:---:|:---:|:---:|:---:|:---:|:---:|'
)

for b in bus:
  res = get_sales_performance_data(
      target_date='2026-08-31', period='2026-08', bu_code=b
  )
  for node in res.get('tree', []):
    m = node['metrics']
    code = node['code']
    name = node['name']
    yt = f"{m['year_target']:,.0f}"
    ya = f"{m['year_actual']:,.0f} ({m['year_rate']}%)"
    pt = f"{m['prev_target']:,.0f}"
    pa = f"{m['prev_actual']:,.0f} ({m['prev_rate']}%)"
    mt = f"{m['month_target']:,.0f}"
    ma = f"{m['month_actual']:,.0f} ({m['month_rate']}%)"
    day = f"{m['day_revenue']:,.0f}"
    print(
        f'| {code} | {name} | {yt} | {ya} | {pt} | {pa} | {mt} | {ma} | {day} |'
    )
    for reg in node.get('children', []):
      rm = reg['metrics']
      r_name = reg['name']
      r_yt = f"{rm['year_target']:,.0f}"
      r_ya = f"{rm['year_actual']:,.0f} ({rm['year_rate']}%)"
      r_pt = f"{rm['prev_target']:,.0f}"
      r_pa = f"{rm['prev_actual']:,.0f} ({rm['prev_rate']}%)"
      r_mt = f"{rm['month_target']:,.0f}"
      r_ma = f"{rm['month_actual']:,.0f} ({rm['month_rate']}%)"
      r_day = f"{rm['day_revenue']:,.0f}"
      print(
          f'| ↳ *{r_name}* | *{len(reg.get("children", []))} sales* | {r_yt} |'
          f' {r_ya} | {r_pt} | {r_pa} | {r_mt} | {r_ma} | {r_day} |'
      )
