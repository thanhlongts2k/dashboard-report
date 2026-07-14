# Cú pháp chạy tại Terminal:
#   .venv\Scripts\python.exe manage.py calculate_global_performance --month 6 --year 2026
#
# (Hoặc không truyền tham số để tính cho tháng hiện tại):
#   .venv\Scripts\python.exe manage.py calculate_global_performance

import sys
from django.core.management.base import BaseCommand
from datetime import datetime
from accounting.tasks import update_single_bu_performance

class Command(BaseCommand):
    help = 'Tinh toan chi so hieu suat MTD, YTD va Daily cho toan Tong cong ty (Global)'

    def add_arguments(self, parser):
        parser.add_argument('--month', type=int, help='Thang can tinh toan (1-12)')
        parser.add_argument('--year', type=int, help='Nam can tinh toan (YYYY)')

    def handle(self, *args, **options):
        # Reconfigure sys.stdout for Windows console UTF-8 support
        try:
            sys.stdout.reconfigure(encoding='utf-8')
        except Exception:
            pass

        month = options.get('month')
        year = options.get('year')
        
        today = datetime.now()
        calc_month = month if month else today.month
        calc_year = year if year else today.year
        
        self.stdout.write(self.style.WARNING(f"Dang tinh toan hieu suat GLOBAL cho ky: {calc_month}/{calc_year}..."))
        
        try:
            result = update_single_bu_performance(
                bu_id=None,
                month=calc_month,
                year=calc_year
            )
            self.stdout.write(self.style.SUCCESS(f"Thanh cong: {result}"))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"That bai: {str(e)}"))
