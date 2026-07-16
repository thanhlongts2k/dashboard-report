"""
Script chạy import thủ công một file Excel vào hệ thống.

Cách dùng:
    .venv\Scripts\python.exe run_import.py <đường_dẫn_file>

Ví dụ:
    .venv\Scripts\python.exe run_import.py "media\auto_imports\processed\success\BAN_HANG_20260715.xlsx"
    .venv\Scripts\python.exe run_import.py "D:\Data\BAN_HANG_20260715.xlsx"

Các loại file được hỗ trợ (theo prefix tên file):
    - BAN_HANG_*.xlsx        → Dữ liệu bán hàng
    - KHACH_HANG_*.xlsx      → Danh sách khách hàng
    - MUA_HANG_*.xlsx        → Dữ liệu mua hàng
    - TON_KHO_*.xlsx         → Tồn kho
    - CONG_NO_NCC_*.xlsx     → Công nợ nhà cung cấp
    - TUOI_NO_KH_*.xlsx      → Tuổi nợ khách hàng
    - TAI_KHOAN_CT_*.xlsx    → Sổ chi tiết tài khoản

Sau khi import thành công, hệ thống sẽ tự động:
    1. Tính toán lại KPI cho tất cả các Business Unit
    2. Đồng bộ dữ liệu tồn kho Warehouse
"""

import os
import sys

# Reconfigure stdout to use UTF-8 encoding on Windows terminals
sys.stdout.reconfigure(encoding='utf-8')

# Setup Django Environment TRƯỚC KHI import bất kỳ module nào của Django
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'report2026.settings')

import django
django.setup()

from import_specific_file import import_file


def main():
    if len(sys.argv) < 2:
        print("=" * 60)
        print("❌ LỖI: Chưa cung cấp đường dẫn file!")
        print("=" * 60)
        print()
        print("Cách dùng:")
        print('  .venv\\Scripts\\python.exe run_import.py "<đường_dẫn_file>"')
        print()
        print("Ví dụ:")
        print('  .venv\\Scripts\\python.exe run_import.py "media\\auto_imports\\BAN_HANG_20260715.xlsx"')
        sys.exit(1)

    file_path = sys.argv[1]

    # Nếu là đường dẫn tương đối, resolve theo thư mục gốc của project
    if not os.path.isabs(file_path):
        project_root = os.path.dirname(os.path.abspath(__file__))
        file_path = os.path.join(project_root, file_path)

    file_path = os.path.normpath(file_path)

    print("=" * 60)
    print(f"📂 File: {file_path}")
    print("=" * 60)

    if not os.path.exists(file_path):
        print(f"❌ Không tìm thấy file: {file_path}")
        sys.exit(1)

    import_file(file_path)


if __name__ == '__main__':
    main()
