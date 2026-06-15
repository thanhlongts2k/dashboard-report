#!/usr/bin/env python
"""Django's command-line utility for administrative tasks."""
import os
import sys


def main():
    """Run administrative tasks."""
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'report2026.settings')
    
    # Tự động chạy Celery Worker và Beat khi khởi động runserver
    if len(sys.argv) > 1 and sys.argv[1] == 'runserver':
        if os.environ.get('RUN_MAIN') != 'true':
            import subprocess
            import atexit
            
            processes = []
            try:
                # Windows flag để tạo cửa sổ terminal độc lập mới
                CREATE_NEW_CONSOLE = 0x00000010
                
                print("🚀 Đang khởi động Celery Worker...")
                worker_p = subprocess.Popen(
                    ['.venv/Scripts/celery', '-A', 'report2026', 'worker', '--loglevel=info', '-P', 'solo'],
                    creationflags=CREATE_NEW_CONSOLE
                )
                processes.append(worker_p)
                
                print("🚀 Đang khởi động Celery Beat...")
                beat_p = subprocess.Popen(
                    ['.venv/Scripts/celery', '-A', 'report2026', 'beat', '--loglevel=info'],
                    creationflags=CREATE_NEW_CONSOLE
                )
                processes.append(beat_p)
                
                def cleanup_celery():
                    print("\n🛑 Đang tự động tắt các tiến trình Celery...")
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
                    print("✅ Đã đóng toàn bộ terminal Celery.")
                
                # Đăng ký dọn dẹp khi dừng django server (Ctrl+C hoặc tắt)
                atexit.register(cleanup_celery)
                
            except Exception as e:
                print(f"⚠️ Không thể tự động khởi chạy Celery: {e}")

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
