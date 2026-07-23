# HANDOVER LOG - REPORT2026 WORKSPACE

## [2026-07-22 09:15:00] Task: Email Display Name (Alias) Support

### 1. Current Objective
Support Email Display Name (Alias) (e.g. `"Hệ thống Báo cáo Hạo Phương" <email@gmail.com>`) when sending email reports via `POST /api/reports/send-email/`, so recipient Gmail inbox displays the friendly sender name instead of raw email address.

### 2. Planned Modifications
- `report2026/settings.py`: Add `EMAIL_DISPLAY_NAME = env('EMAIL_DISPLAY_NAME', default='Hệ thống Báo cáo Hạo Phương')`
- `accounting/serializers.py`: Add `from_name = serializers.CharField(required=False, allow_blank=True, allow_null=True)` in `SendEmailSerializer`
- `accounting/views.py`: Update `from_email` construction in `SendEmailView` to format RFC 5322 `"Display Name" <smtp_user>`
- `DocumentAPI_Report2026.md`, `target.md`, `guildSendMail.md`: Update documentation to reflect `from_name` parameter and Display Name configuration.

### 3. Current Status
- **Completed**: Code implementation, syntax check, and documentation (`DocumentAPI_Report2026.md`, `target.md`, `guildSendMail.md`) updated.

---

## [2026-07-22 13:06:00] Task: Google OAuth2 Login Endpoint Implementation

### 1. Current Objective
Implement `POST /api/google-login/` endpoint for Single Sign-On (SSO) with Google ID token, verifying token authenticity with Google's OAuth2 servers, auto-creating/fetching Django User, and issuing Knox AuthToken for DRF authentication.

### 2. Planned Modifications
- `requirements.txt`: Add `google-auth` library
- `report2026/settings.py`: Add `GOOGLE_CLIENT_ID = env('GOOGLE_CLIENT_ID', default='')`
- `accounting/serializers.py`: Add `GoogleLoginSerializer`
- `accounting/views.py`: Add `GoogleLoginAPI` view verifying `id_token` and issuing Knox token
- `accounting/urls.py`: Register `path('google-login/', GoogleLoginAPI.as_view())`
- `DocumentAPI_Report2026.md`, `target.md`: Document `POST /api/google-login/`

