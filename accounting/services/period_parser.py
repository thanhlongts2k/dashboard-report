import re
import logging
import calendar
import pandas as pd
from datetime import datetime

logger = logging.getLogger(__name__)

def detect_period_from_filename(filename, file_path):
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

    # 2. Check định dạng Ngày/Tháng thông thường: ví dụ BAN_HANG_20260630_163003.xlsx
    single_match = re.search(r'_(\d{4})(\d{2})(\d{2})_', filename)
    if single_match:
        y, m, d = map(int, single_match.groups())
        start_date = datetime(y, m, 1).date()
        last_day = calendar.monthrange(y, m)[1]
        end_date = datetime(y, m, last_day).date()
        reporting_period = f"{y:04d}-{m:02d}"
        logger.info(f"Detected single period from filename {filename}: {start_date} to {end_date}, period: {reporting_period}")
        return start_date, end_date, reporting_period, False

    # 3. Check định dạng Tháng: ví dụ BAN_HANG_202606.xlsx
    month_match = re.search(r'(?<!\d)(\d{4})(\d{2})(?!\d)', filename)
    if month_match:
        y, m = map(int, month_match.groups())
        if 1 <= m <= 12 and 2000 <= y <= 2100:
            start_date = datetime(y, m, 1).date()
            last_day = calendar.monthrange(y, m)[1]
            end_date = datetime(y, m, last_day).date()
            reporting_period = f"{y:04d}-{m:02d}"
            logger.info(f"Detected monthly period from filename {filename}: {start_date} to {end_date}, period: {reporting_period}")
            return start_date, end_date, reporting_period, False

    # 4. Fallback: Đọc nội dung file tìm cột ngày hạch toán/chứng từ để lấy chính xác dải ngày min-max
    try:
        df = pd.read_excel(file_path, header=None)
        header_row_idx = -1
        date_col_idx = -1
        
        for idx, row in df.iterrows():
            for c_idx, val in enumerate(row.values):
                val_str = str(val).strip() if pd.notna(val) else ""
                if val_str in ["Ngày hạch toán", "Ngày chứng từ"]:
                    header_row_idx = idx
                    date_col_idx = c_idx
                    break
            if header_row_idx >= 0:
                break

        if header_row_idx >= 0 and date_col_idx >= 0:
            s_dates = pd.to_datetime(df.iloc[header_row_idx + 1:, date_col_idx], errors='coerce').dropna()
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

    # 5. Fallback cuối cùng: Lấy tháng hiện tại
    today = datetime.now()
    start_date = datetime(today.year, today.month, 1).date()
    last_day = calendar.monthrange(today.year, today.month)[1]
    end_date = datetime(today.year, today.month, last_day).date()
    reporting_period = f"{today.year:04d}-{today.month:02d}"
    logger.info(f"Fallback to current period for {filename}: {start_date} to {end_date}, period: {reporting_period}")
    return start_date, end_date, reporting_period, False
