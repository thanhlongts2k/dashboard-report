import os
import asyncio
import logging
from django.core.management.base import BaseCommand
from django.conf import settings
from accounting.misa import run_misa_automation
from accounting.tasks import auto_import_excel_from_folder
from accounting.services import detect_period_from_filename

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = "Đồng bộ dữ liệu MISA: Tải báo cáo Excel qua Playwright, nạp vào CSDL và cập nhật KPI cho các BU."

    def add_arguments(self, parser):
        parser.add_argument(
            '--action',
            type=str,
            default='all',
            choices=['all', 'download', 'import'],
            help='Hành động cần thực thi: all (tải + nạp), download (chỉ tải), import (chỉ nạp).'
        )
        parser.add_argument(
            '--prefix',
            type=str,
            default=None,
            help='Tiền tố báo cáo MISA cụ thể (ví dụ: SO_DU_NH, TAI_KHOAN_CT, BAN_HANG, MUA_HANG, TON_KHO...)'
        )
        parser.add_argument(
            '--period',
            type=str,
            default=None,
            help='Kỳ báo cáo (ví dụ: 2026-06 hoặc "Tháng này")'
        )
        parser.add_argument(
            '--file',
            type=str,
            default=None,
            help='Đường dẫn tệp Excel cụ thể cần nạp trực tiếp vào cơ sở dữ liệu'
        )

    def handle(self, *args, **options):
        action = options['action']
        prefix = options['prefix']
        period = options['period']
        file_path = options['file']

        self.stdout.write(self.style.SUCCESS(f"🚀 Bắt đầu thực thi sync_misa: action={action}, prefix={prefix}, period={period}"))

        if file_path:
            if not os.path.exists(file_path):
                self.stderr.write(self.style.ERROR(f"❌ Không tìm thấy tệp: {file_path}"))
                return
            self.stdout.write(self.style.SUCCESS(f"📦 Đang nạp trực tiếp tệp: {file_path}"))
            res = auto_import_excel_from_folder(specific_file=os.path.abspath(file_path))
            self.stdout.write(self.style.SUCCESS(f"✅ Hoàn tất nạp tệp: {res}"))
            return

        # 1. Tải báo cáo từ MISA Web qua Playwright (nếu action is 'all' or 'download')
        if action in ['all', 'download']:
            self.stdout.write(self.style.WARNING("📥 Đang kích hoạt Playwright tự động tải báo cáo từ MISA Web..."))
            try:
                loop = asyncio.get_event_loop()
            except RuntimeError:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                
            try:
                download_res = loop.run_until_complete(run_misa_automation(period_option=period, prefix_filter=prefix))
                self.stdout.write(self.style.SUCCESS(f"✅ Kết quả tải MISA: {download_res}"))
            except Exception as e:
                self.stderr.write(self.style.ERROR(f"❌ Lỗi khi tải báo cáo MISA: {str(e)}"))
                if action == 'download':
                    return

        # 2. Nạp dữ liệu từ tệp Excel vào CSDL (nếu action is 'all' or 'import')
        if action in ['all', 'import']:
            self.stdout.write(self.style.WARNING("📊 Đang đọc và nạp các tệp Excel từ media/auto_imports vào cơ sở dữ liệu..."))
            try:
                import_res = auto_import_excel_from_folder()
                self.stdout.write(self.style.SUCCESS(f"✅ Kết quả nạp CSDL & Cập nhật KPI:\n{import_res}"))
            except Exception as e:
                self.stderr.write(self.style.ERROR(f"❌ Lỗi khi nạp dữ liệu CSDL: {str(e)}"))

        self.stdout.write(self.style.SUCCESS("🎉 Hoàn tất lệnh sync_misa thành công!"))
