import os
import sys
import argparse
import asyncio
import logging
from datetime import datetime

# Enforce UTF-8 output encoding for Windows terminal compatibility
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')
if hasattr(sys.stderr, 'reconfigure'):
    sys.stderr.reconfigure(encoding='utf-8')

# Setup Django Environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'report2026.settings')
import django
django.setup()

from django.conf import settings
from playwright.async_api import async_playwright
from accounting.misa.browser import login_to_misa, close_misa_popups
from accounting.misa.report_exporter import download_report_from_url

logging.basicConfig(
    level=logging.INFO,
    format='[%(asctime)s: %(levelname)s/%(name)s] %(message)s'
)
logger = logging.getLogger("download_report")

REPORT_KEYWORDS = {
    'BAN_HANG': 'Báo cáo Sổ chi tiết bán hàng',
    'MUA_HANG': 'Báo cáo Sổ chi tiết mua hàng',
    'TON_KHO': 'Báo cáo Tổng hợp tồn kho',
    'CONG_NO_NCC': 'Báo cáo Phải trả nhà cung cấp',
    'TUOI_NO_KH': 'Báo cáo Tuổi nợ khách hàng',
    'TAI_KHOAN_CT': 'Báo cáo Sổ chi tiết các tài khoản (111, 112, 341, 641, 642)',
    'SO_DU_NH': 'Báo cáo Bảng kê số dư ngân hàng',
}

async def download_single(prefix, period=None):
    prefix = prefix.upper().strip()
    valid_prefixes = list(settings.MISA_REPORTS.keys())
    if prefix != 'ALL' and prefix not in valid_prefixes:
        print(f"\n❌ LỖI: Keyword '{prefix}' không hợp lệ!")
        print(f"Các keyword được hỗ trợ: {valid_prefixes} hoặc ALL")
        return False

    email = settings.MISA_EMAIL
    password = settings.MISA_PASSWORD
    headless = settings.MISA_HEADLESS
    
    if not email or not password:
        logger.error("MISA_EMAIL và MISA_PASSWORD chưa được cấu hình trong settings/.env")
        return False

    auto_imports_dir = os.path.join(settings.BASE_DIR, 'media', 'auto_imports')
    os.makedirs(auto_imports_dir, exist_ok=True)
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')

    prefixes_to_download = valid_prefixes if prefix == 'ALL' else [prefix]

    async with async_playwright() as p:
        channel = getattr(settings, 'MISA_BROWSER_CHANNEL', 'chrome')
        logger.info(f"Khởi tạo trình duyệt Playwright (headless={headless}, channel={channel})...")
        try:
            browser = await p.chromium.launch(headless=headless, channel=channel)
        except Exception:
            browser = await p.chromium.launch(headless=headless)

        context = None
        state_path = settings.MISA_BROWSER_STATE_PATH
        if os.path.exists(state_path):
            try:
                context = await browser.new_context(
                    storage_state=state_path,
                    viewport={'width': 1366, 'height': 768},
                    user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
                )
            except Exception:
                context = await browser.new_context(viewport={'width': 1366, 'height': 768})
        else:
            context = await browser.new_context(viewport={'width': 1366, 'height': 768})

        context.set_default_timeout(30000)
        page = await context.new_page()

        # Login verification
        logger.info("Kiểm tra phiên đăng nhập MISA...")
        await page.goto("https://actapp.misa.vn/", timeout=30000, wait_until="load")
        await asyncio.sleep(2)
        if "login" in page.url or "sso" in page.url or "id.misa.vn" in page.url:
            logger.info("Phiên làm việc hết hạn. Tiến hành đăng nhập lại...")
            await login_to_misa(page, context, email, password)

        success_count = 0
        for current_prefix in prefixes_to_download:
            url = settings.MISA_REPORTS.get(current_prefix)
            if not url:
                logger.warning(f"URL cho báo cáo '{current_prefix}' chưa được cấu hình trong MISA_REPORTS.")
                continue

            filename = f"{current_prefix}_{timestamp}.xlsx"
            output_path = os.path.join(auto_imports_dir, filename)
            desc = REPORT_KEYWORDS.get(current_prefix, current_prefix)
            logger.info(f"\n==========================================")
            logger.info(f"🚀 Đang tải báo cáo: [{current_prefix}] - {desc}")
            logger.info(f"Target File: {output_path}")
            logger.info(f"==========================================")

            success = await download_report_from_url(
                page,
                url,
                settings.MISA_EXPORT_SELECTOR,
                output_path,
                prefix=current_prefix,
                skip_parameters=False,
                period_option=period
            )

            if success and os.path.exists(output_path):
                sz = os.path.getsize(output_path)
                logger.info(f"✅ THÀNH CÔNG: Đã tải báo cáo [{current_prefix}] ({sz:,} bytes) lưu tại {output_path}")
                success_count += 1
            else:
                logger.error(f"❌ THẤT BẠI: Không thể tải báo cáo [{current_prefix}]")

        await browser.close()
        return success_count > 0

def main():
    parser = argparse.ArgumentParser(description="Script tải riêng từng báo cáo MISA theo keyword.")
    parser.add_argument(
        'keyword',
        type=str,
        help='Keyword loại báo cáo: BAN_HANG, MUA_HANG, TON_KHO, CONG_NO_NCC, TUOI_NO_KH, TAI_KHOAN_CT, SO_DU_NH hoặc ALL'
    )
    parser.add_argument(
        '--period',
        type=str,
        default=None,
        help='Kỳ báo cáo chọn (mặc định lấy từ settings: "Tháng này" hoặc "Năm nay")'
    )

    args = parser.parse_args()
    asyncio.run(download_single(args.keyword, args.period))

if __name__ == '__main__':
    main()
