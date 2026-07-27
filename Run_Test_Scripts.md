# Hướng dẫn Chạy Terminal & Test Scripts — Report2026

Tài liệu này là **Nguồn tham chiếu trung tâm (Single Source of Truth)** cho toàn bộ các lệnh terminal, Django Management Commands và script tiện ích của dự án **Report2026**.

> [!IMPORTANT]
> **Quy ước thư mục làm việc**: Tất cả các lệnh bên dưới đều phải chạy tại thư mục gốc của dự án (`d:\Sources\dashboard-report\`), nơi có tệp `manage.py`.

---

## MỤC LỤC NHANH

| Tình huống | Lệnh cần dùng |
|---|---|
| Cài đặt lần đầu | [Mục 1](#1-cài-đặt--thiết-lập-môi-trường-chạy-1-lần) |
| Chạy server hàng ngày | `python manage.py runserver` ([Mục 2.2](#22-khởi-chạy-server-phát-triển)) |
| Tải + Nạp + Tính KPI đầy đủ 1 lần | `python manage.py sync_misa` ([Mục 3.1](#31-chạy-đồng-bộ-toàn-diện-sync_misa---khuyến-nghị)) |
| Chỉ tải 1 loại báo cáo MISA | `python download_report.py BAN_HANG` ([Mục 3.2](#32-tải-riêng-từng-báo-cáo-misa-download_reportpy)) |
| Nạp 1 file Excel rời vào DB | `python import_specific_file.py <path>` ([Mục 3.3](#33-nạp-file-excel-rời-vào-csdl-import_specific_filepy)) |
| Tính lại KPI 1 BU | `python manage.py calculate_bu_performance` ([Mục 3.4](#34-tính-lại-kpi-cho-bu-cụ-thể)) |
| Tính lại KPI Tổng công ty | `python manage.py calculate_global_performance` ([Mục 3.5](#35-tính-lại-kpi-tổng-công-ty)) |
| Debug quá trình tải MISA | `python test_download_ban_hang.py` ([Mục 4.1](#41-debug-tải-báo-cáo-bán-hàng-test_download_ban_hangpy)) |
| Nạp lại dữ liệu nhiều tháng | `python scripts/reimport_months_1_to_7.py` ([Mục 5.1](#51-nạp-lại-dữ-liệu-nhiều-tháng-reimport_months_1_to_7py)) |
| Tạo tài khoản admin | `python manage.py createdefaultuser` ([Mục 6.1](#61-tạo-tài-khoản-admin-mặc-định)) |

---

## 1. Cài đặt & Thiết lập Môi trường (Chạy 1 lần)

> [!NOTE]
> Thực hiện toàn bộ mục này **1 lần duy nhất** khi cài đặt mới hoặc khôi phục môi trường. Sau đó chuyển thẳng sang Mục 2.

### 1.1. Tạo file cấu hình môi trường `.env`

Hệ thống dùng `django-environ` để tách cấu hình nhạy cảm ra khỏi mã nguồn. Tạo file `.env` tại thư mục gốc dự án:

```env
# ── 1. KẾT NỐI CƠ SỞ DỮ LIỆU PostgreSQL ──────────────────────────────────
DB_NAME=reportdb                   # Tên database (mặc định: reportdb)
DB_USER=postgres                   # Username PostgreSQL
DB_PASSWORD=your_password          # Mật khẩu PostgreSQL
DB_HOST=localhost                  # Host (mặc định: localhost)
DB_PORT=5433                       # Cổng PostgreSQL (lưu ý: 5433, không phải 5432)

# ── 2. CELERY BEAT — LỊCH TỰ ĐỘNG NẠP EXCEL ──────────────────────────────
# Kiểu lịch: daily | weekly | monthly | custom
IMPORT_SCHEDULE_TYPE=daily
IMPORT_SCHEDULE_HOUR=7             # Giờ chạy (0-23)
IMPORT_SCHEDULE_MINUTE=0           # Phút chạy (0-59)

# Chỉ áp dụng khi IMPORT_SCHEDULE_TYPE=weekly (0=CN, 1=T2 ... 6=T7)
IMPORT_SCHEDULE_DAY_OF_WEEK=1

# Chỉ áp dụng khi IMPORT_SCHEDULE_TYPE=monthly (1-31)
IMPORT_SCHEDULE_DAY_OF_MONTH=1

# Chỉ áp dụng khi IMPORT_SCHEDULE_TYPE=custom (cú pháp cron 5 trường)
IMPORT_SCHEDULE_CRON=20 7,9,11,14,16 * * 1-6

# ── 3. MISA AMIS — ĐĂNG NHẬP & TỰ ĐỘNG TẢI BÁO CÁO (Playwright) ─────────
MISA_AMIS_LOGIN_URL=https://act.amis.vn/
MISA_EMAIL=your_misa_email@example.com
MISA_PASSWORD=your_misa_password
MISA_HEADLESS=True                 # True = chạy ẩn (không mở cửa sổ trình duyệt)

# Kỳ báo cáo mặc định khi xuất MISA (Tháng này | Năm nay | Tháng trước...)
MISA_REPORT_PERIOD_OPTION=Tháng này

# Cơ chế xuất báo cáo:
# 1 = Xuất từng bước (Bot tự click tham số → Mặc định)
# 2 = Tải từ danh sách Saved Reports (nhanh hơn nhưng cần đã lưu sẵn)
USE_OPTION_EXPORT_REPORT_MISA=1
```
> *(File `.env` đã được thêm vào `.gitignore` — không bao giờ commit file này lên Git.)*

### 1.2. Cài đặt thư viện Python

```powershell
# Kích hoạt môi trường ảo trước
.venv\Scripts\activate

# Cài đặt tất cả dependencies
pip install -r requirements.txt
```

### 1.3. Cài đặt Driver trình duyệt Playwright

Cần thực hiện 1 lần để Playwright có thể điều khiển Chromium tải báo cáo MISA:

```powershell
playwright install chromium
```

### 1.4. Cấu hình đường dẫn Redis Server

Mở file [settings.py](file:///d:/Sources/dashboard-report/report2026/settings.py) và cập nhật đường dẫn tới Redis theo máy của bạn:

```python
# Trong report2026/settings.py — dòng ~172
REDIS_SERVER_PATH = r"d:\downloads\redis-x64-5.0.14.1\redis-server.exe"
```

> [!IMPORTANT]
> **Tương thích Redis trên Windows**: Dùng phiên bản `redis==4.6.0` (đã có trong `requirements.txt`). Phiên bản `redis >= 5.x` gây lỗi `unknown command 'HELLO'` do Redis Windows cũ không hỗ trợ giao thức RESP3.

### 1.5. Khởi tạo Database & Tạo tài khoản Admin

```powershell
# Tạo các bảng trong database
python manage.py migrate

# Tạo tài khoản admin mặc định (username: admin / password: 123)
python manage.py createdefaultuser
```

---

## 2. Khởi chạy Hệ thống Hàng Ngày

### 2.1. Kiểm tra cấu hình trước khi chạy

```powershell
# Kiểm tra toàn bộ cấu hình Django — phải trả về "0 issues found"
python manage.py check
```

### 2.2. Khởi chạy Server phát triển

```powershell
python manage.py runserver
```

> [!TIP]
> **Tự động hóa hoàn toàn**: Khi chạy lệnh trên, [manage.py](file:///d:/Sources/dashboard-report/manage.py) sẽ **tự động mở thêm** các cửa sổ terminal cho:
> - **Redis Server** (nếu chưa chạy)
> - **Celery Worker** (xử lý hàng đợi nạp Excel ngầm)
> - **Celery Beat** (lên lịch nạp dữ liệu tự động theo cron)
>
> Khi nhấn `Ctrl + C` để dừng server, toàn bộ các tiến trình trên đều được **đóng sạch tự động**.

---

## 3. Luồng Đồng bộ Dữ liệu MISA (Hàng ngày / Thủ công)

> [!NOTE]
> **Luồng chuẩn đầy đủ** gồm 3 bước: **Tải báo cáo Excel từ MISA** → **Nạp vào CSDL** → **Tính toán lại KPI**.
> Dùng **Mục 3.1** (`sync_misa` không tham số) để chạy cả 3 bước 1 lần. Các mục còn lại dùng khi cần kiểm soát từng bước riêng lẻ.

### 3.1. Chạy đồng bộ toàn diện (`sync_misa`) — Khuyến nghị

* **File nguồn**: [accounting/management/commands/sync_misa.py](file:///d:/Sources/dashboard-report/accounting/management/commands/sync_misa.py)
* **Tác dụng**: Thực hiện đầy đủ 3 bước: Mở Chromium → Đăng nhập MISA → Tải 7 loại báo cáo Excel về `media/auto_imports/` → Nạp vào CSDL → Tính KPI cho toàn bộ Business Unit.

```powershell
# ── DÙNG THƯỜNG XUYÊN NHẤT ────────────────────────────────────────────────

# [Khuyến nghị] Chạy toàn bộ 3 bước: Tải MISA → Nạp DB → Tính KPI
python manage.py sync_misa

# Chạy toàn bộ nhưng chỉ định kỳ báo cáo là "Tháng trước"
python manage.py sync_misa --period="Tháng trước"

# ── KIỂM SOÁT TỪNG BƯỚC ───────────────────────────────────────────────────

# Bước 1 riêng: Chỉ tải file Excel từ MISA về máy (không nạp DB)
# → Dùng khi muốn kiểm tra file Excel trước khi nạp
python manage.py sync_misa --action=download

# Bước 2+3 riêng: Chỉ nạp TẤT CẢ file Excel trong media/auto_imports/ vào DB & tính KPI
# → Dùng sau khi đã có file Excel sẵn trong thư mục
python manage.py sync_misa --action=import

# Bước 2+3 cho 1 file Excel rời cụ thể: Nạp DB & tính KPI ngay
# → Dùng khi có 1 file tải về thủ công (ví dụ: SO_DU_NH tải riêng)
python manage.py sync_misa --action=import --file="media/auto_imports/SO_DU_NH_20260727_100638.xlsx"

# ── LỌC THEO LOẠI BÁO CÁO ────────────────────────────────────────────────

# Chỉ tải + nạp báo cáo Bán hàng (BAN_HANG)
python manage.py sync_misa --prefix=BAN_HANG

# Chỉ tải + nạp báo cáo Số dư ngân hàng (SO_DU_NH)
python manage.py sync_misa --prefix=SO_DU_NH --period="Tháng này"

# Kết hợp: Chỉ tải (không nạp) báo cáo Tồn kho kỳ "Năm nay"
python manage.py sync_misa --action=download --prefix=TON_KHO --period="Năm nay"
```

**Danh sách `--prefix` hợp lệ và bảng tương ứng:**

| `--prefix` | Loại báo cáo | Bảng CSDL |
|---|---|---|
| `BAN_HANG` | Bán hàng chi tiết | `SalesTransaction` |
| `MUA_HANG` | Mua hàng chi tiết | `PurchaseDetail` |
| `TON_KHO` | Tổng hợp tồn kho | `InventorySummary` |
| `CONG_NO_NCC` | Công nợ nhà cung cấp | `SupplierDebt` |
| `TUOI_NO_KH` | Tuổi nợ khách hàng | `ReceivablesAgeing` |
| `TAI_KHOAN_CT` | Sổ chi tiết TK 111/112/341/641/642 | `AccountDetail` |
| `SO_DU_NH` | Bảng kê số dư ngân hàng | `BankBalance` |

---

### 3.2. Tải riêng từng báo cáo MISA (`download_report.py`)

* **File nguồn**: [download_report.py](file:///d:/Sources/dashboard-report/download_report.py)
* **Tác dụng**: Script CLI nhẹ hơn — **chỉ thực hiện Bước 1** (tải file Excel từ MISA về `media/auto_imports/`). Dùng khi cần tải thủ công 1 loại báo cáo cụ thể mà không chạy cả pipeline.

```powershell
# Tải báo cáo Bán hàng (BAN_HANG)
python download_report.py BAN_HANG

# Tải báo cáo Mua hàng (MUA_HANG)
python download_report.py MUA_HANG

# Tải báo cáo Tồn kho (TON_KHO)
python download_report.py TON_KHO

# Tải báo cáo Công nợ Nhà cung cấp (CONG_NO_NCC)
python download_report.py CONG_NO_NCC

# Tải báo cáo Tuổi nợ Khách hàng (TUOI_NO_KH)
python download_report.py TUOI_NO_KH

# Tải báo cáo Sổ chi tiết Tài khoản 111/112/341/641/642 (TAI_KHOAN_CT)
python download_report.py TAI_KHOAN_CT

# Tải báo cáo Số dư ngân hàng (SO_DU_NH)
python download_report.py SO_DU_NH

# Tải TẤT CẢ 7 loại báo cáo — tương đương sync_misa --action=download
python download_report.py ALL

# Tải TẤT CẢ báo cáo với kỳ báo cáo là "Năm nay"
python download_report.py ALL --period "Năm nay"
```

> [!NOTE]
> Sau khi chạy lệnh này, file Excel được lưu vào `media/auto_imports/` với tên dạng `BAN_HANG_20260727_143022.xlsx`.
> Để nạp file đó vào CSDL, dùng lệnh ở **Mục 3.3** hoặc **Mục 3.1** (`--action=import`).

---

### 3.3. Nạp file Excel rời vào CSDL (`import_specific_file.py`)

* **File nguồn**: [import_specific_file.py](file:///d:/Sources/dashboard-report/import_specific_file.py)
* **Tác dụng**: **Bước 2+3** — Nạp thủ công 1 file Excel bất kỳ trong `media/auto_imports/` vào CSDL rồi tính lại KPI ngay lập tức. Dùng khi có file Excel tải về thủ công hoặc file bị lỗi cần nạp lại.

```powershell
# Xem danh sách các file Excel đang có trong media/auto_imports/ và chờ nạp
python import_specific_file.py

# Nạp file Số dư ngân hàng vừa tải thủ công
python import_specific_file.py media/auto_imports/SO_DU_NH_20260727_100638.xlsx

# Nạp file Bán hàng tháng 6/2026
python import_specific_file.py media/auto_imports/BAN_HANG_20260630_083000.xlsx

# Nạp file Tồn kho
python import_specific_file.py media/auto_imports/TON_KHO_20260727_090000.xlsx
```

> [!TIP]
> Sau khi nạp thành công, script tự động:
> 1. Xóa dữ liệu cũ của **đúng kỳ báo cáo** đó (không xóa tháng khác).
> 2. Bulk insert dữ liệu mới theo chunk 1,000 dòng.
> 3. Kích hoạt tính lại KPI cho toàn bộ BU có liên quan.

---

### 3.4. Tính lại KPI cho BU cụ thể

* **File nguồn**: `accounting/management/commands/calculate_bu_performance.py`
* **Tác dụng**: Tính toán lại chỉ số KPI MTD/YTD cho **1 Business Unit cụ thể** (và tất cả BU con của nó) trong tháng/năm chỉ định. Dùng khi cần cập nhật lại số liệu của 1 BU mà không chạy lại toàn bộ.

```powershell
# Cú pháp: python manage.py calculate_bu_performance --bu_id=<ID> --month=<1-12> --year=<YYYY>

# Tính lại KPI cho BU có ID=70 (ví dụ: HPC) tháng 7/2026
python manage.py calculate_bu_performance --bu_id=70 --month=7 --year=2026

# Tính lại KPI cho BU có ID=44 (ví dụ: BU_ELEVATOR) tháng 6/2026
python manage.py calculate_bu_performance --bu_id=44 --month=6 --year=2026

# Tính lại KPI cho BU ID=1 (ví dụ: BU_IBIZ) tháng hiện tại (7/2026)
python manage.py calculate_bu_performance --bu_id=1 --month=7 --year=2026
```

> [!NOTE]
> Để tra cứu `bu_id`, vào Django Admin → Business Units (`/admin/accounting/businessunit/`) và xem cột ID.

---

### 3.5. Tính lại KPI Tổng công ty

* **File nguồn**: `accounting/management/commands/calculate_global_performance.py`
* **Tác dụng**: Tính toán lại KPI tích lũy cấp **Tổng công ty (TOTAL_CORP)** — loại trừ các BU trong `EXCLUDED_BU_CODES` (hiện tại: `ĐTCT`). Tự động kích hoạt sau khi bất kỳ BU con nào cập nhật, nhưng có thể chạy thủ công khi cần.

```powershell
# Cú pháp: python manage.py calculate_global_performance --month=<1-12> --year=<YYYY>

# Tính lại KPI Tổng công ty tháng 7/2026
python manage.py calculate_global_performance --month=7 --year=2026

# Tính lại KPI Tổng công ty tháng 6/2026 (kiểm tra lại số cũ)
python manage.py calculate_global_performance --month=6 --year=2026
```

---

## 4. Debug & Kiểm thử MISA (Dành cho Developer)

### 4.1. Debug tải báo cáo Bán hàng (`test_download_ban_hang.py`)

* **File nguồn**: [test_download_ban_hang.py](file:///d:/Sources/dashboard-report/test_download_ban_hang.py)
* **Tác dụng**: Chạy thử tải báo cáo Bán hàng (`BAN_HANG`) ở chế độ **có giao diện** (`headless=False`) — mở cửa sổ trình duyệt Chromium thật để developer quan sát từng bước Playwright tương tác với MISA. Dùng khi cần debug popup, selector, hoặc luồng tải mới.

```powershell
# Mở Chromium có giao diện, đăng nhập MISA và thực hiện tải báo cáo BAN_HANG
# → Theo dõi trực tiếp quá trình bot tương tác với MISA trên màn hình
python test_download_ban_hang.py
```

> [!TIP]
> Khác với `download_report.py BAN_HANG` (chạy ẩn `headless=True`), script này giữ nguyên cửa sổ trình duyệt mở để quan sát và debug. Log chi tiết từng bước sẽ hiển thị trong terminal.

---

## 5. Scripts Bảo trì & Quản lý Dữ liệu

### 5.1. Nạp lại dữ liệu nhiều tháng (`reimport_months_1_to_7.py`)

* **File nguồn**: `scripts/reimport_months_1_to_7.py`
* **Tác dụng**: Script bảo trì toàn diện — làm sạch và nạp lại dữ liệu của **Tháng 1 đến Tháng 7/2026**: xóa dữ liệu giao dịch cũ, tải lại từng tháng từ MISA, tính toán lại toàn bộ KPI BU & Global. Dùng khi cần phục hồi dữ liệu hoặc đồng bộ lại sau thay đổi logic tính toán.

```powershell
# ⚠️ Cảnh báo: Script này xóa và nạp lại dữ liệu 7 tháng, có thể mất 30-60 phút
python scripts/reimport_months_1_to_7.py
```

> [!CAUTION]
> Chỉ chạy khi thực sự cần thiết. Script xóa dữ liệu giao dịch nhiều tháng trước khi nạp lại.

### 5.2. Nạp Danh mục Nhóm Khách hàng (`import_customer_group.py`)

* **File nguồn**: `scripts/import_customer_group.py`
* **Tác dụng**: Import dữ liệu phân nhóm khách hàng (Oversea, Internal, thông thường...) từ file danh mục Excel vào bảng `CustomerGroup`. Chạy 1 lần khi có thay đổi phân nhóm khách hàng.

```powershell
python scripts/import_customer_group.py
```

### 5.3. Nạp Mục tiêu Kế hoạch (`seed_target_plans.py`)

* **File nguồn**: [scripts/seed_target_plans.py](file:///d:/Sources/dashboard-report/scripts/seed_target_plans.py)
* **Tác dụng**: Nạp và cập nhật toàn bộ chỉ tiêu kế hoạch Năm & Tháng (Doanh thu, Thu tiền, Tồn kho, Tiền cuối kỳ, Nợ NH, OPEX) vào bảng `BUTargetPlan` cho tất cả các BU. Chạy khi có thay đổi mục tiêu kế hoạch từ Kế toán.

```powershell
python scripts/seed_target_plans.py
```

---

## 6. Quản trị Hệ thống

### 6.1. Tạo tài khoản Admin mặc định

* **File nguồn**: `accounting/management/commands/createdefaultuser.py`
* **Tác dụng**: Tạo nhanh tài khoản superuser mặc định (`username: admin` / `password: 123`) khi cần cài lại từ đầu hoặc restore database.

```powershell
# Tạo tài khoản admin/123 — chỉ chạy 1 lần sau khi migrate xong
python manage.py createdefaultuser
```

> [!CAUTION]
> Tài khoản `admin/123` chỉ dùng trong môi trường **phát triển nội bộ**. Đổi mật khẩu ngay khi triển khai lên server thực tế.

### 6.2. Khởi chạy Celery Worker thủ công (`run_celery.bat`)

* **File nguồn**: [run_celery.bat](file:///d:/Sources/dashboard-report/run_celery.bat)
* **Tác dụng**: Khởi chạy Celery Worker trong cửa sổ CMD **độc lập** khi cần test tác vụ Celery mà không qua `manage.py runserver`. Hữu ích khi debug task queue hoặc test Celery Beat riêng biệt.

```cmd
# Chạy trong CMD (không phải PowerShell)
run_celery.bat
```

> [!NOTE]
> Trong luồng phát triển bình thường, **không cần chạy file này** vì `manage.py runserver` đã tự động khởi chạy Celery Worker và Beat (xem Mục 2.2).
