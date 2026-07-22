# FrontEndLogin - Bộ Giao Diện Kiểm Thử Đăng Nhập SSO Google & Account API

Bộ ứng dụng Web Frontend đơn giản (Single-Page App) được thiết kế đặc biệt để phục vụ việc kiểm thử giao diện (UI Testing) cho các API xác thực người dùng trong hệ thống **Report2026**:
1. **Google SSO Login (`POST /api/google-login/`)**
2. **Username/Password Login (`POST /api/login/`)**
3. **Test API Bảo Mật bằng Knox Auth Token (`GET /api/business-units/`)**

---

## 🚀 Hướng dẫn khởi chạy

### Cách 1: Khởi chạy bằng Python Server (Khuyên dùng)
1. Đảm bảo Django Backend server đang chạy tại cổng `8000`:
   ```powershell
   python manage.py runserver 8000
   ```
2. Khởi chạy script Python HTTP server từ thư mục gốc của dự án:
   ```powershell
   python FrontEndLogin/server.py
   ```
3. Trình duyệt sẽ tự động mở địa chỉ: `http://127.0.0.1:3000`

### Cách 2: Mở trực tiếp file `index.html`
- Bạn cũng có thể click đúp mở trực tiếp file `FrontEndLogin/index.html` trong trình duyệt web (Google Chrome / Edge).

---

## 🧪 Các tính năng kiểm thử chính

### 1. Test Google SSO Login (Tab "Google SSO"):
* **Cách A - Test bằng nút bấm Google SDK:**
  - Nhập **Google Client ID** của ứng dụng vào ô input.
  - Nhấn nút **Nạp SDK** để hiển thị nút *"Sign in with Google"* chuẩn của Google.
  - Sau khi đăng nhập Google thành công, nút bấm tự động gửi `id_token` sang Backend `/api/google-login/`.
* **Cách B - Test bằng cách Paste ID Token thủ công:**
  - Dán chuỗi `id_token` lấy từ [Google OAuth2 Playground](https://developers.google.com/oauthplayground/) vào ô textarea.
  - Bấm nút **Gửi Request API (/api/google-login/)**.

### 2. Test Đăng nhập Tài khoản Truyền thống (Tab "Tài Khoản"):
* Nhập Username và Password của User trong Django DB.
* Bấm **Đăng Nhập (/api/login/)**.

### 3. Bảng Phản hồi API (Response Inspector):
* Hiển thị trạng thái HTTP Status (200 OK, 400 Bad Request, 500 Internal Error).
* Hiển thị thời gian phản hồi (Response time ms).
* Hiển thị dữ liệu JSON chi tiết trả về từ Backend (Knox token, expiry, thông tin lỗi).

### 4. Quản lý Session & Gọi API Bảo Mật:
* Khi đăng nhập thành công, chuỗi **Knox Auth Token** được tự động lưu vào `localStorage`.
* Nút **Sao chép Token** hỗ trợ copy token nhanh vào bộ nhớ tạm.
* Nút **Test Gọi API Bảo Mật (`GET /api/business-units/`)** cho phép kiểm thử trực tiếp header `Authorization: Token <knox_token>` lên Backend server.
