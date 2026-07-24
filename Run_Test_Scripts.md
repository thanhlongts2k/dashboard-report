# Tài liệu Hướng dẫn Chạy Terminal và Test Scripts

Tài liệu này tổng hợp chi tiết hướng dẫn thiết lập môi trường, cấu hình dịch vụ, khởi chạy máy chủ phát triển và danh sách toàn bộ các tệp script kiểm thử / lệnh quản trị terminal trong dự án **Report2026**.

---

## 1. Hướng dẫn Thiết lập & Khởi chạy Hệ thống

### Bước 0: Khởi tạo file cấu hình môi trường `.env`
Hệ thống sử dụng thư viện `django-environ` để bảo mật và tách cấu hình cơ sở dữ liệu khỏi mã nguồn.
1. Tạo một tệp tin tên `.env` ở thư mục gốc của dự án (cùng cấp với thư mục `report2026/` và tệp `manage.py`).
2. Nhập các thông tin kết nối database tương ứng của máy bạn và cấu hình chu kỳ chạy Celery Beat nếu cần:
   ```env
   # 1. Cấu hình cơ sở dữ liệu
   DB_NAME=reportdb
   DB_USER=postgres
   DB_PASSWORD=your_password
   DB_HOST=localhost
   DB_PORT=5433

   # 2. Cấu hình chu kỳ tự động chạy nạp Excel của Celery Beat
   # Hỗ trợ các kiểu: daily (mặc định), weekly, monthly, custom (cron tùy chọn)
   IMPORT_SCHEDULE_TYPE=daily
   IMPORT_SCHEDULE_HOUR=7
   IMPORT_SCHEDULE_MINUTE=0
   
   # Thứ trong tuần (0-6 tương ứng CN-T7, áp dụng khi IMPORT_SCHEDULE_TYPE=weekly)
   IMPORT_SCHEDULE_DAY_OF_WEEK=1
   
   # Ngày trong tháng (1-31, áp dụng khi IMPORT_SCHEDULE_TYPE=monthly)
   IMPORT_SCHEDULE_DAY_OF_MONTH=1
   
   # Cron tùy chỉnh (áp dụng khi IMPORT_SCHEDULE_TYPE=custom)
   IMPORT_SCHEDULE_CRON=0 7 * * *

   # 3. Cấu hình tự động tải báo cáo từ MISA AMIS (Sử dụng Playwright)
   MISA_AMIS_LOGIN_URL=https://act.amis.vn/
   MISA_EMAIL=your_misa_email@example.com
   MISA_PASSWORD=your_misa_password
   MISA_HEADLESS=True
   MISA_EXPORT_SELECTOR="button:has-text('Xuất khẩu')"
   
   # Lựa chọn cơ chế tải báo cáo MISA:
   # 1: Xuất từng bước (Mặc định - Bot tự chọn tham số và click xuất)
   # 2: Tải từ danh sách báo cáo đã lưu (Saved Reports) để tối ưu thời gian chọn tham số
   USE_OPTION_EXPORT_REPORT_MISA=1
   MISA_URL_REPORT_SAVED=https://actapp.misa.vn/app/RP/ReportSavedList
   
   # URL của các báo cáo MISA cụ thể cần tải tự động
   MISA_URL_BAN_HANG=https://act.amis.vn/report/sales-detail
   MISA_URL_MUA_HANG=https://act.amis.vn/report/purchase-detail
   MISA_URL_TON_KHO=https://act.amis.vn/report/inventory-summary
   MISA_URL_CONG_NO_NCC=https://act.amis.vn/report/supplier-debt
   MISA_URL_TUOI_NO_KH=https://act.amis.vn/report/receivables-ageing
   MISA_URL_TAI_KHOAN_CT=https://act.amis.vn/report/account-detail
   ```
*(Lưu ý: Tệp `.env` đã được tự động thêm vào `.gitignore` để tránh đẩy thông tin nhạy cảm lên Git).*

### Bước 0.5: Cài đặt các thư viện Python cần thiết
Trước khi khởi chạy hệ thống lần đầu, bạn cần cài đặt toàn bộ các thư viện được định nghĩa sẵn trong dự án:
1. Đảm bảo môi trường ảo (Virtual Environment) đã được kích hoạt.
2. Chạy lệnh cài đặt:
   ```powershell
   pip install -r requirements.txt
   ```

