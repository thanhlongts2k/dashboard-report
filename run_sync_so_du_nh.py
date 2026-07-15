import os
import sys
import asyncio
from datetime import datetime

# Setup path and Django Environment
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'report2026.settings')

import django
django.setup()
from django.conf import settings
from django.db.models import Sum, Q
from playwright.async_api import async_playwright

async def download_misa_report(output_path):
    report_url = settings.MISA_REPORTS.get('SO_DU_NH')
    
    print("--- BUOC 1: KHOI CHAY PLAYWRIGHT & DOWLOAD BANG KE SO DU NGAN HANG ---")
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
                prefix='SO_DU_NH',
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
    print(" KHOI CHAY TIEN TRINH DONG BO BANG KE SO DU NGAN HANG (SO_DU_NH)...")
    print(" Vui long quan sat cua so trinh duyet Chrome de xem bot thao tac tren MISA.")
    print("="*80 + "\n")
    
    # Thư mục chứa file tải về để import
    import_dir = os.path.join(settings.BASE_DIR, 'media', 'auto_imports')
    os.makedirs(import_dir, exist_ok=True)
    
    # Định dạng tên file: SO_DU_NH_YYYYMMDD_HHMMSS.xlsx
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    filename = f"SO_DU_NH_{timestamp}.xlsx"
    output_path = os.path.join(import_dir, filename)
    
    # 1. Chạy bước tải báo cáo trong Async Context của Playwright
    download_success = asyncio.run(download_misa_report(output_path))
    if not download_success:
        return

    # 2. Chạy bước nạp dữ liệu (Import) trong Sync Context
    print("\n--- BUOC 2: NAP DU LIEU (IMPORT) SO DU NGAN HANG VAO DATABASE ---")
    from accounting.tasks import auto_import_excel_from_folder
    
    try:
        result_msg = auto_import_excel_from_folder()
        print(f"📊 Ket qua Import: {result_msg}")
    except Exception as e:
        print(f"❌ LOI TRONG QUA TRINH IMPORT: {str(e)}")
        return

    # 3. Tính toán lại hiệu suất (KPI)
    print("\n--- BUOC 3: TINH TOAN LAI KPI & TIEN CUOI KY (CASH BALANCE) ---")
    from accounting.tasks import update_single_bu_performance
    from accounting.models import BusinessUnit, BUPerformance, AccountDetail, BankBalance
    
    today = datetime.now()
    month = today.month
    year = today.year
    reporting_period = f"{year:04d}-{month:02d}"
    
    print(f"Dang chay tinh toan cho toan bo cac BU trong Th{month}/{year}...")
    
    # Tính cho Tổng công ty
    try:
        msg = update_single_bu_performance(bu_id=None, month=month, year=year)
        print(f"✅ Tong cong ty: {msg}")
    except Exception as e:
        print(f"❌ Loi khi tinh cho Tong cong ty: {str(e)}")
        
    # Tính cho từng BU chi tiết
    bus = BusinessUnit.objects.all()
    for bu in bus:
        try:
            msg = update_single_bu_performance(bu_id=bu.id, month=month, year=year)
            print(f"✅ BU {bu.code}: {msg}")
        except Exception as e:
            print(f"❌ Loi khi tinh cho BU {bu.code}: {str(e)}")

    # 4. In kết quả đối chiếu số dư tiền cuối kỳ
    print("\n" + "="*80)
    print(f" SO DU TIEN CUOI KY SAU KHI LOAI TRU TAI KHOAN (Thang {month}/{year}):")
    print("="*80)
    
    # Truy vấn dữ liệu từ sổ chi tiết
    ledger_filter = Q(posting_date__month=month, posting_date__year=year)
    last_111 = AccountDetail.objects.filter(ledger_filter, account_number='111').order_by('posting_date', 'id').last()
    last_112 = AccountDetail.objects.filter(ledger_filter, account_number='112').order_by('posting_date', 'id').last()
    
    cash_bal_111 = last_111.balance_debit if last_111 else 0
    cash_bal_112 = last_112.balance_debit if last_112 else 0
    
    # Số dư các tài khoản loại trừ
    excluded_accs = getattr(settings, 'MISA_EXCLUDED_BANK_ACCOUNTS', ['113611393939'])
    excluded_balances = []
    total_excluded = 0
    for acc in excluded_accs:
        bal_record = BankBalance.objects.filter(reporting_month=reporting_period, bank_account_number=acc).first()
        bal_val = bal_record.balance if bal_record else 0
        excluded_balances.append(f"  - TK {acc}: {bal_val:,.2f} VND")
        total_excluded += bal_val

    # Hiển thị số liệu
    perf_corp = BUPerformance.objects.filter(business_unit__isnull=True, month=month, year=year).first()
    if perf_corp:
        print(f"TỔNG HỢP TOÀN CÔNG TY:")
        print(f"  + Số dư tiền mặt TK 111 (Sổ chi tiết)       : {cash_bal_111:,.2f} VND")
        print(f"  + Số dư tiền gửi ngân hàng TK 112 (Sổ chi tiết): {cash_bal_112:,.2f} VND")
        print(f"  + Tổng số dư ban đầu (111 + 112)           : {cash_bal_111 + cash_bal_112:,.2f} VND")
        print("  + Chi tiết các tài khoản bị loại trừ:")
        for line in excluded_balances:
            print(line)
        print(f"  + Tổng số dư loại trừ                      : -{total_excluded:,.2f} VND")
        print(f"  => Tiền cuối kỳ thực tế sau loại trừ       : {perf_corp.cash_balance_actual:,.2f} VND")
        print("-" * 50)
        
    print("\n" + "="*80)
    print(" DONG BO HOAN TAT THANH CONG!")
    print("="*80 + "\n")

if __name__ == '__main__':
    sys.stdout.reconfigure(encoding='utf-8')
    main()
