import os
from celery import Celery

# Thiết lập module settings mặc định cho celery
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'report2026.settings')

app = Celery('report2026')

# Sử dụng chuỗi cấu hình từ settings.py với tiền tố CELERY_
app.config_from_object('django.conf:settings', namespace='CELERY')

# Tự động tìm tasks.py trong tất cả các app
app.autodiscover_tasks()