# Tài liệu hướng dẫn tổng quan dự án Report2026 (HP Co.)

Chào mừng bạn tiếp quản dự án! Đừng lo lắng nếu bạn chưa rành về Python. Tài liệu này được thiết kế để giúp bạn nắm bắt toàn bộ bức tranh của dự án từ kiến trúc, nghiệp vụ đến cách vận hành thực tế.

---

## 1. Dự án này là gì?
Dự án **Report2026** là một hệ thống **Backend API (Application Programming Interface)** chuyên phục vụ cho việc:
1. **Thu thập dữ liệu tự động**: Đọc các file báo cáo Excel xuất ra từ các hệ thống kế toán khác.
2. **Tính toán chỉ số hiệu suất**: Tính doanh thu, công nợ, dòng tiền, chi phí vận hành, tồn kho theo từng ngày, từng tháng cho từng đơn vị kinh doanh (Business Unit - BU) và cho toàn công ty.
3. **Cung cấp API cho Frontend**: Trả dữ liệu đã tính toán dưới dạng JSON để giao diện Dashboard (React/Vue) vẽ biểu đồ.

---

## 2. Các công nghệ cốt lõi được sử dụng
*   **Ngôn ngữ**: Python 3.14 (chạy trong môi trường ảo ở thư mục `.venv`).
*   **Framework Web**: **Django** & **Django REST Framework (DRF)**. Django giúp quản lý Database và Admin, còn DRF dùng để xây dựng các API.
*   **Hệ quản trị cơ sở dữ liệu**: **PostgreSQL** (chạy ở cổng `5433`, tên database là `reportdb`).
*   **Hệ thống hàng đợi & Tác vụ ngầm**: **Celery** phối hợp với một Message Broker (như Redis) để chạy các tác vụ import file Excel tự động vào ban đêm.
*   **Thư viện xử lý Excel**: `django-import-export` kết hợp `pandas` và `tablib` để đọc/ghi file Excel cấu trúc lớn.

---

## 3. Cấu trúc thư mục & Ý nghĩa các file quan trọng

