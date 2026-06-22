# Báo cáo Phân tích Logic Hệ thống (Tồn kho, Nợ ngân hàng & Báo cáo thu nợ)

Tài liệu này tổng hợp toàn bộ kết quả rà soát chi tiết về logic tính toán tồn kho, nợ ngân hàng và các sai lệch nghiệp vụ trong báo cáo thu nợ trên Dashboard và các Celery Task của hệ thống Report2026.

---

## 1. Logic Tính Tồn Kho (Inventory)

Dữ liệu tồn kho được xử lý và lưu trữ qua hai cấp độ chính trong hệ thống:

### A. Cấp độ Báo cáo Hiệu suất BU (`BUPerformance`)
* **Nguồn dữ liệu:** Nạp từ các file Excel có tiền tố `TON_KHO` (ví dụ: `TON_KHO*.xlsx`) vào bảng [InventorySummary](file:///d:/Sources/dashboard-report/accounting/models.py#L255-L284).
* **Mối liên kết đơn vị (BU):** Bảng `InventorySummary` không lưu trực tiếp thông tin `business_unit_id` mà liên kết gián tiếp qua trường kho hàng `warehouse` (`warehouse__business_unit_id`).
* **Logic tính toán tích lũy tháng:** Được thực hiện tự động trong Celery task [update_single_bu_performance](file:///d:/Sources/dashboard-report/accounting/tasks.py#L168):
  * **Bộ lọc thời gian:** Lọc theo tháng và năm chứng từ (`created_at__month=month`, `created_at__year=year`).
  * **Bộ lọc BU:**
    * Nếu tính cho *Tổng công ty* (`is_global = True`): Không lọc theo BU, cộng dồn toàn bộ dữ liệu từ tất cả các kho.
    * Nếu tính cho *BU cụ thể* (`is_global = False`): Lọc theo đơn vị sở hữu kho hàng (`warehouse__business_unit_id=bu_id`).
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
| **`receivable_total`** | Dư nợ cần thu (snapshot hiện tại của `ReceivablesAgeing`). | `Sum('total_debt')` từ bảng `ReceivablesAgeing` lọc theo BU. | **Khớp nghiệp vụ.** Đây là tổng số dư nợ chưa thu hiện tại của các khách hàng thuộc BU. |
| **`commitment_overdue`** | Cam kết (quá hạn) — dùng tạm `overdue_total`. | `Sum('overdue_total')` từ bảng `ReceivablesAgeing` lọc theo BU. | **Khớp nghiệp vụ.** (Tạm thời dùng số nợ quá hạn do chưa có bảng theo dõi cam kết trả nợ riêng). |
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
