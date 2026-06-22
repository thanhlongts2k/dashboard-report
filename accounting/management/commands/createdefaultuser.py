from django.core.management.base import BaseCommand
from django.contrib.auth.models import User

class Command(BaseCommand):
    # Dòng mô tả này sẽ hiện ra khi gõ: python manage.py createdefaultuser --help
    help = 'Tạo nhanh một tài khoản admin mặc định cho dự án Report2026'

    def handle(self, *args, **options):
        import sys
        try:
            sys.stdout.reconfigure(encoding='utf-8')
        except (AttributeError, IOError):
            pass

        username = 'admin'
        email = 'admin@haophuong.com'
        password = '123'

        # Kiểm tra xem tài khoản này đã tồn tại trong DB PostgreSQL chưa
        if not User.objects.filter(username=username).exists():
            # Tạo tài khoản Admin tối cao (Superuser)
            User.objects.create_superuser(
                username=username, 
                email=email, 
                password=password
            )
            self.stdout.write(
                self.style.SUCCESS(f' Chúc mừng bạn! Đã tạo thành công tài khoản: [{username}]')
            )
        else:
            self.stdout.write(
                self.style.WARNING(f'⚠️ Tài khoản [{username}] đã tồn tại trong hệ thống rồi ạ!')
            )