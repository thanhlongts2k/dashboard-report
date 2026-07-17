# Hướng Dẫn Sử Dụng Tính Năng Gửi Báo Cáo Qua Email (Send Email API)

Tài liệu này hướng dẫn chi tiết cách cấu hình, vận hành và kiểm thử tính năng gửi email mới được tích hợp vào Backend của dự án **Report2026**. Hướng dẫn này được viết cực kỳ chi tiết, dễ hiểu, phù hợp cho người mới bắt đầu hoặc người không chuyên về lập trình Python.

---

## 1. Giới thiệu Tính Năng

Chúng ta vừa xây dựng một **API Endpoint** tại đường dẫn:  
`POST http://localhost:8000/api/reports/send-email/`

**Mục đích:** Hỗ trợ giao diện Frontend gửi các email báo cáo kèm tệp đính kèm (như file Excel, hình ảnh, PDF...) đến các nhân sự hoặc đối tác.

---

## 2. Các File Đã Thay Đổi/Thêm Mới Trên Hệ Thống

Để tính năng này hoạt động, chúng ta đã can thiệp vào các file sau:
1.  **[report2026/settings.py](file:///d:/Sources/dashboard-report/report2026/settings.py):** Thêm các cấu hình kết nối tới máy chủ gửi mail (SMTP).
2.  **[accounting/serializers.py](file:///d:/Sources/dashboard-report/accounting/serializers.py):** Thêm bộ kiểm tra định dạng dữ liệu đầu vào (`SendEmailSerializer`), giúp đảm bảo tiêu đề, nội dung và các email nhận được nhập đúng định dạng trước khi gửi đi.
3.  **[accounting/views.py](file:///d:/Sources/dashboard-report/accounting/views.py):** Thêm bộ xử lý logic API (`SendEmailAPIView`) nhận yêu cầu từ Frontend, đọc file đính kèm và kích hoạt lệnh gửi email.
4.  **[accounting/urls.py](file:///d:/Sources/dashboard-report/accounting/urls.py):** Đăng ký đường dẫn API để có thể truy cập từ bên ngoài.
5.  **[accounting/tests.py](file:///d:/Sources/dashboard-report/accounting/tests.py):** Viết các kịch bản kiểm thử tự động để bảo vệ mã nguồn, tránh bị lỗi khi nâng cấp sau này.
6.  **[DocumentAPI_Report2026.md](file:///d:/Sources/dashboard-report/DocumentAPI_Report2026.md) & [target.md](file:///d:/Sources/dashboard-report/target.md):** Cập nhật tài liệu dự án để đồng bộ thông tin.

---

## 3. Hướng Dẫn Cấu Hướng Dẫn Cấu Hình SMTP Để Gửi Email (File `.env`)

Hệ thống sử dụng giao thức **SMTP** để gửi mail. Bạn cần mở file cấu hình môi trường `.env` ở thư mục gốc của dự án và bổ sung cấu hình sau:

```env
# --- Cấu hình gửi Mail (SMTP) ---
EMAIL_BACKEND='django.core.mail.backends.smtp.EmailBackend'
EMAIL_HOST='smtp.gmail.com'
EMAIL_PORT=587
EMAIL_USE_TLS=True
EMAIL_USE_SSL=False
# Email của bạn dùng để gửi đi
EMAIL_HOST_USER='your_email@gmail.com'
# Mật khẩu ứng dụng (App Password) từ Gmail
EMAIL_HOST_PASSWORD='your_app_password'
DEFAULT_FROM_EMAIL='your_email@gmail.com'
```

### 💡 Lưu ý quan trọng khi dùng Gmail làm SMTP:
*   Mật khẩu `EMAIL_HOST_PASSWORD` **không phải** là mật khẩu đăng nhập Gmail thông thường của bạn.
*   Bạn cần bật xác thực 2 lớp cho tài khoản Google của mình, sau đó truy cập mục **Bảo mật** -> tạo **Mật khẩu ứng dụng (App Password)** dành cho thiết bị/ứng dụng khác và dán chuỗi 16 ký tự nhận được vào trường này.

---

## 4. Hướng Dẫn Kiểm Thử Không Cần SMTP Thật (Chế độ Console)

Nếu bạn muốn test nhanh ở máy cá nhân (Local) để xem email gửi đi trông như thế nào mà không cần gửi mail thật, hãy thay đổi cấu hình sau trong file `.env`:

```env
EMAIL_BACKEND='django.core.mail.backends.console.EmailBackend'
```

*   **Cách hoạt động:** Khi bạn gọi API gửi mail, hệ thống sẽ **không** gửi mail thật đi. Thay vào đó, toàn bộ nội dung email (tiêu đề, người gửi, người nhận, nội dung tin nhắn và cấu trúc file đính kèm dưới dạng mã hóa) sẽ **được in thẳng ra cửa sổ Terminal/Console** nơi Django Server đang chạy. Bạn có thể dễ dàng kiểm tra nội dung ngay lập tức.

---

## 5. Các Bước Chạy & Gọi API Gửi Email

### Bước 1: Khởi động Server Django
1. Mở cửa sổ terminal/powershell tại thư mục dự án `d:\Sources\dashboard-report`.
2. Kích hoạt môi trường ảo (nếu chưa kích hoạt):
   ```powershell
   .venv\Scripts\activate
   ```
3. Chạy lệnh khởi động máy chủ:
   ```powershell
   python manage.py runserver
   ```
   *(Server sẽ chạy tại địa chỉ mặc định `http://127.0.0.1:8000/`)*

---

### Bước 2: Lấy Token Xác Thực (Authentication Token)
API gửi mail yêu cầu xác thực bằng Token. Bạn cần đăng nhập để lấy Token:
1. Dùng Postman hoặc công cụ bất kỳ, gửi request:
   - **Method:** `POST`
   - **URL:** `http://127.0.0.1:8000/api/login/`
   - **Body (JSON):**
     ```json
     {
       "username": "admin",
       "password": "123"
     }
     ```
2. Bạn sẽ nhận được kết quả dạng:
     ```json
     {
       "expiry": "2026-07-17T...",
       "token": "495df02d9c122394fa..."   <-- ĐÂY LÀ TOKEN CỦA BẠN
     }
     ```

---

### Bước 3: Gửi Yêu Cầu Gửi Mail (POST `/api/reports/send-email/`)
Thiết lập request trên Postman hoặc Client gửi HTTP của bạn như sau:

*   **Method:** `POST`
*   **URL:** `http://127.0.0.1:8000/api/reports/send-email/`
*   **Headers:**
    *   `Authorization`: `Token 495df02d9c122394fa...` *(Thay thế bằng Token bạn vừa lấy ở Bước 2. Hãy nhớ có chữ **Token** và một khoảng trắng phía trước)*
*   **Body Type (Định dạng):** Chọn `form-data` (Multipart form-data)
*   **Các trường dữ liệu (Key-Value):**
    
    | Tên Trường (Key) | Loại (Type) | Bắt Buộc | Ý Nghĩa / Cách Điền |
    | :--- | :--- | :--- | :--- |
    | **`to_emails`** | Text | **Có** | Danh sách các email nhận, ngăn cách bởi dấu phẩy.<br>Ví dụ: `admin@haophuong.com, test@gmail.com` |
    | **`subject`** | Text | **Có** | Tiêu đề của thư.<br>Ví dụ: `Báo cáo bán hàng tháng 6` |
    | **`message`** | Text | **Có** | Nội dung chi tiết của email.<br>Ví dụ: `Chào anh/chị, gửi kèm báo cáo.` |
    | **`file`** | File | Không | Chọn file đính kèm từ máy tính của bạn (Excel, PDF, PNG...). |
    | **`file_name`** | Text | Không | Đặt tên mới cho file đính kèm khi gửi đi.<br>Ví dụ: `Bao_Cao_Moi_Nhat.xlsx` (Nếu không truyền, hệ thống sẽ lấy tên gốc của file tải lên). |
    | **`from_email`** | Text | Không | Địa chỉ người gửi (Nếu bỏ trống sẽ tự lấy email cấu hình trong hệ thống). |

---

### Bước 4: Nhận Kết Quả Trả Về

*   **Thành công (Mã 200 OK):**
    ```json
    {
      "status": "success",
      "message": "Gửi email thành công."
    }
    ```
    *Nếu bạn bật chế độ Console ở mục 4, hãy xem màn hình terminal chạy `runserver` để thấy thư in ra.*

*   **Lỗi tham số (Mã 400 Bad Request):**
    ```json
    {
      "to_emails": [
        "Địa chỉ email không hợp lệ: email_sai_dinh_dang"
      ]
    }
    ```

*   **Lỗi SMTP hoặc máy chủ (Mã 500 Internal Error):**
    ```json
    {
      "status": "error",
      "message": "Không thể gửi email: <Chi tiết lỗi lỗi SMTP hoặc cấu hình sai mật khẩu ứng dụng>"
    }
    ```

---

## 6. Xử Lý Khi Gặp Sự Cố (Troubleshooting)

1.  **Lỗi `401 Unauthorized`**:
    *   *Nguyên nhân:* Bạn chưa truyền Header `Authorization` hoặc truyền sai định dạng.
    *   *Khắc phục:* Đảm bảo Header có key là `Authorization` và giá trị là `Token <key_của_bạn>` (lưu ý chữ T viết hoa và có khoảng trắng).
2.  **Lỗi gửi mail bị treo lâu rồi báo lỗi kết nối (Timeout/ConnectionRefused)**:
    *   *Nguyên nhân:* Cổng `587` hoặc `465` của nhà cung cấp mạng đang bị chặn, hoặc cấu hình sai `EMAIL_PORT`, `EMAIL_USE_TLS`/`EMAIL_USE_SSL`.
    *   *Khắc phục:* Kiểm tra lại thông số cổng phù hợp với máy chủ gửi mail của doanh nghiệp bạn. Thử đổi sang chế độ kiểm thử `Console` trước để chắc chắn logic code chạy tốt.
3.  **Lỗi `Authentication Failed` (Mã lỗi 535)**:
    *   *Nguyên nhân:* Gmail từ chối do thông tin đăng nhập hoặc mật khẩu ứng dụng bị sai.
    *   *Khắc phục:* Kiểm tra lại mật khẩu ứng dụng (App Password) đã được tạo và kích hoạt chính xác chưa.
4.  **Lỗi email gửi đi vẫn hiển thị địa chỉ Gmail của SMTP mặc dù đã truyền `from_email` khác**:
    *   *Nguyên nhân:* Đây là tính năng bảo mật chống giả mạo (Anti-Spoofing) của các nhà cung cấp như Gmail/Office365. Họ tự động thay thế `From` thành hòm thư đăng nhập SMTP thực tế.
    *   *Khắc phục/Giải pháp:* Hệ thống đã tự động đính kèm tiêu đề **`Reply-To`** (Phản hồi tới) bằng địa chỉ `from_email` bạn truyền lên. Khi người nhận bấm nút **Reply (Trả lời)** trên hòm thư của họ, email trả lời sẽ tự động điền địa chỉ `from_email` mà bạn mong muốn.
5.  **Cách kiểm tra lịch sử gửi email**:
    *   Mọi yêu cầu gửi email (cả thành công và thất bại) đều được hệ thống tự động ghi nhận lại trong tệp tin nhật ký **`email_send.log`** đặt tại thư mục gốc của dự án.
    *   Đối với các tệp đính kèm (`file`), tệp nhật ký sẽ chỉ lưu lại tên của tệp đó (ví dụ: `Bao_Cao_Ban_Hang.xlsx`) chứ không lưu nội dung tệp để tránh làm nặng bộ nhớ máy chủ.
6.  **Cách kiểm tra thời gian thực thi (Timing Log)**:
    *   Để biết chính xác quá trình gửi email mất bao nhiêu thời gian (bao gồm thời gian nhận request, validate, đọc file đính kèm, và thời gian SMTP server gửi thư), hệ thống sẽ tự động ghi log vào tệp **`email_timing.log`** tại thư mục gốc của dự án.
    *   Nhật ký này giúp lập trình viên và quản trị viên dễ dàng phát hiện nút thắt cổ chai (bottleneck) nếu quá trình gửi email bị chậm.


