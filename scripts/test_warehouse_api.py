import os
import sys
import json

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE_DIR)
sys.stdout.reconfigure(encoding='utf-8')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'report2026.settings')

import django
django.setup()

from accounting.models import Warehouse, InventorySummary
from django.contrib.auth.models import User
from rest_framework.test import APIRequestFactory, force_authenticate
from accounting.views import WarehouseViewSet
from django.db.models import Sum

def run_test():
    print("=" * 90)
    print("🧪 BẮT ĐẦU KIỂM THỬ ENDPOINT /api/warehouses/ VỚI ĐỘNG HÓA TỒN KHO")
    print("=" * 90)

    user = User.objects.filter(is_superuser=True).first() or User.objects.first()
    factory = APIRequestFactory()

    # TEST 1: Gọi với startDate & endDate kỳ 2026-08
    url_1 = '/api/warehouses/?startDate=2026-08-01&endDate=2026-08-17'
    print(f"\n📡 [TEST 1] Gọi endpoint: {url_1}")
    request_1 = factory.get(url_1)
    force_authenticate(request_1, user=user)
    view = WarehouseViewSet.as_view({'get': 'list'})
    response_1 = view(request_1)

    assert response_1.status_code == 200, f"HTTP Status code is {response_1.status_code}"
    data_1 = response_1.data
    assert isinstance(data_1, list), "Response data should be a list"
    assert len(data_1) == Warehouse.objects.count(), f"Expected {Warehouse.objects.count()} warehouses"

    total_actual_1 = sum(float(item['inventory_value_actual'] or 0) for item in data_1)
    total_opening_1 = sum(float(item['inventory_opening_value'] or 0) for item in data_1)
    total_in_1 = sum(float(item['inventory_in_value'] or 0) for item in data_1)
    total_out_1 = sum(float(item['inventory_out_value'] or 0) for item in data_1)

    db_expected_closing = float(InventorySummary.objects.filter(reporting_period='2026-08').aggregate(t=Sum('closing_value'))['t'] or 0)

    print(f"  HTTP Status: {response_1.status_code} OK")
    print(f"  Số lượng kho hàng trả về: {len(data_1)} kho")
    print(f"  📦 Tổng Tồn Đầu Kỳ:    {total_opening_1:18,.0f} VNĐ")
    print(f"  📥 Tổng Nhập Trong Kỳ: {total_in_1:18,.0f} VNĐ")
    print(f"  📤 Tổng Xuất Trong Kỳ: {total_out_1:18,.0f} VNĐ")
    print(f"  🏦 Tổng Tồn Cuối Kỳ:   {total_actual_1:18,.0f} VNĐ")
    print(f"  🎯 Số liệu DB Mục Tiêu:{db_expected_closing:18,.0f} VNĐ")

    diff = abs(total_actual_1 - db_expected_closing)
    assert diff == 0, f"Chênh lệch số liệu: {diff} VNĐ"
    print(f"  ✅ [PASS TEST 1]: Khớp chính xác 100% số liệu tồn kho kỳ 2026-08 (Chênh lệch: {diff:,.0f} VNĐ)!")

    # Sắp xếp top 3 kho lớn nhất
    sorted_whs = sorted(data_1, key=lambda x: float(x['inventory_value_actual'] or 0), reverse=True)
    print("\n🏆 TOP 5 KHO HÀNG CÓ GIÁ TRỊ TỒN CAO NHẤT:")
    for idx, wh in enumerate(sorted_whs[:5], start=1):
        closing = float(wh['inventory_value_actual'])
        print(f"  {idx}. [{wh['code']:15}] {wh['name']:40} -> {closing:15,.0f} VNĐ")

    print("\n📄 [MẪU JSON RESPONSE CỦA 3 KHO LỚN NHẤT]:")
    print(json.dumps(sorted_whs[:3], ensure_ascii=False, indent=2))

    # TEST 2: Gọi với kỳ cũ 2026-07
    url_2 = '/api/warehouses/?period=2026-07'
    print(f"\n📡 [TEST 2] Gọi endpoint kỳ cũ: {url_2}")
    request_2 = factory.get(url_2)
    force_authenticate(request_2, user=user)
    response_2 = view(request_2)
    data_2 = response_2.data

    total_actual_2 = sum(float(item['inventory_value_actual'] or 0) for item in data_2)
    db_expected_07 = float(InventorySummary.objects.filter(reporting_period='2026-07').aggregate(t=Sum('closing_value'))['t'] or 0)
    diff_07 = abs(total_actual_2 - db_expected_07)
    assert diff_07 == 0, f"Chênh lệch kỳ 2026-07: {diff_07} VNĐ"
    print(f"  HTTP Status: {response_2.status_code} OK")
    print(f"  🏦 Tổng Tồn Cuối Kỳ 2026-07: {total_actual_2:18,.0f} VNĐ (DB Target: {db_expected_07:,.0f} VNĐ)")
    print(f"  ✅ [PASS TEST 2]: Động hóa kỳ 2026-07 khớp 100%!")

    print("\n" + "=" * 90)
    print("🎉 TẤT CẢ CÁC BỘ TEST WAREHOUSE API ĐỀU PASS 100%!")
    print("=" * 90)

if __name__ == '__main__':
    run_test()
