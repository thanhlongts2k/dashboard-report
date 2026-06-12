# Danh Sách Khuyến Nghị Nâng Cấp Hệ Thống (Report2026)
*Bảng tổng hợp các nhiệm vụ cần thực hiện để hoàn thiện hệ thống báo cáo hiệu suất, được phân chia theo mức độ ưu tiên.*

---

## 🚨 1. Ưu Tiên Cao (High Priority) - Cần xử lý sớm

### [ ] Đồng bộ hóa công thức tính Doanh thu
* **Vấn đề**: Hiện tại có sự bất nhất lớn trong logic tính toán:
  * Doanh thu tích lũy tháng (`mtd_revenue_actual`) tính bằng tổng cột **`actual_sales`** (Doanh số thực tế) của bảng `SalesTransaction`.
  * Doanh thu chi tiết từng ngày (`daily_revenue`) lại tính bằng tổng cột **`sales_amount`** (Doanh số bán).
* **Hệ quả**: Dẫn đến việc tổng doanh thu các ngày trong tháng khi vẽ biểu đồ không khớp với con số doanh thu tháng trên Dashboard chính.
* **Đề xuất**: Thống nhất dùng chung một cột dữ liệu (nên là `actual_sales` hoặc làm rõ nghiệp vụ sự khác nhau giữa Doanh số bán và Doanh số thực tế).
* **Nơi xử lý**: Hàm `update_single_bu_performance` trong file [tasks.py](file:///d:/Sources/dashboard-report/accounting/tasks.py#L192).

### [ ] Bổ sung logic tính toán các chỉ số thực tế bị thiếu
* **Vấn đề**: Các trường `bank_debt_actual` (Nợ ngân hàng thực tế), `opex_actual` (Chi phí vận hành thực tế), và `cash_balance_actual` (Tiền cuối kỳ thực tế) trong bảng `BUPerformance` hiện đang để mặc định bằng `0` và chưa có code tính toán.
* **Đề xuất**: 
  * Xác định các tài khoản kế toán tương ứng trong sổ chi tiết (ví dụ: Tài khoản đầu `341` cho nợ ngân hàng, đầu `641`, `642` cho chi phí vận hành opex, và số dư tài khoản `111`, `112` cho tiền cuối kỳ).
  * Viết logic truy vấn từ bảng `AccountDetail` để tự động tổng hợp các giá trị này vào bảng hiệu suất tháng.
* **Nơi xử lý**: Hàm `update_single_bu_performance` trong file [tasks.py](file:///d:/Sources/dashboard-report/accounting/tasks.py#L163).

---

## ⚖️ 2. Ưu Tiên Trung Bình (Medium Priority) - Cần thiết cho nghiệp vụ đầy đủ

### [ ] Tận dụng dữ liệu Mua hàng và Công nợ nhà cung cấp
* **Vấn đề**: File Excel mua hàng (`MUA_HANG`) và công nợ NCC (`CONG_NO_NCC`) đang được import tự động hàng ngày nhưng dữ liệu này hoàn toàn nằm ngoài luồng tính toán hiệu suất BU.
* **Đề xuất**: 
  * Tích hợp thêm các chỉ số về chi phí mua hàng, công nợ NCC phải trả vào báo cáo tháng để người quản trị có góc nhìn toàn diện hơn về dòng tiền ra (cash out).
* **Nơi xử lý**: Cấu trúc bảng `BUPerformance` trong [models.py](file:///d:/Sources/dashboard-report/accounting/models.py#L306) và logic tổng hợp trong [tasks.py](file:///d:/Sources/dashboard-report/accounting/tasks.py).

### [ ] Phân quyền truy cập API chi tiết (Authorization)
* **Vấn đề**: Các API danh mục (ViewSets) như `/api/transactions/`, `/api/account-details/`, `/api/business-units/` đang mở quyền truy cập đầy đủ cho mọi tài khoản đã đăng nhập. Trưởng BU này có thể xem hoặc thay đổi dữ liệu của BU khác.
* **Đề xuất**:
  * Áp dụng phân quyền theo cấp độ (ví dụ: Trưởng BU chỉ được xem dữ liệu thuộc BU mình quản lý và các BU con).
  * Chỉ Admin hệ thống mới được phép gọi các phương thức ghi (`POST`, `PUT`, `DELETE`) hoặc kích hoạt API tính toán lại số liệu `/api/update-performance/`.
* **Nơi xử lý**: Các ViewSet trong file [views.py](file:///d:/Sources/dashboard-report/accounting/views.py).

---

## 📈 3. Ưu Tiên Thấp (Low Priority) - Tối ưu hóa vận hành & Trải nghiệm

### [ ] Khắc phục N+1 Query và Tối ưu hiệu năng database
* **Vấn đề**: Khi lượng giao dịch bán hàng (`SalesTransaction`) và sổ chi tiết tài khoản (`AccountDetail`) tăng lên hàng triệu dòng, các API lấy danh sách sẽ chạy rất chậm do lỗi truy vấn N+1 (truy xuất quan hệ ForeignKey đơn lẻ).
* **Đề xuất**: Sử dụng `.select_related()` hoặc `.prefetch_related()` cho các trường khoá ngoại như `customer`, `product`, `business_unit` ở các ViewSet tương ứng.
* **Nơi xử lý**: [views.py](file:///d:/Sources/dashboard-report/accounting/views.py) (Tương tự cách đã tối ưu cho `PurchaseDetailViewSet`).

### [ ] Xây dựng bảng Log Import dữ liệu
* **Vấn đề**: Hiện tại khi import Excel lỗi hoặc thành công, hệ thống chỉ di chuyển file vào thư mục `success/` hoặc ghi log ở terminal. Lập trình viên khó theo dõi lịch sử import lỗi do dòng dữ liệu nào từ xa.
* **Đề xuất**: 
  * Tạo một model `ImportLog` lưu trữ thời gian import, tên file, trạng thái (Thành công/Lỗi) và mô tả lỗi cụ thể nếu có.
  * Hiển thị bảng này lên Django Admin để người vận hành hệ thống dễ dàng kiểm soát.
* **Nơi xử lý**: Hàm `auto_import_excel_from_folder` trong [tasks.py](file:///d:/Sources/dashboard-report/accounting/tasks.py#L17).
