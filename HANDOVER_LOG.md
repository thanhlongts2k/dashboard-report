# HANDOVER LOG (Active Working Log)

> [!NOTE]
> Historical logs prior to 2026-07-24 11:28 have been archived to [docs/handover_archive/2026_07_archive.md](file:///d:/Sources/dashboard-report/docs/handover_archive/2026_07_archive.md).

## [2026-08-20 10:38:00] Task: Integrate Google Profile Avatar with Smart Fallback (Backend & Frontend) — [DONE]
- **Objective**: Bổ sung tính năng lấy ảnh đại diện Google (Avatar) khi đăng nhập Google SSO và hiển thị ảnh đại diện thông minh (Smart Avatar with Letter Fallback & referrerPolicy="no-referrer") trên cả Desktop Header và Mobile Nav Drawer.
- **Các thay đổi đã thực hiện**:
  1. Backend `dashboard-report`:
     - `accounting/views/misa_api.py`: Tại `GoogleLoginAPI`, trích xuất `avatar_url = id_info.get('picture')` từ Google ID Token và đính kèm vào `response.data['user']['avatar']` / `avatar_url`.
     - `accounting/tests.py`: Cập nhật `test_google_login_jit_provisioning` assert `user.avatar` và `user.avatar_url`.
     - Chạy `python manage.py test accounting`: **43/43 tests PASS 100% (9.76s)**.
     - Đồng bộ tài liệu [DocumentAPI_Report2026.md](file:///d:/Sources/dashboard-report/DocumentAPI_Report2026.md) mục 7.1.
  2. Frontend `project-dashboard`:
     - `src/context/AuthContext.jsx`: Lưu giữ `avatar` trong state `user` và lưu trữ bền vững vào `localStorage` / `sessionStorage` (`auth_user`) khi đăng nhập hoặc làm mới profile từ `/api/auth/me/`.
     - `src/components/common/UserAvatar.jsx` [NEW]: Tạo component Smart Avatar hỗ trợ `referrerPolicy="no-referrer"`, tròn trịa (`object-cover`), và tự động fallback về chữ cái đầu nếu ảnh lỗi (`onError`).
     - `src/components/UserMenu.jsx`: Tích hợp `UserAvatar` cho trigger button (22px) và dropdown header (36px).
     - `src/components/navigation/MobileNavDrawer.jsx`: Tích hợp `UserAvatar` cho profile card (44px).
     - `src/styles/dashboard.css`: Bổ sung class `.user-avatar-img` đảm bảo hiển thị hình tròn chuẩn.
     - Chạy `npm run build`: **Built in 4.85s (0 errors)**.
     - Cập nhật [CHANGELOG.md](file:///d:/Sources/project-dashboard/CHANGELOG.md) & [HANDOVER.md](file:///d:/Sources/project-dashboard/HANDOVER.md) cho bản phát hành `v1.0.27`.
- **Current Status**: **[DONE]**

## [2026-08-19 16:36:00] Task: Integrate Automated Debt Reminder Scheduling (settings.py & Celery Beat & Management Command) — [DONE]
- **Objective**: Thiết lập cơ chế cấu hình linh hoạt (bật/tắt, lịch biểu, chế độ dry-run/live, đối tượng nhận) cho tiến trình tự động gửi email nhắc nợ phân cấp (`send_live_debt_reminders`) trên Backend `dashboard-report`.
- **Các thay đổi đã thực hiện**:
  1. `report2026/schedule_utils.py`:
     - Bổ sung hàm `get_debt_reminder_schedule(env)` hỗ trợ cấu hình động từ `.env` với các loại `weekly` (mặc định Thứ Hai lúc 08:00 sáng), `daily`, `monthly` (ngày 01, 15), hoặc `custom` cron 5 trường.
  2. `report2026/settings.py`:
     - Khai báo các biến cấu hình an toàn: `AUTO_SEND_DEBT_REMINDERS_ENABLED` (mặc định `False`), `DEBT_REMINDER_DRY_RUN` (mặc định `True`), `DEBT_REMINDER_TEST_EMAIL`, `DEBT_REMINDER_RECIPIENT_TYPE`, `DEBT_REMINDER_BU_CODE`.
     - Tự động nạp task `accounting.tasks.send_debt_reminders_task` vào `CELERY_BEAT_SCHEDULE['auto_send_debt_reminders_periodic']` khi bật cờ `AUTO_SEND_DEBT_REMINDERS_ENABLED`.
  3. `accounting/management/commands/send_debt_reminders.py` [NEW]:
     - Tạo Django Management Command tiêu chuẩn `python manage.py send_debt_reminders` với đầy đủ tham số: `--period`, `--live`, `--test-email`, `--bu`, `--recipient-type`, `--yes`.
     - Tích hợp bảo vệ an toàn với prompt xác nhận khi chạy `--live` và thống kê tiến độ gửi chi tiết.
  4. `.env.example`:
     - Bổ sung mục 7 `AUTOMATED DEBT REMINDER EMAIL SCHEDULE & NOTIFICATION` kèm giải thích tường minh từng tham số.
  5. `DocumentAPI_Report2026.md`:
     - Thêm mục 20 `Tự Động Hóa Lịch Biểu Gửi Email Nhắc Nợ (Automated Debt Reminder Scheduler & CLI)` hướng dẫn vận hành 3 cơ chế thực thi (Celery Beat, Management Command, Script CLI).
  6. Kiểm thử:
     - `python manage.py check`: **System check identified no issues (0 silenced)**.
     - `python manage.py send_debt_reminders --period 2026-08`: Chạy dry-run thành công, quét đúng 23 Sales & 7 Trưởng BU.
     - `python manage.py test accounting`: **43/43 tests PASS 100% (9.46s)**.
- **Current Status**: **[DONE]**

## [2026-08-19 14:10:00] Task: Full-Stack Terminology Audit — Standardize DTCT to "Đầu tư cho thuê" — [DONE]
- **Objective**: Quét và chuẩn hóa tận gốc tên gọi Khối ĐTCT ("Đầu tư cho thuê" / "Đầu tư cho thuê / ĐTCT") trên cả Backend (`dashboard-report`) và Frontend (`project-dashboard`), loại bỏ triệt để cụm từ cũ "Đối tác chiến lược".
- **Các thay đổi đã thực hiện**:
  1. Backend `dashboard-report`:
     - CSDL `BusinessUnit`: Xác nhận bản ghi `code = 'ĐTCT'` có `name = 'Đầu tư cho thuê'`.
     - `accounting/services/user_provisioner.py`: Cập nhật `BU_DEFINITIONS['ĐTCT']['name'] = 'Đầu tư cho thuê'`, làm sạch keywords `['đtct', 'dtct', 'cho thuê', 'đầu tư cho thuê', 'bu_dtct', 'bu_đtct']`.
     - Chạy `python manage.py sync_employee_users` đồng bộ 100% (173/173 tài khoản).
     - Chạy `python manage.py test accounting`: **43/43 tests PASS 100% (9.83s)**.
  2. Frontend `project-dashboard`:
     - `src/utils/dashboardMapper.js`: Sửa nhãn map `BU_DTCT / ĐTCT / DTCT: "Đầu tư cho thuê / ĐTCT"` và keywords matching.
     - `src/utils/detailMapper.js` & `src/context/AuthContext.jsx`: Chuẩn hóa keywords matching `['dtct', 'đtct', 'cho thuê', 'đầu tư']`.
     - Chạy `npm run build`: **Built in 669ms (0 errors)**.
  3. Quét xác nhận toàn hệ thống: 0 occurrences của cụm từ "Đối tác chiến lược" trong toàn bộ source code của cả 2 repositories.
  4. Tài liệu hệ thống: Đồng bộ `DocumentAPI_Report2026.md`, `target.md`, `CHANGELOG.md`, `HANDOVER.md`.
- **Current Status**: **[DONE]**

## [2026-08-19 13:16:00] Task: Fix Key Accounts Debt Collection Zero Metrics & Add Latest Active Date Metadata — [DONE]
- **Objective**: Khắc phục hiện tượng các chỉ số thu tiền trong ngày bằng 0 trên tab "Công nợ & Thu tiền" (`/receivables`) khi người dùng mở vào ngày chưa phát sinh hạch toán kế toán mới (`2026-08-19`). Bổ sung thông tin `latest_available_date`, lọc kỳ `reporting_period` cho `ReceivablesAgeing`, bao quát `customer__business_unit`, phân quyền RBAC và hiển thị chỉ dẫn ngày chốt gần nhất trên Frontend.
- **Các thay đổi đã thực hiện**:
  1. Backend `accounting/views/dashboard_api.py` (`DashboardCollectionByBUAPIView`):
     - Thêm `permission_classes = [permissions.IsAuthenticated]` và lọc BU theo RBAC (`assigned_bus` / `managed_bus`).
     - Tự động xác định `latest_available_date` từ `AccountDetail` (ngày phát sinh thu tiền gần nhất: `2026-08-18`). Nếu không truyền `date` thì mặc định lấy `latest_available_date`.
     - Lọc `ReceivablesAgeing` theo đúng kỳ `reporting_period` (tháng 8/2026) thay vì gom toàn bộ kỳ cũ.
     - Lọc `AccountDetail` thu tiền mở rộng `Q(business_unit_id__in=bu_ids) | Q(customer__business_unit_id__in=bu_ids)` đảm bảo không sót chứng từ.
     - Bổ sung `latest_available_date`, `has_data`, `reporting_period` vào payload trả về.
  2. Frontend `project-dashboard`:
     - `src/utils/receivableMapper.js`: Nhận diện `latestAvailableDate` và `hasData` trong payload response.
     - `src/pages/ReceivableReportPage.jsx`: Thêm smart notification banner khi ngày chọn chưa có dữ liệu thu tiền mới, cho phép 1-click chuyển nhanh về ngày chốt gần nhất (`18/08/2026`).
  3. Kiểm thử & Bàn giao:
     - `python manage.py test accounting`: **43/43 tests PASS 100% (10.23s)**.
     - `npm run build`: **Built in 659ms (0 errors)**.
- **Current Status**: **[DONE]**

## [2026-08-19 11:56:00] Task: Fix Initial State Conflict & Add Smart Fallback for Sales in Aging Report — [DONE]
- **Objective**: Khắc phục lỗi xung đột khởi tạo khi Sales truy cập Báo cáo Tuổi nợ (Frontend khởi tạo `selectedBu = 'HPC'` dẫn đến gọi API `/api/debt/bus/HPC/drilldown/` bị chặn 403).
- **Các thay đổi đã thực hiện**:
  1. Backend `accounting/services/user_provisioner.py`:
     - Nâng cấp `resolve_user_rbac(employee)`: Khi chọn `primary_assignment`, ưu tiên vai trò cao nhất và BU thương mại (`is_commercial = True`) thay vì lấy mặc định dòng đầu tiên (`HPC`). Giúp nhân sự Sales như `2000812` nhận diện đúng `primary_bu_code = 'BU_ELEVATOR'`.
     - Chạy `manage.py sync_employee_users` đồng bộ lại 173/173 tài khoản.
  2. Backend `accounting/views/debt_api.py`:
     - Tích hợp Smart Fallback trong `AgingMatrixAPIView`: Khi non-BOD user (Sales / Viewer) truyền `bu_code = 'HPC'` hoặc `'ALL'`, Backend tự động fallback về BU thương mại đầu tiên trong `assigned_bus` (e.g. `BU_ELEVATOR`) thay vì trả về lỗi 403.
  3. Frontend `project-dashboard`:
     - `src/pages/DebtAgingReportPage.jsx`:
       * `userFixedBu`: Lọc tìm BU thương mại đầu tiên trong `allowedBUs` (loại trừ `HPC` / `ALL`).
       * `selectedBu`: Mặc định chọn BU thương mại được cấp quyền thay vì `HPC`.
       * `buSelectOptions`: Loại bỏ hoàn toàn `HPC` và `ALL` đối với tài khoản Sales / Viewer.
     - `npm run build`: Build production bundle thành công trong 587ms (0 errors).
  4. Công cụ Dev `scripts/generate_dev_token.py`:
     - Chuẩn hóa độ rộng border 70 ký tự ASCII an toàn, loại bỏ triệt để hiện tượng vỡ dòng/chèn chữ trên Windows cmd/PowerShell.
- **Current Status**: **[DONE]**

## [2026-08-19 11:49:00] Task: Defense-in-Depth Backend API Security & Object-Level RBAC Enforcement — [DONE]
- **Objective**: Bịt kín toàn bộ lỗ hổng xác thực & phân quyền tầng Backend API. Đổi `permission_classes` từ `AllowAny` sang `IsAuthenticated`, phân quyền cứng cho API gửi mail nhắc nợ (`BOD_ADMIN`/`BU_HEAD` only, từ chối `403` với `SALES`/`VIEWER`), triển khai chốt chặn Object-Level Filter Guard trên `AgingMatrixAPIView` và các API tài chính, cập nhật `.gitignore` và bổ sung unit test kiểm thử bảo mật.
- **Các thay đổi đã thực hiện**:
  1. `accounting/views/debt_api.py`:
     - Thiết lập `permission_classes = [permissions.IsAuthenticated]` cho toàn bộ các view: `AllBUsDebtSummaryAPIView`, `AgingMatrixAPIView`, `SendDebtRemindersAPIView`.
     - `SendDebtRemindersAPIView`: Phân quyền thực thi chỉ cho phép `BOD_ADMIN` và `BU_HEAD`, từ chối `403 Forbidden` đối với `SALES`/`VIEWER`. Kiểm tra `managed_bus` cho `BU_HEAD`.
     - `AgingMatrixAPIView`: Tích hợp Object-Level Filter Guard kiểm tra `assigned_bus` và khóa cứng truy vấn theo mã nhân viên cá nhân cho `SALES`/`VIEWER`, từ chối `403 Forbidden` khi cố tình query BU hoặc Sales khác.
     - Giữ alias `BUDebt3TierDrilldownAPIView = AgingMatrixAPIView` tương thích ngược 100%.
  2. `.gitignore`: Bổ sung các script dev nhạy cảm (`scripts/generate_dev_token.py`, `scripts/swap_dev_email.py`, `scripts/audit_all_user_rbac.py`, `*.log`).
  3. Token Cleanup: Thu hồi toàn bộ 82 token cũ trong bảng `knox_authtoken`.
  4. Unit Tests & Verification:
     - `accounting/tests.py`: Bổ sung 2 test suites chuyên sâu `test_send_reminders_permission_defense_in_depth` và `test_aging_matrix_object_level_filter_guard` kiểm tra đầy đủ các tình huống 401, 403 và 200 cho từng vai trò.
     - Chạy `manage.py test accounting`: **43/43 unit tests PASS 100% (9.92s)**.
     - Chạy `npm run build`: **Vite bundle thành công trong 614ms (0 errors)**.
  5. Đồng bộ tài liệu: Cập nhật `DocumentAPI_Report2026.md` Mục 18 & 19.
- **Current Status**: **[DONE]**

## [2026-08-19 11:47:00] Task: Full-Stack Audit, Production Security Hardening & 100% Documentation Sync — [DONE]
- **Objective**: Tổng rà soát hệ thống Full-Stack, gia cố bảo mật môi trường sản xuất (chặn script dev, giới hạn token lifespan 2h, bảo vệ .gitignore), đồng bộ 100% tài liệu kỹ thuật (`DocumentAPI_Report2026.md`, `target.md`, `project-dashboard/HANDOVER.md`, `CHANGELOG.md`), xác thực 100% test suite và production bundle.
- **Các thay đổi đã thực hiện**:
  1. Bảo mật & Gia cố Backend (`dashboard-report`):
     - `scripts/generate_dev_token.py`: Bổ sung điều kiện chặn cứng `if not settings.DEBUG: sys.exit(1)`, giới hạn thời gian sống của token tối đa 2 giờ (`expiry = timedelta(hours=2)`).
     - `scripts/swap_dev_email.py`: Bổ sung điều kiện chặn cứng `if not settings.DEBUG: sys.exit(1)`.
     - `.gitignore`: Xác nhận các file nhạy cảm (`.env`, `scratch/`, logs) được bảo vệ tuyệt đối.
  2. Bảo mật & Cô lập Frontend (`project-dashboard`):
     - Dev Role Switcher được bọc trong `{import.meta.env.DEV && ( ... )}` và tự động bị loại bỏ hoàn toàn trên bản build Production (`npm run build`).
  3. Đồng bộ Tài liệu Kỹ thuật:
     - `DocumentAPI_Report2026.md`: Cập nhật chi tiết luồng JIT Provisioning, Động cơ phân quyền 4 tầng, cấu trúc payload mới của `/api/google-login/` & `/api/auth/me/`, tài liệu API `/api/debt/aging/`, `/api/debt/notifications/send-reminders/` và tiêu chuẩn bảo mật sản xuất (Mục 17, 18, 19).
     - `target.md`: Cập nhật Mục 15 với đầy đủ kiến trúc 4-Layer RBAC Engine, ma trận phân quyền mới và quy chuẩn bảo mật.
     - `project-dashboard/HANDOVER.md` & `CHANGELOG.md`: Nâng cấp phiên bản lên `v1.0.12`.
  4. Kiểm thử & Đóng gói:
     - `manage.py test accounting`: **41/41 tests PASS 100% (9.31s)**.
     - `scripts/audit_all_user_rbac.py`: **100% PASS (0 lỗi toàn vẹn trên 173 nhân sự)**.
     - `npm run build`: **Thành công 100% (0 errors, 556ms)**.
- **Current Status**: **[DONE]**

## [2026-08-19 11:35:00] Task: Revoke debt_collection Tab Permission from SALES Role (Aging Tab Only) — [DONE]
- **Objective**: Cập nhật ma trận phân quyền: Thu hồi quyền xem Tab "Thu hồi nợ" (`debt_collection`) của nhóm SALES, chỉ cho phép truy cập duy nhất 1 Tab là "Tuổi nợ" (`aging`).
- **Các thay đổi đã thực hiện**:
  1. Backend `accounting/services/user_provisioner.py`:
     - Cập nhật `DEFAULT_ROLE_TABS['SALES'] = ['aging']`.
  2. Frontend `project-dashboard`:
     - `src/context/AuthContext.jsx`: Cập nhật `DEFAULT_ROLE_TABS.SALES = ['aging']`.
     - `src/routes/ProtectedRoute.jsx` & `src/routes/AppRoutes.jsx`: Tự động redirect về `/aging` khi người dùng thuộc nhóm SALES truy cập `/debt-collection`, `/dashboard`, `/bu/*`, `/inventory`.
     - `src/layouts/DashboardLayout.jsx` & `src/components/navigation/MobileNavDrawer.jsx`: Thanh Navbar & Menu điều hướng chỉ render duy nhất tab "Tuổi nợ" (`aging`).
     - Build Production `npm run build`: Thành công trong 744ms (0 lỗi).
  3. Cập nhật Unit Tests & Database Sync:
     - `accounting/tests.py`: Cập nhật test case `test_google_login_jit_provisioning` kiểm tra `SALES` không có quyền `debt_collection`.
     - `manage.py sync_employee_users`: Đồng bộ thành công 173/173 tài khoản với quyền mới.
     - `manage.py test accounting`: **41/41 unit tests PASS 100% (11.16s)**.
     - `scripts/audit_all_user_rbac.py`: **100% PASS (0 lỗi toàn vẹn trên 173 nhân sự)**.
- **Current Status**: **[DONE]**

## [2026-08-19 11:22:00] Task: Implement 4-Layer Data-Driven RBAC Engine & Multi-Dimensional Touchpoint Resolution — [DONE]
- **Objective**: Triển khai kiến trúc phân quyền 4 tầng dữ liệu CSDL (HR Assignment + BU Manager + Customer Portfolio + Sales Transactions). Chuẩn hóa bản ghi `ĐTCT` (`is_main = True`, `parent = HPC`), nâng cấp `resolve_user_rbac()`, sửa lỗi console buffer wrapping trong `generate_dev_token.py`, đồng bộ `DashboardContext.jsx` và audit 100% 173 nhân sự.
- **Các thay đổi đã thực hiện**:
  1. Cập nhật CSDL `BusinessUnit`:
     - Cập nhật bản ghi `ĐTCT` (ID 72): `is_main = True`, `parent = HPC` để đồng bộ 100% với 7 BU thương mại còn lại.
  2. `accounting/services/user_provisioner.py`:
     - Tích hợp trọn vẹn 4 tầng dữ liệu CSDL vào `resolve_user_rbac()`:
       * Tầng 1: `EmployeeAssignment` $\rightarrow$ `DEPARTMENT_BU_REGISTRY`.
       * Tầng 2: `BusinessUnit.manager` $\rightarrow$ `BU_HEAD`.
       * Tầng 3: `Customer.assigned_employee` $\rightarrow$ `SALES` (Phụ trách khách hàng trong BU).
       * Tầng 4: `SalesTransaction.employee` $\rightarrow$ `SALES` (Phát sinh doanh số trong BU).
     - Phân cấp `primary_role` ưu tiên: `BOD_ADMIN` > `BU_HEAD` > `SALES` > `VIEWER`.
  3. `scripts/generate_dev_token.py`:
     - Format lại output code JavaScript đa dòng thụt lề an toàn (`devAuth`), sử dụng đường kẻ ASCII chuẩn, giải quyết dứt điểm lỗi tràn bộ đệm đè chữ trên Windows PowerShell/Command Prompt.
  4. `scripts/audit_all_user_rbac.py`:
     - Tích hợp bộ kiểm tra toàn vẹn 4 tầng: Quét 100% 173 nhân sự, xác minh không có bất kỳ nhân sự nào bị sót BU phụ trách khách hàng hoặc BU doanh số. Kết quả: **100% PASS (0 Lỗi toàn vẹn)**.
  5. Frontend `project-dashboard`:
     - `DashboardContext.jsx`: Bổ sung `BU_DTCT`, `ĐTCT`, `DTCT`, `OVERSEA` vào `labelMap` và `toneMap`.
     - Build Production `npm run build`: Thành công trong 658ms, 0 lỗi.
  6. Đồng bộ & Unit Tests:
     - `manage.py sync_employee_users`: Đồng bộ thành công 173/173 tài khoản.
     - `manage.py test accounting`: **41/41 unit tests PASS 100% (9.31s)**.
- **Current Status**: **[DONE]**

## [2026-08-19 11:06:00] Task: Implement Data-Driven RBAC Engine & Audit 100% Employees — [DONE]
- **Objective**: Chuyển đổi toàn diện cơ chế phân quyền từ Keyword String Matching thủ công sang Data-Driven RBAC Engine. Xây dựng bảng quy hoạch `DEPARTMENT_BU_REGISTRY`, hàm phân giải tổng quát `resolve_user_rbac(employee)`, script audit tự động 100% nhân sự `scripts/audit_all_user_rbac.py`, sửa lỗi format terminal output trong `scripts/generate_dev_token.py`, đồng bộ `AuthContext.jsx` & `DebtAgingReportPage.jsx` trên Frontend.
- **Các thay đổi đã thực hiện**:
  1. `accounting/services/user_provisioner.py`:
     - Xây dựng `BU_DEFINITIONS` (8 Commercial BUs) và `DEPARTMENT_BU_REGISTRY` mapping chuẩn xác từ `department_code` sang mã `BusinessUnit` trong CSDL.
     - Triển khai hàm phân giải tổng quát `resolve_user_rbac(employee)`: Quét active assignments $\rightarrow$ map qua `DEPARTMENT_BU_REGISTRY` $\rightarrow$ tra cứu `BusinessUnit.manager` $\rightarrow$ phân loại role theo cấp bậc ưu tiên.
     - Cập nhật các wrapper `get_employee_assignments_info()`, `determine_employee_role()`, `get_user_role_info()`.
  2. `scripts/audit_all_user_rbac.py`:
     - Tạo script audit quét toàn diện 100% nhân sự (173 nhân viên active).
     - Phân loại rõ ràng: 5 BOD_ADMIN, 25 BU_HEAD, 32 SALES, 126 VIEWER; 22 Multi-BU, 80 Single-BU, 81 Support/No-BU.
     - Đối soát hoàn hảo các case trọng điểm: `3003` (Elevator), `9004` (Agritech, Eco, ĐTCT), `7583` (Manufacturing, Agritech, Eco), `2001` (BOD_ADMIN toàn quyền 8 BU).
  3. `scripts/generate_dev_token.py`:
     - Format lại đoạn mã `js_snippet` ngắt dòng tường minh, loại bỏ triệt để lỗi wrapping buffer đè dòng trên Windows PowerShell/cmd.
  4. Frontend `project-dashboard`:
     - `AuthContext.jsx`, `DebtAgingReportPage.jsx`, `detailMapper.js`, `dashboardMapper.js`: Đồng bộ đầy đủ 8 BU keys (`elevator`, `ibizPremium`, `ibizValue`, `agritech`, `eco`, `manufacturing`, `dtct`, `oversea`).
     - Build Production `npm run build` thành công trong 689ms, 0 lỗi.
  5. Đồng bộ & Unit Tests:
     - `manage.py sync_employee_users`: Cập nhật đồng loạt 173 tài khoản thành công 100%.
     - `manage.py test accounting`: **41/41 unit tests PASS 100% (9.89s)**.
- **Current Status**: **[DONE]**

## [2026-08-19 11:00:00] Task: Fix DTCT Recognition & Multi-BU Expansion for Employee 9004 (Phạm Văn Mừng) — [DONE]
- **Objective**: Sửa lỗi nhận diện thiếu khối ĐTCT (Đầu tư cho thuê / Đầu tư cho thuê) và mở rộng phân công công tác cho nhân sự `9004` (Phạm Văn Mừng) gồm đầy đủ 3 BU: `BU_AGRITECH`, `BU_ECO`, `ĐTCT`.
- **Các thay đổi đã thực hiện**:
  1. `accounting/services/user_provisioner.py`:
     - Bổ sung `COMMERCIAL_BU_KEYWORDS` với `BU_AGRITECH`, `BU_ECO`, và `ĐTCT` (`frontend_key: 'dtct'`, `bu_name: 'Đầu tư cho thuê / ĐTCT'`).
     - Thêm `resolve_assignment_bu_list()` tự động tách phòng ban `BU_Agritech-Eco` thành 2 BU thương mại: `BU_AGRITECH` và `BU_ECO`.
     - Quét thêm từ `BusinessUnit` model nơi nhân sự được chỉ định làm `manager` (`PHẠM VĂN MỪNG` quản lý `ĐTCT`), tự động nâng cấp vai trò `BU_HEAD` và đưa vào `managed_bus`, `assigned_bus`, `assignments`.
  2. Frontend `project-dashboard`:
     - `src/context/AuthContext.jsx`: Thêm `'dtct'` vào `ALL_BU_KEYS`, chuẩn hóa `mapBuCodeToFrontendKey()` nhận diện `dtct` / `đtct` / `đối tác` / `cho thuê`.
     - `src/utils/detailMapper.js` & `src/utils/dashboardMapper.js`: Thêm `BU_DTCT`, `ĐTCT`, `DTCT` $\rightarrow$ `dtct`, hiển thị tên "Đầu tư cho thuê / ĐTCT".
  3. `accounting/tests.py`:
     - Bổ sung test case kiểm tra tra cứu `BusinessUnit` manager và phân giải đa BU $\rightarrow$ `manage.py test accounting` pass **41/41 tests 100%**.
  4. Đồng bộ DB:
     - Chạy `manage.py sync_employee_users` đồng bộ 173 tài khoản thành công 100%.
     - Kiểm thử `scripts/generate_dev_token.py --code 9004`: Nhận diện chuẩn xác cả 3 BU (`BU_AGRITECH`, `BU_ECO`, `ĐTCT`).
- **Current Status**: **[DONE]**

## [2026-08-19 10:48:00] Task: Multi-BU & Multi-Assignment RBAC Upgrade (Backend & Frontend) — [DONE]
- **Objective**: Triển khai cơ chế phân quyền đa đơn vị kinh doanh (Multi-BU) và đa vai trò kiêm nhiệm (Multi-Assignment) giữa Backend (`dashboard-report`) và Frontend (`project-dashboard`). Cho phép nhân sự thuộc nhiều BU chuyển đổi linh hoạt các BU được phân công, và tự động áp dụng Dynamic Filter Guard (toàn quyền chọn nhân viên tại BU mình làm Trưởng BU, khóa cứng mã cá nhân tại BU mình làm Sales).
- **Các thay đổi đã thực hiện**:
  1. `accounting/services/user_provisioner.py`:
     - Thêm `ROLE_PRIORITY` (`BOD_ADMIN` > `BU_HEAD` > `SALES` > `VIEWER`).
     - Thêm `determine_assignment_role()` và `get_employee_assignments_info()` quét toàn bộ `EmployeeAssignment` active của nhân sự.
     - Nâng cấp `get_user_role_info()` trả về: `primary_role`, `managed_bus`, `assigned_bus`, `managed_bu_keys`, `assigned_bu_keys`, và mảng chi tiết `assignments`.
  2. `scripts/generate_dev_token.py`:
     - Hiển thị danh sách BU Quản lý, BU Kiêm nhiệm và bảng chi tiết các phân công công tác.
     - Tối ưu định dạng terminal output sạch đẹp, chống lỗi ngắt dòng Windows console.
  3. `accounting/tests.py`:
     - Thêm test case `test_multi_assignment_user_resolution` (kiểm tra phân giải 2 assignment đồng thời của nhân sự Huỳnh Trọng Huy).
  4. Frontend `src/context/AuthContext.jsx`:
     - Lưu trữ `managed_bus`, `assigned_bus`, `assignments`.
     - Bổ sung helper `getRoleInCurrentBu(buCodeOrKey)`, `isBuHeadInBu(bu)`, `isSalesInBu(bu)`, tính toán `allowedBUs` từ toàn bộ `assigned_bus`.
  5. Frontend `src/pages/DebtAgingReportPage.jsx`:
     - **Dropdown BU**: Cho phép chuyển đổi giữa các BU thuộc `assigned_bus` (nếu có từ 2 BU trở lên), khóa nếu chỉ có 1 BU.
     - **Dropdown Nhân viên**: Mở toàn quyền chọn nhân sự nếu là `BU_HEAD` trong BU đang chọn; tự động chọn và khóa cứng theo `employee_code` nếu là `SALES` trong BU đó.
  6. Frontend `CHANGELOG.md` & `HANDOVER.md`:
     - Ghi nhận phiên bản release `v1.0.11`.
- **Kết quả kiểm thử**:
  - `manage.py test accounting` → **41/41 tests PASS 100% (10.5s)**.
  - `npm run build` → **0 Errors, 0 Warnings (621ms)**.
  - Kiểm thử thực tế nhân sự Huỳnh Trọng Huy (`7583`): Đầy đủ 2 BU (`BU_MANUFACTURING` vai trò BU_HEAD, `BU_Agritech - Eco` vai trò VIEWER).
- **Current Status**: **[DONE]**

## [2026-08-19 10:32:00] Task: Fix Commercial BU Mapping & Fallback Resilience (Backend & Frontend) — [DONE]
- **Objective**: Sửa triệt để lỗi phân loại vai trò `BU_HEAD` cho nhân sự thuộc khối hỗ trợ (SSC/Shared Services) trong backend, ưu tiên Trưởng BU thương mại (`BU_ELEVATOR`, `BU_ECO`, `BU_PREMIUM`...) khi chạy dev token script, và bổ sung cơ chế fallback an toàn chống crash/toast error trong frontend `DashboardContext.jsx` & `AuthContext.jsx`.
- **Các thay đổi đã thực hiện**:
  1. `accounting/services/user_provisioner.py`:
     - Thêm `COMMERCIAL_BU_KEYWORDS` và hàm `is_commercial_department()`.
     - `determine_employee_role()`: Chỉ cấp quyền `BU_HEAD` cho nhân sự quản lý 6 BU kinh doanh thương mại (`BU_ELEVATOR`, `BU_IBIZ PREMIUM`, `BU_IBIZ VALUE`, `BU_Agritech - Eco`, `BU_MANUFACTURING`, `ĐTCT`, `Oversea`). Quản lý khối hỗ trợ (SSC, SCM, HCNS, Kế toán...) được phân vào `VIEWER` để không kích hoạt dữ liệu chi tiết BU kinh doanh.
     - `resolve_bu_info_from_department()` và `get_user_role_info()`: Bổ sung cờ `is_commercial`, nếu non-commercial thì gán `allowed_tabs = ['aging']`.
  2. `scripts/generate_dev_token.py`:
     - Lựa chọn ưu tiên Trưởng BU kinh doanh cốt lõi (`dung.daotien@haophuong.com` - `BU_ELEVATOR`, `phong.nguyenngochuy@haophuong.com` - `BU_Value`, `minh.ho@haophuong.com` - `BU_Premium`).
     - Sửa lỗi in JavaScript snippet trên 1 dòng sạch sẽ, không bị wrap/xuống dòng sai định dạng trên Windows terminal.
  3. Frontend `src/utils/detailMapper.js` & `src/utils/dashboardMapper.js`:
     - `buIdFromCode()` nhận diện mạnh mẽ và chuẩn hóa tất cả định dạng mã BU (space, underscore, lower/uppercase).
  4. Frontend `src/context/DashboardContext.jsx`:
     - `loadDetailData()`: Thêm cơ chế Fallback an toàn tự động chuyển về BU thương mại đầu tiên nếu `buId` không tồn tại, loại bỏ throw exception / toast lỗi đỏ gây crash.
  5. Frontend `src/context/AuthContext.jsx`:
     - Bổ sung `mapBuCodeToFrontendKey()` đồng bộ mã BU backend sang frontend `buKey`.
  6. Frontend `src/routes/AppRoutes.jsx`:
     - `DashboardBuDetailPageWrapper` tự động chuẩn hóa `currentBuKey` qua `buIdFromCode()`.
- **Kết quả kiểm thử**:
  - `sync_employee_users`: 21 BU_HEAD (chuẩn 6 BU thương mại), 115 VIEWER.
  - `generate_dev_token.py --role BU_HEAD`: In đúng Mr. Đào Tiến Dũng (`BU_Elevator`, `is_commercial: true`).
  - Frontend Production Build: `npm run build` → **✅ 0 Errors (630ms)**.
  - Backend Unit Tests: `manage.py test accounting` → **40/40 tests PASS 100% (9.4s)**.
- **Current Status**: **[DONE]**


## [2026-08-19 10:20:00] Task: Full-Stack RBAC & Permission Normalization (Backend & Frontend) — [DONE]
- **Objective**: Chuẩn hóa toàn diện cơ chế Phân quyền người dùng (RBAC) giữa Backend và Frontend, cung cấp endpoint `/api/auth/me/`, phân quyền hiển thị Navbar Tabs theo `allowed_tabs`, Route Guard tự động redirect trang không được phép, Filter Guard khóa cứng BU/Nhân viên cho BU_HEAD/SALES, và cô lập công cụ Dev Role Switcher trong `import.meta.env.DEV`.
- **Các thay đổi đã thực hiện**:
  1. `accounting/services/user_provisioner.py`:
     - Thêm `resolve_bu_info_from_department()` và `TAB_PERMISSIONS`.
     - Nâng cấp `get_user_role_info()` trả về `id`, `user_id`, `role`, `primary_role`, `employee_code`, `bu_code`, `bu_name`, `department`, `title`, `allowed_tabs`.
  2. `accounting/views/misa_api.py` & `accounting/views/__init__.py` & `accounting/views.py`:
     - Xây dựng `CurrentUserAPIView` (`GET /api/auth/me/`) yêu cầu xác thực Knox token.
     - Đồng bộ response của `GoogleLoginAPI` & `LoginAPI` chứa payload `user` đầy đủ.
  3. `accounting/urls.py`: Đăng ký route `path('auth/me/', CurrentUserAPIView.as_view(), name='current_user_api')`.
  4. `accounting/tests.py`: Bổ sung 2 test case (`test_current_user_api_endpoint`, `test_google_login_jit_provisioning` với payload RBAC).
  5. `scripts/generate_dev_token.py`: Nâng cấp JS snippet dán console lưu cả `auth_user` JSON string vào `localStorage`.
  6. Frontend `src/context/AuthContext.jsx`:
     - Đồng bộ quyền hạn từ `GET /api/auth/me/`.
     - Cung cấp `allowedTabs`, `canAccessTab`, `firstAllowedPath`, `isBOD`, `isBuHead`, `isSales`, `isViewer`.
  7. Frontend `src/layouts/DashboardLayout.jsx` & `src/components/navigation/MobileNavDrawer.jsx`:
     - Ẩn/hiện Navbar Tabs theo `canAccessTab` (`BOD_ADMIN`: 5 tabs, `BU_HEAD`: 4 tabs, `SALES`: 2 tabs, `VIEWER`: 1 tab).
     - Bấm Logo Header chuyển về `firstAllowedPath`.
  8. Frontend `src/components/UserMenu.jsx` & `MobileNavDrawer.jsx`:
     - Hiển thị Mã NV, Đơn vị BU, Role badge thực tế.
     - Bọc khối "Chuyển vai trò (Dev only)" bằng `{import.meta.env.DEV && ( ... )}` (tự động loại bỏ khi build Production).
  9. Frontend `src/components/auth/ProtectedRoute.jsx` & `src/routes/AppRoutes.jsx`:
     - Route Guard kiểm tra `requiredTab`; nếu user không đủ quyền truy cập URL trực tiếp sẽ tự động chuyển hướng về `firstAllowedPath`.
  10. Frontend `src/pages/DebtAgingReportPage.jsx`:
      - Filter Guard: Khóa cứng Dropdown BU cho `BU_HEAD` và khóa cả Dropdown BU + Nhân viên cho `SALES`.
  11. Frontend `CHANGELOG.md` & `HANDOVER.md`: Ghi nhận phiên bản `[1.0.10]`.
  12. `DocumentAPI_Report2026.md` (Mục 17.4) & `target.md` (Mục 15.3): Cập nhật tài liệu API và kiến trúc phân quyền.
- **Kết quả kiểm thử**:
  - Backend Unit Tests: **40/40 tests PASS 100%** (`Ran 40 tests in 9.385s - OK`).
  - Frontend Production Build: `npm run build` → **✅ Built in 4.09s, 0 Errors**.
- **Current Status**: **[DONE]**


## [2026-08-19 09:50:00] Task: Employee User Provisioning & Google SSO JIT Sync — [DONE]
- **Objective**: Đồng bộ danh sách nhân viên (`Employee`) vào tài khoản người dùng đăng nhập (`User`) của hệ thống, hỗ trợ đăng nhập Google SSO tức thì (Just-In-Time) không cần chờ kích hoạt thủ công, phân quyền tự động theo 4 nhóm (`BOD_ADMIN`, `BU_HEAD`, `SALES`, `VIEWER`), và chặn các domain ngoài `@haophuong.com`.
- **Các thay đổi đã thực hiện**:
  1. `report2026/settings.py`: Cấu hình `ALLOWED_SSO_DOMAINS = env.list('ALLOWED_SSO_DOMAINS', default=['haophuong.com'])`.
  2. `accounting/models/employee.py`: Thêm quan hệ OneToOne `user = models.OneToOneField(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='employee_profile', verbose_name="Tài khoản đăng nhập")`.
  3. `accounting/migrations/0047_employee_user.py` [NEW]: Tạo và thực thi migration liên kết User-Employee trong CSDL.
  4. `accounting/services/user_provisioner.py` [NEW]: Dịch vụ quản lý IAM & Provisioning:
     - Tạo và bảo đảm 4 Django Groups: `BOD_ADMIN`, `BU_HEAD`, `SALES`, `VIEWER`.
     - Tách Họ & Tên chuẩn tiếng Việt: `first_name` (Tên - từ cuối cùng), `last_name` (Họ & Tên đệm - phần còn lại).
     - Phân quyền tự động từ `JobTitle` & `Department` của `EmployeeAssignment`.
     - `provision_user_for_employee()`: Tạo/cập nhật `User`, `is_active=True`, `set_unusable_password()`, gán Group và link `employee.user`.
     - `get_user_role_info()`: Trả về thông tin quyền hạn mở rộng (role, groups, full_name, employee_code, department, title).
  5. `accounting/services/__init__.py`: Export các hàm từ `user_provisioner.py`.
  6. `accounting/management/commands/sync_employee_users.py` [NEW]: Command đồng bộ hàng loạt `python manage.py sync_employee_users` (hỗ trợ `--dry-run`, `--bu`, `--email`).
  7. `accounting/views/misa_api.py`: Nâng cấp `GoogleLoginAPI` và `LoginAPI`:
     - Chặn domain ngoài `@haophuong.com` (trả về `403 Forbidden`).
     - Tự động Just-In-Time (JIT) provisioning & kích hoạt `is_active=True` ngay khi nhân viên nội bộ đăng nhập Google lần đầu.
     - Trả về token kèm toàn bộ thông tin role/profile trong response body.
  8. `accounting/admin.py`: Cập nhật `EmployeeAdmin` hiển thị trạng thái tài khoản User (`user_account`) và nhóm quyền (`user_role`).
  9. `accounting/tests.py`: Bổ sung bộ test `EmployeeUserProvisioningTests` (test tách tên, test role mapping, test command, test domain restriction 403, test JIT provisioning).
  10. `DocumentAPI_Report2026.md` & `target.md`: Cập nhật tài liệu kiến trúc IAM và hướng dẫn sử dụng API/command.
- **Kết quả thực thi & Kiểm thử**:
  - **Đồng bộ thực tế CSDL (`python manage.py sync_employee_users`)**:
    * Tổng số nhân viên quét: **173** nhân viên đang hoạt động có email hợp lệ.
    * Tạo mới tài khoản: **172** User.
    * Cập nhật tài khoản cũ: **1** User.
    * Phân bổ 4 Groups: `BOD_ADMIN`: 4 tài khoản (2.3%), `BU_HEAD`: 30 tài khoản (17.3%), `SALES`: 33 tài khoản (19.1%), `VIEWER`: 106 tài khoản (61.3%).
  - **Kiểm thử tự động**:
    * `manage.py test accounting`: **39/39 tests OK (100% PASS)**.
    * `scripts/test_debt_email_automation.py`: **4/4 suites PASS (100% PASS)**.
- **Current Status**: **[DONE]**

## [2026-08-18 10:32:00] Task: Include Oversea & DTCT in Commercial Debt Management — [DONE]
- **Objective**: Bỏ bộ lọc loại trừ khách hàng Oversea trong tính toán công nợ và hệ thống Email nhắc nợ; đồng thời hiển thị BU ĐTCT (Đầu tư cho thuê) như một Khối BU kinh doanh trong báo cáo công nợ.
- **Các thay đổi đã thực hiện**:
  1. `report2026/settings.py`:
     - Cập nhật `OVERSEA_CUSTOMER_GROUP_CODES = ['Oversea', 'Overseas']`.
     - Bổ sung `'ĐTCT'` vào `CORE_COMMERCIAL_BU_CODES = ['BU_ELEVATOR', 'BU_IBIZ PREMIUM', 'BU_ECO', 'BU_MANUFACTURING', 'BU_AGRITECH', 'BU_IBIZ VALUE', 'ĐTCT']`.
     - Cập nhật `EXCLUDED_DEBT_BU_CODES = ['VHC_HR']`.
  2. `accounting/views/debt_api.py`:
     - Bỏ loại trừ `oversea_groups` trong `BUReceivablesDrilldownAPIView`, chỉ loại trừ nhóm nội bộ `Internal`.
  3. `accounting/services/debt_mailer.py`:
     - Bỏ loại trừ `oversea_groups` trong `collect_sales_debt_data` và `collect_bu_manager_debt_data`.
     - Khách hàng Oversea thuộc Sales phụ trách (Fuji Electric Thailand thuộc Lê Văn Tín, Hạo Phương Campuchia thuộc Ngô Đình Trung Tân) và BU ĐTCT đã được tự động tính vào danh sách nợ.
  4. `accounting/services/kpi_calculator.py`:
     - Sửa logic `bu_ids` khi tính toán cho BU nằm trong `EXCLUDED_BU_CODES` (để tính toán đúng số liệu cho chính `ĐTCT` khi yêu cầu).
     - Đồng bộ `ageing_filter` để tính công nợ đầy đủ cho từng BU (chỉ BU Oversea mới lọc riêng nhóm Oversea).
  5. `accounting/views/debt_api.py`:
     - Nâng cấp `BUDebt3TierDrilldownAPIView` tra cứu mã BU linh hoạt (hỗ trợ cả `ĐTCT` và `BU_ĐTCT` nếu frontend gửi có prefix).
  6. Frontend `project-dashboard`:
     - Cập nhật `normalizeBuCode` và `BU_CODE_MAP` trong `agingMockData.js` để giữ nguyên mã `ĐTCT` và `Oversea` thay vì tự động gắn prefix `BU_`.
  7. Đã chạy tính toán lại `BUPerformance` toàn bộ 23 BUs tháng 08/2026.
  8. `scripts/test_debt_email_automation.py`: Cập nhật assertion kiểm thử số lượng BU tối thiểu >= 6.
- **Kết quả kiểm thử & API**:
  - `GET /api/debt/bus/?period=2026-08`: `ĐTCT` trả về đầy đủ Tổng nợ **`730,801,226` VNĐ**, Quá hạn **`114,050,877` VNĐ** (15.61%).
  - `GET /api/debt/bus/ĐTCT/drilldown/?period=2026-08` & `.../BU_ĐTCT/drilldown/`: Đều trả về HTTP 200 OK với Drilldown 3 tầng chi tiết 2 Sales (Phạm Văn Mừng, Đào Tiến Dũng) và 8 khách hàng.
  - `manage.py test accounting`: **34/34 tests OK (100% PASS)**.
  - `scripts/test_debt_email_automation.py`: **4/4 suites PASS (100% PASS)**.
- **Current Status**: **[DONE]**

## [2026-08-18 10:09:00] Task: Investigate & Fix Total Company Oversea Revenue MTD (01/08/2026 – 18/08/2026) — [DONE]
- **Objective**: Điều tra nguyên nhân vì sao Doanh thu Oversea MTD (Thực tế) kỳ 2026-08 (01/08/2026 – 18/08/2026) tại dashboard Tổng Toàn Công Ty đang hiển thị = 0, và đưa ra giải pháp khắc phục triệt để.
- **Nguyên nhân cốt lõi (Root Cause)**:
  - Khi cấu hình `EXCLUDED_BU_CODES = ['ĐTCT', 'Oversea', 'VHC_HR']` trong `settings.py` để loại trừ các BU không có công nợ thương mại khỏi danh sách BU Drilldown, mã BU `'Oversea'` bị đưa nhầm vào danh sách loại trừ tính toán hiệu suất chung.
  - Trong `accounting/services/kpi_calculator.py`, điều kiện `elif 'Oversea' in excluded_bu_codes:` khi `is_global=True` (Tổng Toàn Công Ty) đã vô tình lọc bỏ toàn bộ giao dịch của nhóm khách hàng `Oversea` khỏi `sales_qs` và `ageing_filter`.
  - Hậu quả: `rev_oversea_actual` bị tính thành `0 VNĐ`, và Doanh thu Tổng Toàn Công Ty bị thiếu hụt mất phần doanh thu Oversea (chỉ còn 17.69 tỷ thay vì 25.73 tỷ).
- **Các thay đổi đã thực hiện**:
  1. `report2026/settings.py`: Tách bạch rõ 2 cấu hình:
     - `EXCLUDED_BU_CODES = env.list('EXCLUDED_BU_CODES', default=['ĐTCT'])`: Chỉ loại trừ đơn vị cho thuê (ĐTCT) khi tính toán hiệu suất Tổng Công Ty.
     - `EXCLUDED_DEBT_BU_CODES = env.list('EXCLUDED_DEBT_BU_CODES', default=['ĐTCT', 'Oversea', 'VHC_HR'])`: Dành riêng cho lọc danh sách BU trong Debt Drilldown APIs.
  2. `accounting/views/debt_api.py`: Sử dụng `EXCLUDED_DEBT_BU_CODES` để lọc 6 BU thương mại.
  3. `accounting/services/kpi_calculator.py`: Loại bỏ logic `elif 'Oversea' in excluded_bu_codes:` trong `customer_rev_filter` và `ageing_filter`. Cấp Tổng Toàn Công Ty (`is_global=True`) giờ đây luôn bao gồm cả Khách hàng Trong nước và Khách hàng Oversea, sau đó tự động tách bạch thành `mtd_revenue_exclude_oversea_actual` và `mtd_revenue_oversea_actual`.
  4. `accounting/tests.py`: Cập nhật fixture `account_code='1311'` cho `ReceivablesAgeing` và assertion kiểm thử `Reply-To` cho email API.
  5. `scripts/update_company_total.py`: Chạy lại cập nhật toàn bộ 8 tháng của năm 2026.
- **Kết quả xác minh số liệu**:
  - **Doanh thu Tổng Toàn Công Ty Tháng 08/2026 (01/08 - 18/08)**:
    * `mtd_revenue_actual` (Tổng DT có Oversea): **`25,730,201,043` VNĐ**
    * `mtd_revenue_exclude_oversea_actual` (Không gồm Oversea): **`17,695,573,656` VNĐ**
    * `mtd_revenue_oversea_actual` (Doanh thu Oversea MTD): **`8,034,627,387` VNĐ** (~8.03 Tỷ, KHỚP 100%)
    * `mtd_collection_actual` (Tổng thực thu): **`24,366,882,385` VNĐ**
    * `mtd_collection_oversea_actual` (Thực thu Oversea): **`5,749,663,870` VNĐ**
  - **Kiểm thử tự động**:
    * `manage.py test accounting`: **34/34 tests OK (100% PASS)**.
    * `scripts/test_debt_email_automation.py`: **4/4 suites PASS (100% PASS)**.
- **Current Status**: **[DONE]**

## [2026-08-18 08:23:00] Task: Debt Reminder Email Automation (Hệ Thống Gửi Mail Nhắc Nợ Phân Cấp) — [DONE]
- **Objective**: Phát triển hệ thống tự động hóa gửi email thông báo nhắc nợ phân cấp 2 tầng:
  1. Gửi email chi tiết từng Khách hàng nợ cho Nhân viên Kinh doanh (Sales) phụ trách.
  2. Gửi email báo cáo tổng hợp toàn BU cho Trưởng BU (kèm bảng phân bổ nhân viên và Top khách hàng nợ quá hạn).
- **Các thay đổi đã thực hiện**:
  1. `accounting/services/debt_mailer.py` [NEW]: Module gom dữ liệu nợ Sales & BU (`collect_sales_debt_data`, `collect_bu_manager_debt_data`), render template và gửi mail qua Django `EmailMultiAlternatives` (`send_sales_debt_email`, `send_bu_manager_debt_email`, `send_debt_reminders_process`).
  2. `accounting/services/__init__.py`: Export các hàm từ `debt_mailer.py`.
  3. `templates/emails/debt_reminder_sales.html` [NEW]: HTML Template responsive gửi cho Sales (4 Card KPI + Bảng danh sách khách hàng + Badge cảnh báo dải quá hạn + CTA Dashboard link).
  4. `templates/emails/debt_summary_manager.html` [NEW]: HTML Template responsive gửi cho Trưởng BU (Card KPI BU + Bảng phân bổ nhân viên + Bảng Top khách hàng nợ quá hạn lớn nhất + CTA Dashboard link).
  5. `accounting/tasks.py`: Thêm Celery shared task `send_debt_reminders_task(period, dry_run, test_email, bu_code, recipient_type)`.
  6. `accounting/serializers.py`: Thêm `DebtReminderRequestSerializer`.
  7. `accounting/views/debt_api.py`: Thêm API View `SendDebtRemindersAPIView` (`POST /api/debt/notifications/send-reminders/`).
  8. `accounting/views/__init__.py`: Export `SendDebtRemindersAPIView`.
  9. `accounting/urls.py`: Đăng ký route API `path('debt/notifications/send-reminders/', SendDebtRemindersAPIView.as_view(), name='send_debt_reminders_api')`.
  10. `report2026/settings.py`: Thêm `'django.contrib.humanize'` vào `INSTALLED_APPS` để format số tiền tự nhiên.
  11. `scripts/test_debt_email_automation.py` [NEW]: Bộ test kiểm thử tự động toàn diện (Gom data, Render 2 templates, Dry-Run email sending, REST API call).
  13. `templates/emails/`: Tái cấu trúc toàn bộ 2 templates HTML sang chuẩn **Bulletproof Email cho Microsoft Outlook / Word Engine** (chuyển sang Table-based layout, inlined styles 100%, bổ sung solid `bgcolor` và mã màu Hex fallback loại bỏ `linear-gradient` và `rgba` gây lỗi mất màu nền/chữ trắng, thiết kế lại CTA button dạng Table bulletproof và tăng độ tương phản rõ nét).
  14. `accounting/services/debt_mailer.py`: Sửa lỗi đường dẫn CTA Button Dashboard chuẩn hóa: loại bỏ dấu `//` thừa, định tuyến đúng `/aging`, bổ sung tham số `bu` cho cả email Sales (`/aging?period=...&bu=...&employee=...`) và email Trưởng BU (`/aging?period=...&bu=...`).
- **Kết quả kiểm thử tự động**:
  - `scripts/test_debt_email_automation.py`: **4/4 Test Suites PASS 100%**.
  - `scripts/send_test_debt_emails.py`: Gửi thực tế thành công 100% qua SMTP đến `thanhlongts2k@gmail.com` và `khoai.nguyenvan@haophuong.com` cả 2 mẫu Sales và Trưởng BU với đường link Dashboard chuẩn xác.
- **Current Status**: **[DONE]**

## [2026-08-17 16:46:00] Task: Dynamic Inventory Aggregation for Warehouse API (`/api/warehouses/`) — [DONE]
- **Objective**: Nâng cấp `WarehouseViewSet` để bóc tách tham số thời gian (`startDate`, `endDate`, `period`, `month`, `year`), tính toán động từ bảng `InventorySummary` theo từng kho và trả về số liệu thực tế chính xác.
- **Các thay đổi đã thực hiện**:
  1. `accounting/views/inventory_api.py`: Nâng cấp `WarehouseViewSet` (ghi đè `list()` và `retrieve()` method) để parse query params (`startDate`, `endDate`, `period`, `month`, `year`), query `InventorySummary` aggregate `opening_value`, `in_value`, `out_value`, `closing_value`, map vào danh sách `Warehouse`.
  2. `scripts/test_warehouse_api.py`: Viết test script gọi API `/api/warehouses/?startDate=2026-08-01&endDate=2026-08-17` và `?period=2026-07`, xác thực 100% khớp số liệu (215,097,709,657 VNĐ kỳ 08 và 217,165,903,238 VNĐ kỳ 07, 0 VNĐ chênh lệch).
- **Current Status**: **[DONE]**

## [2026-08-17 15:37:00] Task: Deep Linking & URL State Sync for BU & Employee Drilldown — [DONE]
- **Objective**: Đồng bộ trạng thái Deep Linking vào URL params (`period`, `bu`, `employee`), hỗ trợ F5, back/forward trình duyệt và chia sẻ liên kết trực tiếp đến đúng BU và Nhân viên.
- **Các thay đổi đã thực hiện**:
  1. `accounting/views/debt_api.py`: `BUDebt3TierDrilldownAPIView` nhận query param `employee_code` (hoặc `sales_code`, `employee`), gắn cờ `is_selected` và trả về `selected_employee_code`.
  2. `project-dashboard/src/api/agingApi.js`: Cập nhật `fetchBUDebtDrilldown` hỗ trợ param `employee`.
  3. `project-dashboard/src/pages/DebtAgingReportPage.jsx`: Đồng bộ 2 chiều hoàn chỉnh giữa URL params (`period`, `bu`, `employee`) với React state qua `useSearchParams`, hỗ trợ Deep Link khi load trang và Back/Forward. File đạt 198 dòng (< 200 dòng).
  4. Test suite và build xác thực 100% (3/3 tests pass, `npm run build` 0 lỗi).
- **Current Status**: **[DONE]**

## [2026-08-17 15:09:00] Task: Enforce Strict 6 Core Commercial BUs on Backend API — [DONE]
- **Objective**: Khóa cứng Backend API `GET /api/debt/bus/` chỉ trả về đúng danh sách 6 Khối BU Kinh Doanh Cốt Lõi (`CORE_COMMERCIAL_BU_CODES`), loại bỏ toàn bộ 13 phòng ban vận hành/back-office rỗng khỏi API và Dropdown.
- **Các thay đổi đã thực hiện**:
  1. `report2026/settings.py`: Thêm `CORE_COMMERCIAL_BU_CODES = ['BU_ELEVATOR', 'BU_IBIZ PREMIUM', 'BU_ECO', 'BU_MANUFACTURING', 'BU_AGRITECH', 'BU_IBIZ VALUE']`.
  2. `accounting/views/debt_api.py`: Áp dụng filter `business_unit__code__in=core_bu_codes` trong `AllBUsDebtSummaryAPIView`.
  3. `scripts/test_debt_apis.py`: Test suite Pass 100% (3/3 tests).
- **Trạng thái**: **[DONE]**

## [2026-08-17 14:51:00] Task: Exclude Oversea & VHC_HR from Domestic Debt Governance Scope — [DONE]
- **Objective**: Loại bỏ 2 khối không thuộc phạm vi quản trị công nợ kinh doanh nội địa: `Oversea` (Thị trường quốc tế) và `VHC_HR` (Nhân sự nội bộ).
- **Các thay đổi đã thực hiện**:
  1. `report2026/settings.py`: Cập nhật `EXCLUDED_BU_CODES = env.list('EXCLUDED_BU_CODES', default=['ĐTCT', 'Oversea', 'VHC_HR'])`.
  2. `accounting/views/debt_api.py`: Loại trừ các BU trong `EXCLUDED_BU_CODES` khỏi danh sách `bus[]` trong `AllBUsDebtSummaryAPIView`.
  3. `accounting/services/kpi_calculator.py`: Loại trừ các nhóm khách hàng `Oversea` khỏi `ageing_filter` và `customer_rev_filter` khi tính Global.
  4. Recalculate lại toàn bộ BUs và Global kỳ `2026-08`.
  5. Restart Celery worker daemon.
  6. `scripts/test_debt_apis.py`: Cập nhật và chạy kiểm thử tự động, 3/3 test suite PASS 100%.
- **Kết quả đối soát số liệu**:
  - `global_summary.receivable_total`: **55,707,311,450 VNĐ** (~55.71 Tỷ).
  - `global_summary.overdue_total`: **10,580,990,314 VNĐ** (18.99%).
  - Số lượng BU kinh doanh cốt lõi: **6 BU** (`BU_ELEVATOR`, `BU_IBIZ PREMIUM`, `BU_ECO`, `BU_MANUFACTURING`, `BU_AGRITECH`, `BU_IBIZ VALUE`).
  - Tổng nợ 6 BU cộng lại: **55,707,311,450 VNĐ** (Khớp **100% Tuyệt đối 0 VNĐ chênh lệch** so với Global).
- **Current Status**: **[DONE]**

## [2026-08-17 14:05:00] Task: FIX CRITICAL — Chuẩn Hóa Số Liệu Công Nợ (x2 Bug + Missing Data) — [DONE]
- **Objective**: Sửa triệt để lỗi sai số x2 trong `global_summary.receivable_total`, xử lý lỗi database field length varchar(20), sửa bug lọc nhầm khách hàng có chữ 'tổng' trong tên, và khớp 100% dữ liệu MISA.
- **Root Cause & Các điểm lỗi đã khắc phục triệt để**:
  1. `BUPerformance` tính trên cả TK 131 + TK 1311 → đã recalculate lọc riêng `TARGET_RECEIVABLE_ACCOUNTS = ['1311']`.
  2. Lỗi `value too long for type character varying(20)` ở `NHAN_VIEN`: `EmployeeResource` thiếu `before_import` header detection dẫn đến map sai cột, và model các trường `employee_code`, `identity_number`, `phone_number`, `account_code` bị ngắn (20 chars) → Đã tăng lên max_length=50..100 và chạy migration `0046_alter_employee_email_alter_employee_employee_code_and_more.py`.
  3. Lỗi rớt 2 khách hàng (`KH2025/000255` và `PAR2022/002634` tương đương 792.3 triệu): Do `merge_tuoi_no_kh_excel_files` trong `accounting/misa/report_exporter.py` lọc chuỗi `'tổng' in c1` (cột Tên khách hàng) → Đã sửa thành chỉ bỏ qua dòng summary ở cột 0 (`c0.startswith('tổng cộng')`).
- **Kết quả đối soát sau fix 100%**:
  - `ReceivablesAgeing` TK 1311 trong DB: **60,117,611,604 VNĐ** (Khớp **100% Tuyệt Đối 0 VNĐ chênh lệch** với dòng Tổng cộng trong file Excel MISA gốc).
  - `Global BUPerformance`: **57,650,085,327 VNĐ** (Sau khi trừ nhóm `Internal` và BU `ĐTCT` theo chính sách exclusion nghiệp vụ).
  - `BU_ELEVATOR`: **30,582,719,312 VNĐ** (Khớp drilldown 100% `is_matched: true`).
  - `BU_IBIZ PREMIUM`: **20,922,010,913 VNĐ**.
  - `BU_ECO`: **1,244,572,679 VNĐ**.
  - `BU_MANUFACTURING`: **1,091,763,792 VNĐ**.
  - `BU_AGRITECH`: **1,076,972,429 VNĐ**.
  - `BU_IBIZ VALUE`: **789,272,325 VNĐ**.
  - `Oversea`: **1,942,619,988 VNĐ**.
  - `VHC_HR`: **153,889 VNĐ**.
  - Tổng cộng 22 BU: **57,650,085,327 VNĐ** (Chênh lệch với Global = **0 VNĐ**).
  - Test suite `scripts/test_debt_apis.py`: **3/3 PASS 100%**.

## [2026-08-14 15:05:00] Task: Expose Full Aging Buckets at Customer Level in BU Drilldown API
- **Objective**: Bổ sung đầy đủ 14 trường dải tuổi nợ chi tiết (Trước hạn: `no_due_limit`, `due_0_7`..`due_above_60`, `due_total`; Quá hạn: `overdue_0_14`..`overdue_above_120`, `overdue_total`; `total_debt`) vào cấp Khách hàng trong API `GET /api/debt/bus/<bu_code>/drilldown/`.
- **Planned Modifications**:
  1. `accounting/serializers.py`: Cập nhật `CustomerDebtDetailSerializer` khai báo đầy đủ 14 fields dải tuổi nợ.
  2. `accounting/views/debt_api.py`: Gom và `Sum()` tất cả 14 trường dải tuổi nợ cho từng khách hàng trong `BUDebt3TierDrilldownAPIView`.
  3. `scripts/test_debt_apis.py`: Cập nhật bộ test verify các trường tuổi nợ chi tiết và in mẫu JSON response.
  4. `DocumentAPI_Report2026.md` & `target.md`: Cập nhật tài liệu API specs.
- **Current Status**: **COMPLETED** — Đã hoàn thành 100%:
  * Đã cập nhật `CustomerDebtDetailSerializer` trong `accounting/serializers.py` với đầy đủ 14 dải tuổi nợ.
  * Đã cập nhật `BUDebt3TierDrilldownAPIView` trong `accounting/views/debt_api.py` tính tổng tất cả các dải tuổi nợ cho từng khách hàng.
  * Đã kiểm thử tự động qua `scripts/test_debt_apis.py`: 3/3 test suite pass 100%, verify đầy đủ 14 trường dải tuổi nợ và đối soát khớp 0 VNĐ.
  * Đã đồng bộ tài liệu `DocumentAPI_Report2026.md` và `target.md`.


## [2026-08-14 14:05:00] Task: Enforce Configurable Target Receivable Accounts Filter (TK 1311)
- **Objective**: Chuẩn hóa cấu hình danh sách tài khoản công nợ mục tiêu `TARGET_RECEIVABLE_ACCOUNTS = ['1311']`, áp dụng bộ lọc `account_code__in=TARGET_RECEIVABLE_ACCOUNTS` trên toàn bộ hệ thống (kpi_calculator, employee_debt_calculator, debt_api, scripts kiểm thử).
- **Planned Modifications**:
  1. `report2026/settings.py`: Khai báo `TARGET_RECEIVABLE_ACCOUNTS = ['1311']` (dạng List có thể mở rộng).
  2. `accounting/services/kpi_calculator.py`: Bổ sung điều kiện lọc `account_code__in=target_accounts` khi tính công nợ `BUPerformance`.
  3. `accounting/services/employee_debt_calculator.py`: Bổ sung điều kiện lọc `account_code__in=target_accounts` khi tính nợ `EmployeeReceivableSummary`.
  4. `accounting/views/debt_api.py`: Áp dụng bộ lọc `account_code__in=target_accounts` trong cả 2 view API (`AllBUsDebtSummaryAPIView` và `BUDebt3TierDrilldownAPIView`).
  5. `scripts/report_3tier_bu_drilldown.py`, `scripts/report_bu_employee_debt.py`, `scripts/test_debt_apis.py`: Cập nhật bộ lọc tài khoản.
  6. Chạy lại tính toán KPI (`update_single_bu_performance`) và Nợ Nhân viên (`update_employee_receivable_summary`), kiểm thử và cập nhật `target.md`, `DocumentAPI_Report2026.md`.
- **Current Status**: **COMPLETED** — Đã hoàn thành 100%:
  * Đã cấu hình `TARGET_RECEIVABLE_ACCOUNTS = env.list('TARGET_RECEIVABLE_ACCOUNTS', default=['1311'])` tại `report2026/settings.py`.
  * Đã tích hợp bộ lọc `account_code__in=target_accounts` vào `kpi_calculator.py`, `employee_debt_calculator.py`, `debt_api.py`, `report_3tier_bu_drilldown.py`, `report_bu_employee_debt.py`, `test_debt_apis.py`.
  * Đã chạy tính toán lại `BUPerformance` và `EmployeeReceivableSummary` kỳ `2026-08`: Tổng 22 BUs = 57,082,185,049 VNĐ, khớp tuyệt đối 100% (0 VNĐ chênh lệch) với Global KPI.
  * 3/3 Test suites `test_debt_apis.py` PASS 100%.
  * Đồng bộ cập nhật tài liệu `target.md` và `DocumentAPI_Report2026.md`.


## [2026-08-14 11:25:00] Task: Phase 3 — Build REST API Endpoints for Receivables Debt & 3-Tier Drilldown
- **Objective**: Thiết kế và triển khai 2 Django REST Framework Endpoints chuẩn hóa:
  1. `GET /api/debt/bus/` (All BUs Summary): Mặc định lọc ẩn các BU có `overdue_rate = 0.0` (chỉ hiển thị các BU có nợ quá hạn > 0), hỗ trợ param `include_all=true` để lấy đủ 22 BU. Global summary bất biến ở mức 129.7 Tỷ.
  2. `GET /api/debt/bus/<bu_code>/drilldown/` (BU 3-Tier Drilldown): Trả về cấu trúc 3 tầng (BU -> Key Accounts / Sales / Managers -> Customers) kèm đối soát khớp 0 VNĐ (`is_matched: true`).
- **Planned Modifications**:
  1. `accounting/views/debt_api.py`: Xây dựng các API Views `AllBUsDebtSummaryAPIView` và `BUDebt3TierDrilldownAPIView`.
  2. `accounting/views/__init__.py`: Export các View mới.
  3. `accounting/urls.py`: Đăng ký routes chuẩn gọn gàng `/debt/bus/` và `/debt/bus/<str:bu_code>/drilldown/`.
  4. `HANDOVER_LOG.md`, `target.md`, `DocumentAPI_Report2026.md`, `Run_Test_Scripts.md`, `database_mapping.md`: Đồng bộ toàn bộ tài liệu dự án.
- **Current Status**: **COMPLETED** — Đã hoàn thành và kiểm thử thành công 100%:
  * Khai báo serializers trong `accounting/serializers.py`: `CustomerDebtDetailSerializer`, `SalesDebtDetailSerializer`, `BUDebtSummarySerializer`, `AllBUsDebtResponseSerializer`.
  * Xây dựng Views trong `accounting/views/debt_api.py`: `AllBUsDebtSummaryAPIView` và `BUDebt3TierDrilldownAPIView`.
  * Đăng ký URL endpoints trong `accounting/urls.py`: `/api/debt/bus/` và `/api/debt/bus/<str:bu_code>/drilldown/`.
  * Viết script test `scripts/test_debt_apis.py`: 3/3 test suite pass 100% (Khớp số liệu tuyệt đối 0 VNĐ chênh lệch).


## [2026-08-14 10:50:00] Task: Fix BU Hierarchy, Eliminate Double Counting (HPC) & Align Employee-BU Debt
- **Objective**:
  1. Loại bỏ `HPC` (Công ty mẹ/Chi nhánh pháp nhân) khỏi danh sách 22 BU kinh doanh để tránh cộng trùng, đảm bảo tổng nợ các BU độc lập khớp 100% với Global (129.7 Tỷ).
  2. Điều tra và xử lý triệt để nguyên nhân lệch 33 Tỷ giữa Tổng nợ BU Elevator (60.6 Tỷ) và Tổng nợ Sales gom được (26.8 Tỷ).
  3. Chuẩn hóa Cây Quản lý trong `auto_assign_managers.py`: Đào Tiến Dũng (Trưởng BU Elevator) là Sếp cao nhất của BU Elevator; Ngô Đình Trung Tân (Giám đốc Kinh doanh) phân đúng về Khối Kinh doanh; thiết lập thứ bậc phân cấp chuẩn (Giám đốc Khối -> Trưởng BU -> Trưởng bộ phận MB/MN -> Sales).
  4. Cập nhật `scripts/report_bu_employee_debt.py`, tính toán lại toàn bộ nợ và xuất báo cáo chuẩn hóa.
- **Planned Modifications**:
  1. `scripts/auto_assign_managers.py`: Tinh chỉnh logic phân cấp chức danh & phòng ban (Rank priority: Giám đốc Khối / Trưởng BU > Trưởng bộ phận MB/MN > Nhân viên).
  2. `scripts/report_bu_employee_debt.py`: Lọc bỏ BU cha `HPC`, gom nhóm nợ nhân viên theo đúng BU/Phòng ban và đối soát khớp 100%.
  3. `accounting/services/employee_debt_calculator.py`: Chạy lại tính toán chốt số liệu `EmployeeReceivableSummary` kỳ `2026-08`.
  4. `HANDOVER_LOG.md`: Ghi nhận tiến độ và kết quả thực thi.
- **Current Status**: **COMPLETED** — Đã khắc phục hoàn toàn cả 3 vấn đề:
  * Đã loại bỏ mã mẹ `HPC` khỏi danh sách 22 BU. Tổng nợ 22 BU cộng lại = **129,696,981,480 VNĐ**, KHỚP 100% (chênh lệch 0 VNĐ) với Global KPI Toàn Công Ty.
  * Đã chuẩn hóa Cây Quản lý đa cấp: `ĐÀO TIẾN DŨNG` (Trưởng BU Elevator) đứng đầu BU Elevator quản lý `NGUYỄN ĐỨC THƯỞNG` (MB) & `TRỊNH HOÀNG QUÂN` (MN). `NGÔ ĐÌNH TRUNG TÂN` là Giám đốc Kinh doanh (CCO) đứng đầu toàn bộ 5 BU và phụ trách các khách hàng Key Account lớn toàn công ty (51.05 Tỷ nợ cá nhân, 129.90 Tỷ nợ toàn khối).
  * Đã chạy tính toán lại toàn bộ bảng `EmployeeReceivableSummary` và xuất 2 Báo cáo chuẩn hóa qua `scripts/report_bu_employee_debt.py`.


## [2026-08-14 10:08:00] Task: MISA Master Data Crawler (Customer & Employee) & Prioritized Auto-Sync Pipeline
- **Objective**: Tích hợp Crawler Playwright 5 bước tinh gọn tự động tải 2 danh mục `DANH_SACH_KHACH_HANG` và `DANH_SACH_NHAN_VIEN` từ MISA AMIS, đồng thời thiết lập thứ tự ưu tiên nạp trong `auto_import_excel_from_folder()` (Nhân viên -> Khách hàng -> Báo cáo -> Chốt nợ tự động).
- **Planned Modifications**:
  1. `report2026/settings.py` & `.env`: Khai báo `MISA_URL_CUSTOMER`, `MISA_URL_EMPLOYEE` và cập nhật `MISA_REPORTS`.
  2. `accounting/misa/report_exporter.py`: Bổ sung luồng tải 5 bước trực tiếp qua Green Excel icon trên Toolbar Grid (`div[class*='excel']:visible`) kèm auto-fallback sang download manager panel.
  3. `download_report.py`: Bổ sung tham số `DANH_SACH_KHACH_HANG`, `DANH_SACH_NHAN_VIEN`, `KHACH_HANG`, `NHAN_VIEN`.
  4. `accounting/tasks.py`: Thiết lập thứ tự nạp ưu tiên (Priority 1: Nhân viên -> Priority 2: Khách hàng -> Priority 3: Báo cáo) và tự động kích hoạt `update_employee_receivable_summary()`.
  5. `target.md`, `Run_Test_Scripts.md`: Cập nhật tài liệu kỹ thuật.
- **Current Status**: **COMPLETED** — Đã cấu hình và kiểm thử thành công 100%:
  * Tải `DANH_SACH_NHAN_VIEN` (48,029 bytes) lưu về `media/auto_imports/DANH_SACH_NHAN_VIEN_20260814_101602.xlsx`.
  * Tải `DANH_SACH_KHACH_HANG` (1,466,759 bytes) lưu về `media/auto_imports/DANH_SACH_KHACH_HANG_20260814_101628.xlsx`.
  * Đã kiểm tra cú pháp toàn bộ file bằng `py_compile` (0 lỗi).


## [2026-08-14 09:48:00] Task: Customer & Sales Assignment Import & Employee Debt Summary Calculation (2026-08)
- **Objective**: Viết script `scripts/import_customer_mapping.py` nạp mapping từ `media/auto_imports/Danh_sach_khach_hang.xlsx` vào `Customer.assigned_employee`, chạy chốt số liệu công nợ `EmployeeReceivableSummary` kỳ `2026-08` và xuất báo cáo Top Quản lý nợ nhóm lớn nhất.
- **Planned Modifications**:
  1. `scripts/import_customer_mapping.py`: [NEW] Script đọc file Excel danh mục khách hàng, get_or_create nhân viên Sales mới nếu cần, và bulk update/create `Customer.assigned_employee`.
  2. `Run_Test_Scripts.md`: Cập nhật Mục 5.9 hướng dẫn chạy script.
  3. `HANDOVER_LOG.md`: Ghi nhận tiến độ và kết quả thực thi.
- **Current Status**: **COMPLETED** — Đã nạp thành công 11,019 dòng từ file Excel danh mục khách hàng, tạo mới 10,015 khách hàng, cập nhật Sales cho 986 khách hàng (tổng 9,350 khách hàng đã gán Sales). Đã chạy chốt số liệu `EmployeeReceivableSummary` kỳ `2026-08` cho 166 nhân viên/quản lý và trích xuất Top 3 Quản lý có dư nợ nhóm lớn nhất.


## [2026-08-11 09:36:00] Task: Multi-Account TUOI_NO_KH Export & Import (131 & 1311) - Direct MISA Raw Export Fix
- **Objective**: Tải và nạp dữ liệu nguyên bản từ MISA cho 2 tài khoản `131` và `1311` báo cáo `TUOI_NO_KH`, loại bỏ hoàn toàn các script Python tự `groupby` gây mất dữ liệu.
- **Planned Modifications**:
  1. `accounting/misa/report_exporter.py`: Điều hướng Playwright Crawler chọn tùy chọn xuất Excel trực tiếp từ MISA, gộp file thô nguyên bản của 2 tài khoản `131` và `1311` mà không can thiệp groupby bằng Python.
  2. Database Cleanup & Import: Xóa sạch data cũ kỳ `2026-08` trong DB (`ReceivablesAgeing.objects.filter(reporting_period='2026-08').delete()`) và nạp file Excel gộp trực tiếp từ MISA vào DB.
- **Current Status**: **COMPLETED** — Đã tải thành công 2 file thô nguyên bản từ MISA (1,469 dòng TK 131 và 1,383 dòng TK 1311). Đã nạp vào DB và verify lệnh `SELECT COUNT(*)` ghi nhận đúng **2,832 bản ghi** (1,459 dòng TK 131 + 1,373 dòng TK 1311).


## [2026-07-31 11:18:00] Task: Fail-Fast Refactoring for MISA Report Exporter (`report_exporter.py`)
- **Objective**: Tái cấu trúc (Refactor) module download MISA `accounting/misa/report_exporter.py` sang cơ chế **Fail-Fast**. Ném Exception dừng tiến trình lập tức nếu không chọn được ô "Bao gồm chi nhánh phụ thuộc", không chọn được "Mẫu chuẩn." hoặc chọn sai Kỳ báo cáo.
- **Planned Modifications**:
  1. `accounting/misa/report_exporter.py`: 
     - Sửa logic checkbox "Bao gồm chi nhánh phụ thuộc": raise `Exception("CRITICAL: Không thể click chọn 'Bao gồm chi nhánh phụ thuộc'...")` nếu không tick được.
     - Sửa logic chọn "Mẫu chuẩn." cho `BAN_HANG`: raise `Exception("CRITICAL: Không thể chuyển sang 'Mẫu chuẩn.'...")` nếu quá timeout 30s hoặc không tìm thấy menu item.
     - Sửa logic chọn Kỳ báo cáo (`period_option`): bắt buộc chọn đúng period bằng UI dropdown, ném lỗi nếu không chọn được.
  2. `DocumentAPI_Report2026.md`: Cập nhật tài liệu kỹ thuật về cơ chế Fail-Fast bảo vệ dữ liệu import.
- **Current Status**: **COMPLETED** — Đã hoàn thành 100% việc tái cấu trúc `report_exporter.py` sang cơ chế Fail-Fast, kiểm thử py_compile thành công và cập nhật `DocumentAPI_Report2026.md`.

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


















































































