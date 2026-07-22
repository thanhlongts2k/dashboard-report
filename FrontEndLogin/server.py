"""
Report2026 FrontEndLogin Tester - Local Development Server
"""
import http.server
import socketserver
import webbrowser
import os

PORT = 3000
DIRECTORY = os.path.dirname(os.path.abspath(__file__))

class Handler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=DIRECTORY, **kwargs)

if __name__ == '__main__':
    url = f"http://127.0.0.1:{PORT}"
    print("=" * 65)
    print(f"🚀 Report2026 Auth UI Tester đang chạy tại: {url}")
    print(f"📁 Thư mục phục vụ: {DIRECTORY}")
    print("👉 Đảm bảo Django Backend đang chạy tại http://127.0.0.1:8000")
    print("=" * 65)

    # Tự động mở trình duyệt
    try:
        webbrowser.open(url)
    except Exception as e:
        print(f"Không thể tự động mở trình duyệt: {e}")

    with socketserver.TCPServer(("127.0.0.1", PORT), Handler) as httpd:
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("\n🛑 Đã dừng FrontEnd Test Server.")