Thư mục làm việc của bạn bao gồm:
*   `.venv/`: Thư mục chứa môi trường Python và các thư viện đã cài đặt. Bạn không cần sửa gì trong này.
*   `report2026/`: Thư mục mã nguồn chính của dự án.
    *   `manage.py`: File script điều khiển của Django. Bạn dùng nó để chạy server, tạo database, tạo admin...
    *   `db.sqlite3`: File database chạy thử (SQLite), tuy nhiên cấu hình thực tế đang kết nối PostgreSQL.
    *   `report2026/` *(Thư mục cấu hình dự án)*:
        *   [settings.py](file:///d:/Sources/dashboard-report/report2026/settings.py): Cấu hình chung của dự án (Kết nối database, cấu hình bảo mật CORS/CSRF, danh sách các thư viện được cài đặt, lịch chạy tác vụ tự động Celery).
        *   [urls.py](file:///d:/Sources/dashboard-report/report2026/urls.py): File định tuyến (Routing) chính, điều hướng các request từ trình duyệt tới ứng dụng.
    *   `accounting/` *(Ứng dụng xử lý kế toán - Nơi chứa toàn bộ logic nghiệp vụ)*:
        *   [models.py](file:///d:/Sources/dashboard-report/accounting/models.py): **Nơi định nghĩa cấu trúc cơ sở dữ liệu (Database Schema)**. Mỗi class trong này tương đương với một bảng trong DB (như Khách hàng, Sản phẩm, Tồn kho, Chỉ số hiệu suất...).
        *   [views.py](file:///d:/Sources/dashboard-report/accounting/views.py): **Nơi nhận request và trả về response**. Chứa logic xử lý đăng nhập và các API cung cấp dữ liệu báo cáo.
        *   [serializers.py](file:///d:/Sources/dashboard-report/accounting/serializers.py): Bộ chuyển đổi dữ liệu. Nó chuyển đổi các đối tượng Database phức tạp thành định dạng JSON (và ngược lại) để Frontend dễ đọc.
        *   [tasks.py](file:///d:/Sources/dashboard-report/accounting/tasks.py): **Tác vụ ngầm**. Chứa code tự động quét thư mục để import dữ liệu từ file Excel và code công thức tính toán chỉ số hiệu suất tài chính.
        *   [resources.py](file:///d:/Sources/dashboard-report/accounting/resources.py): Định nghĩa quy tắc mapping (ánh xạ) giữa các cột trong file Excel vào các cột tương ứng trong Database để phục vụ việc import.
        *   [urls.py](file:///d:/Sources/dashboard-report/accounting/urls.py): Định tuyến riêng cho các API của app `accounting`.

---

## 4. Các luồng nghiệp vụ chính của dự án

### Luồng A: Tự động nạp dữ liệu từ file Excel (Auto Import)
1. Hàng ngày vào lúc **01:00 AM** (giờ UTC, cấu hình Celery Beat trong `settings.py`), Celery Beat sẽ kích hoạt hàm `auto_import_excel_from_folder` trong [tasks.py](file:///d:/Sources/dashboard-report/accounting/tasks.py#L17).
2. Hệ thống quét thư mục `media/auto_imports/` để tìm các file có tên dạng:
    *   `BAN_HANG*.xlsx` (Bán hàng) -> Lưu vào `SalesTransaction`
    *   `MUA_HANG*.xlsx` (Mua hàng) -> Lưu vào `PurchaseDetail`
    *   `TON_KHO*.xlsx` (Tồn kho) -> Lưu vào `InventorySummary`
    *   `CONG_NO_NCC*.xlsx` (Công nợ nhà cung cấp) -> Lưu vào `SupplierDebt`
    *   `TUOI_NO_KH*.xlsx` (Tuổi nợ khách hàng) -> Lưu vào `ReceivablesAgeing`
    *   `SO_CHI_TIET*.xlsx` (Sổ chi tiết tài khoản ngân hàng/tiền mặt 111-112) -> Lưu vào `AccountDetail`
3. Với mỗi file tìm thấy, hệ thống sẽ **xóa sạch dữ liệu cũ** của bảng đó trong DB rồi **nạp dữ liệu mới** vào. Nếu thành công, file Excel sẽ được di chuyển vào thư mục `success/`. Nếu có lỗi, giao dịch (transaction) sẽ được Rollback (hoàn tác) để tránh mất dữ liệu cũ.

### Luồng B: Tính toán chỉ số hiệu suất (KPI/Performance)
Sau khi dữ liệu Excel mới được nạp vào, hệ thống chạy hàm `update_single_bu_performance` để tổng hợp số liệu cho từng đơn vị kinh doanh (BU) và cho Tổng công ty:
*   **Doanh thu lũy kế tháng**: Tổng hợp từ bảng `SalesTransaction` dựa trên các khách hàng có `has_revenue=True`.
    > [!IMPORTANT]
    > **Lưu ý sự bất nhất về logic:**
    > - Doanh thu tháng (`rev_actual`) được tính bằng cách cộng cột `actual_sales` (Doanh số thực tế) của `SalesTransaction`.
    > - Doanh thu ngày (`daily_rev`) lại được tính bằng cách cộng cột `sales_amount` (Doanh số bán) của `SalesTransaction`.
    > Do đó, tổng doanh thu các ngày trong tháng có thể không khớp hoàn toàn với doanh thu lũy kế của tháng đó.
*   **Thực thu tiền mặt/ngân hàng**: Lọc từ bảng `AccountDetail` các bút toán có tài khoản nợ bắt đầu bằng `111` hoặc `112` và tài khoản đối ứng bắt đầu bằng `1311` hoặc `1312`.
*   **Tuổi nợ**: Tổng hợp công nợ quá hạn (`overdue_total`) và trước hạn (`due_total`) từ bảng `ReceivablesAgeing`.
    *   *Đã thu (đến hạn)* (`collection_due_actual`) lấy từ `due_total`.
    *   *Thu trong hạn + COD* (`collection_in_term_cod`) tính bằng `total_debt - overdue_total`.
*   **Tồn kho**: Tính tổng giá trị tồn kho từ bảng `InventorySummary` (cột `closing_value`).
*   Tất cả số liệu này được lưu vào bảng `BUPerformance` (theo tháng) và `BUPerformanceDaily` (theo ngày).

> [!WARNING]
> **Các trường số liệu thực tế chưa được tính toán:**
> Hiện tại, các trường `bank_debt_actual` (Nợ ngân hàng thực tế), `opex_actual` (Chi phí vận hành thực tế), và `cash_balance_actual` (Tiền cuối kỳ thực tế) trong bảng `BUPerformance` **chưa có logic tính toán** trong backend và luôn mang giá trị mặc định là `0`.

> [!NOTE]
> **Các bảng độc lập:**
> Dữ liệu mua hàng (`PurchaseDetail`) và Công nợ nhà cung cấp (`SupplierDebt`) được tự động nạp từ Excel nhưng hiện tại **không tham gia** vào luồng tính toán hiệu suất BU.

### Luồng C: Đồng bộ tồn kho kho hàng (Warehouse Inventory Sync)
Bên cạnh tác vụ import Excel, hệ thống có hàm `sync_warehouse_inventory_data` trong [tasks.py](file:///d:/Sources/dashboard-report/accounting/tasks.py#L218) dùng để tổng hợp số liệu tồn kho từ bảng `InventorySummary` (đầu kỳ, nhập, xuất, cuối kỳ) rồi cập nhật trực tiếp vào từng kho trong bảng `Warehouse`.
Nhà phát triển hoặc Admin có thể kích hoạt đồng bộ thủ công qua tính năng Action trong Django Admin của bảng `Warehouse`.

---

## 5. Hướng dẫn chạy và thao tác với dự án dành cho bạn

Để bắt đầu làm việc trên máy tính này, bạn làm theo các bước sau trong terminal của VS Code:

### Bước 1: Kích hoạt Môi trường ảo (Virtual Environment)
Môi trường ảo giúp tách biệt các thư viện của dự án này với các dự án khác trên máy.
*   Nếu dùng **PowerShell** (mặc định của VS Code trên Windows):
    ```powershell
    .\.venv\Scripts\Activate.ps1
    ```
*   Nếu dùng **Command Prompt (cmd)**:
    ```cmd
    .\.venv\Scripts\activate.bat
    ```
*(Khi kích hoạt thành công, bạn sẽ thấy chữ `(.venv)` xuất hiện ở đầu dòng lệnh).*

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
Môi trường ảo giúp cập nhật cấu trúc database phù hợp với file `models.py`:
```bash
# 1. Tạo file ghi nhận sự thay đổi cấu trúc
python manage.py makemigrations

# 2. Áp dụng thay đổi đó vào Database thật
python manage.py migrate
```

---

## 6. Mẹo nhỏ cho người mới tiếp cận Django & Danh sách API phục vụ Frontend

### Phân quyền & Bảo mật API (Authentication)
*   Hệ thống đang cấu hình yêu cầu xác thực mặc định bằng **Knox Token** hoặc **Session** (trong [settings.py](file:///d:/Sources/dashboard-report/report2026/settings.py#L77)).
*   Giao thức gọi API (ngoại trừ `/api/login/`) bắt buộc phải đính kèm Header:
    `Authorization: Token <key_nhận_được_khi_login>`

### Danh sách các API Endpoint phục vụ Frontend Dashboard:
1.  **Đăng nhập hệ thống**:
    *   `POST /api/login/`: Gửi `username` và `password` để nhận Token Knox và thông tin user.
2.  **Lấy số liệu Hiệu suất BU theo Tháng (Dashboard chính)**:
    *   `GET /api/bu-performance/`: Trả về số liệu kế hoạch và thực tế theo tháng kèm theo các trường KPI được tính toán tự động như `revenue_kpi`, `collection_kpi`, `inventory_vs_plan`.
    *   *Các filter khả dụng*: `?month=6&year=2026&bu_id=X` (bu_id có thể là `null` để lấy Tổng công ty hoặc `all` để lấy toàn bộ).
3.  **Lấy số liệu Hiệu suất BU theo Ngày (Vẽ biểu đồ)**:
    *   `GET /api/performance/daily/`: Trả về dữ liệu doanh thu và thực thu phát sinh trong từng ngày của tháng.
    *   *Các filter khả dụng*: `?bu_id=X&month=6&year=2026`.
4.  **Kích hoạt tính toán lại dữ liệu**:
    *   `POST /api/update-performance/`: Cho phép trigger tính toán và cập nhật lại chỉ số hiệu suất từ các bảng chi tiết. Body gửi dạng:
        `{"bu_id": X, "month": 6, "year": 2026, "target_date": "2026-06-12"}`
5.  **Các API danh mục chi tiết (DRF ViewSets)**:
    *   `/api/branches/`, `/api/business-units/`, `/api/transactions/`, `/api/customers/`, `/api/suppliers/`, `/api/supplier-debts/`, `/api/account-details/`, `/api/receivables-ageing/`, `/api/purchase-details/`, `/api/inventory-summaries/`.
    *   Các link này có giao diện Web API trực quan của DRF giúp bạn test dữ liệu trả về trực tiếp trên trình duyệt.
