#!/usr/bin/env python
"""Django's command-line utility for administrative tasks."""
import os
import sys


def start_background_services():
    """Tự động khởi chạy Redis Server, Celery Worker và Celery Beat khi chạy lệnh runserver."""
    if len(sys.argv) > 1 and sys.argv[1] == 'runserver':
        if os.environ.get('RUN_MAIN') != 'true':
            import subprocess
            import atexit
            
            processes = []
            try:
                # Windows flag để tạo cửa sổ terminal độc lập mới
                CREATE_NEW_CONSOLE = 0x00000010

                # Lấy cấu hình Redis Server từ settings.py
                try:
                    from report2026.settings import REDIS_SERVER_PATH
                except Exception:
                    REDIS_SERVER_PATH = None
                
                # 1. Tự động khởi chạy Redis Server
                if REDIS_SERVER_PATH and os.path.exists(REDIS_SERVER_PATH):
                    print(f"🚀 Đang khởi động Redis Server tại {REDIS_SERVER_PATH}...")
                    redis_p = subprocess.Popen(
                        [REDIS_SERVER_PATH],
                        creationflags=CREATE_NEW_CONSOLE
                    )
                    processes.append(redis_p)
                elif REDIS_SERVER_PATH:
                    print(f"⚠️ Cấu hình REDIS_SERVER_PATH không tồn tại trên đĩa: {REDIS_SERVER_PATH}")
                
                # 2. Khởi động Celery Worker
                print("🚀 Đang khởi động Celery Worker...")
                worker_p = subprocess.Popen(
                    ['.venv/Scripts/celery', '-A', 'report2026', 'worker', '--loglevel=info', '-P', 'solo'],
                    creationflags=CREATE_NEW_CONSOLE
                )
                processes.append(worker_p)
                
                # 3. Khởi động Celery Beat
                print("🚀 Đang khởi động Celery Beat...")
                beat_p = subprocess.Popen(
                    ['.venv/Scripts/celery', '-A', 'report2026', 'beat', '--loglevel=info'],
                    creationflags=CREATE_NEW_CONSOLE
                )
                processes.append(beat_p)
                
                def cleanup_services():
                    print("\n🛑 Đang tự động tắt các tiến trình Celery & Redis...")
                    for p in processes:
                        try:
                            p.terminate()
                            # Chờ tối đa 3 giây để đóng tiến trình
                            p.wait(timeout=3)
                        except Exception:
                            try:
                                p.kill()
                            except Exception:
                                pass
                    print("✅ Đã đóng toàn bộ terminal Celery & Redis.")
                
                # Đăng ký dọn dẹp khi dừng django server (Ctrl+C hoặc tắt)
                atexit.register(cleanup_services)
                
            except Exception as e:
                print(f"⚠️ Không thể tự động khởi chạy Celery & Redis: {e}")


def main():
    """Run administrative tasks."""
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'report2026.settings')
    
    # Khởi chạy các dịch vụ nền (Redis, Celery) nếu chạy lệnh runserver
    start_background_services()

    try:
        from django.core.management import execute_from_command_line
    except ImportError as exc:
        raise ImportError(
            "Couldn't import Django. Are you sure it's installed and "
            "available on your PYTHONPATH environment variable? Did you "
            "forget to activate a virtual environment?"
        ) from exc
    execute_from_command_line(sys.argv)


if __name__ == '__main__':
    main()
