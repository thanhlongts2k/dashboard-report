"""
Script chạy đồng bộ Sổ chi tiết tài khoản (TAI_KHOAN_CT) thủ công. (Legacy)
Ghi chú: Đã có lệnh tiêu chuẩn `python manage.py sync_misa --prefix=TAI_KHOAN_CT` thay thế.
"""
import os
import sys
import asyncio
import calendar
from datetime import datetime

# Setup path and Django Environment
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, PROJECT_ROOT)
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'report2026.settings')

import django
django.setup()
from django.conf import settings
from django.db.models import Sum
from playwright.async_api import async_playwright

async def download_misa_report(output_path):
    report_url = settings.MISA_REPORTS.get('TAI_KHOAN_CT')
    
    print("--- BUOC 1: KHOI CHAY PLAYWRIGHT & DOWLOAD SO CHI TIET TAI KHOAN ---")
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False, channel="chrome")
        
        if os.path.exists(settings.MISA_BROWSER_STATE_PATH):
            print(f"Khoi phuc phien dang nhap tu: {settings.MISA_BROWSER_STATE_PATH}")
            context = await browser.new_context(
                storage_state=settings.MISA_BROWSER_STATE_PATH,
                viewport={"width": 1280, "height": 800}
            )
        else:
            print("Khong tim thay file session, bat dau phien moi...")
            context = await browser.new_context(viewport={"width": 1280, "height": 800})
            
        page = await context.new_page()
        
        from accounting.misa_tasks import download_report_from_url
        
        try:
            success = await download_report_from_url(
                page=page,
                report_url=report_url,
                export_selector=settings.MISA_EXPORT_SELECTOR,
                output_path=output_path,
                prefix='TAI_KHOAN_CT',
                skip_parameters=False
            )
            if not success:
                print("\n❌ LOI: Tai bao cao tu MISA that bai. Vui long kiem tra lai.")
                await browser.close()
                return False
        except Exception as e:
            print(f"\n❌ LOI TRONG QUA TRINH DOWNLOAD: {str(e)}")
            await browser.close()
            return False
            
        print(f"✅ Tai file tu MISA thanh cong: {output_path}")
        print("Cho 3 giay truoc khi dong trinh duyet...")
        await asyncio.sleep(3.0)
        await browser.close()
        return True

def main():
    print("\n" + "="*80)
    print(" KHOI CHAY TIEN TRINH DONG BO SO CHI TIET TAI KHOAN (TAI_KHOAN_CT)...")
    print(" Vui long quan sat cua so trinh duyet Chrome de xem bot thao tac tren MISA.")
    print("="*80 + "\n")
    
    # Thư mục chứa file tải về để import
    import_dir = os.path.join(settings.BASE_DIR, 'media', 'auto_imports')
    os.makedirs(import_dir, exist_ok=True)
    
    # Định dạng tên file: TAI_KHOAN_CT_YYYYMMDD_HHMMSS.xlsx
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    filename = f"TAI_KHOAN_CT_{timestamp}.xlsx"
    output_path = os.path.join(import_dir, filename)
    
    # 1. Chạy bước tải báo cáo trong Async Context của Playwright
    # Sau khi chạy xong, Async Event Loop sẽ được đóng hoàn toàn
    download_success = asyncio.run(download_misa_report(output_path))
    if not download_success:
        return

    # 2. Chạy bước nạp dữ liệu (Import) trong Sync Context bình thường
    print("\n--- BUOC 2: NAP DU LIEU (IMPORT) EXCEL VAO DATABASE ---")
    from accounting.tasks import auto_import_excel_from_folder
    
    try:
        # Hàm này sẽ tự quét media/auto_imports, tìm file TAI_KHOAN_CT_*,
        # import vào bảng AccountDetail, lưu log và di chuyển file sang success/
        result_msg = auto_import_excel_from_folder()
        print(f"📊 Ket qua Import: {result_msg}")
    except Exception as e:
        print(f"❌ LOI TRONG QUA TRINH IMPORT: {str(e)}")
        return

    # 3. Tính toán lại hiệu suất (KPI) bao gồm Doanh thu, Thực thu và Chi phí opex
    print("\n--- BUOC 3: TINH TOAN LAI KPI & CHI PHI VAN HANH (OPEX) ---")
    from accounting.tasks import update_single_bu_performance
    from accounting.models import BusinessUnit, BUPerformance
    
    # Lấy tháng và năm hiện tại để tính toán
    today = datetime.now()
    month = today.month
    year = today.year
    
    print(f"Dang chay tinh toan cho toan bo cac BU trong Th{month}/{year}...")
    
    # 1. Tính cho Tổng công ty (bu_id = None)
    try:
        msg = update_single_bu_performance(bu_id=None, month=month, year=year)
        print(f"✅ Tong cong ty: {msg}")
    except Exception as e:
        print(f"❌ Loi khi tinh cho Tong cong ty: {str(e)}")
        
    # 2. Tính cho từng BU chi tiết
    bus = BusinessUnit.objects.all()
    for bu in bus:
        try:
            msg = update_single_bu_performance(bu_id=bu.id, month=month, year=year)
            print(f"✅ BU {bu.code}: {msg}")
        except Exception as e:
            print(f"❌ Loi khi tinh cho BU {bu.code}: {str(e)}")

    # 4. In kết quả hiển thị kiểm chứng opex
    print("\n" + "="*80)
    print(f" BIEN DONG CHI PHI VAN HANH (OPEX) SAU KHI DONG BO (Thang {month}/{year}):")
    print("="*80)
    
    # Hiển thị số liệu của Tổng công ty
    perf_corp = BUPerformance.objects.filter(business_unit__isnull=True, month=month, year=year).first()
    if perf_corp:
        print(f"TỔNG TOÀN CÔNG TY:")
        print(f"  - Chi phi opex Ke hoach (Thang): {perf_corp.opex_plan:,.2f} VND")
        print(f"  - Chi phi opex Thuc te (Thang) : {perf_corp.opex_actual:,.2f} VND")
        print(f"  - Luy ke opex Ke hoach (YTD)  : {perf_corp.ytd_opex_plan:,.2f} VND")
        print(f"  - Luy ke opex Thuc te (YTD)   : {perf_corp.ytd_opex_actual:,.2f} VND")
        print("-" * 50)
        
    # Hiển thị số liệu của từng BU
    perf_bus = BUPerformance.objects.filter(business_unit__isnull=False, month=month, year=year)
    for p in perf_bus:
        print(f"BU: {p.business_unit.code} - {p.business_unit.name}")
        print(f"  - Chi phi opex Ke hoach (Thang): {p.opex_plan:,.2f} VND")
        print(f"  - Chi phi opex Thuc te (Thang) : {p.opex_actual:,.2f} VND")
        print(f"  - Luy ke opex Ke hoach (YTD)  : {p.ytd_opex_plan:,.2f} VND")
        print(f"  - Luy ke opex Thuc te (YTD)   : {p.ytd_opex_actual:,.2f} VND")
        print("-" * 50)
        
    print("\n" + "="*80)
    print(" DONG BO HOAN TAT THANH CONG!")
    print("="*80 + "\n")

if __name__ == '__main__':
    if hasattr(sys.stdout, 'reconfigure'):
        try:
            sys.stdout.reconfigure(encoding='utf-8')
        except Exception:
            pass
    main()
