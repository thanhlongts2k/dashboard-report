#!/usr/bin/env bash
# ==============================================================================
# SCRIPT CẬP NHẬT MÃ NGUỒN & RESTART DỊCH VỤ REPORT2026 TRÊN SERVER LINUX
# Dự án: Dashboard Report 2026
# Sử dụng: bash /data/www/backend/dashboard-report/scripts/deploy/server_update.sh
#          hoặc bash /tmp/server_update.sh
# ==============================================================================

set -e

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
RED='\033[0;31m'
NC='\033[0m'

APP_DIR="/data/www/backend/dashboard-report"
TAR_FILE="/tmp/dashboard_be.tar.gz"

echo -e "\n${CYAN}====================================================================${NC}"
echo -e "${CYAN}    TIẾN TRÌNH CẬP NHẬT BACKEND: $APP_DIR${NC}"
echo -e "${CYAN}====================================================================${NC}"

# 1. Kiểm tra và giải nén gói mã nguồn mới (nếu có trong /tmp)
if [ -f "$TAR_FILE" ]; then
    echo -e "${YELLOW}[1/5] Phát hiện gói mã nguồn mới tại $TAR_FILE, tiến hành giải nén...${NC}"
    mkdir -p "$APP_DIR"
    
    # Bảo toàn file .env trên server
    if [ -f "$APP_DIR/.env" ]; then
        echo -e "      Đang sao lưu tạm file .env của server..."
        cp "$APP_DIR/.env" /tmp/dashboard_report_env.bak
    fi
    
    # Giải nén đè mã nguồn mới vào thư mục backend
    tar -xzf "$TAR_FILE" -C "$APP_DIR"
    rm -f "$TAR_FILE"
    
    # Phục hồi lại file .env của server
    if [ -f /tmp/dashboard_report_env.bak ]; then
        mv /tmp/dashboard_report_env.bak "$APP_DIR/.env"
        echo -e "      Đã phục hồi file .env server nguyên vẹn."
    elif [ ! -f "$APP_DIR/.env" ] && [ -f "$APP_DIR/.env.example" ]; then
        echo -e "      Chưa có .env, khởi tạo từ .env.example..."
        cp "$APP_DIR/.env.example" "$APP_DIR/.env"
    fi
else
    echo -e "${YELLOW}[1/5] Không có tệp $TAR_FILE mới, tiến hành cập nhật trực tiếp tại $APP_DIR...${NC}"
fi

cd "$APP_DIR"

# 2. Kiểm tra môi trường ảo Python (.venv)
echo -e "\n${YELLOW}[2/5] Kiểm tra môi trường ảo Python và dependencies...${NC}"
if [ ! -d ".venv" ]; then
    echo -e "      Chưa có .venv, đang khởi tạo môi trường Python mới..."
    python3 -m venv .venv
    source .venv/bin/activate
    pip install --upgrade pip
    pip install -r requirements.txt
    pip install gunicorn
else
    source .venv/bin/activate
    pip install -r requirements.txt
fi

# 3. Chạy Database Migrations & Gom Static Files
echo -e "\n${YELLOW}[3/5] Thực thi migrate và collectstatic...${NC}"
python manage.py migrate --noinput
python manage.py collectstatic --noinput

# 4. Phân quyền thư mục đảm bảo www-data hoạt động trơn tru
echo -e "\n${YELLOW}[4/5] Thiết lập cấu trúc thư mục & phân quyền www-data...${NC}"
mkdir -p media/auto_imports/success media/auto_imports/backup staticfiles
sudo chown -R www-data:www-data "$APP_DIR"
sudo chmod -R 755 "$APP_DIR"
sudo chmod -R 775 "$APP_DIR/media"

# Đảm bảo script update giữ quyền thực thi
chmod +x "$APP_DIR/scripts/deploy/server_update.sh" 2>/dev/null || true

# 5. Khởi động lại các Systemd Services và Nginx
echo -e "\n${YELLOW}[5/5] Khởi động lại các Systemd Services...${NC}"
sudo systemctl restart dashboard-backend 2>/dev/null || echo -e "${RED}Cảnh báo: Không thể restart dashboard-backend (hãy kiểm tra quyền sudo)${NC}"
sudo systemctl restart dashboard-celery 2>/dev/null || true
sudo systemctl restart dashboard-beat 2>/dev/null || true
sudo systemctl reload nginx 2>/dev/null || true

echo -e "\n${GREEN}====================================================================${NC}"
echo -e "${GREEN} ✅ CẬP NHẬT BACKEND HOÀN TẤT THÀNH CÔNG!${NC}"
echo -e "${GREEN}    Hệ thống đang phục vụ tại: $APP_DIR${NC}"
echo -e "${GREEN}====================================================================${NC}\n"