### Bước 0.6: Cài đặt Driver trình duyệt cho Playwright (Bắt buộc cho tác vụ MISA)
Tác vụ tự động hóa MISA sử dụng Playwright để điều khiển Chromium. Bạn cần tải về driver trình duyệt:
1. Đảm bảo môi trường ảo đã được kích hoạt.
2. Chạy lệnh:
   ```powershell
   playwright install chromium
   ```

### Bước 1: Cấu hình và Tự động khởi động Redis Server
Hệ thống hỗ trợ tự động khởi chạy Redis Server cùng lúc với Django Web Server.
1. Mở file [settings.py](file:///d:/Sources/dashboard-report/report2026/settings.py#L172) và cấu hình đường dẫn tới file chạy Redis trên máy của bạn:
   ```python
   REDIS_SERVER_PATH = r"d:\downloads\redis-x64-5.0.14.1\redis-server.exe"
   ```
2. Khi khởi chạy lệnh ở Bước 2, hệ thống sẽ tự động kiểm tra và bật cửa sổ Redis Server chạy song song mà bạn không cần mở thủ công.

> [!IMPORTANT]
> **Khuyến nghị tương thích**: Redis chạy trên Windows thường là phiên bản cũ (v5.0.x). Do đó, thư viện kết nối Python trong môi trường ảo `.venv` bắt buộc phải sử dụng phiên bản `redis==4.6.0`. (Phiên bản `redis >= 5.x` sử dụng giao thức RESP3 sẽ gây lỗi `unknown command 'HELLO'`).

### Bước 2: Chạy Server phát triển (Development Server) & Celery + Redis tự động
Chạy máy chủ web Django thông thường trong môi trường ảo:
```powershell
py manage.py runserver
```

> [!TIP]
> **Tự động hóa hoàn toàn**: Chúng ta đã tích hợp mã nguồn quản lý trực tiếp vào [manage.py](file:///d:/Sources/dashboard-report/manage.py). Khi chạy lệnh `runserver` ở trên:
> 1. Django sẽ **tự động khởi chạy Redis Server, Celery Worker và Celery Beat** trong các cửa sổ terminal độc lập hoàn toàn tự động.
> 2. Cơ chế thông minh đảm bảo các dịch vụ chỉ mở đúng 1 bản duy nhất mỗi lần khởi chạy server (không bị lặp lại do `auto-reloader`).
> 3. **Tự động dọn dẹp khi dừng server**: Khi bạn nhấn `Ctrl + C` để dừng `runserver`, Django sẽ tự động gửi lệnh kết thúc và **đóng hoàn toàn tất cả các cửa sổ terminal Celery & Redis** đang chạy, tránh rác tiến trình chạy ngầm trên Windows.

---

## 2. Danh sách Django Custom Management Commands

Hệ thống cung cấp các câu lệnh quản trị tiêu chuẩn gọi qua `python manage.py <command_name>`:

### 2.1. Lệnh Đồng bộ MISA toàn diện (`sync_misa`)
* **File nguồn**: [accounting/management/commands/sync_misa.py](file:///d:/Sources/dashboard-report/accounting/management/commands/sync_misa.py)
* **Tác dụng**: Lệnh chuyên trách chạy tự động hóa MISA Playwright, nạp file Excel vào CSDL và cập nhật KPI cho tất cả các Business Unit.
* **Cú pháp sử dụng**:
  ```powershell
  # Chạy toàn bộ (Tải MISA Web -> Nạp CSDL -> Cập nhật KPI)
  python manage.py sync_misa

  # Chỉ tải báo cáo Excel từ MISA Web
  python manage.py sync_misa --action=download

  # Chỉ nạp tệp Excel từ media/auto_imports/ vào cơ sở dữ liệu
  python manage.py sync_misa --action=import

  # Chỉ định kỳ báo cáo cụ thể
  python manage.py sync_misa --period="Tháng này"

  # Nạp trực tiếp 1 tệp Excel chỉ định
  python manage.py sync_misa --file="media/auto_imports/BAN_HANG_202606.xlsx"
  ```

### 2.2. Lệnh Tính KPI cho BU chỉ định (`calculate_bu_performance`)
* **File nguồn**: `accounting/management/commands/calculate_bu_performance.py`
* **Tác dụng**: Tính toán và cập nhật lại chỉ số KPI MTD/YTD cho một Business Unit cụ thể trong tháng/năm chỉ định.
* **Cú pháp sử dụng**:
  ```powershell
  python manage.py calculate_bu_performance --bu_id=1 --month=6 --year=2026
  ```

### 2.3. Lệnh Tính KPI Tổng công ty (`calculate_global_performance`)
* **File nguồn**: `accounting/management/commands/calculate_global_performance.py`
* **Tác dụng**: Tính toán lại chỉ số KPI tích lũy cấp Tổng công ty (Global).
* **Cú pháp sử dụng**:
  ```powershell
  python manage.py calculate_global_performance --month=6 --year=2026
  ```

### 2.4. Lệnh Khởi tạo Superuser Mặc định (`createdefaultuser`)
* **File nguồn**: `accounting/management/commands/createdefaultuser.py`
* **Tác dụng**: Tạo nhanh tài khoản admin/superuser mặc định (`admin`/`123`) khi cài đặt lại DB.
* **Cú pháp sử dụng**:
  ```powershell
  python manage.py createdefaultuser
  ```

---

## 3. Danh sách Helper & Test Scripts

Các script kiểm thử độc lập và bảo trì dữ liệu đặt tại thư mục gốc và thư mục `scripts/`:

### 3.1. Script Tải thử nghiệm Bán hàng MISA (`test_download_ban_hang.py`)
* **File nguồn**: [test_download_ban_hang.py](file:///d:/Sources/dashboard-report/test_download_ban_hang.py)
* **Tác dụng**: Chạy tải thử nghiệm báo cáo Bán hàng (`BAN_HANG`) từ MISA ở chế độ có giao diện (`headless=False`) để lập trình viên trực quan sát quá trình tương tác và xử lý tắt popup.
* **Cú pháp sử dụng**:
  ```powershell
  .venv\Scripts\python.exe test_download_ban_hang.py
  ```

### 3.2. Script Import File Excel Chỉ định (`import_specific_file.py`)
* **File nguồn**: [import_specific_file.py](file:///d:/Sources/dashboard-report/import_specific_file.py)
* **Tác dụng**: Import thủ công một file Excel bất kỳ trong thư mục `media/auto_imports/`.
* **Cú pháp sử dụng**:
  ```powershell
  # Xem danh sách file đang chờ import
  .venv\Scripts\python.exe import_specific_file.py

  # Nạp file cụ thể
  .venv\Scripts\python.exe import_specific_file.py BAN_HANG_202606.xlsx
  ```

### 3.3. Script Nạp lại dữ liệu 7 tháng năm 2026 (`scripts/reimport_months_1_to_7.py`)
* **File nguồn**: `scripts/reimport_months_1_to_7.py`
* **Tác dụng**: Làm sạch dữ liệu giao dịch phát sinh từ Tháng 1 đến Tháng 7/2026, tải lại báo cáo MISA tương ứng từng tháng và tính toán lại toàn bộ KPI BU & Global.
* **Cú pháp sử dụng**:
  ```powershell
  .venv\Scripts\python.exe scripts/reimport_months_1_to_7.py
  ```

### 3.4. Script Nạp Danh mục Nhóm Khách hàng (`scripts/import_customer_group.py`)
* **File nguồn**: `scripts/import_customer_group.py`
* **Tác dụng**: Import dữ liệu phân nhóm khách hàng từ file danh mục.
* **Cú pháp sử dụng**:
  ```powershell
  .venv\Scripts\python.exe scripts/import_customer_group.py
  ```

### 3.5. Batch Script Khởi chạy Celery độc lập (`run_celery.bat`)
* **File nguồn**: [run_celery.bat](file:///d:/Sources/dashboard-report/run_celery.bat)
* **Tác dụng**: Khởi chạy Celery Worker trong cửa sổ CMD riêng biệt khi cần test không thông qua `manage.py runserver`.
* **Cú pháp sử dụng**:
  ```cmd
  run_celery.bat
  ```
