# Báo cáo Phân tích Logic Hệ thống (Tồn kho, Nợ ngân hàng & Báo cáo thu nợ)

Tài liệu này tổng hợp toàn bộ kết quả rà soát chi tiết về logic tính toán tồn kho, nợ ngân hàng và các sai lệch nghiệp vụ trong báo cáo thu nợ trên Dashboard và các Celery Task của hệ thống Report2026.

---

## 1. Logic Tính Tồn Kho (Inventory)

Dữ liệu tồn kho được xử lý và lưu trữ qua hai cấp độ chính trong hệ thống:

### A. Cấp độ Báo cáo Hiệu suất BU (`BUPerformance`)
* **Nguồn dữ liệu:** Nạp từ các file Excel có tiền tố `TON_KHO` (ví dụ: `TON_KHO*.xlsx`) vào bảng [InventorySummary](file:///d:/Sources/dashboard-report/accounting/models/performance.py).
* **Mối liên kết đơn vị (BU):** Bảng `InventorySummary` không lưu trực tiếp thông tin `business_unit_id` mà liên kết gián tiếp qua trường kho hàng `warehouse` (`warehouse__business_unit_id`).
* **Logic tính toán tích lũy tháng:** Được thực hiện tự động trong [update_single_bu_performance](file:///d:/Sources/dashboard-report/accounting/services/kpi_calculator.py):
  * **Bộ lọc thời gian:** Lấy theo Snapshot hiện hành của bảng `InventorySummary`.
  * **Bộ lọc BU & Loại trừ cấu hình ở settings:** Xem quy tắc chi tiết tại [Mục 4.1 của DocumentAPI_Report2026.md](file:///d:/Sources/dashboard-report/DocumentAPI_Report2026.md#1-logic-x%C3%A1c-%C4%91%E1%BB%8Bnh-ph%E1%BA%A1m-vi-global--sub-bu).
  * **Công thức tổng hợp:**
    * `inventory_opening_value` (Giá trị đầu kỳ) = Tổng cột `opening_value`
    * `inventory_in_value` (Giá trị nhập kho trong kỳ) = Tổng cột `in_value`
    * `inventory_out_value` (Giá trị xuất kho trong kỳ) = Tổng cột `out_value`
    * `inventory_value_actual` (Giá trị tồn kho thực tế cuối kỳ) = Tổng cột `closing_value`

### B. Cấp độ Chi tiết Kho hàng (`Warehouse`)
* **Tác vụ đồng bộ:** Được thực hiện qua hàm [sync_warehouse_inventory_data_logic](file:///d:/Sources/dashboard-report/accounting/services/inventory_sync.py).
* **Mô tả xử lý:** Tác vụ quét qua tất cả các kho hàng ([Warehouse](file:///d:/Sources/dashboard-report/accounting/models/organization.py)), thực hiện tính tổng (`opening_value`, `in_value`, `out_value`, `closing_value`) từ bảng `InventorySummary` của kho đó rồi lưu ngược lại vào các trường:
  * `wh.inventory_opening_value`
  * `wh.inventory_in_value`
  * `wh.inventory_out_value`
  * `wh.inventory_value_actual`
* **Lưu ý vận hành:** Tiến trình này tự động kích hoạt sau khi nạp file Excel tồn kho hoặc chạy thủ công từ giao diện Admin.

---

## 2. Logic Tính Nợ Ngân Hàng (Bank Debt)

* **Thiết kế cơ sở dữ liệu:**
  * Bảng [BUPerformance](file:///d:/Sources/dashboard-report/accounting/models/performance.py) đã định nghĩa sẵn 2 trường để theo dõi:
    * `bank_debt_plan` (Nợ ngân hàng - Kế hoạch)
    * `bank_debt_actual` (Nợ ngân hàng - Thực tế)
  * Trong luồng nạp dữ liệu tự động từ Misa (sử dụng Playwright), hệ thống thiết lập tải về chi tiết tài khoản **`341`** (tiền vay và nợ thuê tài chính liên quan trực tiếp đến nợ ngân hàng) cùng tài khoản `111, 112` để nạp vào bảng [AccountDetail](file:///d:/Sources/dashboard-report/accounting/models/transactions.py).
* **Hiện trạng logic tính toán:**
  * **Hiện tại chưa có logic tính toán cho trường này**. Trong file xử lý nghiệp vụ [tasks.py](file:///d:/Sources/dashboard-report/accounting/tasks.py), hệ thống hoàn toàn **chưa thực hiện bất kỳ phép cộng dồn hay tính toán nào** đối với trường `bank_debt_actual`.
  * Do đó, giá trị của `bank_debt_actual` trong DB và trên Dashboard luôn mang giá trị mặc định là `0`. Đây là một phần **nợ kỹ thuật (Technical Debt)** đã được ghi nhận rõ trong tài liệu hướng dẫn tổng quan của dự án.

---

## 3. Logic Báo Cáo Thu Nợ & Công Nợ Khách Hàng (Receivables & Collection)

Phần này phân tích logic, các sai lệch nghiệp vụ và các đề xuất xử lý liên quan đến báo cáo thu nợ hàng ngày và báo cáo hiệu suất BU.

### A. Phân tích chi tiết API View `DashboardCollectionByBUAPIView`
Lớp API View [DashboardCollectionByBUAPIView](file:///d:/Sources/dashboard-report/accounting/views.py#L253) trả về 5 chỉ số thu nợ hàng ngày cho từng BU chính (`is_main=True`). Qua đối chiếu giữa comment thiết kế và logic thực tế, có sự sai lệch nghiêm trọng:

| Chỉ số | Định nghĩa trong Comment | Logic thực tế trong Code | Đánh giá & Bất cập nghiệp vụ |
| :--- | :--- | :--- | :--- |
| **`receivable_total`** | Dư nợ cần thu (snapshot hiện tại của `ReceivablesAgeing`). | `Sum('total_debt')` từ bảng `ReceivablesAgeing` lọc theo BU. | **[GẶP LỖI / BUG]**<br>Thiếu bộ lọc `reporting_period` dẫn đến việc cộng dồn công nợ của **tất cả các tháng** có trong DB (ví dụ: tháng 5, 6, 7/2026), khiến số liệu dư nợ của BU bị phóng đại gấp nhiều lần (HPC tháng 6/2026 thực tế 61.4 tỷ nhưng Dashboard hiện thị 211 tỷ). |
| **`commitment_overdue`** | Cam kết (quá hạn) — dùng tạm `overdue_total`. | `Sum('overdue_total')` từ bảng `ReceivablesAgeing` lọc theo BU. | **[GẶP LỖI / BUG]**<br>Tương tự `receivable_total`, thiếu bộ lọc theo kỳ báo cáo dẫn đến cộng dồn lũy kế qua các tháng. |
| **`total_collected`** | Tổng thu trong ngày. | Tính từ phát sinh Nợ - Có (`debit_amount - credit_amount`) của các tài khoản tiền/ngân hàng (`111`, `112`) đối ứng phải thu khách hàng (`1311`, `1312`) trong ngày từ bảng [AccountDetail](file:///d:/Sources/dashboard-report/accounting/models.py#L185). | **Khớp nghiệp vụ.** Phản ánh đúng dòng tiền thực thu trong ngày của BU. |
| **`collected_due`** | Đã thu (đến hạn) — phát sinh trên khách hàng có nợ quá hạn. | Lấy `Sum('due_total')` từ bảng snapshot dư nợ [ReceivablesAgeing](file:///d:/Sources/dashboard-report/accounting/models.py#L222). | **[ĐÃ GIẢI QUYẾT / FIXED]**<br>Code đã được sửa thành lọc đối ứng tiền thu trực tiếp từ `AccountDetail` thay vì dùng bảng Ageing. |
| **`collected_in_term_cod`**| Thu trong hạn + COD = Tổng thu - Đã thu đến hạn. | Tính bằng công thức:<br>`total_collected - collected_due` | **[ĐÃ GIẢI QUYẾT / FIXED]**<br>Đã sửa theo công thức chính xác là `Tổng thực thu (dòng tiền) - Đã thu đến hạn`. |

### B. So sánh với logic MTD (Tháng) trong `tasks.py`
Sự bất nhất này bắt nguồn từ việc copy pattern tính toán lũy kế tháng trong [tasks.py:L237-L246](file:///d:/Sources/dashboard-report/accounting/tasks.py#L237-L246) sang view API:
* **Tại `tasks.py` (Cấp độ tháng):**
  * `collection_due_actual` được gán bằng `due_now` (tổng `due_total` của `ReceivablesAgeing`).
  * `collection_in_term_cod` được tính bằng `receivable_total - receivable_overdue` (tức là `total_debt - overdue_total`).
* **Vấn đề:**
  * Về mặt toán học: `total_debt - overdue_total` chính là `due_total`. Vì vậy, hai trường `collection_due_actual` và `collection_in_term_cod` ở bảng tháng thực chất đang nhận cùng một giá trị như nhau.
  * Cả hai đều được lấy trực tiếp từ bảng snapshot dư nợ cuối kỳ chứ không phải từ số tiền thực tế đã thu qua sổ chi tiết tài khoản.

### C. Sự bất nhất trong xử lý phân cấp Đơn vị kinh doanh (BU Hierarchy)
* **Bối cảnh cấu trúc phân cấp (BU Hierarchy):** Bảng [BusinessUnit](file:///d:/Sources/dashboard-report/accounting/models.py#L94) sử dụng mối quan hệ tự tham chiếu (Self-reference) qua khóa ngoại `parent` để mô tả mô hình cây (BU cha - BU con). Theo tài liệu thiết kế hệ thống, cấu trúc này nhằm phục vụ việc **cộng dồn KPI từ dưới lên** (Bottom-up rollup).
* **Vấn đề thực tế trong code (ĐÃ GIẢI QUYẾT / FIXED):**
  * **Lỗi treats root BUs as global trong `update_single_bu_performance`:** Trước đây, hệ thống tự động gán `is_global = True` nếu BU không có cha (`parent_id is None`). Logic này làm cho tất cả các BU gốc (như HPC, ĐTCT,...) khi tính hiệu suất đều bị lấy tổng số liệu của toàn bộ Tổng công ty thay vì tách biệt theo nhánh của mình. Hiện tại, **đã sửa đổi**: hệ thống chỉ bật `is_global = True` khi `bu_id` nhận vào là `None` (Tổng công ty thực sự).
  * **Trong Celery Task `update_single_bu_performance`:** Hệ thống đã được cập nhật logic đệ quy gọi hàm `bu.get_all_descendant_ids()` để lấy các BU con.
  * **Trong `DashboardCollectionByBUAPIView`:** Đã cập nhật áp dụng mảng danh sách các BU con thay vì lọc chính xác bằng id cứng, đảm bảo gom số liệu chuẩn xác.

### D. Đề xuất Hướng sửa đổi
Để hệ thống tính toán chính xác theo đúng ý nghĩa nghiệp vụ:
1. **Đối với `collected_due` (Đã thu đến hạn):**
   * Không lấy từ bảng snapshot `ReceivablesAgeing`.
   * Cần lọc các phát sinh thu tiền trong ngày từ bảng `AccountDetail` (đối ứng 111, 112 với 131) nhưng chỉ lấy những khách hàng có trạng thái nợ quá hạn/đến hạn tại thời điểm thu.
2. **Đối với `collected_in_term_cod` (Thu trong hạn + COD):**
   * Tính toán bằng công thức: `total_collected` (Tổng thực thu trong ngày) - `collected_due` (Đã thu đến hạn thực tế).
3. **Đối với xử lý phân cấp BU (BU Hierarchy):**
   * Cần bổ sung logic đệ quy tìm toàn bộ danh sách ID của các BU con (và cháu, chắt...) của BU hiện tại:
     ```python
     def get_all_child_bu_ids(bu_id):
         bu_ids = [bu_id]
         children = BusinessUnit.objects.filter(parent_id=bu_id).values_list('id', flat=True)
         for child_id in children:
             bu_ids.extend(get_all_child_bu_ids(child_id))
         return bu_ids
     ```
   * Khi thực hiện lọc theo BU trong các câu lệnh `filter(...)`, chuyển từ lọc chính xác (`business_unit=bu` hoặc `business_unit_id=bu_id`) sang lọc tập hợp `__in` (`business_unit_id__in=bu_ids` hoặc `business_unit_in=bu_list`).
4. **Đối với bộ lọc công nợ trên Dashboard (`receivable_total` và `commitment_overdue`):**
   * Cần bổ sung điều kiện lọc theo kỳ báo cáo `reporting_period` khớp với ngày yêu cầu (ví dụ: `reporting_period=f"{date.year:04d}-{date.month:02d}"`) khi truy vấn bảng `ReceivablesAgeing` trong [DashboardCollectionByBUAPIView](file:///d:/Sources/dashboard-report/accounting/views.py#L272) để tránh cộng dồn sai lệch qua các tháng.

---

## 4. Custom Django Commands hỗ trợ chạy từ Terminal
Xem chi tiết cú pháp và tất cả tùy chọn tại **[Run_Test_Scripts.md](Run_Test_Scripts.md)** (Mục 2: Django Custom Management Commands). Các lệnh chính:
- `python manage.py calculate_global_performance --month 6 --year 2026`
- `python manage.py calculate_bu_performance --bu_id 70 --month 6 --year 2026`
- `python manage.py sync_misa [--action=all|download|import] [--file=<PATH>]`

---

## 5. Doanh thu khách hàng Oversea & Doanh thu không bao gồm Oversea
Hệ thống hỗ trợ tách biệt doanh thu bán hàng của nhóm khách hàng nước ngoài (Oversea) để phục vụ báo cáo cơ cấu doanh thu:
* **Cấu hình nhóm:** Nhóm khách hàng được định nghĩa qua biến `OVERSEA_CUSTOMER_GROUP_CODES` trong [settings.py](file:///d:/Sources/dashboard-report/report2026/settings.py) (mặc định là `['Oversea']`).
* **Các trường dữ liệu mới (bảng `BUPerformance`):**
  * `mtd_revenue_oversea_actual`: Doanh thu Oversea thực tế trong tháng (MTD).
  * `mtd_revenue_exclude_oversea_actual`: Doanh thu thực tế trong tháng không bao gồm Oversea (MTD).
  * `ytd_revenue_oversea_actual`: Doanh thu Oversea thực tế lũy kế năm (YTD).
  * `ytd_revenue_exclude_oversea_actual`: Doanh thu thực tế lũy kế năm không bao gồm Oversea (YTD).
  * `mtd_collection_oversea_actual`: Thực thu Oversea thực tế trong tháng (MTD).
  * `mtd_collection_exclude_oversea_actual`: Thực thu thực tế trong tháng không bao gồm Oversea (MTD).
  * `ytd_collection_oversea_actual`: Thực thu Oversea thực tế lũy kế năm (YTD).
  * `ytd_collection_exclude_oversea_actual`: Thực thu thực tế lũy kế năm không bao gồm Oversea (YTD).
* **Công thức tính toán:**
  * `mtd_revenue_oversea_actual` = Tổng doanh thu của các khách hàng có nhóm thuộc `OVERSEA_CUSTOMER_GROUP_CODES` trong tháng.
  * `mtd_revenue_exclude_oversea_actual` = Tổng doanh thu tháng (`mtd_revenue_actual`) - Doanh thu Oversea tháng.
  * `mtd_collection_oversea_actual` = Tổng thực thu của các khách hàng có nhóm thuộc `OVERSEA_CUSTOMER_GROUP_CODES` trong tháng.
  * `mtd_collection_exclude_oversea_actual` = Tổng thực thu tháng (`mtd_collection_actual`) - Thực thu Oversea tháng.
  * Các chỉ số lũy kế YTD tương ứng được tự động cộng dồn qua từng tháng và lan truyền đến hết tháng 12 của năm đó.
* **Bộ lọc phân tách theo BU:**
  * **Tổng công ty (Global - `bu_id is None`)**: Tính toán bao gồm cả trong nước và Oversea (không loại trừ).
  * **Nhánh Oversea** (BU có code `Oversea` hoặc trực thuộc `Oversea`): Tính **TẤT CẢ giao dịch của khách hàng thuộc nhóm Oversea**, bất kể giao dịch đó được ghi nhận ở BU nào trong MISA. Không filter theo `business_unit_id`. Áp dụng cho cả Doanh thu, Thực thu và Công nợ.
  * **Các BU trong nước khác**: Loại bỏ hoàn toàn các khách hàng thuộc nhóm khách hàng Oversea khi tính toán Doanh thu, Thực thu và Công nợ/Tuổi nợ.
* **Nhật ký đối soát thu tiền (Accounting Tracking History)**: Xem chi tiết toàn bộ lịch sử đối soát số liệu thu tiền giữa Kế toán và Database tại [Accounting_Tracking_History.md](file:///d:/Sources/dashboard-report/Accounting_Tracking_History.md).

---

## 6. Quy trình xuất Báo cáo từ MISA qua Playwright
Để đảm bảo số liệu xuất từ MISA là chính xác và không bị thiếu hụt dữ liệu, hệ thống Playwright thực hiện các bước tự động sau:

### 6.1. Quy trình tổng quát (Áp dụng cho BAN_HANG, MUA_HANG, TON_KHO, CONG_NO_NCC, TUOI_NO_KH, SO_DU_NH)
1. Truy cập trực tiếp vào URL báo cáo tương ứng.
2. Click nút **"Chọn tham số"**.
3. Tích chọn checkbox **"Bao gồm số liệu chi nhánh phụ thuộc"** (có bước xác nhận lại class `checked-true` và JS fallback nếu chưa tick thành công).
4. Loại bỏ các chi nhánh phụ thuộc có chứa ký tự `_Nhật`.
5. Chọn kỳ báo cáo (mặc định cấu hình **"Tháng này"** trong `settings.MISA_REPORT_PERIOD_OPTION` hoặc tùy chỉnh **"Năm nay"**; riêng `TUOI_NO_KH` bỏ qua bước chọn kỳ báo cáo).
6. Tích chọn các checkbox độc lập nằm kế bên nhãn **"Chọn tất cả"** (loại trừ checkbox `th` header, bổ sung độ trễ 1.0s giữa mỗi ô click).
7. Click nút **"Đồng ý"** / **"Xem báo cáo"** và chờ 20 giây để báo cáo hiển thị kết quả.
8. Đối với báo cáo bán hàng (`BAN_HANG`): Click chọn biểu tượng **Bánh răng** (`.mi-setting__list-bold`) ở góc trên bên phải grid $\rightarrow$ Chọn mẫu **"Mẫu chuẩn."** (chờ 4 giây fallback render và 5 giây để MISA tải lại dữ liệu).
9. Mở khay download dọn sạch lịch sử tải cũ (**"Xóa hết lịch sử tải tệp"** $\rightarrow$ bấm **"Có"**) để chống dính file cũ, sau đó đóng khay.
10. Click vào biểu tượng **Excel** trên thanh công cụ và chọn **"Xuất Excel (dạng dữ liệu)"**.
11. Chờ 20 giây để hệ thống MISA kết xuất, mở khay download (dùng 3 indicator nhận diện chuẩn Commit `57a0e59`: `["Tải tệp Excel, tệp in,...", "Đang tạo đường dẫn tải tệp...", "Đường dẫn tải tệp sẽ hết hạn"]`) và click **"Tải tệp"** (ô mới nhất) để lưu về máy.

### 6.2. Quy trình đặc thù cho Sổ chi tiết các tài khoản (TAI_KHOAN_CT)
Để thu thập đủ dữ liệu hạch toán Thu tiền (TK 111, 112), Nợ ngân hàng (TK 341) và Chi phí vận hành OPEX (TK 641, 642):
* **Chọn Bậc = 1**: Chọn combobox Bậc/Cấp = 1 (với fallback dùng phím `ArrowDown` + `Enter`).
* **Lọc từng tài khoản cụ thể**: Với từng mã tài khoản trong danh sách `settings.MISA_SO_CHI_TIET_ACCOUNTS` (`['111', '112', '341', '641', '642']`):
  1. Gõ mã tài khoản vào ô tìm kiếm (`Nhập từ khóa tìm kiếm`).
  2. Chờ 1.5 giây để lưới dữ liệu MISA lọc kết quả.
  3. Chạy JS script để tìm dòng khớp chính xác mã tài khoản và tick chọn checkbox của dòng đó.
* **Bỏ qua Bước 5 ("Chọn tất cả")**: Báo cáo `TAI_KHOAN_CT` **bắt buộc loại trừ khỏi bước "Chọn tất cả"** (`if prefix != 'TAI_KHOAN_CT':`) để tránh việc nút "Chọn tất cả" chạy đè làm hủy/thay đổi trạng thái tick của 5 tài khoản đã chọn ở bước trước.

### 6.3. Danh sách từng bước chi tiết cho 7 Báo Cáo MISA Web (Chuẩn Mã Nguồn)

#### 1. Báo cáo `BAN_HANG` (Sổ chi tiết bán hàng)
- **URL**: `https://actapp.misa.vn/app/SA/ReportAnalysis/RPDynamicViewer/SalesBookDetailDefault`
- **Từng bước thực hiện**:
  1. Mở URL báo cáo `SalesBookDetailDefault`.
  2. Click nút **"Chọn tham số"**.
  3. Tích chọn **"Bao gồm số liệu chi nhánh phụ thuộc"** (xác nhận trạng thái `checked-true`).
  4. Quét và xóa toàn bộ các tag chi nhánh chứa `_Nhật` (như `FUJI_Nhật`, `Nippon_Nhật`).
  5. Chọn **Kỳ báo cáo**: Mở combobox Kỳ báo cáo, chọn `"Tháng này"` (hoặc `"Năm nay"`).
  6. **Tích Chọn tất cả**: Tích ô **"Chọn tất cả"** cho danh sách *Vật tư hàng hóa* **VÀ** *Khách hàng* (delay 1.0s giữa các lần click).
  7. Click nút **"Đồng ý" / "Xem báo cáo"**.
  8. *Auto-dismiss alert*: Nếu MISA bật popup cảnh báo *"Bạn chưa chọn..."*, tự động chụp screenshot debug, bấm **"Đóng"**, kích hoạt lại **"Chọn tất cả"** và bấm lại **"Đồng ý"**.
  9. ⭐ **BƯỚC ĐẶC BIỆT - Chọn Mẫu chuẩn**: Đợi dữ liệu tải xong (timeout 30s) $\rightarrow$ Click nút bánh răng cài đặt lưới (`.mi-setting__list-bold`) $\rightarrow$ Chọn mẫu **`"Mẫu chuẩn."`** $\rightarrow$ Chờ 5s reload.
  10. ⭐ **BƯỚC ĐẶC BIỆT - Xóa lịch sử tải cũ**: Bấm Panel quản lý tải tệp (`.ms-download`) $\rightarrow$ Click **"Xóa hết lịch sử tải tệp"** $\rightarrow$ Bấm **"Có"** xác nhận $\rightarrow$ Đóng panel.
  11. **Yêu cầu Xuất Excel**: Click icon **Excel** $\rightarrow$ Chọn **"Xuất Excel (dạng dữ liệu)"** $\rightarrow$ Bấm **"Đồng ý"** (nếu hiện popup).
  12. **Tải file về**: Chờ 20s MISA kết xuất ngầm $\rightarrow$ Mở lại Panel Quản lý tải tệp $\rightarrow$ Chờ nút **"Tải tệp"** (mới nhất) xuất hiện với `page.expect_download(timeout=45000)` $\rightarrow$ Lưu file về `media/auto_imports/BAN_HANG_YYYYMMDD_HHMMSS.xlsx`.

#### 2. Báo cáo `MUA_HANG` (Sổ chi tiết mua hàng)
- **URL**: `https://actapp.misa.vn/app/PU/ReportAnalysis/RPDynamicViewer/PUDetailPurchaseByInventoryItemDynamic`
- **Từng bước thực hiện**:
  1. Mở URL báo cáo `PUDetailPurchaseByInventoryItemDynamic`.
  2. Click nút **"Chọn tham số"**.
  3. Tích chọn **"Bao gồm số liệu chi nhánh phụ thuộc"**.
  4. Quét và xóa toàn bộ các tag chi nhánh chứa `_Nhật`.
  5. Chọn **Kỳ báo cáo**: `"Tháng này"` (hoặc `"Năm nay"`).
  6. **Tích Chọn tất cả**: Tích ô **"Chọn tất cả"** cho danh sách *Vật tư hàng hóa* **VÀ** *Nhà cung cấp* (delay 1.0s).
  7. Click **"Đồng ý" / "Xem báo cáo"** (kèm auto-dismiss cảnh báo nếu có).
  8. Mở Panel Quản lý tải tệp $\rightarrow$ **Xóa hết lịch sử tải tệp** $\rightarrow$ Bấm **"Có"** $\rightarrow$ Đóng panel.
  9. Click icon **Excel** $\rightarrow$ Chọn **"Xuất Excel (dạng dữ liệu)"** $\rightarrow$ Bấm **"Đồng ý"** (nếu có).
  10. Chờ 20s $\rightarrow$ Mở Panel Quản lý tải tệp $\rightarrow$ Click **"Tải tệp"** mới nhất $\rightarrow$ Lưu file về `media/auto_imports/MUA_HANG_YYYYMMDD_HHMMSS.xlsx`.

#### 3. Báo cáo `TON_KHO` (Tổng hợp tồn kho)
- **URL**: `https://actapp.misa.vn/app/IN/ReportAnalysis/RPDynamicViewer/INInventoryBalanceSummary`
- **Từng bước thực hiện**:
  1. Mở URL báo cáo `INInventoryBalanceSummary`.
  2. Click nút **"Chọn tham số"**.
  3. Tích chọn **"Bao gồm số liệu chi nhánh phụ thuộc"**.
  4. Quét và xóa toàn bộ các tag chi nhánh chứa `_Nhật`.
  5. Chọn **Kỳ báo cáo**: `"Tháng này"` (hoặc `"Năm nay"`).
  6. **Tích Chọn tất cả**: Tích ô **"Chọn tất cả"** cho danh sách *Vật tư hàng hóa* / *Kho* (delay 1.0s).
  7. Click **"Đồng ý" / "Xem báo cáo"** (kèm auto-dismiss cảnh báo nếu có).
  8. Mở Panel Quản lý tải tệp $\rightarrow$ **Xóa hết lịch sử tải tệp** $\rightarrow$ Bấm **"Có"** $\rightarrow$ Đóng panel.
  9. Click icon **Excel** $\rightarrow$ Chọn **"Xuất Excel (dạng dữ liệu)"** $\rightarrow$ Bấm **"Đồng ý"** (nếu có).
  10. Chờ 20s $\rightarrow$ Mở Panel Quản lý tải tệp $\rightarrow$ Click **"Tải tệp"** mới nhất $\rightarrow$ Lưu file về `media/auto_imports/TON_KHO_YYYYMMDD_HHMMSS.xlsx`.

#### 4. Báo cáo `CONG_NO_NCC` (Tổng hợp công nợ phải trả nhà cung cấp)
- **URL**: `https://actapp.misa.vn/app/PU/ReportAnalysis/RPDynamicViewer/PUPayableSummaryBySupplier`
- **Từng bước thực hiện**:
  1. Mở URL báo cáo `PUPayableSummaryBySupplier`.
  2. Click nút **"Chọn tham số"**.
  3. Tích chọn **"Bao gồm số liệu chi nhánh phụ thuộc"**.
  4. Quét và xóa toàn bộ các tag chi nhánh chứa `_Nhật`.
  5. Chọn **Kỳ báo cáo**: `"Tháng này"` (hoặc `"Năm nay"`).
  6. **Tích Chọn tất cả**: Tích ô **"Chọn tất cả"** cho danh sách *Nhà cung cấp* (delay 1.0s).
  7. Click **"Đồng ý" / "Xem báo cáo"** (kèm auto-dismiss cảnh báo nếu có).
  8. Mở Panel Quản lý tải tệp $\rightarrow$ **Xóa hết lịch sử tải tệp** $\rightarrow$ Bấm **"Có"** $\rightarrow$ Đóng panel.
  9. Click icon **Excel** $\rightarrow$ Chọn **"Xuất Excel (dạng dữ liệu)"** $\rightarrow$ Bấm **"Đồng ý"** (nếu có).
  10. Chờ 20s $\rightarrow$ Mở Panel Quản lý tải tệp $\rightarrow$ Click **"Tải tệp"** mới nhất $\rightarrow$ Lưu file về `media/auto_imports/CONG_NO_NCC_YYYYMMDD_HHMMSS.xlsx`.

#### 5. Báo cáo `TUOI_NO_KH` (Chi tiết công nợ theo tuổi nợ)
- **URL**: `https://actapp.misa.vn/app/PU/ReportAnalysis/RPDynamicViewer/ReceivableDetailByDebtAge`
- **Từng bước thực hiện**:
  1. Mở URL báo cáo `ReceivableDetailByDebtAge`.
  2. Click nút **"Chọn tham số"**.
  3. Tích chọn **"Bao gồm số liệu chi nhánh phụ thuộc"**.
  4. Quét và xóa toàn bộ các tag chi nhánh chứa `_Nhật`.
  5. ⭐ **BƯỚC BỎ QUA**: **Bỏ qua bước chọn Kỳ Báo Cáo** (Form MISA báo cáo này không có ô Chọn Kỳ).
  6. **Tích Chọn tất cả**: Tích ô **"Chọn tất cả"** cho danh sách *Khách hàng* (delay 1.0s).
  7. Click **"Đồng ý" / "Xem báo cáo"** (kèm auto-dismiss cảnh báo nếu có).
  8. Mở Panel Quản lý tải tệp $\rightarrow$ **Xóa hết lịch sử tải tệp** $\rightarrow$ Bấm **"Có"** $\rightarrow$ Đóng panel.
  9. Click icon **Excel** $\rightarrow$ Chọn **"Xuất Excel (dạng dữ liệu)"** $\rightarrow$ Bấm **"Đồng ý"** (nếu có).
  10. Chờ 20s $\rightarrow$ Mở Panel Quản lý tải tệp $\rightarrow$ Click **"Tải tệp"** mới nhất $\rightarrow$ Lưu file về `media/auto_imports/TUOI_NO_KH_YYYYMMDD_HHMMSS.xlsx`.

#### 6. Báo cáo `TAI_KHOAN_CT` (Sổ chi tiết các tài khoản) — BÁO CÁO ĐẶC BIỆT
- **URL**: `https://actapp.misa.vn/app/RP/ReportList/RPDynamicViewer/GLAccountLedger`
- **Từng bước thực hiện**:
  1. Mở URL báo cáo `GLAccountLedger`.
  2. Click nút **"Chọn tham số"**.
  3. Tích chọn **"Bao gồm số liệu chi nhánh phụ thuộc"**.
  4. Quét và xóa toàn bộ các tag chi nhánh chứa `_Nhật`.
  5. ⭐ **BƯỚC ĐẶC BIỆT 1 - Chọn Bậc**: Click ô combobox **Bậc** $\rightarrow$ Chọn **`1`** (fallback bàn phím `Home` $\rightarrow$ `ArrowDown` $\rightarrow$ `Enter`).
  6. ⭐ **BƯỚC ĐẶC BIỆT 2 - Lọc chọn 5 Tài khoản**: Gõ từng mã tài khoản vào ô *"Nhập từ khóa tìm kiếm"*, chờ 1.5s filter rồi tích chọn dòng khớp qua JS: `111` (Tiền mặt), `112` (Tiền gửi NH), `341` (Vay & nợ thuê tài chính), `641` (CP Bán hàng), `642` (CP QLDN).
  7. ⭐ **BƯỚC BỎ QUA**: **BỎ QUA hoàn toàn ô "Chọn tất cả"** (không chọn tất cả tài khoản).
  8. Chọn **Kỳ báo cáo**: `"Tháng này"` (hoặc `"Năm nay"`).
  9. Click **"Đồng ý" / "Xem báo cáo"** (kèm auto-dismiss cảnh báo nếu có).
  10. Mở Panel Quản lý tải tệp $\rightarrow$ **Xóa hết lịch sử tải tệp** $\rightarrow$ Bấm **"Có"** $\rightarrow$ Đóng panel.
  11. Click icon **Excel** $\rightarrow$ Chọn **"Xuất Excel (dạng dữ liệu)"** $\rightarrow$ Bấm **"Đồng ý"** (nếu có).
  12. Chờ 20s $\rightarrow$ Mở Panel Quản lý tải tệp $\rightarrow$ Click **"Tải tệp"** mới nhất $\rightarrow$ Lưu file về `media/auto_imports/TAI_KHOAN_CT_YYYYMMDD_HHMMSS.xlsx`.

#### 7. Báo cáo `SO_DU_NH` (Bảng kê số dư ngân hàng) — BÁO CÁO ĐẶC BIỆT
- **URL**: `https://actapp.misa.vn/app/BA/ReportAnalysis/RPDynamicViewer/BAListOfBalance`
- **Từng bước thực hiện**:
  1. Mở URL báo cáo `BAListOfBalance`.
  2. Click nút **"Chọn tham số"**.
  3. Tích chọn **"Bao gồm số liệu chi nhánh phụ thuộc"**.
  4. Quét và xóa toàn bộ các tag chi nhánh chứa `_Nhật`.
  5. Chọn **Kỳ báo cáo**: `"Tháng này"` (hoặc `"Năm nay"`).
  6. **Tích Chọn tất cả**: Tích ô **"Chọn tất cả"** cho danh sách *Tài khoản ngân hàng* (delay 1.0s).
  7. Click **"Đồng ý" / "Xem báo cáo"** (kèm auto-dismiss cảnh báo nếu có).
  8. Mở Panel Quản lý tải tệp $\rightarrow$ **Xóa hết lịch sử tải tệp** $\rightarrow$ Bấm **"Có"** $\rightarrow$ Đóng panel.
  9. Click icon **Excel** $\rightarrow$ Chọn **"Xuất Excel (dạng dữ liệu)"** $\rightarrow$ Bấm **"Đồng ý"** (nếu có).
  10. Chờ 20s $\rightarrow$ Mở Panel Quản lý tải tệp $\rightarrow$ Click **"Tải tệp"** mới nhất $\rightarrow$ Lưu file về `media/auto_imports/SO_DU_NH_YYYYMMDD_HHMMSS.xlsx`. *(Nạp CSDL và Lọc bỏ STK 113611393939 do Celery Worker thực thi sau khi nhận diện file Excel)*.

* **Tải riêng từng báo cáo / Nạp file Excel rời vào CSDL:**
  Xem hướng dẫn đầy đủ tại **[Run_Test_Scripts.md](Run_Test_Scripts.md)** — Mục 3.1 (`download_report.py`) và Mục 3.2 (`import_specific_file.py`) và Mục 2.1 (`sync_misa --action import --file <PATH>`).

---

## 7. Chi phí vận hành (OPEX)
Hệ thống hỗ trợ tính toán và theo dõi Chi phí vận hành thực tế (`opex_actual`) và Kế hoạch (`opex_plan`) của từng BU và toàn công ty:
* **Tài khoản hạch toán đầu vào:** Trích xuất từ các phát sinh của tài khoản đầu **`641`** (Chi phí bán hàng) và **`642`** (Chi phí quản lý doanh nghiệp) trong sổ chi tiết tài khoản `AccountDetail`.
* **Cấu hình đồng bộ từ MISA:** Khi xuất Sổ chi tiết tài khoản (`TAI_KHOAN_CT`), hệ thống Playwright tự động chọn thêm các tài khoản cấu hình trong `settings.py` (`MISA_SO_CHI_TIET_ACCOUNTS` mặc định gồm `['111', '112', '341', '641', '642']`).
* **Công thức tính toán Thực tế lũy kế tháng (`opex_actual`):**
  $$opex\_actual = \sum_{d=1}^{D_{target}} \text{daily\_opex\_plan}(d) + \sum_{d=1}^{D_{target}} \text{daily\_opex\_actual}(d)$$
  *Trong đó:*
  * `daily_opex_plan` (Kế hoạch ngày - CPVHKHMN): Phân bổ từ kế hoạch tháng chia số ngày trong tháng, hoặc chỉnh sửa thủ công riêng cho từng ngày.
  * `daily_opex_actual` (Thực tế ngày - CPVHTTMN): Tổng phát sinh Nợ của các tài khoản `641` và `642` trong ngày đó từ bảng `AccountDetail`.
  * $D_{target}$: Số ngày từ ngày 1 đến ngày hạch toán mục tiêu (`target_date`).
* **Đồng bộ kế hoạch hai chiều (Django Admin):**
  * Khi lưu Kế hoạch tháng (`opex_plan`): Tự động chia đều cho số ngày trong tháng để điền kế hoạch ngày (`daily_opex_plan`).
  * Khi lưu chi tiết Kế hoạch ngày (`daily_opex_plan`): Tự động cộng dồn tất cả các ngày con để cập nhật ngược lại kế hoạch tháng (`opex_plan`).
* **Lũy kế năm (YTD):** Chi phí opex lũy kế thực tế (`ytd_opex_actual`) và kế hoạch (`ytd_opex_plan`) được cộng dồn lũy kế qua các tháng và lan truyền tự động đến hết năm tài chính.

---

## 8. Số dư ngân hàng & Tiền cuối kỳ (Cash Balance)
Hệ thống tính toán Tiền cuối kỳ thực tế (`cash_balance_actual`) bằng cách kết hợp số liệu từ Sổ chi tiết tài khoản và Bảng kê số dư ngân hàng:
* **Công thức tính toán:**
  $$\text{cash\_balance\_actual} = (\text{cash\_bal\_111 (sổ chi tiết)} + \text{cash\_bal\_112 (sổ chi tiết)}) - \text{Số dư ngân hàng loại trừ}$$
  *Trong đó:*
  * `cash_bal_111` và `cash_bal_112`: Dư Nợ dòng cuối cùng của tài khoản `111` và `112` tương ứng trong bảng `AccountDetail` của kỳ báo cáo.
  * `Số dư ngân hàng loại trừ`: Tổng số dư (`balance`) của các tài khoản ngân hàng nằm trong danh sách cấu hình loại trừ (ví dụ tài khoản `"113611393939"` cấu hình trong `settings.MISA_EXCLUDED_BANK_ACCOUNTS`), được trích xuất từ bảng `BankBalance` thuộc tháng báo cáo đó (`reporting_month`).
* **Cấu hình đồng bộ từ MISA:** Khi tải báo cáo Bảng kê số dư ngân hàng (`BAListOfBalance`), hệ thống Playwright tự động loại bỏ các chi nhánh có chứa `_Nhật`, chọn kỳ báo cáo là "Tháng này", bấm xem báo cáo và xuất Excel tải về thư mục `media/auto_imports` dưới tiền tố `SO_DU_NH`.
* **Cơ chế Import & Xóa:** Dữ liệu từ tệp `SO_DU_NH*.xlsx` được import thông qua `BankBalanceResource`. Trước khi import, hệ thống tự động xóa toàn bộ các bản ghi `BankBalance` có `reporting_month` trùng với tháng báo cáo hiện tại (`reporting_period`) để tránh trùng lặp dữ liệu.

---

## 9. Endpoint gửi email backend (POST /api/reports/send-email/)
Hệ thống bổ sung thêm tính năng gửi báo cáo qua email từ Frontend:
* **Các tham số đầu vào (Multipart form-data):**
  * `to_emails` (Bắt buộc): Chuỗi danh sách email nhận phân tách bằng dấu phẩy.
  * `subject` (Bắt buộc): Tiêu đề email.
  * `message` (Bắt buộc): Nội dung email.
  * `file` (Tùy chọn): Tệp tin báo cáo đính kèm.
  * `file_name` (Tùy chọn): Tên tệp đính kèm khi gửi đi.
  * `from_name` (Tùy chọn): Tên hiển thị người gửi (Alias/Display Name, ví dụ: `"Hao Phuong Reporting System"`). Nếu không truyền sẽ lấy `EMAIL_DISPLAY_NAME` từ cấu hình hệ thống.
  * `from_email` (Tùy chọn): Địa chỉ email phản hồi (Reply-To).
* **Cấu hình SMTP & Alias:** Các tham số SMTP được đọc động từ `.env` (EMAIL_HOST, EMAIL_PORT, EMAIL_HOST_USER, EMAIL_HOST_PASSWORD, EMAIL_USE_TLS, EMAIL_USE_SSL, EMAIL_DISPLAY_NAME). Tiêu đề người gửi được chuẩn hóa theo chuẩn RFC 5322 `"Display Name" <email@gmail.com>` giúp hiển thị Tên Alias đẹp mắt trên hòm thư nhận. Hệ thống hỗ trợ chế độ kiểm thử bằng cách đổi `EMAIL_BACKEND` thành `django.core.mail.backends.console.EmailBackend`.

---

## 10. Phân tích chênh lệch Thu tiền Mảng Thang máy (BU_ELEVATOR) & Hướng khắc phục nhanh
* **Bối cảnh phát hiện (Tháng 7/2026):**
  * Báo cáo Kế toán (Excel chốt 20/07/2026): Thực thu mảng Elevator là **26,976,316,588 VNĐ** (gồm 3 mục con: *Elevator các KH khác* = 18.85B, *Hisa* = 7.26B, *5EX* = 0.87B).
  * Hệ thống Database (`BUPerformance` cho `BU_ELEVATOR`): Ghi nhận **18,649,562,243 VNĐ** (Chênh lệch ~8.33 tỷ VNĐ so với Kế toán).
* **Nguyên nhân cốt lõi:**
  1. **Bản chất con số 18.65 tỷ trên DB:** Dữ liệu thực thu của khách hàng **HISA (`PAR2019/000883`)** trị giá **7,255,800,099 VNĐ** ĐÃ NẰM TRONG con số 18.65 tỷ này (18.65B = 7.26B HISA + 11.39B của 111 KH Thang máy khác). Con số 18.65B **không bị thiếu HISA**.
  2. **Vấn đề lệch 7.46 tỷ VNĐ từ các KH Thang máy khác:** Trực thuộc nhóm *"Elevator các KH khác"* (18.85 tỷ Kế toán). Trên phần mềm MISA, các chứng từ thu tiền của nhóm KH này bị nhập nhầm mã chi nhánh hạch toán thành **`HPC` (ID 70)** thay vì **`BU_ELEVATOR` (ID 44)**.
  3. **Vấn đề 5EX (0.87 tỷ VNĐ):** Khách hàng `5EX` (`PAR2025/000694`) hiện đang gán thuộc BU `VHC_BOD` trên DB.
  4. **Cơ chế lọc của hệ thống (`accounting/tasks.py`):** Hàm `update_single_bu_performance` lọc chứng từ `AccountDetail` bằng `base_filter &= Q(business_unit_id__in=bu_ids)` (lọc theo chi nhánh chứng từ MISA). Do đó, chứng từ nào của KH Thang máy bị nhập nhầm chi nhánh `HPC` sẽ bị đẩy về Total Corp (`HPC`) chứ không về `BU_ELEVATOR`.
* **Hướng khắc phục nhanh cho Agent (Refactoring Guide):**
  * **File cần sửa:** [accounting/tasks.py](file:///d:/Sources/dashboard-report/accounting/tasks.py#L523-L525)
  * **Vị trí code cũ (Line 523-525):**
    ```python
    if not is_global and not is_under_oversea_branch:
        base_filter &= Q(business_unit_id__in=bu_ids)
    ```
  * **Giải pháp sửa code (Chuyển sang lọc kép theo BU Chi Nhánh HOẶC BU Khách Hàng):**
    ```python
    if not is_global and not is_under_oversea_branch:
        base_filter &= (Q(business_unit_id__in=bu_ids) | Q(customer__business_unit_id__in=bu_ids))
    ```
  * **Tác động sau khi sửa:** Toàn bộ giao dịch thu tiền của các Khách hàng được gán mã BU `BU_ELEVATOR` (bao gồm cả các chứng từ bị kế toán nhập nhầm chi nhánh `HPC` trên MISA) sẽ tự động quy gom chính xác 100% về `BU_ELEVATOR` trên Dashboard.

---

## 11. Endpoint Đăng nhập bằng tài khoản Google (POST /api/google-login/)
* **Tính năng:** Đăng nhập Single Sign-On (SSO) sử dụng tài khoản Google dành cho Frontend (React/Vite/Next.js).
* **Luồng xử lý Backend:**
  1. Nhận `id_token` (JWT) truyền lên từ Google Sign-In SDK phía Frontend.
  2. Xác thực tính hợp lệ của Token trực tiếp với máy chủ xác thực Google (`google-auth` Python SDK) và đối chiếu `GOOGLE_CLIENT_ID`.
  3. Lấy `email`, `first_name`, `last_name` từ payload Google.
  4. Thực hiện `User.objects.get_or_create(username=email)` để tự động liên kết hoặc khởi tạo tài khoản User mới trong Django.
---

## 12. Ghi nhớ nghiệp vụ Bóc tách Doanh thu (July 2026 Reconciliation)
* **Chi tiết mảng SAB (343.2 triệu VNĐ)**: Trong CSDL và MISA **không có mã BU độc lập tên SAB**. Giao dịch SAB được ghi nhận dưới chứng từ `NKBH26070847` ngày 20/07/2026 (Nhân viên: `TRẦN HỒNG QUÂN` - Mr. Hồng Quân) với giá trị **`343,200,000` VNĐ**. Tên dự án trong file Excel MISA ghi rõ: **`"Dự án sản xuất – kinh doanh thuộc BU Agritech – SAB Tôm 1 gram"`** (Cột Dự án), và mã BU Chi nhánh hạch toán MISA là **`BU_AGRITECH`**. Do đó trên DB toàn bộ 343.2M này được cộng tự động vào `BU_AGRITECH` (tổng `832.62M`), khớp 100.0% với `489.42M (AgriTech)` + `343.20M (SAB)` của Kế toán.
---

## 13. Rà soát Toàn bộ Hệ thống & Đề xuất Nâng cấp (July 23, 2026 Audit)
* **Kết quả Rà soát 8/8 Mục Tài chính**:
  1. `IV. HÀNG TỒN KHO`: **Khớp 100.0% tuyệt đối** (`219,575,366,379` VNĐ).
  2. `V. TIỀN CUỐI KỲ`: **Khớp 100.0% tuyệt đối** (`33,536,701,186` VNĐ).
  3. `VI. NỢ NGÂN HÀNG`: **Khớp 100.0% tuyệt đối** (`167,440,721,479` VNĐ).
  4. `VIII. CHI PHÍ VẬN HÀNH`: **Khớp 98.7%** (Lệch nhẹ 61.8 triệu trên 4.72 tỷ).
  5. `III. PHẢI THU KH`: DB = `66.83B` vs Kế toán = `62.02B`.
  6. `VII. PHẢI TRẢ NCC`: DB = `99.25B` vs Kế toán = `103.35B`.
  7. `I. DOANH THU`: DB = `34.44B` vs Kế toán = `43.75B` (Lệch `+10.64B` ở Elevator do FJT/5EX ngoài MISA).
  8. `II. THU TIỀN`: DB = `37.86B` vs Kế toán = `35.15B`.

* **Đề xuất Nâng cấp Hệ thống**:
  1. **[TÙY CHỌN DỰ PHÒNG TƯƠNG LAI] Bổ sung cột Phải trả NCC (`supplier_debt_actual`)**: Thêm cột `supplier_debt_actual` vào `BUPerformance` nhóm theo dư Có của `SupplierDebt` để hiển thị đủ 8/8 chỉ tiêu tài chính như Excel Kế toán. *(Ghi nhớ: Xem xét áp dụng khi cần hiển thị thêm chỉ tiêu NCC trên Dashboard)*.
---

## 14. Hoàn tất Triển khai Đề xuất 2 & 4 (July 23, 2026 Implementation)
* **Model `BUTargetPlan` (Chỉ tiêu Kế hoạch)**: Đã tạo bảng CSDL quản lý đầy đủ 6 nhóm chỉ tiêu Năm & Tháng + Người phụ trách + Ghi chú. Cho phép Kế toán tự nhập hoặc nạp file Excel. Khi lưu, hệ thống tự động cập nhật số Kế hoạch vào `BUPerformance`.
* **Model `ManualAdjustment` (Điều chỉnh Ngoại bảng)**: Đã tạo bảng CSDL quản lý điều chỉnh Cộng (+), Trừ (-), Ghi đè (=) cho 9 chỉ tiêu tài chính. Đã thử nghiệm thành công khoản điều chỉnh Doanh thu `BU_ELEVATOR` (`+9.63B` Hisa-FJT & `+1.02B` 5EX), kết quả tính Doanh thu `BU_ELEVATOR` đạt **`29,439,197,570` VNĐ (63.7%)**, **KHỚP 100.0% VỚI BÁO CÁO KẾ TOÁN**.
* **REST API & Django Admin**: Khởi tạo 2 ViewSet `/api/target-plans/` và `/api/adjustments/` kèm Giao diện Django Admin hỗ trợ recalculate tự động.
---

## 15. Chức năng Cập nhật Số liệu Tổng Toàn Công Ty (TOTAL_CORP Recalculation)
* **Tự động Lan truyền (Automatic Cascade Update)**: Khi bất kỳ BU con nào có thay đổi số liệu trong `update_single_bu_performance(bu_id, month, year)`, hệ thống tự động kích hoạt tính lại số liệu Tổng Toàn Công Ty (`bu_id=None`) cho cùng kỳ month/year.
* **Celery Task & Helper Function**: `recalculate_company_total_task(month, year)` cho phép gọi cập nhật lại số Tổng bất cứ lúc nào qua Celery hoặc code Python.
---

---

---

## 18. Sửa Lỗi Loại Trừ BU Bị Ẩn (`EXCLUDED_BU_CODES`) Cấp Tổng Công Ty
* **Nguyên nhân bug cũ**: Trong `tasks.py`, khi tính toán `is_global=True` (`TOTAL_CORP`), bộ lọc `base_filter` từng bị thiếu `~Q(business_unit_id__in=excluded_bu_ids)`. Do `settings.py` cấu hình `EXCLUDED_BU_CODES = ['ĐTCT']` (Đầu tư cho thuê = `1,230,155,034` VNĐ), số liệu `TOTAL_CORP` cũ bị cộng thừa 1.23 tỷ của ĐTCT, dẫn đến `mtd_revenue_actual` = `34,439,480,233` và `mtd_revenue_exclude_oversea_actual` = `32,312,499,887`.
* **Đã xử lý**: Đã thêm `base_filter &= ~Q(business_unit_id__in=excluded_bu_ids)` khi `is_global=True` trong [accounting/tasks.py](file:///d:/Sources/dashboard-report/accounting/tasks.py#L520).
* **Kết quả đối soát chính xác tuyệt đối**:
  1. `mtd_revenue_actual` MISA gốc TOTAL_CORP = **`33,209,325,199` VNĐ** (**Chính xác 33.21 tỷ VNĐ**, **khớp 100.0% lời Kế toán 'hơn 33 tỷ thôi'**).
  2. `mtd_revenue_exclude_oversea_actual` TOTAL_CORP = **`31,082,344,853` VNĐ** (**Chính xác 31.08 tỷ VNĐ**, **khớp 100.0% lời Kế toán 'không gồm oversea 30.9 tỷ'**).
  3. `mtd_revenue_oversea_actual` TOTAL_CORP = **`2,126,980,346` VNĐ** (**Chính xác 2.13 tỷ VNĐ**, **khớp 100.0% lời Kế toán 'oversea 2.13 tỷ'**).

---

---

## 20. Nạp Dữ Liệu Mục Tiêu Kế Hoạch Năm & Tháng vào `BUTargetPlan` (July 23, 2026 Seeding)
* **Nguồn dữ liệu**: Bóc tách từ Báo cáo Kế toán *"SỐ LIỆU MỤC TIÊU ĐƯỢC GIAO VÀ CAM KẾT TỪ BỘ PHẬN"* (Hình ảnh ngày 22/07/2026).
* **Script Tái sử dụng**: [scripts/seed_target_plans.py](file:///d:/Sources/dashboard-report/scripts/seed_target_plans.py) — `python scripts/seed_target_plans.py`.
* **Bảng Chỉ tiêu Kế hoạch đã nạp thành công**:
  1. **TỔNG TOÀN CÔNG TY (`TOTAL_CORP`)**: Quản lý `BOD & Kế toán` | DT Năm `724.025` tỷ, DT Tháng `65.605` tỷ | Thu tiền Năm `594.875` tỷ, Thu tiền Tháng `64.528` tỷ | Tồn kho `200` tỷ | Tiền cuối kỳ `30` tỷ | Nợ ngân hàng `175` tỷ | OPEX Tháng `4.851` tỷ.
  2. **`BU_ELEVATOR` (Thang máy)**: Quản lý `Mr Tiến Dũng` | DT Năm `499` tỷ, DT Tháng `46.205` tỷ | Thu tiền Năm `382.175` tỷ, Thu tiền Tháng `37.769` tỷ.
  3. **`BU_IBIZ PREMIUM` (iBiz Premium)**: Quản lý `Mr Nhật Minh` | DT Năm `174.6` tỷ, DT Tháng `15.5` tỷ | Thu tiền Năm `162.274` tỷ, Thu tiền Tháng `21.440` tỷ.
  4. **`BU_IBIZ VALUE` (iBiz Value)**: Quản lý `Mr Huy Phong` | DT Năm `15` tỷ, DT Tháng `1.3` tỷ | Thu tiền Năm `15` tỷ, Thu tiền Tháng `1.3` tỷ.
  5. **`BU_ECO` (ECO Solar)**: Quản lý `Mr Duy Hiếu` | DT Năm `16.4` tỷ, DT Tháng `1.6` tỷ | Thu tiền Năm `16.4` tỷ, Thu tiền Tháng `2.443` tỷ.
  6. **`BU_AGRITECH` (AgriTech & SAB Tôm)**: Quản lý `Mr Duy Hiếu & Mr Hồng Quân` | DT Năm `13.620` tỷ, DT Tháng `1.0` tỷ | Thu tiền Năm `13.620` tỷ, Thu tiền Tháng `1.576` tỷ.
---

---

---

---

---

---

---

---

## 31. Điều Tra Chứng Từ Bị Đổi Mã Bộ Phận (BU Transfer) & Xuất File `bu_changed_investigation.csv`
* **Script Tái sử dụng**: Created [scripts/investigate_bu_changes.py](file:///d:/Sources/dashboard-report/scripts/investigate_bu_changes.py).
* **Quy trình Thực thi**:
  1. Đọc toàn bộ 9,505 chứng từ thô năm 2026 từ file `LIVE_MISA_BAN_HANG_2026_ALL.xlsx` không qua bộ lọc BU.
  2. INNER JOIN với dữ liệu DB (`BU_MANUFACTURING` & `BU_ELEVATOR`).
  3. Lọc danh sách chứng từ có `business_unit_db != business_unit_misa`.
---

---

---

---

---

---

---

---

---

## 42. Cập Nhật Bắt Bộc Về Kiến Trúc Cơ Sở Dữ Liệu Target Plan (`BUTargetPlan` vs `BUPerformance`)
* **Tệp tài liệu gốc**: [DocumentAPI_Report2026.md](file:///d:/Sources/dashboard-report/DocumentAPI_Report2026.md#L158-L177) & [target.md](file:///d:/Sources/dashboard-report/target.md).
* **Phân biệt kiến trúc CSDL**:
  1. **Bảng `BUTargetPlan` (Ngân sách Kế hoạch Cố định)**: Chứa ngân sách chuẩn do Kế toán phân bổ, phân tách rõ `month_*_target` (Target Tháng) và `year_*_target` (Target Cả Năm Cố Định, ví dụ Thu tiền Cả Năm: **594.87 tỷ VNĐ**).
  2. **Bảng `BUPerformance` (Bảng Tính Toán Hiệu Suất Tự Động Hàng Tháng)**: Trường `ytd_*_plan` trong bảng này được tính tự động bằng cách **cộng dồn `mtd_*_plan` của các tháng đã đi qua**.
* **Quy tắc mapping bắt buộc dành cho lập trình viên & AI Agents**:
  - Khi cần lấy **Target Tháng (MTD Target)**: Bắt buộc ưu tiên đọc `month_*_target` từ `BUTargetPlan`.
  - Khi cần lấy **Target Cả Năm (YTD Target)**: **BẮT BUỘC ƯU TIÊN đọc trực tiếp từ `year_*_target` của `BUTargetPlan`**. Tuyệt đối không dùng số kế hoạch lũy kế tháng của `BUPerformance` để đại diện cho Target Cả Năm.
## 44. Danh Sách Các Tác Vụ Chờ Tự Động Hóa MISA (≥ 30 Giây)
* **Tệp tài liệu gốc**: [accounting/misa_tasks.py](file:///d:/Sources/dashboard-report/accounting/misa_tasks.py) & [target.md](file:///d:/Sources/dashboard-report/target.md).
* **Danh sách các tác vụ chờ cố định và timeout**:
  1. `await asyncio.sleep(50)` ([L1157](file:///d:/Sources/dashboard-report/accounting/misa_tasks.py#L1157)): **50 giây cố định** — Chờ MISA tạo file báo cáo ngầm dưới background sau khi bấm "Xuất Excel".
  2. `page.expect_download(timeout=45000)` ([L1261](file:///d:/Sources/dashboard-report/accounting/misa_tasks.py#L1261)): **45 giây timeout** — Chờ sự kiện trình duyệt tải file về đĩa sau khi bấm "Tải tệp".
  3. Loop chờ nút "Tải tệp" 20 lần x 2s ([L1223-L1239](file:///d:/Sources/dashboard-report/accounting/misa_tasks.py#L1223-L1239)): **40 giây timeout** — Chờ file mới xuất hiện trong panel Download Manager.
  4. `await asyncio.sleep(40)` ([L686](file:///d:/Sources/dashboard-report/accounting/misa_tasks.py#L686)): **40 giây cố định** — Chờ báo cáo lưu sẵn tải hoàn tất (Saved Reports flow).
  5. `page.goto(report_url, timeout=30000)` ([L602](file:///d:/Sources/dashboard-report/accounting/misa_tasks.py#L602)): **30 giây timeout** — Timeout điều hướng mở URL MISA.
## 48. Kiến Trúc Tái Cấu Trúc Module Nhỏ Gọn & Quản Lý Lệnh Đồng Bộ (`sync_misa`)
* **Tệp tài liệu gốc**: [accounting/services/](file:///d:/Sources/dashboard-report/accounting/services/), [accounting/misa/](file:///d:/Sources/dashboard-report/accounting/misa/), [accounting/views/](file:///d:/Sources/dashboard-report/accounting/views/), [accounting/models/](file:///d:/Sources/dashboard-report/accounting/models/), [accounting/management/commands/sync_misa.py](file:///d:/Sources/dashboard-report/accounting/management/commands/sync_misa.py).
* **Đặc điểm & Thiết kế**:
  1. **Modular Services Package (`accounting/services/`)**: Tách logic tính toán KPI (`kpi_calculator.py`), đọc định dạng tệp (`period_parser.py`) và đồng bộ tồn kho (`inventory_sync.py`). `accounting/tasks.py` giữ Celery tasks và re-export 100% functions.
  2. **Modular MISA Automation (`accounting/misa/`)**: Tách Playwright UI automation (`browser.py`, `locators.py`, `report_exporter.py`, `automation.py`). `accounting/misa_tasks.py` re-export 100% Celery tasks.
  3. **Modular Views & Models Packages (`accounting/views/`, `accounting/models/`)**: Tách monolith `views.py` và `models.py` thành các submodule chuyên biệt (`dashboard_api.py`, `collection_api.py`, `organization.py`, `performance.py`...), giữ wrapper re-export 100% tương thích ngược.
  4. **Django Custom Management Command (`sync_misa.py`)**: Gom toàn bộ các script bảo trì rải rác ngoài thư mục root thành câu lệnh Django chuẩn hóa: `python manage.py sync_misa --action=all|download|import --prefix=... --period=...`.

---

## 11. Hệ thống Quản lý Nhân sự (Employee Management)

### 11.1. Thiết kế Database
Hệ thống gồm 4 bảng mới trong DB PostgreSQL, được định nghĩa tại [`accounting/models/employee.py`](file:///d:/Sources/dashboard-report/accounting/models/employee.py):

| Bảng | Model Django | Mô tả |
|------|-------------|--------|
| `departments` | `Department` | Danh mục đơn vị / Phòng ban (tự tham chiếu parent) |
| `job_titles` | `JobTitle` | Danh mục chức danh |
| `employees` | `Employee` | Danh sách nhân viên (unique: `employee_code`) |
| `employee_assignments` | `EmployeeAssignment` | Lịch sử quá trình công tác |

### 11.2. Schema Chi Tiết
```
Department:
  - department_code    VARCHAR(50) PRIMARY KEY
  - parent_department  FK → departments.department_code (nullable)
  - department_name    VARCHAR(255)

JobTitle:
  - title_id           SERIAL PRIMARY KEY
  - title_name         VARCHAR(255)

Employee (bảng: employees):
  - id                 SERIAL PRIMARY KEY (nội bộ Django)
  - employee_code      VARCHAR(20) UNIQUE NOT NULL  (VD: '0512')
  - full_name          VARCHAR(100) DEFAULT ''
  - gender             VARCHAR(10) CHOICES('MALE','FEMALE') nullable
  - date_of_birth      DATE nullable
  - identity_number    VARCHAR(20) nullable
  - phone_number       VARCHAR(20) nullable
  - email              VARCHAR(100) nullable
  - is_active          BOOLEAN DEFAULT TRUE

EmployeeAssignment:
  - assignment_id      SERIAL PRIMARY KEY
  - employee           FK → employees.id
  - department         FK → departments.department_code
  - title              FK → job_titles.title_id
  - start_date         DATE
  - end_date           DATE nullable (NULL = đang giữ vị trí)
```

### 11.3. Import Excel (`Danh_sach_nhan_vien.xlsx`)
- **File**: `media/auto_imports/Danh_sach_nhan_vien.xlsx`
- **Sheet**: `DANH SÁCH NHÂN VIÊN` — header tại row index 2 (Excel row 3)
- **Columns mapping**:

| Column Excel | Field Model |
|-------------|------------|
| Mã nhân viên | `employee_code` |
| Tên nhân viên | `full_name` |
| Giới tính (`Nam`/`Nữ`) | `gender` (`MALE`/`FEMALE`) |
| Ngày sinh | `date_of_birth` |
| Số CMND | `identity_number` |
| Chức danh | `JobTitle.title_name` (auto get_or_create) |
| Trạng thái người dùng | `is_active` |
| Mã đơn vị | `Department.department_code` (auto get_or_create) |
| Tên đơn vị | `Department.department_name` |

- **Resource**: [`accounting/resources/employee.py`](file:///d:/Sources/dashboard-report/accounting/resources/employee.py) — `EmployeeResource`
- **Logic**: `before_import_row` tự động `get_or_create` `Department`, `JobTitle`, `EmployeeAssignment` cho mỗi dòng.
- **Import via CLI**:
  ```bash
  py manage.py sync_misa --action=import --file="media/auto_imports/Danh_sach_nhan_vien.xlsx"
  ```
- **Import via folder scan**: Đặt file vào `media/auto_imports/DANH_SACH_NHAN_VIEN_*.xlsx` → Celery task tự động nhận diện prefix `DANH_SACH_NHAN_VIEN`.
- **Lưu ý**: `skip_delete=True` — import nhân viên **KHÔNG** xóa dữ liệu cũ (upsert mode).

---

## 12. Hệ thống Chống Popup Tự động Toàn cục (Global Smart Anti-Popup Engine)

### 12.1. Mục tiêu & Nguyên lý
Giải quyết triệt để 100% lỗi nghẽn giao diện khi MISA xuất hiện các thông báo, banner quảng cáo, cảnh báo nâng cấp, hoặc pop-up hệ thống ngẫu nhiên làm cản trở tiến trình tự động tải báo cáo Playwright.

### 12.2. Cơ chế Hoạt động (Phân loại Thông minh - Smart Detection)
1. **Phân biệt Modal Tham số vs Pop-up Rác**:
   - **Giữ lại**: Modal chứa tiêu đề/nút *"Chọn tham số"*, *"Đồng ý"*, *"Xem báo cáo"*, *"Kỳ báo cáo"*.
   - **Tiêu diệt**: Mọi dialog/popup khác (`.ms-popup`, `.dx-dialog-wrapper`, `.con-ms-popup`).
2. **Auto-Clean JS Injection**:
   - Tự động inject qua `context.add_init_script()` chạy liên tục bằng `MutationObserver` trên mọi frame/sub-frame.
   - Thử bấm nút đóng thông minh (`Đóng`, `Hủy`, `Đã hiểu`, `Nhắc lại sau`, `Bỏ qua`...) trước; nếu không biến mất sẽ xóa trực tiếp phần tử khỏi DOM (`element.remove()`).
   - Tự động xóa các lớp phủ mờ (`.ms-overlay`, `.dx-overlay-shader`) và khôi phục `pointer-events: auto` cho giao diện chính.

---

## 13. Kiến Trúc Tính Toán Công Nợ Theo Nhân Viên & Người Quản Lý Nhóm (Employee & Manager Debt Architecture Spec)

### 13.1. Mục Tiêu Nghiệp Vụ
Tính toán và phân bổ chỉ số Công nợ (Nợ trong hạn, Nợ quá hạn, Nợ xấu) theo phân cấp Nhân viên Sales phụ trách trực tiếp và Người quản lý nhóm (Trưởng nhóm / Trưởng phòng / Giám đốc), giúp đôn đốc thu nợ hiệu quả theo mô hình phân cấp quản trị.

### 13.2. Giải Pháp Kiến Trúc 4 Trụ Cột

#### Trụ Cột 1: Thiết Kế Mối Liên Kết Dữ Liệu (Data Relationships)
1. **Khách hàng $\rightarrow$ Sales phụ trách (`Customer.assigned_employee`)**:
   - Thêm trường `assigned_employee = models.ForeignKey(Employee, null=True, blank=True, verbose_name="Nhân viên phụ trách")` vào model `Customer`.
   - Mỗi Khách hàng sẽ do 1 Sales trực tiếp phụ trách. Toàn bộ dư nợ từ `ReceivablesAgeing` của khách hàng sẽ quy về cho Sales đó.
2. **Bảo tồn Lịch sử Quản lý theo Thời gian (`EmployeeAssignment.manager` - SCD Type 2)**:
   - ⭐ **Quy tắc thiết kế quan trọng**: Trường `manager` (`ForeignKey(Employee, null=True, blank=True, related_name='managed_assignments')`) **BẮT BUỘC lưu ở bảng `EmployeeAssignment`**, KHÔNG lưu ở bảng `Employee`.
   - **Lý do nghiệp vụ**: Sếp của một nhân viên có thể thay đổi theo thời gian (chuyển nhóm/chuyển phòng ban). Việc lưu ở `EmployeeAssignment` kết hợp `start_date` và `end_date` giúp bảo toàn 100% tính chính xác của số liệu công nợ trong quá khứ khi đối soát theo kỳ báo cáo (`start_date <= query_date <= end_date`).

#### Trụ Cột 2: Model Lưu Trữ Báo Cáo Công Nợ (`EmployeeReceivableSummary`)
Tạo model mới lưu chốt số liệu công nợ nhân viên và nhóm theo kỳ báo cáo:
```python
class EmployeeReceivableSummary(models.Model):
    employee = models.ForeignKey(Employee, on_delete=models.CASCADE, verbose_name="Nhân viên")
    department = models.ForeignKey(Department, on_delete=models.CASCADE, verbose_name="Phòng ban")
    reporting_period = models.CharField(max_length=7, db_index=True, verbose_name="Kỳ báo cáo") # YYYY-MM
    is_manager = models.BooleanField(default=False, verbose_name="Là Trưởng nhóm/Quản lý")

    # Chỉ số công nợ cá nhân (Own Debt)
    own_total_debt = models.DecimalField(max_digits=18, decimal_places=2, default=0, verbose_name="Tổng nợ cá nhân")
    own_due_total = models.DecimalField(max_digits=18, decimal_places=2, default=0, verbose_name="Nợ trong hạn cá nhân")
    own_overdue_total = models.DecimalField(max_digits=18, decimal_places=2, default=0, verbose_name="Nợ quá hạn cá nhân")
    own_overdue_above_60 = models.DecimalField(max_digits=18, decimal_places=2, default=0, verbose_name="Nợ quá hạn >60 ngày")
    own_overdue_above_120 = models.DecimalField(max_digits=18, decimal_places=2, default=0, verbose_name="Nợ xấu >120 ngày")

    # Chỉ số công nợ nhóm / quản lý (Team / Managed Debt - Cộng dồn đệ quy)
    team_total_debt = models.DecimalField(max_digits=18, decimal_places=2, default=0, verbose_name="Tổng nợ cả nhóm")
    team_due_total = models.DecimalField(max_digits=18, decimal_places=2, default=0, verbose_name="Nợ trong hạn cả nhóm")
    team_overdue_total = models.DecimalField(max_digits=18, decimal_places=2, default=0, verbose_name="Nợ quá hạn cả nhóm")
    team_overdue_above_120 = models.DecimalField(max_digits=18, decimal_places=2, default=0, verbose_name="Nợ xấu cả nhóm")
    subordinate_count = models.IntegerField(default=0, verbose_name="Số nhân viên cấp dưới")
```

#### Trụ Cột 3: Động Cơ Tính Toán & Thuật Toán Cộng Dồn Đệ Quy (Calculation Engine)
- **Bước 1 (Nợ cá nhân)**: Quét `ReceivablesAgeing` trong kỳ, group by `customer__assigned_employee`, tính tổng `own_total_debt`, `own_overdue_total`...
- **Bước 2 (Nợ quản lý nhóm)**: Với mỗi Trưởng nhóm / Trưởng phòng, truy vấn danh sách nhân viên cấp dưới trực thuộc tại mốc thời gian `reporting_period` từ `EmployeeAssignment`, thực hiện cộng dồn đệ quy:
  $$\text{team\_total\_debt} = \text{own\_total\_debt} + \sum_{i \in \text{cấp dưới}} \text{own\_total\_debt}(i)$$

#### Trụ Cột 4: REST API & Drill-Down Dashboard Views
- `GET /api/v1/receivables/employees/`: Trả về danh sách nợ Sales (lọc theo Phòng ban, Mức nợ quá hạn).
- `GET /api/v1/receivables/managers/`: Trả về danh sách công nợ Quản lý (xem tổng hợp cả nhóm và drill-down chi tiết từng Sales trực thuộc).

### 13.3. Lộ Trình Triển Khai (Roadmap)
- **Phase 1**: Bổ sung `manager` trong `EmployeeAssignment` và `assigned_employee` trong `Customer`. Tạo migration & cập nhật `EmployeeResource` import Excel.
- **Phase 2**: Tạo model `EmployeeReceivableSummary` & viết service tính toán công nợ cá nhân + đệ quy quản lý.
- **Phase 3**: Tạo Django Command `python manage.py calculate_employee_debt` & REST API drill-down.


