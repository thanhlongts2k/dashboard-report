# Báo cáo Phân tích Logic Hệ thống (Tồn kho, Nợ ngân hàng & Báo cáo thu nợ)

Tài liệu này tổng hợp toàn bộ kết quả rà soát chi tiết về logic tính toán tồn kho, nợ ngân hàng và các sai lệch nghiệp vụ trong báo cáo thu nợ trên Dashboard và các Celery Task của hệ thống Report2026.

---

## 1. Logic Tính Tồn Kho (Inventory)

Dữ liệu tồn kho được xử lý và lưu trữ qua hai cấp độ chính trong hệ thống:

### A. Cấp độ Báo cáo Hiệu suất BU (`BUPerformance`)
* **Nguồn dữ liệu:** Nạp từ các file Excel có tiền tố `TON_KHO` (ví dụ: `TON_KHO*.xlsx`) vào bảng [InventorySummary](file:///d:/Sources/dashboard-report/accounting/models.py#L255-L284).
* **Mối liên kết đơn vị (BU):** Bảng `InventorySummary` không lưu trực tiếp thông tin `business_unit_id` mà liên kết gián tiếp qua trường kho hàng `warehouse` (`warehouse__business_unit_id`).
* **Logic tính toán tích lũy tháng:** Được thực hiện tự động trong Celery task [update_single_bu_performance](file:///d:/Sources/dashboard-report/accounting/tasks.py#L431):
  * **Bộ lọc thời gian:** Lấy theo Snapshot hiện hành của bảng `InventorySummary` (không lọc theo thời gian cụ thể của trường `created_at` do bảng được xóa và nạp mới hoàn toàn mỗi lần import).
  * **Bộ lọc BU & Loại trừ cấu hình ở settings:**
    * Lọc loại trừ BU: Hệ thống tự động bỏ các BU có mã nằm trong danh sách `EXCLUDED_BU_CODES` ở [settings.py](file:///d:/Sources/dashboard-report/report2026/settings.py) (hiện tại là `['ĐTCT']`) và các BU con trực thuộc nhánh này khỏi mọi phép tính hiệu suất.
    * Lọc loại trừ Khách hàng: Loại trừ các khách hàng thuộc nhóm có mã trong `EXCLUDED_CUSTOMER_GROUP_CODES` ở [settings.py](file:///d:/Sources/dashboard-report/report2026/settings.py) (hiện tại là `['Internal']`).
    * Lọc loại trừ Loại Chứng từ: Loại trừ các chứng từ có tiền tố thuộc `EXCLUDED_DOC_ID_PREFIXES` ở [settings.py](file:///d:/Sources/dashboard-report/report2026/settings.py) (hiện tại là `['THANHLY']`) khỏi doanh thu bán hàng thương mại.
    * Nếu tính cho *Tổng công ty* (`is_global = True`): Không lọc theo BU (chỉ áp dụng lọc loại trừ các BU/Khách hàng đặc thù nói trên).
    * Nếu tính cho *BU cụ thể* (`is_global = False`): Lọc theo đơn vị sở hữu kho hàng (`warehouse__business_unit_id=bu_id`) và loại trừ các BU/Khách hàng đặc thù.
  * **Công thức tổng hợp:**
    * `inventory_opening_value` (Giá trị đầu kỳ) = Tổng cột `opening_value`
    * `inventory_in_value` (Giá trị nhập kho trong kỳ) = Tổng cột `in_value`
    * `inventory_out_value` (Giá trị xuất kho trong kỳ) = Tổng cột `out_value`
    * `inventory_value_actual` (Giá trị tồn kho thực tế cuối kỳ) = Tổng cột `closing_value`

### B. Cấp độ Chi tiết Kho hàng (`Warehouse`)
* **Tác vụ đồng bộ:** Được thực hiện qua Celery task [sync_warehouse_inventory_data](file:///d:/Sources/dashboard-report/accounting/tasks.py#L303).
* **Mô tả xử lý:** Tác vụ quét qua tất cả các kho hàng ([Warehouse](file:///d:/Sources/dashboard-report/accounting/models.py#L9)), thực hiện tính tổng (`opening_value`, `in_value`, `out_value`, `closing_value`) từ bảng `InventorySummary` của kho đó rồi lưu ngược lại vào các trường:
  * `wh.inventory_opening_value`
  * `wh.inventory_in_value`
  * `wh.inventory_out_value`
  * `wh.inventory_value_actual`
* **Lưu ý vận hành:** Tiến trình này **không tự động kích hoạt** sau khi nạp file Excel tồn kho, mà bắt buộc phải chạy thủ công từ giao diện Admin (nút Action trong danh sách Kho hàng) hoặc qua lập lịch Celery Beat riêng.

---

## 2. Logic Tính Nợ Ngân Hàng (Bank Debt)

* **Thiết kế cơ sở dữ liệu:**
  * Bảng [BUPerformance](file:///d:/Sources/dashboard-report/accounting/models.py#L319) đã định nghĩa sẵn 2 trường để theo dõi:
    * `bank_debt_plan` (Nợ ngân hàng - Kế hoạch)
    * `bank_debt_actual` (Nợ ngân hàng - Thực tế)
  * Trong luồng nạp dữ liệu tự động từ Misa (sử dụng Playwright), hệ thống thiết lập tải về chi tiết tài khoản **`341`** (tiền vay và nợ thuê tài chính liên quan trực tiếp đến nợ ngân hàng) cùng tài khoản `111, 112` để nạp vào bảng [AccountDetail](file:///d:/Sources/dashboard-report/accounting/models.py#L185).
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
Hệ thống cung cấp 2 lệnh Django Management Command để kế toán hoặc kỹ thuật viên có thể trigger tính toán hiệu suất BU trực tiếp từ Terminal:

1. **Tính hiệu suất cho Tổng công ty (Global):**
   * **Cú pháp:**
     ```bash
     python manage.py calculate_global_performance --month 6 --year 2026
     ```
   * **Mô tả:** Chạy tính toán KPI cho toàn Tổng công ty trong kỳ tháng 6/2026 (đã loại bỏ các BU loại trừ và khách hàng nhóm 'Internal' cấu hình ở `settings.py`).
2. **Tính hiệu suất cho BU cụ thể:**
   * **Cú pháp:**
     ```bash
     python manage.py calculate_bu_performance --bu_id 70 --month 6 --year 2026
     ```
   * **Mô tả:** Chạy tính toán KPI cho đơn vị kinh doanh có ID = 70 (và các đơn vị con của nó) trong kỳ tháng 6/2026 (đã loại bỏ các BU/Khách hàng loại trừ).

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

## 6. Quy trình xuất Báo cáo bán hàng (BAN_HANG) từ MISA
Để đảm bảo số liệu xuất từ MISA là chính xác, hệ thống Playwright thực hiện các bước sau (áp dụng khi sử dụng xuất thủ công từng bước):
1. Truy cập trực tiếp vào URL báo cáo bán hàng.
2. Click nút **"Chọn tham số"**.
3. Tích chọn checkbox **"Bao gồm số liệu chi nhánh phụ thuộc"**.
4. Loại bỏ các chi nhánh phụ thuộc có chứa ký tự `_Nhật`.
5. Chọn kỳ báo cáo là **"Tháng này"**.
6. Tích chọn checkbox **"Chọn tất cả"**.
7. Click nút **"Xem báo cáo"** và chờ 10 giây để báo cáo hiển thị kết quả.
8. Click chọn biểu tượng **Bánh răng** (Cài đặt) ở góc trên bên phải grid hiển thị báo cáo $\rightarrow$ Chọn mẫu **"Mẫu chuẩn."** (có dấu chấm ở cuối).
9. Click vào biểu tượng **Excel** trên thanh công cụ và chọn **"Xuất Excel (dạng dữ liệu)"**.
10. Chờ 50 giây để hệ thống MISA kết xuất, mở khay download và click **"Tải tệp"** để lưu về máy.

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
  * `from_email` (Tùy chọn): Địa chỉ email gửi.
* **Cấu hình SMTP:** Các tham số SMTP được đọc động từ `.env` (EMAIL_HOST, EMAIL_PORT, EMAIL_HOST_USER, EMAIL_HOST_PASSWORD, EMAIL_USE_TLS, EMAIL_USE_SSL). Hệ thống hỗ trợ chế độ kiểm thử bằng cách đổi `EMAIL_BACKEND` thành `django.core.mail.backends.console.EmailBackend`.

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


