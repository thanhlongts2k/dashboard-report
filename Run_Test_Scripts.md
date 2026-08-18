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
| Tính lại KPI Tổng công ty theo Tháng chỉ định | `python manage.py calculate_global_performance` / `python scripts/update_company_total.py` ([Mục 3.5](#35-tính-lại-kpi-tổng-công-ty-theo-tháng-chỉ-định)) |
| Xem Snapshot CSDL thời điểm hiện tại | `python scripts/show_snapshot.py` ([Mục 5.4](#54-xem-báo-cáo-data-snapshot-csdl-ngay-lập-tức-show_snapshotpy)) |
| Phát hiện Chức danh Quản lý & Trưởng phòng | `python scripts/detect_manager_titles.py` ([Mục 5.5](#55-phát-hiện-chức-danh-quản-lý--trưởng-bộ-phận-detect_manager_titlespy)) |
| Tự động Gán Sếp cho Nhân viên theo Phòng ban | `python scripts/auto_assign_managers.py` ([Mục 5.6](#56-tự-động-gán-sếp-cho-nhân-viên-theo-phòng-ban-auto_assign_managerspy)) |
| Xem Cây Phòng ban & Nhân viên Trực thuộc | `python scripts/show_department_tree.py` ([Mục 5.7](#57-xem-cây-phòng-ban-trưởng-bộ-phận--danh-sách-nhân-viên-show_department_treepy)) |
| Tự động Gán Sales phụ trách Khách hàng từ Sổ Bán hàng | `python scripts/auto_assign_customer_sales.py` ([Mục 5.8](#58-tự-động-gán-sales-phụ-trách-khách-hàng-từ-sổ-bán-hàng-auto_assign_customer_salespy)) |
| Nạp Danh mục Khách hàng & Mapping Sales | `python scripts/import_customer_mapping.py` ([Mục 5.9](#59-nạp-danh-mục-khách-hàng--mapping-sales-phụ-trách-import_customer_mappingpy)) |
| Báo cáo Công nợ BU & Nhân viên kỳ chỉ định | `python scripts/report_bu_employee_debt.py` ([Mục 5.10](#510-báo-cáo-công-nợ-toàn-diện-theo-bu--nhân-viên-report_bu_employee_debtpy)) |
| Báo cáo Phân cấp Công nợ 3 tầng (BU -> Sales -> KH) | `python scripts/report_3tier_bu_drilldown.py` ([Mục 5.11](#511-báo-cáo-công-nợ-phân-cấp-3-tầng-drilldown-report_3tier_bu_drilldownpy)) |
| Test Bộ REST API Endpoints Công nợ (Phase 3) | `python scripts/test_debt_apis.py` ([Mục 5.12](#512-kiểm-thử-bộ-rest-api-endpoints-công-nợ--drilldown-test_debt_apispy)) |
| Test Tự Động Hóa Gửi Email Nhắc Nợ | `python scripts/test_debt_email_automation.py` ([Mục 5.13](#513-kiểm-thử-tự-động-hóa-gửi-email-nhắc-nợ-phân-cấp-test_debt_email_automationpy)) |
| Gửi Thử Nghiệm Email Nhắc Nợ Chỉ Định | `python scripts/send_test_debt_emails.py` ([Mục 5.14](#514-gửi-thử-nghiệm-email-nhắc-nợ-chỉ-định-qua-smtp-send_test_debt_emailspy)) |
| Debug quá trình tải MISA | `python scripts/test_download_ban_hang.py` ([Mục 4.1](#41-debug-tải-báo-cáo-bán-hàng-test_download_ban_hangpy)) |
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
| `DANH_SACH_KHACH_HANG` | Danh mục Khách hàng & Sales phụ trách | `Customer` |
| `DANH_SACH_NHAN_VIEN` | Danh mục Nhân viên & Quản trị | `Employee` |

---

### 3.2. Tải riêng từng báo cáo MISA (`download_report.py`)

* **File nguồn**: [download_report.py](file:///d:/Sources/dashboard-report/download_report.py)
* **Tác dụng**: Script CLI nhẹ hơn — **chỉ thực hiện Bước 1** (tải file Excel từ MISA về `media/auto_imports/`). Dùng khi cần tải thủ công 1 loại báo cáo cụ thể mà không chạy cả pipeline.

```powershell
# Tải Danh mục Nhân viên (Master Data)
python download_report.py DANH_SACH_NHAN_VIEN

# Tải Danh mục Khách hàng & Sales phụ trách (Master Data)
python download_report.py DANH_SACH_KHACH_HANG

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

# Tải TẤT CẢ các loại báo cáo & danh mục
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

### 3.5. Tính lại KPI Tổng công ty theo Tháng chỉ định

* **File nguồn**: `accounting/management/commands/calculate_global_performance.py` & `scripts/update_company_total.py`
* **Tác dụng**: Tính toán lại KPI tích lũy cấp **Tổng công ty (TOTAL_CORP)** — loại trừ các BU trong `EXCLUDED_BU_CODES` (hiện tại: `ĐTCT`).

```powershell
# Cách 1: Tính lại KPI Tổng công ty cho 1 tháng chỉ định (Management Command)
python manage.py calculate_global_performance --month 7 --year 2026

# Cách 2: Tính lũy kế tuần tự từ Tháng 1 -> Tháng chỉ định (Khuyên dùng khi cần đồng bộ YTD chuẩn)
python scripts/update_company_total.py 7 2026
```

> [!TIP]
> **Khi nào dùng lệnh nào?**
> - Dùng **Cách 1** khi chỉ cần tính lại 1 tháng đơn lẻ nhanh chóng.
> - Dùng **Cách 2** (`update_company_total.py`) khi muốn hệ thống tính tuần tự từ Tháng 1 đến tháng chỉ định để số liệu lũy kế YTD chuẩn xác 100%.

---

## 4. Debug & Kiểm thử MISA (Dành cho Developer)

### 4.1. Debug tải báo cáo Bán hàng (`test_download_ban_hang.py`)

* **File nguồn**: [scripts/test_download_ban_hang.py](file:///d:/Sources/dashboard-report/scripts/test_download_ban_hang.py)
* **Tác dụng**: Chạy thử tải báo cáo Bán hàng (`BAN_HANG`) ở chế độ **có giao diện** (`headless=False`) — mở cửa sổ trình duyệt Chromium thật để developer quan sát từng bước Playwright tương tác với MISA. Dùng khi cần debug popup, selector, hoặc luồng tải mới.

```powershell
# Mở Chromium có giao diện, đăng nhập MISA và thực hiện tải báo cáo BAN_HANG
# → Theo dõi trực tiếp quá trình bot tương tác với MISA trên màn hình
python scripts/test_download_ban_hang.py
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

### 5.4. Xem Báo Cáo Data Snapshot CSDL Ngay Lập Tức (`show_snapshot.py`)

* **File nguồn**: [scripts/show_snapshot.py](file:///d:/Sources/dashboard-report/scripts/show_snapshot.py)
* **Tác dụng**: Script CLI hỗ trợ **in nhanh toàn bộ báo cáo Snapshot số liệu thực tế trong CSDL hiện tại** (Doanh thu MTD/YTD, Thực thu MTD/YTD, Tồn kho, Tiền mặt, Nợ NH, OPEX) cho Tổng công ty và từng đơn vị kinh doanh (BU) dưới dạng danh sách dễ đọc trên Terminal, hiển thị chính xác vết thời gian chốt số liệu (`NGÀY CHỐT SỐ LIỆU: HH:MM:SS DD/MM/YYYY`).

```powershell
# Xem Snapshot CSDL Tháng hiện tại (mặc định: Tháng 7/2026) cho Tổng công ty và các BU
python scripts/show_snapshot.py

# Xem Snapshot cho kỳ tháng khác (ví dụ: Tháng 6/2026)
python scripts/show_snapshot.py --month 6 --year 2026

# Xem Snapshot riêng cho 1 BU cụ thể (ví dụ: BU_ELEVATOR hoặc HPC)
python scripts/show_snapshot.py --bu BU_ELEVATOR

# Hiển thị đầy đủ tất cả các BU (kể cả các BU inactive chưa phát sinh số liệu)
python scripts/show_snapshot.py --show-all
```

### 5.5. Phát hiện Chức danh Quản lý & Trưởng bộ phận (`detect_manager_titles.py`)

* **File nguồn**: [scripts/detect_manager_titles.py](file:///d:/Sources/dashboard-report/scripts/detect_manager_titles.py)
* **Tác dụng**: Quét toàn bộ danh mục Chức danh (`JobTitle`) và Danh sách nhân viên trong CSDL, tự động lọc ra các chức danh cấp Quản lý / Trưởng bộ phận (dựa trên các từ khóa như *"Trưởng"*, *"Chủ nhiệm"*, *"Giám đốc"*, *"Quản lý"*, *"Leader"*, *"Manager"*...) và in danh sách nhân viên đang nắm giữ các vị trí quản lý này.

```powershell
# Quét CSDL và hiển thị danh sách Chức danh & Nhân viên Quản lý
python scripts/detect_manager_titles.py
```

### 5.6. Tự động Gán Sếp cho Nhân viên theo Phòng ban (`auto_assign_managers.py`)

* **File nguồn**: [scripts/auto_assign_managers.py](file:///d:/Sources/dashboard-report/scripts/auto_assign_managers.py)
* **Tác dụng**: Tự động nhận diện Trưởng bộ phận / Quản lý của từng Phòng ban (`Department`) và gán lại `manager` cho toàn bộ nhân viên trong phòng ban đó. Đồng thời tự động liên kết Trưởng phòng tới Trưởng bộ phận cấp trên theo cây `parent_department`.

```powershell
# Chạy tự động gán Manager cho tất cả nhân viên trong CSDL
python scripts/auto_assign_managers.py
```

### 5.7. Xem Cây Phòng ban, Trưởng bộ phận & Danh sách Nhân viên (`show_department_tree.py`)

* **File nguồn**: [scripts/show_department_tree.py](file:///d:/Sources/dashboard-report/scripts/show_department_tree.py)
* **Tác dụng**: In ra toàn bộ danh sách Đơn vị / Phòng ban (`Department`), Trưởng phòng / Quản lý đại diện của phòng ban đó và danh sách từng Nhân viên trực thuộc kèm theo Sếp trực tiếp phụ trách.

```powershell
# Sắp xếp mặc định theo Mã NV tăng dần (code)
python scripts/show_department_tree.py

# Tuỳ chọn sắp xếp theo Tên Chức danh (A-Z)
python scripts/show_department_tree.py --sort-by title

# Tuỳ chọn sắp xếp theo ID Chức danh (tăng dần)
python scripts/show_department_tree.py --sort-by title_id

# Tuỳ chọn sắp xếp theo Họ và Tên nhân viên (A-Z)
python scripts/show_department_tree.py --sort-by name
```

### 5.8. Tự động Gán Sales phụ trách Khách hàng từ Sổ Bán hàng (`auto_assign_customer_sales.py`)

* **File nguồn**: [scripts/auto_assign_customer_sales.py](file:///d:/Sources/dashboard-report/scripts/auto_assign_customer_sales.py)
* **Tác dụng**: Tự động phân tích lịch sử Bán hàng (`SalesTransaction`) và gán Nhân viên Sales phát sinh giao dịch nhiều nhất làm Sales phụ trách chính (`Customer.assigned_employee`) cho từng Khách hàng.

```powershell
# Tự động gán Sales phụ trách cho Khách hàng từ lịch sử Bán hàng
python scripts/auto_assign_customer_sales.py
```

### 5.9. Nạp Danh mục Khách hàng & Mapping Sales Phụ Trách (`import_customer_mapping.py`)

* **File nguồn**: [scripts/import_customer_mapping.py](file:///d:/Sources/dashboard-report/scripts/import_customer_mapping.py)
* **Tác dụng**: Đọc file Excel danh mục khách hàng (`media/auto_imports/Danh_sach_khach_hang.xlsx`), tự động thêm mới nhân viên Sales nếu chưa có, gán mã Sales phụ trách vào `Customer.assigned_employee` (bulk upsert), và tự động kích hoạt tính toán chốt số liệu công nợ `EmployeeReceivableSummary` theo kỳ chỉ định.

```powershell
# Nạp danh mục khách hàng và tự động chốt công nợ kỳ 2026-08 (Mặc định)
python scripts/import_customer_mapping.py --period 2026-08

# Chỉ định file Excel tuỳ chọn
python scripts/import_customer_mapping.py --file "media/auto_imports/Danh_sach_khach_hang.xlsx" --period 2026-08

# Nạp mapping nhưng không chạy lại engine tính nợ
python scripts/import_customer_mapping.py --no-calc
```

### 5.10. Báo Cáo Công Nợ Toàn Diện Theo BU & Nhân Viên (`report_bu_employee_debt.py`)

* **File nguồn**: [scripts/report_bu_employee_debt.py](file:///d:/Sources/dashboard-report/scripts/report_bu_employee_debt.py)
* **Tác dụng**: Xuất đồng thời 2 báo cáo công nợ chuyên sâu từ CSDL: (1) Tổng hợp công nợ 22 Business Units (BU), tỷ lệ nợ quá hạn; (2) Bóc tách công nợ cá nhân (`own_total_debt`) và nợ nhóm (`team_total_debt`) của từng Sales và Quản lý theo từng BU/Phòng ban.

```powershell
# Chạy báo cáo công nợ kỳ 2026-08 (Mặc định)
python scripts/report_bu_employee_debt.py --period 2026-08

# Chạy báo cáo công nợ kỳ khác
python scripts/report_bu_employee_debt.py --period 2026-07
```

### 5.11. Báo Cáo Công Nợ Phân Cấp 3 Tầng Drilldown (`report_3tier_bu_drilldown.py`)

* **File nguồn**: [scripts/report_3tier_bu_drilldown.py](file:///d:/Sources/dashboard-report/scripts/report_3tier_bu_drilldown.py)
* **Tác dụng**: Xuất báo cáo cấu trúc phân cấp 3 tầng trực quan: [Cấp 1: BU] $\rightarrow$ [Cấp 2: Sales phụ trách] $\rightarrow$ [Cấp 3: Chi tiết từng Khách hàng]. Hỗ trợ xem từng BU hoặc toàn bộ 22 BUs.

```powershell
# Xem phân cấp 3 tầng cho 1 BU (Mặc định: BU_ELEVATOR, kỳ 2026-08)
python scripts/report_3tier_bu_drilldown.py --bu BU_ELEVATOR --period 2026-08

# Xem cho BU khác (ví dụ: BU_IBIZ PREMIUM)
python scripts/report_3tier_bu_drilldown.py --bu "BU_IBIZ PREMIUM" --period 2026-08

# Hiển thị tất cả 22 BU liên tiếp
python scripts/report_3tier_bu_drilldown.py --all --period 2026-08
```

### 5.12. Kiểm Thử Bộ REST API Endpoints Công Nợ & Drilldown (`test_debt_apis.py`)

* **File nguồn**: [scripts/test_debt_apis.py](file:///d:/Sources/dashboard-report/scripts/test_debt_apis.py)
* **Tác dụng**: Chạy tự động 3 bộ test suite kiểm tra: (1) `GET /api/debt/bus/` (Mặc định lọc nợ quá hạn & param `include_all=true`); (2) `GET /api/debt/bus/<bu_code>/drilldown/` (3-Tier Drilldown, đầy đủ 14 dải tuổi nợ chi tiết ở cấp Khách hàng & Đối soát khớp 0 VNĐ); (3) Xử lý lỗi 404 cho BU không tồn tại.

```powershell
python scripts/test_debt_apis.py
```

### 5.13. Kiểm Thử Tự Động Hóa Gửi Email Nhắc Nợ Phân Cấp (`test_debt_email_automation.py`)

* **File nguồn**: [scripts/test_debt_email_automation.py](file:///d:/Sources/dashboard-report/scripts/test_debt_email_automation.py)
* **Tác dụng**: Chạy tự động 4 bộ test suite toàn diện: (1) Gom dữ liệu Sales & 6 BU cốt lõi; (2) Render 2 HTML templates `debt_reminder_sales.html` và `debt_summary_manager.html`; (3) Kiểm thử điều phối tiến trình Dry-Run; (4) Kiểm thử gọi REST API `POST /api/debt/notifications/send-reminders/`.

```powershell
python scripts/test_debt_email_automation.py
```

### 5.14. Gửi Thử Nghiệm Email Nhắc Nợ Chỉ Định Qua SMTP (`send_test_debt_emails.py`)

* **File nguồn**: [scripts/send_test_debt_emails.py](file:///d:/Sources/dashboard-report/scripts/send_test_debt_emails.py)
* **Tác dụng**: Trích xuất dữ liệu thực tế của một Nhân viên Sales chỉ định và một Khối BU chỉ định để render template và gửi thực tế qua SMTP đến email nhận thử nghiệm được chỉ định.

```powershell
python scripts/send_test_debt_emails.py
```

### 5.15. Công Cụ Kích Hoạt Gửi Email Nhắc Nợ CLI / Live (`send_live_debt_reminders.py`)

* **File nguồn**: [scripts/send_live_debt_reminders.py](file:///d:/Sources/dashboard-report/scripts/send_live_debt_reminders.py)
* **Tác dụng**: Công cụ dòng lệnh (CLI Tool) đa năng để gửi email nhắc nợ phân cấp, hỗ trợ cả chế độ Dry-Run an toàn lẫn Kích hoạt gửi Thực tế (Live Production).

```powershell
# Xem hướng dẫn chi tiết
python scripts/send_live_debt_reminders.py --help

# 1. Chạy thử nghiệm thống kê (Mặc định dry-run):
python scripts/send_live_debt_reminders.py --period 2026-08

# 2. Chạy thử nghiệm gửi 1 email mẫu về email test cá nhân:
python scripts/send_live_debt_reminders.py --period 2026-08 --test-email abc@haophuong.com

# 3. KÍCH HOẠT GỬI THỰC TẾ (LIVE) CHO TOÀN BỘ SALES VÀ TRƯỞNG BU:
python scripts/send_live_debt_reminders.py --period 2026-08 --live

# 4. Chỉ gửi thực tế cho riêng Trưởng BU:
python scripts/send_live_debt_reminders.py --period 2026-08 --live --recipient-type MANAGERS

# 5. Chỉ gửi thực tế cho 1 BU cụ thể (Ví dụ BU Thang Máy):
python scripts/send_live_debt_reminders.py --period 2026-08 --live --bu BU_ELEVATOR
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