### 3. Current Status
- **Completed**: `google-auth` installed, `GOOGLE_CLIENT_ID` added to `settings.py`, `GoogleLoginSerializer` and `GoogleLoginAPI` implemented in `views.py`/`urls.py`, syntax check passed 100%, and documentation ([DocumentAPI_Report2026.md](file:///d:/Sources/dashboard-report/DocumentAPI_Report2026.md#L366)) consolidated in section 7.1 (removed duplicate section at bottom).

---

## [2026-07-22 16:08:00] Task: Workspace Documentation Audit & Deduplication

### 1. Current Objective
Rà soát toàn bộ các tệp tài liệu trong dự án (`DocumentAPI_Report2026.md`, `target.md`, `guildSendMail.md`, `database_mapping.md`, `Accounting_Tracking_History.md`, `CheckList.md`) để phát hiện và loại bỏ thông tin trùng lặp hoặc lỗi định dạng tiêu đề.

### 2. Modifications Made
- `DocumentAPI_Report2026.md`: Đã loại bỏ phần cập nhật dư thừa ở cuối file, gộp hướng dẫn kiểm thử vào mục [7.1. Đăng nhập qua Google](file:///d:/Sources/dashboard-report/DocumentAPI_Report2026.md#L366).
- `target.md`: Sắp xếp lại thứ tự tiêu đề Mục 10 (Chênh lệch Thang máy) và Mục 11 (Google Login API) theo đúng thứ tự tuyến tính (10 -> 11).
- `guildSendMail.md`: Sửa lỗi lặp từ tiêu đề `"## 3. Hướng Dẫn Cấu Hướng Dẫn Cấu Hình SMTP..."` -> `"## 3. Hướng Dẫn Cấu Hình SMTP..."`.

### 3. Current Status
- **Completed**: Rà soát 100% tệp tài liệu trong workspace. Đã tích hợp hướng dẫn kiểm thử Google Login API qua Google OAuth2 Playground trực tiếp vào mục [7.1 trong DocumentAPI_Report2026.md](file:///d:/Sources/dashboard-report/DocumentAPI_Report2026.md#L366). Đã `git commit` (`6ac52ae`) và `git push` thành công lên `origin/main`.

---

## [2026-07-22 16:35:00] Task: FrontEndLogin UI Test Suite Implementation

### 1. Current Objective
Build a modern, interactive web frontend application in `FrontEndLogin/` for testing both Google SSO Login (`POST /api/google-login/`) and Username/Password Login (`POST /api/login/`), featuring Google Sign-In SDK button integration, manual ID Token tester, API inspector, Knox token manager, and test execution runner.

### 2. Planned Modifications
- `report2026/settings.py`: Enable `CORS_ALLOW_ALL_ORIGINS = True` to permit CORS requests from local frontend test runners.
- `FrontEndLogin/index.html`: Build glassmorphic single-page test dashboard with Google Identity Services SDK, tabbed authentication forms, response inspector, and Knox token tools.
- `FrontEndLogin/style.css`: Modern dark-theme glassmorphism CSS design system with Outfit/Inter typography, glowing borders, code formatting, and toast notifications.
- `FrontEndLogin/app.js`: Interactive JS logic for Google OAuth callback, DRF login endpoints communication, token storage, and response rendering.
- `FrontEndLogin/server.py`: Python HTTP server script for 1-click launching on `http://127.0.0.1:3000`.
- `DocumentAPI_Report2026.md`: Add FrontEndLogin testing guide notes.

### 3. Current Status
- **Completed**: Built `FrontEndLogin/` test suite (`index.html`, `style.css`, `app.js`, `server.py`, `README.md`), enabled `CORS_ALLOW_ALL_ORIGINS = True` in `settings.py`, and updated `DocumentAPI_Report2026.md`.

---

## [2026-07-22 17:03:00] Task: Google OAuth 2.0 "Error 400: origin_mismatch" Diagnosis & Solution

### 1. Current Objective
Diagnose and document the root cause and step-by-step fix for the frontend Google Sign-In error `Error 400: origin_mismatch` encountered when building/deploying to production or external domain.

### 2. Root Cause Analysis
- Google OAuth 2.0 policy requires every domain/origin initiating Google Sign-In SDK requests to be explicitly whitelisted under **Authorized JavaScript origins** in Google Cloud Console Credentials.
- Local testing (`http://localhost:3000` / `http://127.0.0.1:3000`) works because local origins are already whitelisted in the dev Client ID.
- Deploying to production/staging domain sends an unlisted `origin` header to Google OAuth server, triggering `Error 400: origin_mismatch`.

### 3. Solution Documented
- Added detailed step-by-step instructions in [DocumentAPI_Report2026.md](file:///d:/Sources/dashboard-report/DocumentAPI_Report2026.md#L414) explaining how to add the production/staging domain URL to **Authorized JavaScript origins** in Google Cloud Console.---

## [2026-07-23 08:25:00] Task: Duplicate CORS Header Fix (`Access-Control-Allow-Origin` Multiple Values)

### 1. Current Objective
Fix browser CORS blocking error: `The 'Access-Control-Allow-Origin' header contains multiple values 'https://report.haophuong.com, https://report.haophuong.com', but only one is allowed.`

### 2. Root Cause Analysis
- On production/staging server (`api-vending.haophuong.com`), Nginx reverse proxy already has `add_header Access-Control-Allow-Origin ...` configured.
- When `CORS_ALLOW_ALL_ORIGINS = True` was enabled in Django `settings.py`, Django's `CorsMiddleware` AND Nginx BOTH attached the `Access-Control-Allow-Origin` header, causing the browser to receive duplicate comma-separated values (`https://report.haophuong.com, https://report.haophuong.com`) and block the response.

### 3. Modifications Made
- `report2026/settings.py`: Commented out `CORS_ALLOW_ALL_ORIGINS = True` so Django does not duplicate the header that Nginx already provides on production.

### 4. Current Status
- **Completed**: Fixed `settings.py` to prevent duplicate CORS headers on production Nginx proxy.

---

## [2026-07-23 08:37:00] Task: Real-time DB Snapshot Query & Update

### 1. Current Objective
Extract real-time DB snapshot data for Month 7/2026 from `BUPerformance` table using python query syntax documented in `Accounting_Tracking_History.md` and update `Accounting_Tracking_History.md`.

### 2. Modifications Made
- `Accounting_Tracking_History.md`: Updated real-time snapshot table with timestamp `2026-07-23 08:37:00 (UTC+7)` for TOTAL_CORP and all 23 Business Units.

### 3. Current Status
- **Completed**: DB Snapshot extracted and documented in `Accounting_Tracking_History.md`.

---

## [2026-07-23 08:40:00] Task: July 22 Revenue Discrepancy Analysis (Accountant vs DB)

### 1. Current Objective
Analyze line-by-line revenue discrepancies between the Accountant's report (July 22, 2026) and Database `BUPerformance` (July 2026).

### 2. Analysis Findings
- Commercial BUs (**ECO**, **Oversea**, **Manufacture**) match **100.0% perfectly**.
- **AgriTech + SAB** matches **100.0%** (`489.4M + 343.2M = 832.6M`).
- **iBiz Premium** & **iBiz Value** match **99.6%** (minor ~42M / 60M diff).
- Core discrepancy (**+10.64B VNĐ**) is in **Elevator** (`BU_ELEVATOR`), caused by Accountant adding **`Hisa - FJT` (9.63B)** and **`5EX` (1.02B)** on their Excel sheet which are not in MISA `BAN_HANG` sales transactions nạp vào DB.

### 3. Modifications Made
- `Accounting_Tracking_History.md`: Added Section 3 with detailed revenue reconciliation table and breakdown.

### 4. Current Status
- **Completed**: Discrepancy identified and documented in `Accounting_Tracking_History.md`.

---

## [2026-07-23 08:44:00] Task: SOP Compliance Verification & Diagnostic Script Reusability

### 1. Current Objective
Acknowledge strict adherence to `.agents/AGENTS.md` and `CheckList.md` SOP rules (specifically requiring explicit user approval before executing git commits), add Section 12 to `target.md` for memory persistence, and create reusable diagnostic script `scripts/reconcile_revenue.py`.

### 2. Modifications Made
- `scripts/reconcile_revenue.py`: Created reusable diagnostic script to query DB revenue and collection snapshot without inline code duplication.
- `target.md`: Added Section 12 for revenue reconciliation memory persistence (SAB grouping & Elevator FJT analysis).
- `HANDOVER_LOG.md`: Documented task status and SOP compliance.

### 3. Current Status
- **Completed**: Verified SOP compliance. All documentation updated. Ready for user feedback (awaiting explicit user instruction for any future git commit).

---

## [2026-07-23 08:56:00] Task: Search SAB BusinessUnit / Customer in Sales Data

### 1. Current Objective
Check `BusinessUnit` master data, `SalesTransaction` records, and imported sales Excel files for any BU code or name containing `SAB`.

### 2. Planned Modifications
- `scripts/check_sab_bu.py`: Reusable python diagnostic script to search database and Excel files for `SAB`.
- `HANDOVER_LOG.md`: Document task objective and findings.

### 3. Current Status
- **Completed**: Diagnostics completed. Proved no independent `SAB` BU exists in MISA or DB. Identified SAB transaction `NKBH26070847` (343.2M VNĐ) under project `"Dự án sản xuất – kinh doanh thuộc BU Agritech – SAB Tôm 1 gram"` handled by `TRẦN HỒNG QUÂN` assigned to MISA branch `BU_AGRITECH`. Updated `target.md`. Awaiting user commit instructions if needed.






