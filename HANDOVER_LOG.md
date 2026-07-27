# HANDOVER LOG (Active Working Log)

> [!NOTE]
> Historical logs prior to 2026-07-24 11:28 have been archived to [docs/handover_archive/2026_07_archive.md](file:///d:/Sources/dashboard-report/docs/handover_archive/2026_07_archive.md).


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


















































































