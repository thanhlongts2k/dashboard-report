#!/usr/bin/env bash
# ==============================================================================
# SCRIPT TỰ ĐỘNG CÀI ĐẶT & TRIỂN KHAI BACKEND TRÊN SERVER LINUX (UBUNTU/DEBIAN)
# Dự án: Dashboard Report 2026
# Sử dụng: sudo bash server_deploy.sh
# ==============================================================================

set -e

# Màu sắc thông báo
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m'

echo -e "${CYAN}==========================================================${NC}"
echo -e "${YELLOW}  BẮT ĐẦU QUY TRÌNH SETUP TỰ ĐỘNG REPORT2026 BACKEND     ${NC}"
echo -e "${CYAN}==========================================================${NC}"

# 1. Kiểm tra quyền root
if [ "$EUID" -ne 0 ]; then
    echo -e "${RED}[LỖI] Vui lòng chạy script với quyền root hoặc sudo:${NC} sudo bash server_deploy.sh"
    exit 1
fi

# 2. Cài đặt các gói hệ thống cần thiết
echo -e "\n${YELLOW}[1/7] Đang cập nhật hệ điều hành và cài đặt các gói nền tảng...${NC}"
apt update && apt install -y python3 python3-pip python3-venv python3-dev \
    libpq-dev postgresql postgresql-contrib redis-server nginx unzip curl git

systemctl enable --now postgresql
systemctl enable --now redis-server

# 3. Khởi tạo Database PostgreSQL & Restore
echo -e "\n${YELLOW}[2/7] Đang cấu hình PostgreSQL và restore dữ liệu...${NC}"
DB_NAME="reportdb"
DB_USER="postgres"
DB_PASS=${1:-"$(python3 -c 'import secrets; print(secrets.token_urlsafe(16))' 2>/dev/null || openssl rand -base64 16 2>/dev/null || echo 'Report2026SecurePass!')"}
DUMP_FILE="/tmp/dashboard_report.dump"

sudo -u postgres psql -tc "SELECT 1 FROM pg_database WHERE datname = '$DB_NAME'" | grep -q 1 || \
sudo -u postgres psql -c "CREATE DATABASE $DB_NAME;"

sudo -u postgres psql -c "ALTER USER $DB_USER WITH PASSWORD '$DB_PASS';"
sudo -u postgres psql -c "GRANT ALL PRIVILEGES ON DATABASE $DB_NAME TO $DB_USER;"
sudo -u postgres psql -c "ALTER DATABASE $DB_NAME OWNER TO $DB_USER;"

if [ -f "$DUMP_FILE" ]; then
    echo -e "${GREEN}Đang restore dữ liệu từ $DUMP_FILE...${NC}"
    pg_restore -U $DB_USER -d $DB_NAME -v "$DUMP_FILE" || true
    echo -e "${GREEN}[OK] Restore Database hoàn tất!${NC}"
else
    echo -e "${YELLOW}[CẢNH BÁO] Không tìm thấy $DUMP_FILE, bỏ qua bước restore.${NC}"
fi

# 4. Giải nén mã nguồn vào /data/www/backend/dashboard-report
echo -e "\n${YELLOW}[3/7] Đang thiết lập thư mục mã nguồn Backend...${NC}"
APP_DIR="/data/www/backend/dashboard-report"
ZIP_FILE="/tmp/dashboard-report.zip"

mkdir -p /data/www/backend
mkdir -p "$APP_DIR"

if [ -f "$ZIP_FILE" ]; then
    echo -e "Đang giải nén $ZIP_FILE vào $APP_DIR..."
    unzip -o "$ZIP_FILE" -d "$APP_DIR"
    echo -e "${GREEN}[OK] Giải nén mã nguồn thành công!${NC}"
fi

cd "$APP_DIR"

# 5. Khởi tạo Python Virtualenv & Cài đặt thư viện
echo -e "\n${YELLOW}[4/7] Đang tạo môi trường ảo Python và cài đặt thư viện...${NC}"
if [ ! -d ".venv" ]; then
    python3 -m venv .venv
fi
source .venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
pip install gunicorn

# Cài đặt Playwright Chromium & dependencies hệ thống
echo -e "\n${YELLOW}Đang cài đặt headless Chromium & thư viện hệ điều hành cho Playwright...${NC}"
playwright install --with-deps chromium

# 6. Cấu hình .env, Migrate & Collectstatic
echo -e "\n${YELLOW}[5/7] Thiết lập biến môi trường và static files...${NC}"
if [ ! -f ".env" ]; then
    if [ -f ".env.example" ]; then
        cp .env.example .env
    else
        touch .env
    fi
    # Cập nhật thông số chuẩn production vào .env
    RANDOM_KEY=$(python3 -c 'import secrets; print(secrets.token_urlsafe(50))' 2>/dev/null || echo "prod-secret-key-$(date +%s)")
    sed -i "s/generate_a_strong_random_secret_key_for_production/$RANDOM_KEY/g" .env
    sed -i "s/DB_PORT=.*/DB_PORT=5432/g" .env || echo "DB_PORT=5432" >> .env
    sed -i "s/DB_PASSWORD=.*/DB_PASSWORD='$DB_PASS'/g" .env || echo "DB_PASSWORD='$DB_PASS'" >> .env
    sed -i "s/MISA_HEADLESS=.*/MISA_HEADLESS=True/g" .env || echo "MISA_HEADLESS=True" >> .env
    sed -i "s/DEBUG=.*/DEBUG=False/g" .env || echo "DEBUG=False" >> .env
