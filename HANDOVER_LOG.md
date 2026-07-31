# HANDOVER LOG (Active Working Log)

> [!NOTE]
> Historical logs prior to 2026-07-24 11:28 have been archived to [docs/handover_archive/2026_07_archive.md](file:///d:/Sources/dashboard-report/docs/handover_archive/2026_07_archive.md).


## [2026-07-31 09:30:00] Task: Deep Audit Database vs Accountant Snapshot (30/07/2026)
- **Objective**: Phân tích chuyên sâu 100% chỉ số cả MTD (Tháng 7/2026) lẫn YTD (Lũy kế 01/01 - 30/07) đối soát giữa CSDL Hệ thống và Bảng Snapshot Kế toán (chốt 30/07/2026 lúc 7:00 AM).
- **Planned Modifications**:
  1. `scratch/full_ytd_mtd_audit.py`: Viết script đối soát tự động toàn bộ 23 BU và các chỉ số lõi.
  2. `Accounting_Tracking_History.md`: Bổ sung Mục 16 lưu trữ toàn bộ bảng đối soát MTD & YTD chi tiết.
- **Current Status**: **COMPLETED** — Đã hoàn thành đối soát sâu 100% MTD & YTD, cập nhật tài liệu `Accounting_Tracking_History.md` và `HANDOVER_LOG.md` tuân thủ SOP `CheckList.md`.

## [2026-07-31 08:25:00] Task: Handle Re-clicking Activation Link for Already Active Users
- **Objective**: Phân tách phản hồi trang Web cho Admin khi click lại link kích hoạt tài khoản đã được active từ trước (Tránh báo lại "Kích Hoạt Thành Công" làm nhầm lẫn Admin).
- **Planned Modifications**:
  1. `accounting/views/misa_api.py`: `ActivateUserAPIView` kiểm tra trạng thái `already_active = user.is_active` trước khi kích hoạt. Nếu `already_active == True`, truyền context `already_active=True` sang Template và KHÔNG gửi lại email cho User.
  2. `templates/auth/activation_response.html`: Hiển thị Banner `ℹ️ Tài Khoản Này Đã Được Kích Hoạt Từ Trước!` nếu `already_active == True`, hiển thị `🎉 Kích Hoạt Mức 2 Thành Công!` nếu vừa mới kích hoạt.
  3. `DocumentAPI_Report2026.md`: Cập nhật Mục 14 phản hồi API.
  4. `report2026/settings.py`: Khai báo `BACKEND_URL` để sinh link kích hoạt chuẩn xác cho Admin.
  5. `target.md`: Cập nhật lịch sử thay đổi.
- **Current Status**: **COMPLETED** — Đã hoàn thành 100% việc phân tách giao diện phản hồi khi Admin bấm lại link kích hoạt tài khoản đã active từ trước và bổ sung cấu hình BACKEND_URL.

## [2026-07-30 13:17:00] Task: Refactor Email & Web Response HTML to Django Templates
- **Objective**: Tái cấu trúc (Refactor) toàn bộ chuỗi HTML hardcode trong `sso_notifier.py` và `misa_api.py` sang các file Django HTML Templates chuẩn (`templates/emails/` và `templates/auth/`).
- **Planned Modifications**:
  1. `templates/emails/admin_sso_notification.html`: [NEW] Template Email gửi Admin.
  2. `templates/emails/user_activation_success.html`: [NEW] Template Email gửi User.
  3. `templates/auth/activation_response.html`: [NEW] Template trang Web phản hồi kích hoạt thành công.
  4. `templates/auth/activation_error.html`: [NEW] Template trang Web phản hồi lỗi kích hoạt.
  5. `accounting/services/sso_notifier.py`: Sử dụng `render_to_string`.
  6. `accounting/views/misa_api.py`: Sử dụng `user.last_login is None` để phân tách 3 trạng thái: Mới Đăng Ký vs Thử Đăng Nhập Lại Khi Chờ Duyệt vs Tài Khoản Cũ Bị Khóa.
  7. `accounting/views/dashboard_api.py`: Tái sử dụng helper `get_formatted_from_email()`.
  8. `report2026/settings.py`: Khai báo `ADMIN_NOTIFICATION_EMAILS` và `DEFAULT_FROM_EMAIL` fallback.
  9. `guildSendMail.md`: Cập nhật hướng dẫn `.env`.
  9. `DocumentAPI_Report2026.md`: Cập nhật Mục 14 cấu trúc Template.
  10. `target.md`: Cập nhật kiến trúc và sơ đồ luồng Email Template.
- **Current Status**: **COMPLETED** — Đã hoàn thành 100% việc tách HTML hardcode sang 4 Django HTML Templates, tích hợp render_to_string và render, cập nhật tài liệu và kiểm thử thành công.

## [2026-07-30 11:30:00] Task: Google SSO New User Email Notification & One-Click Activation Workflow
- **Objective**: Thêm tính năng tự động gửi Email thông báo tới Admin khi có người dùng mới đăng ký qua Google SSO (`is_active=False`), đính kèm Link Kích hoạt Nhanh (One-Click Activation URL), tự động bật `is_active=True` khi Admin click vào link và gửi mail thông báo cho User.
- **Files Modified**:
  1. `accounting/services/sso_notifier.py`: [NEW] Module sinh token ký số `TimestampSigner`, gửi email HTML thông báo cho Admin và User.
  2. `accounting/services/__init__.py`: Re-export sso_notifier helpers.
  3. `accounting/views/misa_api.py`: Tích hợp gửi mail thông báo trong `GoogleLoginAPI` và thêm [NEW] `ActivateUserAPIView`.
  4. `accounting/views/__init__.py`: Re-export `ActivateUserAPIView`.
  5. `accounting/urls.py`: Đăng ký endpoint `/api/auth/activate-user/`.
  6. `report2026/settings.py`: Thêm cấu hình `FRONTEND_URL` mặc định `https://report.haophuong.com/`.
  7. `DocumentAPI_Report2026.md`: Thêm Mục 14 mô tả quy trình & sequence diagram.
  8. `scratch/test_google_sso_activation.py`: Script kiểm thử tự động toàn bộ luồng.
- **Current Status**: **COMPLETED** — Đã hoàn thành 100% code, API, email notifier, test script và cập nhật tài liệu.

## [2026-07-29 11:50:00] Task: Document Phase 2 Business & Architecture Spec for Accountant Consultation
- **Objective**: Tổng hợp toàn bộ Kiến trúc Kỹ thuật, Thuật toán Dual Mapping, Đệ quy nợ nhóm và Biên soạn Bảng 4 câu hỏi trọng tâm để User làm việc với Kế toán nghiệp vụ.
- **Files Modified**:
  1. `docs/Phase2_Accounting_Business_Spec.md`: [NEW] Báo cáo chi tiết nghiệp vụ Phase 2 & Danh sách câu hỏi gửi Kế toán.
  2. `HANDOVER_LOG.md`: Cập nhật trạng thái bàn giao.
- **Current Status**: **PENDING (PRIORITY ITEM)** — Phase 1 & 2 đã hoàn thành 100% Code & Docs tại `target.md` và `docs/Phase2_Accounting_Business_Spec.md`. Đang tạm ngưng Phase 3 & 4 để chờ User chốt lại quy tắc với Kế toán nghiệp vụ.

## [2026-07-29 11:20:00] Task: Create Auto-Assign Customer Sales Script (`scripts/auto_assign_customer_sales.py`)
- **Objective**: Viết script tự động nhận diện Nhân viên Sales phát sinh giao dịch nhiều nhất trong sổ Bán hàng (`SalesTransaction`) và gán làm Sales phụ trách chính (`Customer.assigned_employee`) cho từng Khách hàng.
- **Files Modified**:
  1. `scripts/auto_assign_customer_sales.py`: [NEW] Script tự động gán Sales phụ trách Khách hàng từ sổ Bán hàng.
  2. `Run_Test_Scripts.md`: Bổ sung Mục 5.8 và Bảng Mục Lục Nhanh.
- **Current Status**: **COMPLETED** — Đã khởi tạo script và cập nhật tài liệu.

## [2026-07-29 10:45:00] Task: Create Department Tree & Staff Inspector Script (`scripts/show_department_tree.py`)
- **Objective**: Viết script hiển thị danh sách toàn bộ Phòng ban (`Department`), Trưởng phòng/Quản lý đại diện và danh sách từng Nhân viên trực thuộc kèm theo Sếp phụ trách.
- **Files Modified**:
  1. `scripts/show_department_tree.py`: [NEW] Script in cây phòng ban và danh sách nhân viên trực thuộc.
  2. `Run_Test_Scripts.md`: Bổ sung Mục 5.7 và Bảng Mục Lục Nhanh.
- **Current Status**: **COMPLETED** — Đã bổ sung tham số CLI `--sort-by` cho phép tuỳ chọn sắp xếp danh sách nhân viên theo Mã NV (`code`), Tên Chức danh (`title`), ID Chức danh (`title_id`) hoặc Họ tên (`name`).

## [2026-07-29 10:40:00] Task: Create Auto-Assign Manager Utility Script (`scripts/auto_assign_managers.py`)
- **Objective**: Viết script tự động nhận diện Trưởng phòng/Quản lý của từng Phòng ban (`Department`) và gán liên kết `manager` cho 100% nhân viên trong phòng ban đó, đồng thời liên kết Trưởng phòng tới Trưởng bộ phận cấp trên theo cây `parent_department`.
- **Files Modified**:
  1. `scripts/auto_assign_managers.py`: [NEW] Script tự động gán Manager cho nhân viên theo phòng ban.
  2. `Run_Test_Scripts.md`: Bổ sung Mục 5.6 và Bảng Mục Lục Nhanh.
- **Current Status**: **COMPLETED** — Đã khởi tạo script và cập nhật tài liệu.

## [2026-07-29 09:58:00] Task: Create Manager JobTitle & Employee Detection Utility Script (`scripts/detect_manager_titles.py`)
- **Objective**: Viết script quét tự động danh mục `JobTitle` và `EmployeeAssignment` để phát hiện các Chức danh Quản lý / Trưởng bộ phận và liệt kê nhân viên đang giữ vị trí quản lý.
- **Files Modified**:
  1. `scripts/detect_manager_titles.py`: [NEW] Script phát hiện chức danh quản lý và danh sách sếp/trưởng nhóm.
  2. `Run_Test_Scripts.md`: Bổ sung Mục 5.5 và Bảng Mục Lục Nhanh.
- **Current Status**: **COMPLETED** — Đã nâng cấp script nhóm chức danh theo Đơn vị / Phòng ban (`Department`) và đếm chính xác số lượng nhân viên thực tế duy nhất (`active & unique`).

## [2026-07-29 09:50:00] Task: Phase 2 Implementation - EmployeeReceivableSummary Model & Debt Calculation Engine
- **Objective**: Tạo Model `EmployeeReceivableSummary`, khởi tạo Migration 0044 và xây dựng Service Engine `employee_debt_calculator.py` hỗ trợ tính nợ cá nhân + đệ quy cộng dồn nợ nhóm cho Trưởng phòng/Trưởng nhóm.
- **Planned Modifications**:
  1. `accounting/models/performance.py`: Tạo model `EmployeeReceivableSummary`.
  2. `accounting/services/employee_debt_calculator.py`: Tạo engine tính toán nợ cá nhân & đệ quy nợ nhóm.
  3. `accounting/admin.py`: Đăng ký `EmployeeReceivableSummaryAdmin`.
- **Current Status**: **COMPLETED** — Đã tạo Model `EmployeeReceivableSummary`, re-export trong `models/__init__.py`, nâng cấp Service Engine `employee_debt_calculator.py` hỗ trợ Dual Mapping (trùng mã NV & assigned_employee) + đệ quy nợ nhóm, đăng ký `EmployeeReceivableSummaryAdmin` và cập nhật tài liệu hệ thống.

## [2026-07-29 09:45:00] Task: Phase 1 Implementation - Employee & Manager Debt Data Relationships
- **Objective**: Bổ sung liên kết `manager` trong `EmployeeAssignment` và `assigned_employee` trong `Customer`, tạo Django migration và cập nhật các Excel Resource tương ứng.
- **Planned Modifications**:
  1. `accounting/models/employee.py`: Thêm trường `manager` vào `EmployeeAssignment`.
  2. `accounting/models/organization.py`: Thêm trường `assigned_employee` vào `Customer`.
  3. `accounting/resources/employee.py` & `organization.py`: Thêm logic đọc `Mã người quản lý` & Sales phụ trách.
- **Current Status**: **COMPLETED** — Đã thêm trường `manager` vào `EmployeeAssignment`, trường `assigned_employee` vào `Customer`, tạo và apply Migration 0042, cập nhật `EmployeeResource` & `CustomerResource`, sửa lỗi `admin.E202` (`fk_name = 'employee'`) trong `accounting/admin.py` và cập nhật tài liệu hệ thống.

## [2026-07-29 09:40:00] Task: Document Employee & Manager Debt Calculation Architecture Spec in target.md
- **Objective**: Ghi nhận toàn bộ Giải pháp Kiến trúc 4 Trụ cột tính công nợ theo Nhân viên & Người quản lý nhóm (bao gồm góp ý quan trọng về lưu `manager` tại `EmployeeAssignment` để bảo toàn lịch sử SCD Type 2) vào [target.md](file:///d:/Sources/dashboard-report/target.md#L554).
- **Files Modified**:
  1. `target.md`: Thêm Mục `13. Kiến Trúc Tính Toán Công Nợ Theo Nhân Viên & Người Quản Lý Nhóm (Employee & Manager Debt Architecture Spec)`.
- **Current Status**: **COMPLETED** — Đã ghi nhận tri thức cố định vào `target.md`.

## [2026-07-29 09:15:00] Task: Audit and Reorganize Root Project Scripts
- **Objective**: Rà soát 7 script tại thư mục gốc (`root`), giữ lại 2 script CLI lõi (`download_report.py`, `import_specific_file.py`), chuyển 2 script debug/test (`test_download_ban_hang.py`, `test_import_customer_group.py`) sang `scripts/`, và lưu trữ 3 script dư thừa (`run_import.py`, `run_sync_so_du_nh.py`, `run_sync_tai_khoan_ct.py`) vào `scripts/legacy/`.
- **Planned Modifications**:
  1. Di chuyển file và cập nhật import path.
  2. Đồng bộ tài liệu `Run_Test_Scripts.md` và `DocumentAPI_Report2026.md`.
- **Current Status**: **COMPLETED** — Đã tái cấu trúc 7 script tại root, chuyển các file debug sang `scripts/`, lưu trữ script cũ vào `scripts/legacy/`, tạo script dọn dẹp `scratch/clean_old_root_files.py` và cập nhật tài liệu hệ thống.

## [2026-07-29 09:05:00] Task: Document `scripts/show_snapshot.py` in `Run_Test_Scripts.md`
- **Objective**: Tìm và bổ sung tài liệu hướng dẫn sử dụng cho script in Snapshot CSDL `scripts/show_snapshot.py` vào [Run_Test_Scripts.md](file:///d:/Sources/dashboard-report/Run_Test_Scripts.md) (Mục 5.4 và Bảng Mục Lục Nhanh).
- **Files Modified**:
  1. `Run_Test_Scripts.md`: Bổ sung Mục `5.4. Xem Báo Cáo Data Snapshot CSDL Ngay Lập Tức (show_snapshot.py)` và bảng mục lục.
- **Current Status**: **COMPLETED** — Đã cập nhật tài liệu đầy đủ.

## [2026-07-29 09:00:00] Task: Persist 7-Report MISA Playwright Automation Spec in target.md
- **Objective**: Lưu trữ toàn bộ quy trình 100% chi tiết của 7 báo cáo MISA vào `target.md` (Mục 6.3) làm tri thức cố định (Memory Persistence) cho các AI agent kế thừa.
- **Files Modified**:
  1. `target.md`: Thêm Mục `6.3. Danh sách từng bước chi tiết cho 7 Báo Cáo MISA Web (Chuẩn Mã Nguồn)`.
- **Current Status**: **COMPLETED** — Đã ghi nhận tri thức vào `target.md`.

## [2026-07-29 08:30:00] Task: Fix Parameter Selection Popup Closing Bug in MISA Automation
- **Objective**: Khắc phục triệt để sự cố modal "Chọn tham số báo cáo" bị đóng/ẩn tự động khi đang điền kỳ báo cáo ("Tháng này"/"Năm nay"), làm nghẽn toàn bộ tiến trình tải báo cáo Playwright MISA.
- **Planned Modifications**:
  1. `accounting/misa/report_exporter.py`: Loại bỏ phím `Escape` (`await page.keyboard.press("Escape")`) tại L506 & L535. Bỏ các lệnh `close_misa_popups(page)` thừa vãi ngay sau khi bật Modal (L416) và trước khi tương tác Kỳ báo cáo (L508, L537). Truyền `close_blockers=False` khi tìm dropdown options.
  2. `accounting/misa/browser.py`: Củng cố hàm JS `get_global_anti_popup_script()` (bảo vệ tuyệt đối các modal chứa `input`, `Kỳ báo cáo`, `Từ ngày`, `Đến ngày`, `Tài khoản`).
  3. `DocumentAPI_Report2026.md` & `target.md`: Đồng bộ tài liệu kỹ thuật về cơ chế bảo vệ Modal Tham Số.
- **Current Status**: **COMPLETED** — Đã loại bỏ phím Escape, dọn dẹp các lệnh close_misa_popups thừa, củng cố script Smart Anti-Popup bảo vệ Modal Tham Số và đồng bộ tài liệu hệ thống.

## [2026-07-29 08:15:00] Task: Triển khai Global Smart Anti-Popup Engine cho MISA Automation
- **Objective**: Triệt hạ 100% các loại thông báo, quảng cáo, banner, dialog cảnh báo bất ngờ của MISA bằng thuật toán Phân loại thông minh (Smart Detection) + Init Script Injection toàn cục.
- **Files Modified**:
  1. `accounting/misa/browser.py`: Tái cấu trúc `close_misa_popups(page)` thành **Smart Anti-Popup Engine** — phân biệt Modal Tham Số Báo Cáo vs Pop-up rác, tự bấm đóng hoặc xóa thẳng khỏi DOM. Bổ sung `get_global_anti_popup_script()`.
  2. `accounting/misa/automation.py`: Inject global anti-popup script via `context.add_init_script()`.
  3. `accounting/misa/report_exporter.py`: Gọi dọn dẹp popup thông minh ngay sau khi bật Modal Tham số Báo cáo.
- **Current Status**: **COMPLETED** — Đã triển khai xong code, sẵn sàng chạy test.

## [2026-07-29 08:00:00] Task: Fix ms-popup blocking Kỳ báo cáo selection — Download failures
- **Objective**: Khắc phục lỗi `ms-popup` chặn click vào combo `Kỳ báo cáo` → gây timeout 30s → download manager không có file → toàn bộ report download thất bại.
- **Root Cause**: Sau khi click "Chọn tham số", MISA hiện `ms-popup` (thông báo info, không phải concurrent login). Code cũ chỉ close popup có text "Đã có máy khác sử dụng" → miss popup dạng khác → `ms-popup` còn hiển thị và block pointer events lên combo input.
- **Files Modified**:
  1. `accounting/misa/browser.py` (L212-238): Mở rộng JS để close **mọi** `ms-popup` đang visible — thử click close button trước, fallback ẩn bằng CSS.
  2. `accounting/misa/report_exporter.py` (L500-543): Thêm `Escape` keypress + `handle_misa_popups()` trước khi click `ky_input`. Fallback `click_count=3` đổi sang `force=True`.
- **Current Status**: **COMPLETED** — Fix applied, cần verify ở lần chạy tự động sáng 30/07/2026.

## [2026-07-27 15:28:00] Task: Implement Employee Management System (Department, JobTitle, Employee, EmployeeAssignment) & Excel Import
- **Objective**: Thiết kế và triển khai các Model Django (`Department`, `JobTitle`, `Employee`, `EmployeeAssignment`), Resource import Excel `Danh_sach_nhan_vien.xlsx`, và đăng ký Django Admin.
- **Files Modified**:
  1. `accounting/models/employee.py` (**TẠO MỚI**): Định nghĩa `Department` (PK: department_code), `JobTitle` (AutoField PK), `Employee` (unique employee_code, full_name, gender, date_of_birth, identity_number, phone_number, email, is_active), `EmployeeAssignment` (FK → Employee, Department, JobTitle).
  2. `accounting/models/organization.py`: Xóa class `Employee` placeholder cũ.
  3. `accounting/models/transactions.py` + `debt.py`: Cập nhật import `Employee` từ `.employee`.
  4. `accounting/models/__init__.py` + `accounting/models.py`: Export 4 model mới.
  5. `accounting/resources/employee.py` (**TẠO MỚI**): `EmployeeResource` với `before_import_row` tự động get_or_create `Department`, `JobTitle`, `EmployeeAssignment`.
  6. `accounting/resources/__init__.py`: Export `EmployeeResource`.
  7. `accounting/tasks.py`: Thêm `DANH_SACH_NHAN_VIEN` và `NHAN_VIEN` vào `IMPORT_MAP` với `skip_delete=True`.
  8. `accounting/admin.py`: Đăng ký `DepartmentAdmin`, `JobTitleAdmin`, `EmployeeAdmin` (with `EmployeeAssignmentInline`), `EmployeeAssignmentAdmin`.
  9. `accounting/migrations/0041_...py`: Migration thủ công với `RunPython(copy_code_to_employee_code)` để migrate data cũ (`code`→`employee_code`, `name`→`full_name`) trước khi enforce unique index.
- **Current Status**: **COMPLETED** — Migration `0041` apply thành công. Bảng `departments`, `job_titles`, `employees`, `employee_assignments` đã tồn tại trong DB PostgreSQL.









- **Objective**: Restored 100% of Commit 57a0e59 download history clearing steps (clear download manager panel history `"Xóa hết lịch sử tải tệp"` -> confirm `"Có"` before exporting), select `"Mẫu chuẩn."` template via gear icon `.mi-setting__list-bold`, set default report period to `"Tháng này"`, and create standalone CLI script `download_report.py` supporting keyword arguments (`BAN_HANG`, `MUA_HANG`, `TON_KHO`, `CONG_NO_NCC`, `TUOI_NO_KH`, `TAI_KHOAN_CT`, `SO_DU_NH`, `ALL`).
- **Planned Modifications**:
  1. `report_exporter.py`: Restored pre-export download manager history clearing and gear template selection.
  2. `settings.py`: Set `MISA_REPORT_PERIOD_OPTION` default to `'Tháng này'`.
  3. `download_report.py`: Created CLI script supporting UTF-8 output and keyword arguments.
- **Current Status**: In Progress (SOP Step 3 Documentation updated, Step 4 System Audit passed, waiting for SOP Step 5 User Commit Approval).

## [2026-07-27 09:16:00] Task: Fix Standalone 'Chọn tất cả' Checkbox Selection (Exclude Header TH)
- **Objective**: Ensure Playwright targets ONLY the standalone checkbox element right next to the text label `'Chọn tất cả'` (e.g., `'Chọn tất cả 31355 vật tư được chọn'`, `'Chọn tất cả 20 khách hàng được chọn'`) and completely excludes table header (`th`/`thead`) checkboxes to select 100% of items and customers across all pages.
- **Planned Modifications**:
  1. `report_exporter.py`: Updated `check_all_select_all_checkboxes` Javascript DOM evaluation to filter out `th`/`thead` elements and click only the checkbox element bound to the `"Chọn tất cả"` text label.
- **Current Status**: Completed (Verified: `Successfully checked 3 standalone 'Chọn tất cả' checkboxes next to text label`, downloaded file size: `24,576 bytes`).






## [2026-07-27 08:45:00] Task: Execute Real End-to-End MISA Playwright Download (7 Reports)
- **Objective**: Execute real local Playwright automation for all 7 MISA reports (`BAN_HANG`, `MUA_HANG`, `TON_KHO`, `CONG_NO_NCC`, `TUOI_NO_KH`, `TAI_KHOAN_CT`, `SO_DU_NH`), verify file downloads in `media/auto_imports/`, and resolve any export timing/download triggers.
- **Planned Modifications**:
  1. `report_exporter.py`: Ensure direct export and download panel handlers trigger cleanly.
  2. Execute via local Python tool redirecting output to `scratch/misa_run.log`.
- **Current Status**: In Progress (Executing real automation run).


### 1. Current Objective
Sửa triệt để 3 lỗi làm cho tiến trình tự động tải báo cáo MISA qua Playwright thất bại toàn bộ (0/7 báo cáo):
1. `close_misa_popups` tự động ẩn nhầm backdrop/phông nền làm hỏng giao diện Dialog "Chọn tham số", khiến nút "Đồng ý" / "Xem báo cáo" không submit được và nút "Xuất khẩu" không xuất hiện.
2. `login_to_misa` bị crash ném exception khi retry đăng nhập do MISA SSO tự động redirect về trang `actapp.misa.vn`.
3. Xử lý mở Combobox chọn Kỳ báo cáo ("Năm nay" / "Tháng này") trước khi bấm chọn giá trị period.

### 2. Planned Modifications
1. `accounting/misa/browser.py`:
   - Sửa `close_misa_popups` không ẩn bừa bãi `.ms-popup-box-background` và `.ms-popup--background`.
   - Thêm cờ `close_blockers=False` trong `find_locator_in_any_frame` khi tìm kiếm phần tử bên trong modal dialog.
   - Sửa `login_to_misa` xử lý mượt mà khi đã tự động redirect vào `actapp.misa.vn` mà không ném exception `Could not find or fill MISA email input field`.
2. `accounting/misa/report_exporter.py`:
   - Thêm thao tác click mở combobox Kỳ báo cáo trước khi chọn `target_period`.
   - Bổ sung selector nút Xuất khẩu linh hoạt hơn (hỗ trợ `ms-dropdown`, `.icon-export`, text `Xuất khẩu`).
3. `DocumentAPI_Report2026.md` & `target.md`: Đồng bộ mô tả xử lý Playwright MISA automation.

- **Completed**: Đã hoàn thành sửa chữa 100% các vấn đề phát sinh trong tự động hóa MISA:
  1. Loại bỏ lệnh ẩn phông nền `backdrops` toàn cục trong `close_misa_popups` và thêm flag `close_blockers=False` cho `find_locator_in_any_frame` để bảo vệ Dialog "Chọn tham số".
  2. Bổ sung kiểm tra SSO tự động redirect thành công trong `login_to_misa`, tránh ném exception ngắt luồng.
  3. Sửa hàm `check_all_select_all_checkboxes` chuyển sang xử lý JS lọc `!isChecked` và loại bỏ lặp `page.main_frame` để tuyệt đối KHÔNG bị click đúp 2 lần gây nhả bỏ (uncheck) checkbox.
  4. Sửa hàm `remove_nhat_branches` quét thẻ tag chip chứa `_Nhật` và tự động click nút `x` gỡ bỏ chi nhánh `_Nhật`.
  5. Sửa logic tích chọn checkbox "Bao gồm số liệu chi nhánh phụ thuộc" qua JS đảm bảo kích hoạt chuẩn `checked-true`.
  6. Rà soát tài liệu hệ thống (`target.md` mục 6, 7, 8): Cập nhật tự động chọn bổ sung 2 tài khoản `641` và `642` trong báo cáo `TAI_KHOAN_CT` (Sổ chi tiết các tài khoản) cùng với `111, 112, 341` để phục vụ tính toán Chi phí vận hành (OPEX).
  7. Bổ sung chuẩn hóa Unicode NFC (`.normalize('NFC')`) trong Javascript để chống mọi lỗi lệch bảng mã font chữ Tiếng Việt khi tương tác với MISA DOM.
  8. Khắc phục triệt để lỗi phạm vi Element: Giới hạn độ dài chuỗi text (`length < 60` cho Chọn tất cả và `length < 50` cho tag Chi nhánh) để tuyệt đối không bị nhận diện nhầm cửa sổ Popup chính (`div.ms-popup`), đảm bảo các ô checkbox không bị toggle nhả ngược lại.
  9. Tối ưu mở combobox Kỳ báo cáo trước khi chọn option 'Năm nay'/'Tháng này'.
  10. Bổ sung nhật ký chi tiết cho bước kiểm tra ô Chi nhánh (`Checked 'Chi nhánh' box: No branch tags containing '_Nhật' found`).
  11. Sửa lỗi Timeout 60s khi Xuất Excel: Tăng thời gian chờ nút 'Tải tệp' từ 10s lên 45s (30 lần x 1.5s) phù hợp với thời gian MISA kết xuất báo cáo lớn ngầm.










### 1. Current Objective
Tạo script tiêu chuẩn `scripts/sync_current_month.py` chuyên trách tải, thay thế dữ liệu và cập nhật KPI cho riêng **Tháng hiện tại** (`period_option="Tháng này"`), giữ nguyên toàn bộ ID và dữ liệu các tháng quá khứ.

### 2. Planned Modifications
1. `scripts/sync_current_month.py` [NEW]:
   - Tải báo cáo MISA Tháng hiện tại qua Playwright.
   - Thay thế dữ liệu cũ của riêng tháng hiện tại và nạp Excel mới vào CSDL.
   - Cập nhật lại KPI (BUPerformance) Tháng hiện tại cho Tổng công ty và 22 BU.
   - Đồng bộ kho hàng cuối kỳ.
2. `DocumentAPI_Report2026.md` & `target.md`: Cập nhật tài liệu kỹ thuật cho script mới.


---

## [2026-07-24 11:36:00] Task: Fix OPEX Duplicated Addition (`opex_actual = opex_trans_actual`)

### 1. Current Objective
Sửa lỗi tính trùng Chi phí vận hành (OPEX) do trước đây cộng dồn `plan_elapsed` (kế hoạch phân bổ chi phí ngày) vào `opex_trans_actual` (thực tế MISA TK 641+642), khiến OPEX thực tế bị đẩy lên 5.282 tỷ thay vì số phát sinh MISA thực tế 1.762 tỷ.

### 2. Planned Modifications
1. `accounting/tasks.py`:
   - Thay đổi `opex_actual = Decimal(str(opex_trans_actual))` trong `update_single_bu_performance`, loại bỏ cộng trùng `plan_elapsed`.
   - Giữ nguyên `opex_plan = target_plan.month_opex_target` (Kế hoạch OPEX tháng, ví dụ 4.851.250.000 VNĐ cho Global).
2. `scripts/show_snapshot.py`:
   - Bổ sung hiển thị `Target` và tỉ lệ `% Đạt` cho Chi phí OPEX.
3. `DocumentAPI_Report2026.md` & `target.md`: Đồng bộ mô tả công thức tính OPEX.

### 3. Current Status

---

## [2026-07-24 11:41:00] Task: Update Legacy Section 7 OPEX Formula in `target.md`

### 1. Current Objective
Cập nhật lại phần tài liệu cũ Mục 7 trong `target.md` (vốn ghi sai công thức cũ `opex_actual = sum(daily_opex_plan) + sum(daily_opex_actual)`) về chuẩn công thức thực tế mới `opex_actual = sum(daily_opex_actual)` để toàn bộ hệ thống tài liệu đồng bộ 100%.

### 2. Planned Modifications
- `target.md` (Mục 7): Cập nhật công thức `opex_actual = sum(daily_opex_actual)` (chỉ tính phát sinh Nợ TK 641 + 642 thực tế từ MISA), ghi chú rõ loại bỏ cộng trùng `daily_opex_plan`.

### 3. Current Status

---

## [2026-07-24 11:42:00] Task: Enforce User Explicit Directive on OPEX Formula (`opex_actual = plan_elapsed + opex_trans_actual`)

### 1. Current Objective
Theo chỉ đạo trực tiếp và xác nhận chính thức từ User ("công thức dưới mới đúng đó"), giữ nguyên và áp dụng công thức thiết kế chuẩn của hệ thống:
$$\text{opex\_actual} = \sum_{d=1}^{D_{target}} \text{daily\_opex\_plan}(d) + \sum_{d=1}^{D_{target}} \text{daily\_opex\_actual}(d)$$

### 2. Planned Modifications
1. `accounting/tasks.py`:
   - Áp dụng `opex_actual = plan_elapsed + opex_trans_actual` (với ép kiểu `Decimal` nhất quán để đảm bảo an toàn tuyệt đối, không phát sinh lỗi float/Decimal).
2. `target.md` (Mục 7 & Mục 48): Giữ và đồng bộ chuẩn công thức theo đúng chỉ đạo của User.

### 3. Current Status

---

## [2026-07-24 11:44:00] Task: Consolidate Duplicate OPEX Sections in `target.md`

### 1. Current Objective
Loại bỏ Mục 48 bị lặp lại trong `target.md` và hợp nhất toàn bộ thông tin tài liệu OPEX về duy nhất **Mục 7. Chi phí vận hành (OPEX)** làm nguồn thông tin gốc (Single Source of Truth).

### 2. Planned Modifications
- `target.md`: Cập nhật chi tiết Mục 7 và xóa Mục 48 bị trùng lặp, giữ tài liệu gọn gàng và không bị trùng lặp thông tin.

### 3. Current Status

---

## [2026-07-24 11:49:00] Task: Execute Modular Project Refactoring (Phases 1 - 5)

### 1. Current Objective
Tái cấu trúc (refactor) các tệp mã nguồn khổng lồ (`accounting/resources.py`, `accounting/misa_tasks.py`, `accounting/tasks.py`, `HANDOVER_LOG.md`, `template/`) thành các gói module nhỏ gọn, đảm bảo tương thích ngược 100% và giảm 60-70% dung lượng token context khi đọc/ghi.

### 2. Planned Modifications
1. **Phase 1: `accounting/resources.py`** $\rightarrow$ gói `accounting/resources/` (`sales.py`, `purchase.py`, `finance.py`, `debt.py`, `inventory.py`). Wrapper `resources.py` re-export 100% classes.
2. **Phase 2: `accounting/misa_tasks.py`** $\rightarrow$ gói `accounting/misa/` (`browser.py`, `reports.py`, `automation.py`). Wrapper `misa_tasks.py` re-export Celery tasks.
3. **Phase 3: `accounting/tasks.py`** $\rightarrow$ gói `accounting/services/` (`kpi_calculator.py`, `inventory_sync.py`). Wrapper `tasks.py` giữ Celery task definitions.
4. **Phase 4: Archiving `HANDOVER_LOG.md`** $\rightarrow$ Rút gọn `HANDOVER_LOG.md`, lưu vết cũ vào `docs/handover_archive/2026_07_archive.md`.
5. **Phase 5: Template UI Modularization** $\rightarrow$ Bóc tách CSS & JS ra `static/css/` và `static/js/`.

### 3. Current Status
- **Completed (Phase 1 & Phase 4)**: 
  - Đã thực thi xong **Phase 1**: Tách `accounting/resources.py` (927 lines) thành gói module `accounting/resources/` (`bulk.py`, `sales.py`, `purchase.py`, `finance.py`, `debt.py`, `inventory.py`), giữ `resources.py` làm wrapper re-export 100% classes (Pass 33/34 django tests & `manage.py check` 0 errors).
  - Đã thực thi xong **Phase 4**: Lưu trữ 778 dòng log cũ của `HANDOVER_LOG.md` vào `docs/handover_archive/2026_07_archive.md`, rút gọn `HANDOVER_LOG.md` về 166 lines.

---

## [2026-07-24 11:57:00] Task: Execute Backend Modular Package Refactoring (Phase 2A - 2D)

### 1. Current Objective
Thực thi tái cấu trúc toàn bộ mã nguồn Backend Python (`accounting/tasks.py`, `accounting/misa_tasks.py`, `accounting/views.py`, `accounting/models.py`) thành các gói module chuyên trách (packages) theo nguyên lý DRY & Single Responsibility, giữ 100% tương thích ngược cho tất cả các câu lệnh import hiện tại.

### 2. Planned Modifications
1. **Phase 2A: `accounting/tasks.py` (945 lines)** $\rightarrow$ gói `accounting/services/` (`kpi_calculator.py`, `inventory_sync.py`, `period_parser.py`). Wrapper `tasks.py` giữ Celery task definitions.
2. **Phase 2B: `accounting/misa_tasks.py` (1,594 lines)** $\rightarrow$ gói `accounting/misa/` (`browser.py`, `locators.py`, `report_exporter.py`, `automation.py`). Wrapper `misa_tasks.py` re-export Celery tasks.
3. **Phase 2C: `accounting/views.py` (629 lines)** $\rightarrow$ gói `accounting/views/` (`dashboard_api.py`, `collection_api.py`, `inventory_api.py`, `misa_api.py`). Wrapper `views.py` re-export API views.
4. **Phase 2D: `accounting/models.py` (564 lines)** $\rightarrow$ gói `accounting/models/` (`organization.py`, `master_data.py`, `transactions.py`, `debt.py`, `performance.py`). Wrapper `models.py` re-export Django models.

### 3. Current Status
- **Completed (Phase 2A - Phase 2D)**:
  - **Phase 2A (`accounting/services/`)**: Tách `tasks.py` (945 lines) $\rightarrow$ `services/` (`kpi_calculator.py`, `inventory_sync.py`, `period_parser.py`, `__init__.py`). `tasks.py` rút gọn về 75 lines wrapper.
  - **Phase 2B (`accounting/misa/`)**: Tách `misa_tasks.py` (1,594 lines) $\rightarrow$ `misa/` (`browser.py`, `locators.py`, `report_exporter.py`, `automation.py`, `__init__.py`). `misa_tasks.py` rút gọn về 55 lines wrapper.
  - **Phase 2C (`accounting/views/`)**: Tách `views.py` (629 lines) $\rightarrow$ `views/` (`dashboard_api.py`, `collection_api.py`, `inventory_api.py`, `misa_api.py`, `__init__.py`). `views.py` rút gọn về 20 lines wrapper.
  - **Phase 2D (`accounting/models/`)**: Tách `models.py` (564 lines) $\rightarrow$ `models/` (`organization.py`, `master_data.py`, `transactions.py`, `debt.py`, `performance.py`, `__init__.py`). `models.py` rút gọn về 20 lines wrapper.
  - Tương thích ngược 100% cho toàn bộ Celery tasks, API Views và Model imports.

---

## [2026-07-24 13:09:00] Task: Management Commands Consolidation (`sync_misa.py`) & Root Cleanup

### 1. Current Objective
Theo chỉ thị trực tiếp từ User ("phần template/ không cần đụng đến nhé"), bỏ qua việc chỉnh sửa `template/`. Tập trung gộp toàn bộ các script bảo trì/đồng bộ MISA riêng lẻ ở root (`run_import.py`, `run_sync_so_du_nh.py`, `run_sync_tai_khoan_ct.py`...) thành Django Custom Management Command tiêu chuẩn `python manage.py sync_misa`.

### 2. Planned Modifications
1. `accounting/management/commands/sync_misa.py` [NEW]:
   - Hỗ trợ các options: `--action` (`all`, `download`, `import`), `--prefix`, `--period`.
2. Dọn dẹp script dư thừa ngoài thư mục root sau khi command chuyển đổi thành công.

### 3. Current Status
- **Completed**: Đã hoàn thành tạo Django Custom Management Command `accounting/management/commands/sync_misa.py`, hỗ trợ đầy đủ các tham số `--action`, `--prefix`, `--period`, `--file`. Dữ liệu chạy thử nghiệm đồng bộ chuẩn xác.

---

## [2026-07-24 13:21:00] Task: Technical QA & Documentation Standardization (DocumentAPI_Report2026.md, target.md, database_mapping.md)

### 1. Current Objective
Thực thi rà soát chéo (cross-check) và chuẩn hóa toàn bộ 3 tệp tài liệu kỹ thuật chính theo phê duyệt từ User:
1. Sửa lỗi đứt đoạn FAQ (khôi phục đầy đủ Q3 đến Q8 trong `DocumentAPI_Report2026.md`).
2. Cập nhật cơ chế `Targeted Chunk Deletion` và điều chỉnh lại 100% đường dẫn file/dòng code sang gói `accounting/models/` và `accounting/services/`.
3. Bổ sung mô tả các Django Custom Management Commands (`sync_misa`, `calculate_bu_performance`, `calculate_global_performance`, `createdefaultuser`), mô tả `scripts/` và model `BankBalance`.
4. Gom nhóm (consolidate) các nội dung mô tả trùng lặp (`EXCLUDED_*` rules, `actual_sales` vs `sales_amount`) và sử dụng link tham chiếu (anchor link).

### 2. Current Status
- **Completed**: Đã hoàn tất 100% việc chuẩn hóa tài liệu, không làm hỏng cấu trúc Markdown, đáp ứng hoàn toàn các yêu cầu rà soát QA.

---

## [2026-07-24 13:32:00] Task: Documentation Extraction (Run_Test_Scripts.md)

### 1. Current Objective
Tái cấu trúc file `DocumentAPI_Report2026.md` theo yêu cầu từ User:
1. Cắt toàn bộ nội dung Mục 5 (`## 5. Hướng dẫn chạy và thao tác với dự án dành cho bạn`).
2. Tạo file mới `Run_Test_Scripts.md` tại thư mục gốc và dán toàn bộ nội dung hướng dẫn thiết lập môi trường, cài đặt, chạy server + các script/commands kiểm thử.
3. Thay thế Mục 5 trong `DocumentAPI_Report2026.md` bằng một đoạn Note ngắn gọn kèm anchor link trỏ về `Run_Test_Scripts.md`.

### 2. Current Status
- **Completed**: Đã tạo thành công `Run_Test_Scripts.md`, bổ sung đầy đủ các Custom Commands và Helper Scripts, đồng thời cập nhật anchor link sạch sẽ trong `DocumentAPI_Report2026.md`.


















































































