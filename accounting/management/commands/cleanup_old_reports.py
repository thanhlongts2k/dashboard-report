from django.core.management.base import BaseCommand
from accounting.tasks import cleanup_old_reports


class Command(BaseCommand):
    help = 'Dọn dẹp các tệp Excel báo cáo MISA cũ tồn đọng (>30 ngày trong success, >15 ngày trong temp/failed)'

    def add_arguments(self, parser):
        parser.add_argument('--days-success', type=int, default=30, help='Số ngày tối đa giữ file success (mặc định: 30)')
        parser.add_argument('--days-temp', type=int, default=15, help='Số ngày tối đa giữ file temp/failed (mặc định: 15)')

    def handle(self, *args, **options):
        days_success = options['days_success']
        days_temp = options['days_temp']
        self.stdout.write(self.style.NOTICE(f'Bắt đầu dọn dẹp báo cáo cũ (success > {days_success} ngày, temp > {days_temp} ngày)...'))
        result = cleanup_old_reports(days_success=days_success, days_temp=days_temp)
        if result.get('status') == 'success':
            self.stdout.write(self.style.SUCCESS(f"Hoàn tất: {result.get('message')}"))
            for f in result.get('deleted_files', []):
                self.stdout.write(f" - Đã xóa: {f}")
        else:
            self.stdout.write(self.style.WARNING(result.get('message', 'Đã bỏ qua.')))
