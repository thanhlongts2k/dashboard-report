# Tài liệu hướng dẫn tổng quan dự án Report2026 (Hạo Phương Co.)

Chào mừng bạn tiếp quản dự án! Đừng lo lắng nếu bạn chưa rành về Python. Tài liệu này được thiết kế để giúp bạn nắm bắt toàn bộ bức tranh của dự án từ kiến trúc, nghiệp vụ đến cách vận hành thực tế.

---

## 1. Dự án này là gì?
Dự án **Report2026** là một hệ thống **Backend API (Application Programming Interface)** chuyên phục vụ cho việc:
1. **Thu thập dữ liệu tự động**: Đọc các file báo cáo Excel xuất ra từ các hệ thống kế toán khác.
2. **Tính toán chỉ số hiệu suất**: Tính doanh thu, công nợ, dòng tiền, chi phí vận hành, tồn kho theo từng ngày, từng tháng cho từng đơn vị kinh doanh (Business Unit - BU) và cho toàn công ty.
3. **Cung cấp API cho Frontend**: Trả dữ liệu đã tính toán dưới dạng JSON để giao diện Dashboard (React/Vue) vẽ biểu đồ.

---

## 2. Các công nghệ cốt lõi được sử dụng
*   **Ngôn ngữ**: Python 3.14 (chạy trong môi trường ảo ở thư mục `python314`).
*   **Framework Web**: **Django** & **Django REST Framework (DRF)**. Django giúp quản lý Database và Admin, còn DRF dùng để xây dựng các API.
*   **Hệ quản trị cơ sở dữ liệu**: **PostgreSQL** (chạy ở cổng `5433`, tên database là `reportdb`).
*   **Hệ thống hàng đợi & Tác vụ ngầm**: **Celery** phối hợp với một Message Broker (như Redis) để chạy các tác vụ import file Excel tự động vào ban đêm.
*   **Thư viện xử lý Excel**: `django-import-export` kết hợp `pandas` và `tablib` để đọc/ghi file Excel cấu trúc lớn.

---

## 3. Cấu trúc thư mục & Ý nghĩa các file quan trọng

