#!/usr/bin/env bash
# ==============================================================================
# SCRIPT TỰ ĐỘNG SAO LƯU (BACKUP) DATABASE REPORTDB TRÊN SERVER LINUX
# Dự án: Dashboard Report 2026
# Sử dụng: Chạy qua Cronjob hàng ngày vào 02:00 AM
# ==============================================================================

set -e

BACKUP_DIR="/data/backups/db"
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
BACKUP_FILE="$BACKUP_DIR/reportdb_$TIMESTAMP.dump"
LOG_PREFIX="[$(date +"%Y-%m-%d %H:%M:%S")]"

echo "$LOG_PREFIX 👉 Bắt đầu tiến trình sao lưu cơ sở dữ liệu reportdb..."

# 1. Tạo thư mục lưu trữ nếu chưa tồn tại
mkdir -p "$BACKUP_DIR"

# 2. Thực hiện dump database bằng PostgreSQL
sudo -u postgres pg_dump -d reportdb -F c -b -f "$BACKUP_FILE"

# Phân quyền cho file backup
sudo chmod 640 "$BACKUP_FILE"
sudo chown postgres:postgres "$BACKUP_FILE"

FILE_SIZE=$(du -h "$BACKUP_FILE" | cut -f1)
echo "$LOG_PREFIX ✅ Sao lưu thành công: $BACKUP_FILE ($FILE_SIZE)"

# 3. Tự động dọn dẹp các bản backup cũ hơn 7 ngày
echo "$LOG_PREFIX 🗑️ Đang kiểm tra và xóa các bản sao lưu cũ hơn 7 ngày..."
DELETED_COUNT=$(find "$BACKUP_DIR" -type f -name "reportdb_*.dump" -mtime +7 | wc -l)
find "$BACKUP_DIR" -type f -name "reportdb_*.dump" -mtime +7 -delete

echo "$LOG_PREFIX 🎯 Hoàn tất! Đã loại bỏ $DELETED_COUNT tệp backup cũ. Dung lượng thư mục backup:"
du -sh "$BACKUP_DIR"
