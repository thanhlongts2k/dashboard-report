# Helper functions to parse Celery crontab parameters into user-friendly Vietnamese descriptions.

def parse_days_of_week_desc(day_of_week_str):
    dow_map = {
        '0': 'Chủ Nhật', '7': 'Chủ Nhật',
        '1': 'Thứ Hai', '2': 'Thứ Ba', '3': 'Thứ Tư',
        '4': 'Thứ Năm', '5': 'Thứ Sáu', '6': 'Thứ Bảy',
        'mon': 'Thứ Hai', 'tue': 'Thứ Ba', 'wed': 'Thứ Tư',
        'thu': 'Thứ Năm', 'fri': 'Thứ Sáu', 'sat': 'Thứ Bảy', 'sun': 'Chủ Nhật'
    }
    if not day_of_week_str or day_of_week_str.strip() == '*':
        return "tất cả các ngày"
    
    parts = [p.strip().lower() for p in day_of_week_str.split(',') if p.strip()]
    desc_parts = []
    for part in parts:
        if '-' in part:
            subparts = [sp.strip() for sp in part.split('-') if sp.strip()]
            if len(subparts) == 2:
                start_desc = dow_map.get(subparts[0], f"Thứ {subparts[0]}")
                end_desc = dow_map.get(subparts[1], f"Thứ {subparts[1]}")
                desc_parts.append(f"từ {start_desc} đến {end_desc}")
            else:
                desc_parts.append(part)
        else:
            desc_parts.append(dow_map.get(part, f"Thứ {part}"))
    return ", ".join(desc_parts)


def parse_days_of_month_desc(day_of_month_str):
    if not day_of_month_str or day_of_month_str.strip() == '*':
        return "mọi ngày"
    
    parts = [p.strip() for p in day_of_month_str.split(',') if p.strip()]
    desc_parts = []
    has_range = any('-' in p for p in parts)
    
    if has_range:
        for part in parts:
            if '-' in part:
                subparts = [sp.strip() for sp in part.split('-') if sp.strip()]
                if len(subparts) == 2:
                    try:
                        start_val = f"{int(subparts[0]):02d}"
                    except ValueError:
                        start_val = subparts[0]
                    try:
                        end_val = f"{int(subparts[1]):02d}"
                    except ValueError:
                        end_val = subparts[1]
                    desc_parts.append(f"từ ngày {start_val} đến ngày {end_val}")
                else:
                    desc_parts.append(f"ngày {part}")
            else:
                try:
                    desc_parts.append(f"ngày {int(part):02d}")
                except ValueError:
                    desc_parts.append(f"ngày {part}")
        return ", ".join(desc_parts)
    else:
        day_labels = []
        for part in parts:
            try:
                day_labels.append(f"{int(part):02d}")
            except ValueError:
                day_labels.append(part)
        return "ngày " + ", ".join(day_labels)


def parse_cron_desc(cron_str):
    parts = cron_str.split()
    if len(parts) != 5:
        return f"Tùy chỉnh (Cron: {cron_str})"
    
    minute, hour, day_of_month, month, day_of_week = parts
    
    try:
        time_desc = f"lúc {int(hour):02d}:{int(minute):02d}"
    except ValueError:
        if hour == '*':
            if minute == '*':
                time_desc = "mỗi phút"
            else:
                time_desc = f"mỗi giờ tại phút {minute.zfill(2)}"
        else:
            time_desc = f"lúc giờ {hour} phút {minute}"
            
    if month == '*':
        if day_of_month == '*':
            date_desc = ""
        else:
            date_desc = f" vào {parse_days_of_month_desc(day_of_month)} hàng tháng"
    else:
        if day_of_month == '*':
            date_desc = f" hàng ngày trong tháng {month}"
        else:
            date_desc = f" vào {parse_days_of_month_desc(day_of_month)} của tháng {month}"
            
    if day_of_week == '*':
        dow_desc = ""
    else:
        dow_desc = f" vào các ngày {parse_days_of_week_desc(day_of_week)}"
        
    desc = f"{time_desc}{date_desc}{dow_desc}".strip()
    if desc:
        desc = desc[0].upper() + desc[1:]
    return f"Tùy chỉnh ({desc})"
