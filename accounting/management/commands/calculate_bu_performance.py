# Cú pháp chạy tại Terminal:
#   .venv\Scripts\python.exe manage.py calculate_bu_performance --bu_id 70 --month 6 --year 2026
#
# (Hoặc không truyền month/year để tính cho tháng hiện tại):
#   .venv\Scripts\python.exe manage.py calculate_bu_performance --bu_id 70

import sys
from django.core.management.base import BaseCommand
from datetime import datetime
from accounting.tasks import update_single_bu_performance
from accounting.models import BusinessUnit

class Command(BaseCommand):
    help = 'Tinh toan chi so hieu suat MTD, YTD va Daily cho mot Don vi Kinh doanh (BU)'

    def add_arguments(self, parser):
        parser.add_argument('--bu_id', type=int, required=True, help='ID cua Don vi Kinh doanh can tinh toan')
        parser.add_argument('--month', type=int, help='Thang can tinh toan (1-12)')
        parser.add_argument('--year', type=int, help='Nam can tinh toan (YYYY)')

    def handle(self, *args, **options):
        # Reconfigure sys.stdout for Windows console UTF-8 support
        try:
            sys.stdout.reconfigure(encoding='utf-8')
        except Exception:
            pass

        bu_id = options.get('bu_id')
        month = options.get('month')
        year = options.get('year')
        
        bu = BusinessUnit.objects.filter(id=bu_id).first()
        if not bu:
            self.stdout.write(self.style.ERROR(f"Loi: Khong tim thay Business Unit voi ID = {bu_id}"))
            return

        today = datetime.now()
        calc_month = month if month else today.month
        calc_year = year if year else today.year
        
        bu_name_safe = bu.code
        self.stdout.write(self.style.WARNING(f"Dang tinh toan hieu suat cho BU [{bu_name_safe}] ky: {calc_month}/{calc_year}..."))
        
        try:
            result = update_single_bu_performance(
                bu_id=bu_id,
                month=calc_month,
                year=calc_year
            )
            self.stdout.write(self.style.SUCCESS(f"Thanh cong: {result}"))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"That bai: {str(e)}"))
