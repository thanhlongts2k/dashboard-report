import os, sys, django
sys.path.insert(0, os.path.abspath('.'))
sys.stdout.reconfigure(encoding='utf-8')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'report2026.settings')
django.setup()

from django.db import transaction
from accounting.models import BusinessUnit, Customer, CustomerGroup, ReceivablesAgeing
from django.db.models import Q, Sum

print("==========================================================================================")
print("  🚀 CẬP NHẬT MAPPING KHÁCH HÀNG OVERSEA -> BU OVERSEA (ID=77)")
print("==========================================================================================")

bu_oversea = BusinessUnit.objects.filter(code__iexact='Oversea').first()
if not bu_oversea:
    print("❌ Không tìm thấy BusinessUnit Oversea!")
    sys.exit(1)

print(f"BU Target: ID={bu_oversea.id} | Code={bu_oversea.code} | Name={bu_oversea.name}")

# 1. Danh sách mã khách hàng quốc tế cần gán trực tiếp
specific_cust_codes = [
    'KH2025/000427',  # FUJI LIFT ENGINEERING CO., LTD
    'PAR2019/001242',  # FUJI ELECTRIC (THAILAND) CO.,LTD.
    'PAR2023/006728',  # HAO PHUONG (CAMBODIA) CO.,LTD
    'PAR2020/000504',  # THAI VATANA UPAKORN AND CHILD (1992) CO.
    'KH2025/000629',  # CHIANG-LY HANDLING MACHINE CO., LTD
    'KH2025/000542',  # SYSTEMS WORKS CO., LTD.
    'PAR2022/001669',  # FUJI INDUSTRY (NINGBO) CO.,LTD.
    'PAR2023/008733',  # XI'AN HUQIANG ELEVATOR FITTINGS CO., LTD
    'KH2026/000153',  # XI'AN YUANQI ELEVATOR PARTS CO.,LTD
    'PAR2019/001547',  # CAMBODIA ELECTRIC SHOP
    'PAR2022/003364',  # TEM TRADING M&E PRODUCT CO.,LTD
    'THAISEMCON',      # THAI SEMCON CO.,LTD
    'VIREAK0220',      # MR. CHAN YOU VIREAK
    'ORKNHA0617',      # MR.ORKNHA SENG SOCHEAT
    'PAR2019/001642',  # PATECH PISNUK AUTOTECH
    'PAR2019/002216',  # COMIN KHMERE CO., LTD
    'PAR2019/002666',  # CHIM SOCHEAT
    'PAR2019/002682',  # LY SOKLEAP ELECTRIC
    'PAR2022/002753',  # JICA CAMBODIA
    'PAR2022/002766',  # MAUSO CO ., LTD
    'KH2025/000286',  # SHANGHAI YIXIN INTERNATIONAL TRADE CO.
]

# 2. Tìm tất cả khách hàng thuộc nhóm Oversea hoặc trong danh sách
ovs_groups = CustomerGroup.objects.filter(
    Q(code__icontains='oversea') | Q(name__icontains='nước ngoài')
)

custs_to_update = Customer.objects.filter(
    Q(group__in=ovs_groups) | Q(code__in=specific_cust_codes)
)

print(f"Tổng số khách hàng Oversea được chọn: {custs_to_update.count()} KH")

updated_count = 0
with transaction.atomic():
    for c in custs_to_update:
        old_bu = c.business_unit.code if c.business_unit else 'NONE'
        if c.business_unit_id != bu_oversea.id:
            c.business_unit = bu_oversea
            c.save(update_fields=['business_unit'])
            updated_count += 1
            print(f"  ✅ [{c.code:<15}] {c.name[:38]:<38} | BU cũ: {old_bu:<15} -> BU mới: Oversea")
        else:
            print(f"  ℹ️ [{c.code:<15}] {c.name[:38]:<38} | Đã thuộc BU Oversea")

print(f"\n🎉 Hoàn thành cập nhật {updated_count} khách hàng sang BU Oversea!")