Thư mục làm việc của bạn bao gồm:
*   `python314/`: Thư mục chứa môi trường Python và các thư viện đã cài đặt. Bạn không cần sửa gì trong này.
*   `report2026/`: Thư mục mã nguồn chính của dự án.
    *   `manage.py`: File script điều khiển của Django. Bạn dùng nó để chạy server, tạo database, tạo admin...
    *   `db.sqlite3`: File database chạy thử (SQLite), tuy nhiên cấu hình thực tế đang kết nối PostgreSQL.
    *   `report2026/` *(Thư mục cấu hình dự án)*:
        *   [settings.py](file:///d:/django/report2026/report2026/settings.py): Cấu hình chung của dự án (Kết nối database, cấu hình bảo mật CORS/CSRF, danh sách các thư viện được cài đặt, lịch chạy tác vụ tự động Celery).
        *   [urls.py](file:///d:/django/report2026/report2026/urls.py): File định tuyến (Routing) chính, điều hướng các request từ trình duyệt tới ứng dụng.
    *   `accounting/` *(Ứng dụng xử lý kế toán - Nơi chứa toàn bộ logic nghiệp vụ)*:
        *   [models.py](file:///d:/django/report2026/accounting/models.py): **Nơi định nghĩa cấu trúc cơ sở dữ liệu (Database Schema)**. Mỗi class trong này tương đương với một bảng trong DB (như Khách hàng, Sản phẩm, Tồn kho, Chỉ số hiệu suất...).
        *   [views.py](file:///d:/django/report2026/accounting/views.py): **Nơi nhận request và trả về response**. Chứa logic xử lý đăng nhập và các API cung cấp dữ liệu báo cáo.
        *   [serializers.py](file:///d:/django/report2026/accounting/serializers.py): Bộ chuyển đổi dữ liệu. Nó chuyển đổi các đối tượng Database phức tạp thành định dạng JSON (và ngược lại) để Frontend dễ đọc.
        *   [tasks.py](file:///d:/django/report2026/accounting/tasks.py): **Tác vụ ngầm**. Chứa code tự động quét thư mục để import dữ liệu từ file Excel và code công thức tính toán chỉ số hiệu suất tài chính.
        *   [resources.py](file:///d:/django/report2026/accounting/resources.py): Định nghĩa quy tắc mapping (ánh xạ) giữa các cột trong file Excel vào các cột tương ứng trong Database để phục vụ việc import.
        *   [urls.py](file:///d:/django/report2026/accounting/urls.py): Định tuyến riêng cho các API của app `accounting`.

---

## 4. Các luồng nghiệp vụ chính của dự án

### Luồng A: Tự động nạp dữ liệu từ file Excel (Auto Import)
1. Hàng ngày vào lúc **01:00 AM**, Celery Beat sẽ kích hoạt hàm `auto_import_excel_from_folder` trong [tasks.py](file:///d:/django/report2026/accounting/tasks.py#L17).
2. Hệ thống quét thư mục `media/auto_imports/` để tìm các file có tên dạng:
    *   `BAN_HANG*.xlsx` (Bán hàng)
    *   `MUA_HANG*.xlsx` (Mua hàng)
    *   `TON_KHO*.xlsx` (Tồn kho)
    *   `CONG_NO_NCC*.xlsx` (Công nợ nhà cung cấp)
    *   `TUOI_NO_KH*.xlsx` (Tuổi nợ khách hàng)
    *   `SO_CHI_TIET*.xlsx` (Sổ chi tiết tài khoản ngân hàng/tiền mặt 111-112)
3. Với mỗi file tìm thấy, hệ thống sẽ **xóa sạch dữ liệu cũ** của bảng đó trong DB rồi **nạp dữ liệu mới** vào. Nếu thành công, file Excel sẽ được di chuyển vào thư mục `success/`. Nếu có lỗi, giao dịch (transaction) sẽ được Rollback (hoàn tác) để tránh mất dữ liệu cũ.

### Luồng B: Tính toán chỉ số hiệu suất (KPI/Performance)
Sau khi dữ liệu Excel mới được nạp vào, hệ thống chạy hàm `update_single_bu_performance` để tổng hợp số liệu cho từng đơn vị kinh doanh (BU):
*   **Doanh thu lũy kế tháng**: Tổng hợp từ bảng `SalesTransaction` dựa trên các khách hàng được ghi nhận doanh thu.
*   **Thực thu tiền mặt/ngân hàng**: Lọc từ bảng `AccountDetail` các bút toán có tài khoản nợ bắt đầu bằng `111` hoặc `112` và tài khoản đối ứng bắt đầu bằng `1311` hoặc `1312`.
*   **Tuổi nợ**: Tổng hợp công nợ quá hạn và trước hạn từ bảng `ReceivablesAgeing`.
*   **Tồn kho**: Tính tổng giá trị tồn kho từ bảng `InventorySummary`.
*   Tất cả số liệu này được lưu vào bảng `BUPerformance` (theo tháng) và `BUPerformanceDaily` (theo ngày).

---

## 5. Hướng dẫn chạy và thao tác với dự án dành cho bạn

Để bắt đầu làm việc trên máy tính này, bạn làm theo các bước sau trong terminal của VS Code:

### Bước 1: Kích hoạt Môi trường ảo (Virtual Environment)
Môi trường ảo giúp tách biệt các thư viện của dự án này với các dự án khác trên máy.
*   Nếu dùng **PowerShell** (như hình bạn chụp):
    ```powershell
    .\python314\Scripts\Activate.ps1
    ```
*   Nếu dùng **Command Prompt (cmd)**:
    ```cmd
    .\python314\Scripts\activate.bat
    ```
*(Khi kích hoạt thành công, bạn sẽ thấy chữ `(python314)` xuất hiện ở đầu dòng lệnh).*

### Bước 2: Chạy Server phát triển (Development Server)
```bash
cd report2026
python manage.py runserver 0.0.0.0:8000
```
*   Tham số `0.0.0.0:8000` giúp server mở cổng cho tất cả thiết bị khác truy cập (như điện thoại của bạn).
*   Truy cập trang Admin của hệ thống tại: `http://127.0.0.1:8000/admin` (hoặc `http://<IP_máy_bạn>:8000/admin`).

### Bước 3: Tạo tài khoản Admin mới (nếu chưa có hoặc quên mật khẩu)
Nếu bạn cần vào trang Admin của Django mà đồng nghiệp cũ chưa bàn giao tài khoản:
```bash
python manage.py createsuperuser
```
*   Nhập username, email và password mong muốn. Sau đó dùng tài khoản này đăng nhập vào link `/admin`.

### Bước 4: Đồng bộ cấu hình Database (Migrations)
Mỗi lần bạn sửa đổi cấu trúc bảng trong file `models.py`, bạn cần chạy 2 lệnh sau để cập nhật cấu trúc đó vào cơ sở dữ liệu PostgreSQL:
```bash
# 1. Tạo file ghi nhận sự thay đổi cấu trúc
python manage.py makemigrations

# 2. Áp dụng thay đổi đó vào Database thật
python manage.py migrate
```

---

## 6. Mẹo nhỏ cho người mới tiếp cận Django

*   **Django Admin cực kỳ mạnh mẽ**: Bạn truy cập vào `http://127.0.0.1:8000/admin` để xem, sửa, xóa, tìm kiếm dữ liệu trực tiếp của mọi bảng trong DB mà không cần gõ lệnh SQL.
*   **Xem các API khả dụng**: Nhờ có Django REST Framework, bạn có thể truy cập thẳng các link như `http://127.0.0.1:8000/api/branches/` hoặc `http://127.0.0.1:8000/api/business-units/` trên trình duyệt máy tính. Hệ thống sẽ hiển thị một giao diện Web API cực kỳ trực quan giúp bạn test dữ liệu trả về mà không cần dùng Postman.