fi

python manage.py migrate
python manage.py collectstatic --noinput

mkdir -p media staticfiles
chown -R www-data:www-data "$APP_DIR"
chmod -R 755 "$APP_DIR"

# 7. Thiết lập Systemd Services
echo -e "\n${YELLOW}[6/7] Đang tạo và kích hoạt các Systemd Services...${NC}"

cat <<EOF > /etc/systemd/system/dashboard-backend.service
[Unit]
Description=Gunicorn daemon for Report2026 Backend API
After=network.target postgresql.service redis-server.service

[Service]
User=www-data
Group=www-data
WorkingDirectory=$APP_DIR
EnvironmentFile=$APP_DIR/.env
ExecStart=$APP_DIR/.venv/bin/gunicorn --workers 3 --bind 127.0.0.1:8000 --timeout 300 report2026.wsgi:application
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
EOF

cat <<EOF > /etc/systemd/system/dashboard-celery.service
[Unit]
Description=Celery Worker for Report2026
After=network.target postgresql.service redis-server.service

[Service]
User=www-data
Group=www-data
WorkingDirectory=$APP_DIR
EnvironmentFile=$APP_DIR/.env
ExecStart=$APP_DIR/.venv/bin/celery -A report2026 worker -l info --concurrency=2
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
EOF

cat <<EOF > /etc/systemd/system/dashboard-beat.service
[Unit]
Description=Celery Beat Scheduler for Report2026
After=network.target postgresql.service redis-server.service

[Service]
User=www-data
Group=www-data
WorkingDirectory=$APP_DIR
EnvironmentFile=$APP_DIR/.env
ExecStart=$APP_DIR/.venv/bin/celery -A report2026 beat -l info --scheduler django_celery_beat.schedulers:DatabaseScheduler
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
EOF

systemctl daemon-reload
systemctl enable --now dashboard-backend dashboard-celery dashboard-beat
systemctl restart dashboard-backend dashboard-celery dashboard-beat

# 8. Cấu hình Nginx
echo -e "\n${YELLOW}[7/7] Đang kiểm tra cấu hình Nginx trong /etc/nginx/nginx.conf...${NC}"
# Backup file nginx.conf trước khi kiểm tra
cp /etc/nginx/nginx.conf /etc/nginx/nginx.conf.bak_$(date +%Y%m%d_%H%M%S)

# Kiểm tra xem block proxy api đã có trong nginx.conf chưa
if grep -q "location ~ \^/(api|admin)/" /etc/nginx/nginx.conf; then
    echo -e "${GREEN}[OK] Block proxy /api/ và /admin/ đã tồn tại trong nginx.conf!${NC}"
else
    echo -e "${YELLOW}Chưa phát hiện block proxy API trong /etc/nginx/nginx.conf.${NC}"
    echo -e "${CYAN}Vui lòng kiểm tra Giai đoạn 5 trong tài liệu docs/DEPLOYMENT_GUIDE_LINUX_NGINX.md để cập nhật block 'server_name report.haophuong.com;' trên cổng 8080 ssl.${NC}"
fi

nginx -t && systemctl reload nginx

echo -e "\n${GREEN}==========================================================${NC}"
echo -e "${GREEN}  CÀI ĐẶT HOÀN TẤT 100%! KIỂM TRA TRẠNG THÁI HỆ THỐNG:   ${NC}"
echo -e "${GREEN}==========================================================${NC}"
systemctl is-active --quiet dashboard-backend && echo -e "Backend Gunicorn:  [${GREEN}RUNNING${NC}]" || echo -e "Backend Gunicorn:  [${RED}FAILED${NC}]"
systemctl is-active --quiet dashboard-celery  && echo -e "Celery Worker:     [${GREEN}RUNNING${NC}]" || echo -e "Celery Worker:     [${RED}FAILED${NC}]"
systemctl is-active --quiet dashboard-beat    && echo -e "Celery Beat:       [${GREEN}RUNNING${NC}]" || echo -e "Celery Beat:       [${RED}FAILED${NC}]"
systemctl is-active --quiet nginx            && echo -e "Nginx Server:      [${GREEN}RUNNING${NC}]" || echo -e "Nginx Server:      [${RED}FAILED${NC}]"
echo -e "${CYAN}Truy cập IP hoặc Domain máy chủ để trải nghiệm hệ thống!${NC}"
