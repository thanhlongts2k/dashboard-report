# Quy Trình Thực Thi Chuẩn (SOP) & Checklist Cho Lập Trình Viên / Agent

Tài liệu này định nghĩa quy trình 5 bước bắt buộc đối với bất kỳ Lập trình viên hoặc AI Coding Agent nào khi thực hiện các nhiệm vụ (tasks) phát triển hoặc sửa lỗi trong dự án **Report2026**.

---

## 📋 QUY TRÌNH 5 BƯỚC THỰC THI (SOP)

### 🔍 BƯỚC 1: PHÂN TÍCH & ĐỀ XUẤT GIẢI PHÁP TỐI ƯU
- **Tìm hiểu & Rà soát**: Đọc và rà soát kỹ các file source code liên quan trực tiếp đến yêu cầu (`models.py`, `views.py`, `tasks.py`, `serializers.py`...).
- **Đề xuất giải pháp tối ưu**:
  - Ưu tiên các thiết kế có hiệu năng cao, tránh lỗi N+1 query và lock bảng dữ liệu.
  - Đảm bảo an toàn bảo mật và phân quyền truy cập (tham chiếu cảnh báo phân quyền tại mục 7.6 của `DocumentAPI_Report2026.md`).
  - Thiết kế dễ mở rộng và TÁI SỬ DỤNG LẠI các hàm/logic đã có trong hệ thống (Tuân thủ nguyên tắc DRY - Don't Repeat Yourself).
- **Phê duyệt**: Trình bày giải pháp dưới dạng sơ lược/bullet points trong chat để Người dùng (hoặc Admin) phê duyệt trước khi viết code chi tiết.

### 💻 BƯỚC 2: THỰC THI & VIẾT CODE MẪU CHUẨN CHỈ
- **Viết code**: Chỉ tiến hành viết code chi tiết sau khi giải pháp ở Bước 1 đã được phê duyệt.
- **Tiêu chuẩn code**:
  - Code phải sạch (Clean Code), đặt tên biến/hàm tường minh, có chú thích đầy đủ ở các đoạn xử lý logic phức tạp.
  - Sử dụng đúng các phiên bản thư viện đã cấu hình sẵn trong dự án (như `redis==4.6.0`, `django-rest-framework`, `django-knox`).

### 📝 BƯỚC 3: CẬP NHẬT TÀI LIỆU DỰ ÁN (DOCUMENTATION)
- **Rà soát tài liệu**: Kiểm tra xem sự thay đổi code có làm ảnh hưởng đến các thông tin mô tả trong file [DocumentAPI_Report2026.md](file:///d:/Sources/dashboard-report/DocumentAPI_Report2026.md) hoặc [target.md](file:///d:/Sources/dashboard-report/target.md) không.
- **Đồng bộ tài liệu**: Soạn thảo sẵn đoạn nội dung (Markdown) cần cập nhật/bổ sung hoặc chỉnh sửa cho các tài liệu tương ứng để đảm bảo tài liệu luôn phản ánh chính xác trạng thái của code.

### 🛡️ BƯỚC 4: RÀ SOÁT TỔNG THỂ (CHECKLIST TRƯỚC COMMIT)
Trước khi kết thúc nhiệm vụ, lập trình viên/Agent phải tự kiểm tra và cam kết các tiêu chí sau:
1. **Hoàn thiện**: Code đã xử lý triệt để bài toán chưa? Có sinh ra lỗi tiềm ẩn (Edge Cases) nào không?
2. **Hiệu năng & An toàn**: Đảm bảo an toàn dữ liệu và tối ưu hiệu năng cơ sở dữ liệu (Không gây Lock bảng lâu khi import, không bị lỗi N+1 Query khi duyệt quan hệ dữ liệu).
3. **Giám sát**: Đã viết logic ghi nhật ký tiến trình (Log) hoặc cảnh báo (Alert) nếu có lỗi xảy ra chưa?

### 🚀 BƯỚC 5: XÁC NHẬN COMMIT
- Khi mọi thứ đã hoàn hảo (Code chạy tốt, Tài liệu đã cập nhật, các tiêu chí Checklist đã pass).
- **Xác nhận**: Đưa ra một câu hỏi tường minh để yêu cầu Người dùng phê duyệt trước khi thực hiện lệnh commit/merge mã nguồn vào nhánh chính (`main`) của dự án.
