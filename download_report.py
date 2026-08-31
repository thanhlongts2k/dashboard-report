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

from accounting.misa.automation import run_misa_automation

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
    'TUOI_NO_KH': 'Báo cáo Tuổi nợ khách hàng (gộp 131 & 1311)',
    'TAI_KHOAN_CT': 'Báo cáo Sổ chi tiết các tài khoản (111, 112, 341, 641, 642)',
    'SO_DU_NH': 'Báo cáo Bảng kê số dư ngân hàng',
    'DANH_SACH_KHACH_HANG': 'Danh mục Khách hàng (Master Data)',
    'DANH_SACH_NHAN_VIEN': 'Danh mục Nhân viên (Master Data)',
    'KHACH_HANG': 'Danh mục Khách hàng (Master Data)',
    'NHAN_VIEN': 'Danh mục Nhân viên (Master Data)',
}

async def download_single(prefix, period=None, use_saved_reports=None):
    prefix = prefix.upper().strip()
    valid_prefixes = list(REPORT_KEYWORDS.keys()) + ['ALL']
    if prefix not in valid_prefixes:
        print(f"\n❌ LỖI: Keyword '{prefix}' không hợp lệ!")
        print(f"Các keyword được hỗ trợ: {list(REPORT_KEYWORDS.keys())} hoặc ALL")
        return False

    prefix_filter = None if prefix == 'ALL' else prefix
    logger.info(f"Bắt đầu tải báo cáo: prefix='{prefix}', period='{period}', use_saved_reports={use_saved_reports}")
    
    result = await run_misa_automation(
        period_option=period,
        prefix_filter=prefix_filter,
        use_saved_reports=use_saved_reports
    )
    logger.info(f"Kết quả: {result}")
    return "SUCCESS" in result

def main():
    parser = argparse.ArgumentParser(description="Script tải báo cáo MISA linh hoạt theo keyword, kỳ và mẫu đã lưu.")
    parser.add_argument(
        'keyword',
        type=str,
        nargs='?',
        default='ALL',
        help='Keyword loại báo cáo: BAN_HANG, MUA_HANG, TON_KHO, CONG_NO_NCC, TUOI_NO_KH, TAI_KHOAN_CT, SO_DU_NH hoặc ALL'
    )
    parser.add_argument(
        '--period',
        type=str,
        default=None,
        help='Kỳ báo cáo chọn (ví dụ: "Tháng trước", "Tháng này", "Tháng 7", "Năm nay" - mặc định lấy từ settings)'
    )
    parser.add_argument(
        '--use-saved-reports',
        action='store_true',
        default=None,
        help='Ép sử dụng mẫu báo cáo đã lưu (Option 2) kết hợp đổi kỳ'
    )
    parser.add_argument(
        '--no-saved-reports',
        dest='use_saved_reports',
        action='store_false',
        help='Ép sử dụng luồng URL động từng bước (Option 1)'
    )

    args = parser.parse_args()
    asyncio.run(download_single(args.keyword, args.period, args.use_saved_reports))

if __name__ == '__main__':
    main()
