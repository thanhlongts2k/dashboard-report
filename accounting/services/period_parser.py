import os
import re
import logging
import calendar
import pandas as pd
from datetime import datetime

logger = logging.getLogger(__name__)

def detect_period_from_filename(filename, file_path):
    """
    Xác định kỳ báo cáo (reporting_period, start_date, end_date) của file Excel.
    Ưu tiên 1: Định dạng dải tháng trong tên file (e.g. BAN_HANG_202601-202605.xlsx)
    Ưu tiên 2: Định dạng 1 tháng duy nhất trong tên file (e.g. BAN_HANG_202607.xlsx)
    Ưu tiên 3: Kiểm tra tiêu đề Excel (Dòng 0-5) cho "Tháng X năm YYYY" hoặc "Từ ngày... Đến ngày..."
    Ưu tiên 4: Quét dải ngày thực tế (min-max) từ các cột Ngày hạch toán/chứng từ
    Ưu tiên 5: Nếu tên file chứa timestamp (_YYYYMMDD_HHMMSS) nhưng Excel không có ngày, dùng ngày trong timestamp làm fallback.
    """
    # 1. Check định dạng Quãng: ví dụ BAN_HANG_202601-202605.xlsx
    range_match = re.search(r'(\d{4})(\d{2})-(\d{4})(\d{2})', filename)
    if range_match:
        start_y, start_m, end_y, end_m = map(int, range_match.groups())
        start_date = datetime(start_y, start_m, 1).date()
        last_day = calendar.monthrange(end_y, end_m)[1]
        end_date = datetime(end_y, end_m, last_day).date()
        reporting_period = f"{end_y:04d}-{end_m:02d}"
        logger.info(f"Detected range period from filename {filename}: {start_date} to {end_date}, period: {reporting_period}")
        return start_date, end_date, reporting_period, True

    # 2. Check định dạng Tháng chỉ định duy nhất (dạng BAN_HANG_202607.xlsx) - 6 chữ số
    month_match = re.search(r'_(\d{4})(\d{2})\.xlsx$', filename, re.IGNORECASE)
    if month_match:
        y, m = map(int, month_match.groups())
        if 1 <= m <= 12 and 2000 <= y <= 2100:
            start_date = datetime(y, m, 1).date()
            last_day = calendar.monthrange(y, m)[1]
            end_date = datetime(y, m, last_day).date()
            reporting_period = f"{y:04d}-{m:02d}"
            logger.info(f"Detected monthly period from filename {filename}: {start_date} to {end_date}, period: {reporting_period}")
            return start_date, end_date, reporting_period, False

    # 3. Đọc tiêu đề Excel (Dòng 0 đến Dòng 5) tìm tiêu đề "Tháng X năm YYYY" hoặc dải ngày
    if file_path and os.path.exists(file_path):
        try:
            df_head = pd.read_excel(file_path, header=None, nrows=10)
            for idx in range(min(6, len(df_head))):
                row_text = " ".join([str(val) for val in df_head.iloc[idx].values if pd.notna(val)])
                
                # Khớp "Tháng 7 năm 2026" hoặc "Tháng 07 năm 2026"
                m_title = re.search(r'Tháng\s+(\d{1,2})\s+năm\s+(\d{4})', row_text, re.IGNORECASE)
                if m_title:
                    m_val, y_val = int(m_title.group(1)), int(m_title.group(2))
                    if 1 <= m_val <= 12 and 2000 <= y_val <= 2100:
                        start_date = datetime(y_val, m_val, 1).date()
                        last_day = calendar.monthrange(y_val, m_val)[1]
                        end_date = datetime(y_val, m_val, last_day).date()
                        reporting_period = f"{y_val:04d}-{m_val:02d}"
                        logger.info(f"Detected period from Excel Title '{m_title.group(0)}' in {filename}: {start_date} to {end_date}, period: {reporting_period}")
                        return start_date, end_date, reporting_period, False

                # Khớp "Từ ngày DD/MM/YYYY Đến ngày DD/MM/YYYY"
                m_range = re.search(r'Từ\s+ngày\s+(\d{2})/(\d{2})/(\d{4})\s+Đến\s+ngày\s+(\d{2})/(\d{2})/(\d{4})', row_text, re.IGNORECASE)
                if m_range:
                    d1, m1, y1, d2, m2, y2 = map(int, m_range.groups())
                    start_date = datetime(y1, m1, d1).date()
                    end_date = datetime(y2, m2, d2).date()
                    reporting_period = f"{y2:04d}-{m2:02d}"
                    logger.info(f"Detected period from Excel Date Range Title in {filename}: {start_date} to {end_date}, period: {reporting_period}")
                    return start_date, end_date, reporting_period, True

            # 4. Quét ngày trong dữ liệu (min-max date)
            df_full = pd.read_excel(file_path, header=None)
            header_row_idx, date_col_idx = -1, -1
            for idx, row in df_full.iterrows():
                for c_idx, val in enumerate(row.values):
                    val_str = str(val).strip() if pd.notna(val) else ""
                    if val_str in ["Ngày hạch toán", "Ngày chứng từ", "Ngày hóa đơn"]:
                        header_row_idx = idx
                        date_col_idx = c_idx
                        break
                if header_row_idx >= 0:
                    break

            if header_row_idx >= 0 and date_col_idx >= 0:
                s_dates = pd.to_datetime(df_full.iloc[header_row_idx + 1:, date_col_idx], errors='coerce').dropna()
                if not s_dates.empty:
                    min_dt = s_dates.min()
                    max_dt = s_dates.max()
                    start_date = min_dt.date()
                    end_date = max_dt.date()
                    reporting_period = f"{max_dt.year:04d}-{max_dt.month:02d}"
                    logger.info(f"Detected exact date range from excel content {filename}: {start_date} to {end_date}, period: {reporting_period}")
                    return start_date, end_date, reporting_period, True
        except Exception as e:
            logger.error(f"Error peeking excel file {filename}: {e}")

    # 5. Check định dạng Timestamp Ngày trong tên file (dạng BAN_HANG_20260803_084610.xlsx) làm fallback nếu Excel rỗng
    single_match = re.search(r'_(\d{4})(\d{2})(\d{2})_', filename)
    if single_match:
        y, m, d = map(int, single_match.groups())
        if 1 <= m <= 12 and 2000 <= y <= 2100:
            start_date = datetime(y, m, 1).date()
            last_day = calendar.monthrange(y, m)[1]
            end_date = datetime(y, m, last_day).date()
            reporting_period = f"{y:04d}-{m:02d}"
            logger.info(f"Detected single period from filename timestamp {filename}: {start_date} to {end_date}, period: {reporting_period}")
            return start_date, end_date, reporting_period, False

    # 6. Fallback cuối cùng: Lấy tháng hiện tại
    today = datetime.now()
    start_date = datetime(today.year, today.month, 1).date()
    last_day = calendar.monthrange(today.year, today.month)[1]
    end_date = datetime(today.year, today.month, last_day).date()
    reporting_period = f"{today.year:04d}-{today.month:02d}"
    logger.info(f"Fallback to current period for {filename}: {start_date} to {end_date}, period: {reporting_period}")
    return start_date, end_date, reporting_period, False

