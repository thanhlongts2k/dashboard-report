import os
import sys
import django
import asyncio
import logging

logging.basicConfig(
    level=logging.INFO,
    format='[%(asctime)s: %(levelname)s/%(name)s] %(message)s'
)

# Setup Django Environment
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_ROOT)
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'report2026.settings')
django.setup()

from django.conf import settings
from playwright.async_api import async_playwright
from datetime import datetime
from accounting.misa_tasks import download_report_from_url, login_to_misa

async def test_download():
    email = settings.MISA_EMAIL
    password = settings.MISA_PASSWORD
    url = settings.MISA_REPORTS.get('BAN_HANG')
    
    if not url:
        print("ERROR: MISA_URL_BAN_HANG is not configured in settings/env.")
        return
        
    print(f"Using Email: {email}")
    print(f"Target URL: {url}")
    
    auto_imports_dir = os.path.join(settings.BASE_DIR, 'media', 'auto_imports')
    os.makedirs(auto_imports_dir, exist_ok=True)
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    filename = f"BAN_HANG_TEST_{timestamp}.xlsx"
    output_path = os.path.join(auto_imports_dir, filename)
    
    async with async_playwright() as p:
        channel = getattr(settings, 'MISA_BROWSER_CHANNEL', 'chrome')
        # Run non-headless so you can watch the automation interact with the browser
        headless = False
        print(f"Launching browser (headless={headless}, channel={channel})...")
        
        browser = await p.chromium.launch(headless=headless, channel=channel)
        
        if os.path.exists(settings.MISA_BROWSER_STATE_PATH):
            print("Loading existing browser session state...")
            context = await browser.new_context(
                storage_state=settings.MISA_BROWSER_STATE_PATH,
                viewport={"width": 1280, "height": 800}
            )
        else:
            print("No session state found, starting fresh context...")
            context = await browser.new_context(viewport={"width": 1280, "height": 800})
            
        page = await context.new_page()
        
        # Test navigation to verify if we are logged in
        print("Checking if we are already logged in...")
        try:
            await page.goto(url, timeout=20000, wait_until="load")
            if "login" in page.url or "sso" in page.url or "id.misa.vn" in page.url or "amisapp.misa.vn/login" in page.url:
                print("Redirected to login. Performing login...")
                await login_to_misa(page, context, email, password)
            else:
                print("Already logged in.")
        except Exception as e:
            print(f"Verification timed out or failed, performing login: {e}")
            await login_to_misa(page, context, email, password)
            
        print(f"Starting download to: {output_path}")
        success = await download_report_from_url(page, url, settings.MISA_EXPORT_SELECTOR, output_path, prefix='BAN_HANG')
        
        await browser.close()

        if success:
            print(f"SUCCESS: Report downloaded and saved to: {output_path}")
            print("------------------------------------------------------------")
            print("🚀 BẮT ĐẦU IMPORT VÀ CẬP NHẬT DỮ LIỆU KPI...")
            print("------------------------------------------------------------")
            from asgiref.sync import sync_to_async
            from import_specific_file import import_file
            await sync_to_async(import_file)(output_path)
            print("------------------------------------------------------------")
            print("✅ QUÁ TRÌNH IMPORT VÀ UPDATE KPI HOÀN TẤT!")
            print("------------------------------------------------------------")
        else:
            print("FAILED to download report.")

if __name__ == '__main__':
    import sys
    if hasattr(sys.stdout, 'reconfigure'):
        try:
            sys.stdout.reconfigure(encoding='utf-8')
        except Exception:
            pass
    asyncio.run(test_download())
