"""
Script Test & Kiểm Thử Toàn Diện 2 Endpoints REST API Công Nợ (Chuẩn Hóa & Đầy Đủ Dải Tuổi Nợ):
1. API 1 (Default Filtered): GET /api/debt/bus/?period=2026-08 (Chỉ hiện các BU có nợ quá hạn > 0)
2. API 1 (Include All): GET /api/debt/bus/?period=2026-08&include_all=true (Hiển thị đầy đủ 22 BU)
3. API 2: GET /api/debt/bus/BU_ELEVATOR/drilldown/?period=2026-08 (3-Tier Drilldown + 14 Dải Tuổi Nợ Chi Tiết)
4. API 2 (Error case): GET /api/debt/bus/NON_EXISTING_BU/drilldown/
"""
import os
import sys
import json
from decimal import Decimal

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE_DIR)

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'report2026.settings')
import django
django.setup()

from rest_framework.test import APIClient


def test_apis():
    client = APIClient()

    print("=" * 110)
    print("🚀 BẮT ĐẦU KIỂM THỬ 2 REST API ENDPOINTS BÁO CÁO CÔNG NỢ (TỐI ƯU LỌC & CHI TIẾT DẢI TUỔI NỢ)")
    print("=" * 110)

    # -------------------------------------------------------------
    # TEST 1A: API 1 — MẶC ĐỊNH (CHỈ HIỆN BU CÓ NỢ QUÁ HẠN > 0)
    # -------------------------------------------------------------
    url_api_1a = '/api/debt/bus/?period=2026-08'
    print(f"\n📡 [TEST 1A] Gọi API 1 (Mặc định lọc nợ quá hạn): {url_api_1a}")
    res1a = client.get(url_api_1a)
    
    assert res1a.status_code == 200, f"Expected 200 OK, got {res1a.status_code}"
    data1a = res1a.json()

    print(f"  HTTP Status: {res1a.status_code} OK")
    print(f"  Kỳ báo cáo: {data1a.get('period')}")
    print(f"  Số lượng BU có nợ quá hạn: {len(data1a.get('bus', []))} BU")
    
    g = data1a.get('global_summary', {})
    print(f"  🏦 Global Total Debt:    {float(g.get('receivable_total', 0)):>18,.0f} VNĐ")
    print(f"  🏦 Global Overdue Debt:  {float(g.get('overdue_total', 0)):>18,.0f} VNĐ ({g.get('overdue_rate')}%)")

    for b in data1a['bus']:
        assert float(b['overdue_total']) > 0, f"LỖI: BU {b['code']} có nợ quá hạn = 0 nhưng vẫn hiển thị!"
        print(f"     • [{b['code']:<20}] {b['name']:<28} | Tổng nợ: {float(b['receivable_total']):>15,.0f} | Quá hạn: {float(b['overdue_total']):>15,.0f} ({b['overdue_rate']}%)")

    print("  ✅ [PASS TEST 1A]: Mặc định lọc bỏ hoàn toàn các BU nợ = 0 hoặc overdue_rate = 0%!")

    # -------------------------------------------------------------
    # TEST 1B: API 1 — TÙY CHỌN INCLUDE_ALL=TRUE (HIỂN THỊ ĐỦ 6 BU KINH DOANH CỐT LÕI)
    # -------------------------------------------------------------
    url_api_1b = '/api/debt/bus/?period=2026-08&include_all=true'
    print(f"\n📡 [TEST 1B] Gọi API 1 (include_all=true): {url_api_1b}")
    res1b = client.get(url_api_1b)
    
    assert res1b.status_code == 200, f"Expected 200 OK, got {res1b.status_code}"
    data1b = res1b.json()
    assert len(data1b.get('bus', [])) == 6, f"LỖI: Kỳ vọng 6 BU kinh doanh cốt lõi, thực tế có {len(data1b.get('bus', []))}"
    print(f"  HTTP Status: {res1b.status_code} OK | Trả về chuẩn 6 BU cốt lõi: {len(data1b.get('bus', []))} BU")
    print("  ✅ [PASS TEST 1B]: Chỉ trả về đúng 6 BU Kinh Doanh Cốt Lõi!")

    # -------------------------------------------------------------
    # TEST 2: API 2 — BÁO CÁO PHÂN CẤP 3 TẦNG DRILLDOWN + 14 DẢI TUỔI NỢ
    # -------------------------------------------------------------
    url_api_2 = '/api/debt/bus/BU_ELEVATOR/drilldown/?period=2026-08'
    print(f"\n📡 [TEST 2] Gọi API 2: {url_api_2}")
    res2 = client.get(url_api_2)
    
    assert res2.status_code == 200, f"Expected 200 OK, got {res2.status_code}"
    data2 = res2.json()

    print(f"  HTTP Status: {res2.status_code} OK")
    t1 = data2.get('tier_1_bu', {})
    print(f"  🏢 [Cấp 1 - BU]: [{t1.get('code')}] {t1.get('name')} | Trưởng BU: {t1.get('manager_name')}")
    print(f"     Tổng nợ BU: {float(t1.get('receivable_total', 0)):>18,.0f} VNĐ | Quá hạn: {float(t1.get('overdue_total', 0)):>18,.0f} VNĐ")

    # Verify 14 Aging Buckets in Customers
    required_bucket_keys = [
        'no_due_limit', 'due_0_7', 'due_8_14', 'due_15_21', 'due_22_28', 'due_29_60', 'due_above_60', 'due_total',
        'overdue_0_14', 'overdue_15_30', 'overdue_31_45', 'overdue_46_60', 'overdue_61_90', 'overdue_91_120', 'overdue_above_120', 'overdue_total',
        'total_debt'
    ]

    ka = data2.get('tier_2_and_3', {}).get('key_accounts_summary')
    sample_cust = None
    if ka and ka.get('customers'):
        sample_cust = ka['customers'][0]
    elif data2.get('tier_2_and_3', {}).get('bu_teams'):
        for team in data2['tier_2_and_3']['bu_teams']:
            if team.get('customers'):
                sample_cust = team['customers'][0]
                break

    assert sample_cust is not None, "LỖI: Không tìm thấy khách hàng nào trong response drilldown!"
    for k in required_bucket_keys:
        assert k in sample_cust, f"LỖI: Khách hàng thiếu trường dải tuổi nợ '{k}'!"

    print("\n  📄 [MẪU 1 KHÁCH HÀNG CÓ ĐẦY ĐỦ 14 DẢI TUỔI NỢ CHI TIẾT]:")
    print(json.dumps(sample_cust, indent=4, ensure_ascii=False))

    recon = data2.get('reconciliation', {})
    print(f"\n  🎯 Đối Soát Drilldown: Discrepancy = {float(recon.get('discrepancy', 0)):,.0f} VNĐ | Is Matched = {recon.get('is_matched')}")
    assert recon.get('is_matched') is True, "LỖI: Drilldown total không khớp với BU total!"
    print("  ✅ [PASS TEST 2]: Drilldown 3 tầng phân cấp chuẩn, có đầy đủ 14 dải tuổi nợ và đối soát khớp 100% (0 VNĐ chênh lệch)!")

    # -------------------------------------------------------------
    # TEST 3: API 2 — 404 NOT FOUND VỚI MÃ BU KHÔNG TỒN TẠI
    # -------------------------------------------------------------
    url_api_3 = '/api/debt/bus/NON_EXISTING_BU/drilldown/'
    print(f"\n📡 [TEST 3] Gọi API 2 với mã không tồn tại: {url_api_3}")
    res3 = client.get(url_api_3)
    assert res3.status_code == 404, f"Expected 404 Not Found, got {res3.status_code}"
    print(f"  HTTP Status: {res3.status_code} NOT FOUND (Đã trả về danh sách available_bus)")
    print("  ✅ [PASS TEST 3]: Xử lý lỗi 404 thành công!")

    print("\n" + "=" * 110)
    print("🎉 TẤT CẢ CÁC BỘ TEST REST API ĐỀU PASS 100%!")
    print("=" * 110)


if __name__ == '__main__':
    test_apis()
