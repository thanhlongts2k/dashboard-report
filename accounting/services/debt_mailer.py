import logging
import calendar
from decimal import Decimal
from collections import defaultdict
from datetime import datetime, date, timedelta
from django.conf import settings
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.utils import timezone
from django.db.models import Sum, Q

from accounting.models import (
    BusinessUnit,
    BUPerformance,
    BUTargetPlan,
    ReceivablesAgeing,
    Customer,
    Employee,
    EmployeeAssignment
)
from accounting.services.sso_notifier import get_formatted_from_email

logger = logging.getLogger(__name__)


def get_target_period(period=None):
    """
    Chuẩn hóa kỳ báo cáo dạng YYYY-MM.
    Nếu không truyền, tự động lấy kỳ mới nhất có trong ReceivablesAgeing hoặc tháng hiện tại.
    """
    if period and isinstance(period, str) and len(period.strip()) >= 7:
        return period.strip()[:7]
    
    latest_ageing = ReceivablesAgeing.objects.order_by('-reporting_period').first()
    if latest_ageing and latest_ageing.reporting_period:
        return latest_ageing.reporting_period
    
    return timezone.now().strftime('%Y-%m')


def format_period_display(period_str):
    """
    Chuyển '2026-08' -> 'Tháng 08/2026'
    """
    try:
        parts = period_str.split('-')
        return f"Tháng {parts[1]}/{parts[0]}"
    except Exception:
        return period_str


def get_bu_manager_info(bu):
    """
    Tra cứu thông tin Trưởng BU (Tên và Email) chuẩn hóa từ BusinessUnit
    """
    if not bu:
        return {"name": "N/A", "email": None, "employee": None}

    # 1. Ưu tiên lấy từ database (bu.manager)
    mgr_name = bu.manager
    if not mgr_name:
        # 2. Fallback từ bảng mapping chuẩn nếu DB chưa điền
        manager_name_map = {
            'BU_ELEVATOR': 'ĐÀO TIẾN DŨNG',
            'BU_IBIZ PREMIUM': 'HỒ TÔN NHẬT MINH',
            'BU_IBIZ VALUE': 'NGUYỄN NGỌC HUY PHONG',
            'BU_MANUFACTURING': 'HỒ XUÂN QUANG',
            'BU_AGRITECH': 'TRẦN DUY HIẾU',
            'BU_ECO': 'TRẦN DUY HIẾU',
            'BU_Agritech - Eco': 'TRẦN DUY HIẾU',
            'Oversea': 'NGÔ ĐÌNH TRUNG TÂN',
        }
        mgr_name = manager_name_map.get(bu.code, "Chưa cấu hình")
    
    # Tìm nhân viên tương ứng trong Employee model để lấy email
    emp = Employee.objects.filter(full_name__iexact=mgr_name).first()
    if not emp and mgr_name:
        last_name_part = mgr_name.strip().split()[-1]
        emp = Employee.objects.filter(full_name__icontains=last_name_part, is_active=True).first()

    return {
        "name": mgr_name,
        "email": getattr(bu, 'manager_email', None) or (emp.email if emp else None),
        "employee_code": emp.employee_code if emp else "",
        "employee": emp
    }


def is_bu_code_excluded(bu_code, exclude_list=None):
    """Kiểm tra mã BU có nằm trong danh sách loại trừ không (hỗ trợ chuẩn hóa tiền tố BU_)"""
    if not bu_code:
        return False
    if exclude_list is None:
        exclude_list = getattr(settings, 'DEBT_REMINDER_EXCLUDE_BU_CODES', ['ĐTCT', 'BU_DTCT'])

    code_str = str(bu_code).strip().upper()
    clean_code = code_str.replace('BU_', '')
    for exc in exclude_list:
        if not exc or not isinstance(exc, str):
            continue
        exc_str = str(exc).strip().upper()
        clean_exc = exc_str.replace('BU_', '')
        if code_str == exc_str or clean_code == clean_exc:
            return True
    return False


def collect_sales_debt_data(period=None, bu_code=None):
    """
    Gom dữ liệu công nợ chi tiết theo từng Nhân viên Sales (Cấp 1).
    - Bộ lọc: TK 1311 (TARGET_RECEIVABLE_ACCOUNTS), 6 BU kinh doanh cốt lõi (CORE_COMMERCIAL_BU_CODES), loại trừ Oversea và BU loại trừ.
    - Chỉ lấy khách hàng có total_debt > 0.
    """
    period = get_target_period(period)
    target_accounts = getattr(settings, 'TARGET_RECEIVABLE_ACCOUNTS', ['1311'])
    raw_core_bus = getattr(settings, 'CORE_COMMERCIAL_BU_CODES', [
        'BU_ELEVATOR', 'BU_IBIZ PREMIUM', 'BU_ECO', 'BU_MANUFACTURING', 'BU_AGRITECH', 'BU_IBIZ VALUE', 'ĐTCT'
    ])
    exclude_bu_codes = getattr(settings, 'DEBT_REMINDER_EXCLUDE_BU_CODES', ['ĐTCT', 'BU_DTCT'])
    core_bus = [b for b in raw_core_bus if not is_bu_code_excluded(b, exclude_bu_codes)]
    excluded_cust_groups = getattr(settings, 'EXCLUDED_CUSTOMER_GROUP_CODES', ['Internal'])

    ageing_filter = Q(
        reporting_period=period,
        account_code__in=target_accounts,
        customer__business_unit__code__in=core_bus
    )
    if bu_code:
        ageing_filter &= Q(customer__business_unit__code__iexact=bu_code)

    ageings = ReceivablesAgeing.objects.filter(ageing_filter).exclude(
        customer__group__code__in=excluded_cust_groups
    ).select_related('customer', 'customer__assigned_employee', 'customer__business_unit')

    # Gom theo Sales -> Customer
    sales_map = defaultdict(lambda: {
        'employee': None,
        'employee_code': '',
        'full_name': '',
        'email': '',
        'customers_dict': defaultdict(lambda: {
            'customer': None,
            'customer_code': '',
            'customer_name': '',
            'bu_code': '',
            'bu_name': '',
            'total_debt': Decimal('0'),
            'due_total': Decimal('0'),
            'overdue_total': Decimal('0'),
            'overdue_0_14': Decimal('0'),
            'overdue_15_30': Decimal('0'),
            'overdue_31_plus': Decimal('0'),
        })
    })

    for a in ageings:
        c = a.customer
        if not c:
            continue
        sales = c.assigned_employee
        bu = c.business_unit

        s_key = sales.id if sales else 0
        s_entry = sales_map[s_key]
        if s_entry['employee'] is None:
            s_entry['employee'] = sales
            s_entry['employee_code'] = sales.employee_code if sales else "UNASSIGNED"
            s_entry['full_name'] = sales.full_name if sales else "Khách hàng tự do / Chưa gán Sales"
            s_entry['email'] = sales.email if (sales and sales.email) else ""

        c_entry = s_entry['customers_dict'][c.id]
        c_entry['customer'] = c
        c_entry['customer_code'] = c.code
        c_entry['customer_name'] = c.name
        c_entry['bu_code'] = bu.code if bu else ""
        c_entry['bu_name'] = bu.name if bu else ""
        c_entry['total_debt'] += a.total_debt or Decimal('0')
        c_entry['due_total'] += a.due_total or Decimal('0')
        c_entry['overdue_total'] += a.overdue_total or Decimal('0')
        c_entry['overdue_0_14'] += a.overdue_0_14 or Decimal('0')
        c_entry['overdue_15_30'] += a.overdue_15_30 or Decimal('0')

        overdue_31_plus = (
            (a.overdue_31_45 or Decimal('0')) +
            (a.overdue_46_60 or Decimal('0')) +
            (a.overdue_61_90 or Decimal('0')) +
            (a.overdue_91_120 or Decimal('0')) +
            (a.overdue_above_120 or Decimal('0'))
        )
        c_entry['overdue_31_plus'] += overdue_31_plus

    results = []
    for s_key, s_data in sales_map.items():
        # Lọc danh sách khách hàng có nợ > 0
        active_customers = [c for c in s_data['customers_dict'].values() if c['total_debt'] > 0]
        if not active_customers:
            continue

        # Sắp xếp khách hàng theo tổng nợ giảm dần
        active_customers.sort(key=lambda x: x['total_debt'], reverse=True)

        tot_debt = sum(c['total_debt'] for c in active_customers)
        tot_due = sum(c['due_total'] for c in active_customers)
        tot_overdue = sum(c['overdue_total'] for c in active_customers)
        tot_0_14 = sum(c['overdue_0_14'] for c in active_customers)
        tot_15_30 = sum(c['overdue_15_30'] for c in active_customers)
        tot_31_plus = sum(c['overdue_31_plus'] for c in active_customers)
        rate = float(round(tot_overdue / tot_debt * 100, 2)) if tot_debt > 0 else 0.0

        # Lấy BU đại diện chính của Sales (BU có nhiều khách hàng nợ nhất)
        bu_counts = defaultdict(int)
        for c in active_customers:
            if c['bu_code']:
                bu_counts[c['bu_code']] += 1
        primary_bu_code = max(bu_counts, key=bu_counts.get) if bu_counts else ""

        results.append({
            'employee_id': s_key,
            'employee_code': s_data['employee_code'],
            'full_name': s_data['full_name'],
            'email': s_data['email'],
            'has_email': bool(s_data['email'] and '@' in s_data['email']),
            'primary_bu_code': primary_bu_code,
            'total_debt': tot_debt,
            'due_total': tot_due,
            'overdue_total': tot_overdue,
            'overdue_0_14': tot_0_14,
            'overdue_15_30': tot_15_30,
            'overdue_31_plus': tot_31_plus,
            'overdue_rate': rate,
            'customer_count': len(active_customers),
            'overdue_customer_count': len([c for c in active_customers if c['overdue_total'] > 0]),
            'customers': active_customers,
        })

    # Sắp xếp Sales theo tổng nợ giảm dần
    results.sort(key=lambda x: x['total_debt'], reverse=True)
    return results


def collect_bu_manager_debt_data(period=None, bu_code=None):
    """
    Gom dữ liệu công nợ tổng hợp cấp BU gửi cho Trưởng BU (Cấp 2).
    - Tổng nợ BU, trong hạn, quá hạn, tỷ lệ quá hạn %.
    - Bảng phân bổ theo từng nhân viên trong BU.
    - Top khách hàng nợ quá hạn cao nhất trong BU.
    """
    period = get_target_period(period)
    core_bus = getattr(settings, 'CORE_COMMERCIAL_BU_CODES', [
        'BU_ELEVATOR', 'BU_IBIZ PREMIUM', 'BU_ECO', 'BU_MANUFACTURING', 'BU_AGRITECH', 'BU_IBIZ VALUE', 'ĐTCT'
    ])
    exclude_bu_codes = getattr(settings, 'DEBT_REMINDER_EXCLUDE_BU_CODES', ['ĐTCT', 'BU_DTCT'])
    target_accounts = getattr(settings, 'TARGET_RECEIVABLE_ACCOUNTS', ['1311'])
    excluded_cust_groups = getattr(settings, 'EXCLUDED_CUSTOMER_GROUP_CODES', ['Internal'])

    bu_list_to_query = [bu_code] if bu_code else core_bus
    results = []

    for b_code in bu_list_to_query:
        if is_bu_code_excluded(b_code, exclude_bu_codes):
            logger.info(f"🚫 [collect_bu_manager_debt_data] Bỏ qua BU {b_code}: Nằm trong DEBT_REMINDER_EXCLUDE_BU_CODES.")
            continue

        bu = BusinessUnit.objects.filter(code=b_code).first()
        if not bu or is_bu_code_excluded(bu.code, exclude_bu_codes):
            continue

        mgr_info = get_bu_manager_info(bu)

        ageings = ReceivablesAgeing.objects.filter(
            reporting_period=period,
            account_code__in=target_accounts,
            customer__business_unit=bu
        ).exclude(
            customer__group__code__in=excluded_cust_groups
        ).select_related('customer', 'customer__assigned_employee')

        # 1. Gom theo Customer
        cust_agg = {}
        # 2. Gom theo Sales
        sales_agg = defaultdict(lambda: {
            'employee_code': '',
            'employee_name': '',
            'email': '',
            'total_debt': Decimal('0'),
            'due_total': Decimal('0'),
            'overdue_total': Decimal('0'),
            'customer_count': 0,
            'customers': []
        })

        for a in ageings:
            c = a.customer
            if not c:
                continue
            sales = c.assigned_employee
            s_code = sales.employee_code if sales else "UNASSIGNED"
            s_name = sales.full_name if sales else "Khách hàng tự do / Chưa gán Sales"
            s_email = sales.email if (sales and sales.email) else ""

            if c.code not in cust_agg:
                cust_agg[c.code] = {
                    'customer_code': c.code,
                    'customer_name': c.name,
                    'sales_code': s_code,
                    'sales_name': s_name,
                    'total_debt': Decimal('0'),
                    'due_total': Decimal('0'),
                    'overdue_total': Decimal('0'),
                    'overdue_0_14': Decimal('0'),
                    'overdue_15_30': Decimal('0'),
                    'overdue_31_plus': Decimal('0'),
                }

            cust_agg[c.code]['total_debt'] += a.total_debt or Decimal('0')
            cust_agg[c.code]['due_total'] += a.due_total or Decimal('0')
            cust_agg[c.code]['overdue_total'] += a.overdue_total or Decimal('0')
            cust_agg[c.code]['overdue_0_14'] += a.overdue_0_14 or Decimal('0')
            cust_agg[c.code]['overdue_15_30'] += a.overdue_15_30 or Decimal('0')

            overdue_31_plus = (
                (a.overdue_31_45 or Decimal('0')) +
                (a.overdue_46_60 or Decimal('0')) +
                (a.overdue_61_90 or Decimal('0')) +
                (a.overdue_91_120 or Decimal('0')) +
                (a.overdue_above_120 or Decimal('0'))
            )
            cust_agg[c.code]['overdue_31_plus'] += overdue_31_plus

        # Group aggregated customers by Sales
        for c_code, c_data in cust_agg.items():
            if c_data['total_debt'] <= 0:
                continue
            s_code = c_data['sales_code']
            sales_entry = sales_agg[s_code]
            sales_entry['employee_code'] = s_code
            sales_entry['employee_name'] = c_data['sales_name']
            sales_entry['total_debt'] += c_data['total_debt']
            sales_entry['due_total'] += c_data['due_total']
            sales_entry['overdue_total'] += c_data['overdue_total']
            sales_entry['customer_count'] += 1
            sales_entry['customers'].append(c_data)

        # BU Totals
        bu_total_debt = sum(s['total_debt'] for s in sales_agg.values())
        bu_due_total = sum(s['due_total'] for s in sales_agg.values())
        bu_overdue_total = sum(s['overdue_total'] for s in sales_agg.values())
        bu_overdue_rate = float(round(bu_overdue_total / bu_total_debt * 100, 2)) if bu_total_debt > 0 else 0.0

        # Sales list
        bu_sales_list = []
        for s_code, s_info in sales_agg.items():
            s_tot = s_info['total_debt']
            s_ovd = s_info['overdue_total']
            s_rate = float(round(s_ovd / s_tot * 100, 2)) if s_tot > 0 else 0.0
            bu_sales_list.append({
                'employee_code': s_info['employee_code'],
                'employee_name': s_info['employee_name'],
                'total_debt': s_tot,
                'due_total': s_info['due_total'],
                'overdue_total': s_ovd,
                'overdue_rate': s_rate,
                'customer_count': s_info['customer_count'],
            })
        bu_sales_list.sort(key=lambda x: x['total_debt'], reverse=True)

        # Top overdue customers in BU
        all_active_customers = [c for c in cust_agg.values() if c['total_debt'] > 0]
        # Sort by overdue descending, then by total_debt descending
        all_active_customers.sort(key=lambda x: (x['overdue_total'], x['total_debt']), reverse=True)
        top_overdue_customers = all_active_customers[:10]  # Top 10 khách hàng

        results.append({
            'bu_id': bu.id,
            'bu_code': bu.code,
            'bu_name': bu.name,
            'manager_name': mgr_info['name'],
            'manager_email': mgr_info['email'],
            'has_manager_email': bool(mgr_info['email'] and '@' in mgr_info['email']),
            'total_debt': bu_total_debt,
            'due_total': bu_due_total,
            'overdue_total': bu_overdue_total,
            'overdue_rate': bu_overdue_rate,
            'sales_count': len(bu_sales_list),
            'customer_count': len(all_active_customers),
            'sales_list': bu_sales_list,
            'top_overdue_customers': top_overdue_customers,
        })

    # Sắp xếp BU theo tổng nợ giảm dần
    results.sort(key=lambda x: x['total_debt'], reverse=True)
    return results


def get_frontend_base_url():
    """Lấy URL gốc Frontend chuẩn hóa, loại bỏ dấu / ở cuối"""
    url = getattr(settings, 'FRONTEND_URL', None) or 'https://report.haophuong.com'
    return str(url).rstrip('/')


def send_sales_debt_email(sales_data, period, dry_run=False, test_email=None, cc_emails=None):
    """
    Render và gửi email nhắc nợ chi tiết cho Nhân viên Sales
    """
    recipient_email = test_email if (dry_run and test_email) else sales_data.get('email')
    if not recipient_email or '@' not in recipient_email:
        logger.warning(f"⚠️ Không thể gửi mail cho Sales {sales_data.get('full_name')}: Thiếu email hợp lệ.")
        return False, "Thiếu email hợp lệ"

def send_sales_debt_email(sales_data, period, dry_run=False, test_email=None, override_email=None, cc_emails=None):
    """
    Render và gửi email thông báo danh sách khách hàng nợ cho từng Sales
    """
    recipient_email = override_email or test_email if (dry_run or override_email or test_email) else sales_data.get('email')
    if not recipient_email or '@' not in recipient_email:
        logger.warning(f"⚠️ Không thể gửi mail cho Sales {sales_data.get('full_name')} ({sales_data.get('employee_code')}): Thiếu email hợp lệ.")
        return False, "Thiếu email hợp lệ"

    period_display = format_period_display(period)
    frontend_base = get_frontend_base_url()
    primary_bu = sales_data.get('primary_bu_code', '')
    bu_param = f"&bu={primary_bu}" if primary_bu else ""
    dashboard_url = f"{frontend_base}/aging?period={period}{bu_param}&employee={sales_data.get('employee_code')}"

    base_subject = f"[Hạo Phương] 📋 Danh Sách Công Nợ Khách Hàng Phụ Trách — {period_display} — {sales_data.get('full_name')}"
    if override_email or test_email:
        subject = f"[TEST - {sales_data.get('full_name')}] {base_subject}"
    elif dry_run:
        subject = f"[TEST DRY-RUN] {base_subject}"
    else:
        subject = base_subject

    from_email = get_formatted_from_email(override_display_name="Hạo Phương - Quản Lý Công Nợ")

    context = {
        'sales': sales_data,
        'period': period,
        'period_display': period_display,
        'dashboard_url': dashboard_url,
        'dry_run': dry_run,
        'generation_time': datetime.now().strftime('%d/%m/%Y %H:%M:%S'),
    }

    html_content = render_to_string('emails/debt_reminder_sales.html', context)

    text_content = f"""
    Kính gửi {sales_data.get('full_name')} ({sales_data.get('employee_code')}),

    Hệ thống Báo cáo Quản trị Hạo Phương xin gửi thông báo chi tiết danh sách công nợ khách hàng do Anh/Chị phụ trách kỳ {period_display}:

    - Tổng nợ phải thu: {sales_data.get('total_debt', 0):,.0f} VNĐ
    - Nợ trong hạn: {sales_data.get('due_total', 0):,.0f} VNĐ
    - Nợ quá hạn: {sales_data.get('overdue_total', 0):,.0f} VNĐ ({sales_data.get('overdue_rate', 0):.1f}%)
    - Số lượng khách hàng nợ: {sales_data.get('customer_count', 0)} khách hàng

    Tra cứu chi tiết trên Dashboard: {dashboard_url}

    Trân trọng,
    Ban Quản Trị Hệ Thống Hạo Phương.
    """

    valid_cc = [e.strip() for e in (cc_emails or []) if e and isinstance(e, str) and '@' in e]
    msg = EmailMultiAlternatives(subject, text_content, from_email, [recipient_email], cc=valid_cc)
    msg.attach_alternative(html_content, "text/html")

    try:
        msg.send(fail_silently=False)
        logger.info(f"✅ Đã gửi email nhắc nợ cho Sales: {sales_data.get('full_name')} ({recipient_email}) [CC: {valid_cc}]")
        return True, "Gửi thành công"
    except Exception as e:
        logger.error(f"❌ Thất bại khi gửi email cho Sales {sales_data.get('full_name')} ({recipient_email}): {e}")
        return False, str(e)


def send_bu_manager_debt_email(bu_data, period, dry_run=False, test_email=None, override_email=None, cc_emails=None):
    """
    Render và gửi email báo cáo tổng hợp công nợ cho Trưởng BU
    """
    recipient_email = override_email or test_email if (dry_run or override_email or test_email) else bu_data.get('manager_email')
    if not recipient_email or '@' not in recipient_email:
        logger.warning(f"⚠️ Không thể gửi mail cho Trưởng BU {bu_data.get('manager_name')} ({bu_data.get('bu_name')}): Thiếu email hợp lệ.")
        return False, "Thiếu email hợp lệ"

    period_display = format_period_display(period)
    frontend_base = get_frontend_base_url()
    dashboard_url = f"{frontend_base}/aging?period={period}&bu={bu_data.get('bu_code')}"

    base_subject = f"[Hạo Phương] 📊 Báo Cáo Tổng Hợp Công Nợ Khối {bu_data.get('bu_name')} — {period_display} — Kính gửi {bu_data.get('manager_name')}"
    if override_email or test_email:
        subject = f"[TEST - {bu_data.get('bu_name')}] {base_subject}"
    elif dry_run:
        subject = f"[TEST DRY-RUN] {base_subject}"
    else:
        subject = base_subject

    from_email = get_formatted_from_email(override_display_name="Hạo Phương - Báo Cáo Điều Hành")

    context = {
        'bu': bu_data,
        'period': period,
        'period_display': period_display,
        'dashboard_url': dashboard_url,
        'dry_run': dry_run,
        'generation_time': datetime.now().strftime('%d/%m/%Y %H:%M:%S'),
    }

    html_content = render_to_string('emails/debt_summary_manager.html', context)

    text_content = f"""
    Kính gửi {bu_data.get('manager_name')} - Trưởng Khối {bu_data.get('bu_name')},

    Hệ thống Báo cáo Quản trị Hạo Phương xin gửi báo cáo tổng hợp tình hình công nợ của Khối kỳ {period_display}:

    - Tổng nợ toàn Khối: {bu_data.get('total_debt', 0):,.0f} VNĐ
    - Nợ trong hạn: {bu_data.get('due_total', 0):,.0f} VNĐ
    - Nợ quá hạn: {bu_data.get('overdue_total', 0):,.0f} VNĐ ({bu_data.get('overdue_rate', 0):.1f}%)
    - Số nhân viên quản lý nợ: {bu_data.get('sales_count', 0)} nhân viên

    Tra cứu chi tiết trên Dashboard: {dashboard_url}

    Trân trọng,
    Ban Quản Trị Hệ Thống Hạo Phương.
    """

    valid_cc = [e.strip() for e in (cc_emails or []) if e and isinstance(e, str) and '@' in e]
    msg = EmailMultiAlternatives(subject, text_content, from_email, [recipient_email], cc=valid_cc)
    msg.attach_alternative(html_content, "text/html")

    try:
        msg.send(fail_silently=False)
        logger.info(f"✅ Đã gửi email tổng hợp công nợ cho Trưởng BU: {bu_data.get('manager_name')} ({recipient_email}) [CC: {valid_cc}]")
        return True, "Gửi thành công"
    except Exception as e:
        logger.error(f"❌ Thất bại khi gửi email cho Trưởng BU {bu_data.get('manager_name')} ({recipient_email}): {e}")
        return False, str(e)


def send_debt_reminders_process(period=None, dry_run=True, test_email=None, override_email=None, bu_code=None, recipient_type=None, cc_emails=None):
    """
    Tiến trình điều phối chính gửi Email Nhắc Nợ Phân Cấp:
    - period: YYYY-MM (Mặc định kỳ mới nhất)
    - dry_run: True/False (Mặc định True để an toàn)
    - test_email / override_email: Email nhận thử nghiệm chuyển hướng
    - bu_code: Chỉ định 1 BU (Tùy chọn)
    - recipient_type: 'ALL', 'SALES', 'MANAGERS' (Mặc định lấy từ settings.DEBT_REMINDER_RECIPIENT_TYPE)
    - cc_emails: Danh sách CC (nếu None sẽ lấy từ settings.DEBT_REMINDER_CC_EMAILS)
    """
    period = get_target_period(period)
    default_rec_type = getattr(settings, 'DEBT_REMINDER_RECIPIENT_TYPE', 'MANAGERS')
    recipient_type = (recipient_type or default_rec_type or 'MANAGERS').upper()
    effective_override = override_email or test_email

    if cc_emails is None:
        cc_emails = getattr(settings, 'DEBT_REMINDER_CC_EMAILS', [])
    exclude_emails_raw = getattr(settings, 'DEBT_REMINDER_EXCLUDE_EMAILS', [])
    exclude_emails = set(e.strip().lower() for e in exclude_emails_raw if e and isinstance(e, str) and e.strip())
    exclude_bu_codes = getattr(settings, 'DEBT_REMINDER_EXCLUDE_BU_CODES', ['ĐTCT', 'BU_DTCT'])

    logs = []
    mode_str = f"CHUYỂN HƯỚNG TEST ({effective_override})" if effective_override else ('DRY-RUN' if dry_run else 'THỰC TẾ (LIVE)')
    logs.append(f"🚀 Bắt đầu tiến trình gửi email nhắc nợ cho kỳ {period} [Chế độ: {mode_str}] [Đối tượng: {recipient_type}]")
    if exclude_bu_codes:
        logs.append(f"🏢 BU loại trừ không gửi: {', '.join(exclude_bu_codes)}")
    if cc_emails:
        logs.append(f"👥 Danh sách CC: {', '.join(cc_emails)}")
    if exclude_emails:
        logs.append(f"🚫 Email Blacklist: {', '.join(exclude_emails)}")
    if effective_override:
        logs.append(f"📧 Email nhận test chỉ định: {effective_override}")

    sales_success = 0
    sales_fail = 0
    sales_skipped = 0
    bu_success = 0
    bu_fail = 0
    bu_skipped = 0

    sales_results = []
    bu_results = []

    # -------------------------------------------------------------
    # 1. GỬI EMAIL CHO SALES
    # -------------------------------------------------------------
    if recipient_type in ['ALL', 'SALES']:
        sales_list = collect_sales_debt_data(period=period, bu_code=bu_code)
        logs.append(f"📋 Tìm thấy {len(sales_list)} nhân viên Sales có phát sinh công nợ.")

        if effective_override:
            # Gửi chuyển hướng test về effective_override
            target_sales = sales_list if bu_code else sales_list[:3]  # Nếu không truyền bu_code thì test 3 sales đại diện
            for s in target_sales:
                logs.append(f"🧪 [TEST OVERRIDE] Gửi email Sales ({s['full_name']}) về {effective_override}...")
                ok, msg_text = send_sales_debt_email(s, period=period, dry_run=True, override_email=effective_override, cc_emails=cc_emails)
                if ok:
                    sales_success += 1
                else:
                    sales_fail += 1
                sales_results.append({
                    'employee_code': s['employee_code'],
                    'full_name': s['full_name'],
                    'target_email': effective_override,
                    'status': 'SUCCESS' if ok else 'FAILED',
                    'message': msg_text
                })
        elif not dry_run:
            # Gửi thực tế cho toàn bộ Sales
            for s in sales_list:
                email = (s.get('email') or '').strip()
                if not email:
                    logs.append(f"⚠️ Bỏ qua Sales {s['full_name']} ({s['employee_code']}): Không có email.")
                    sales_skipped += 1
                    sales_results.append({
                        'employee_code': s['employee_code'],
                        'full_name': s['full_name'],
                        'target_email': 'N/A',
                        'status': 'SKIPPED',
                        'message': 'Không có email'
                    })
                    continue

                if email.lower() in exclude_emails:
                    logs.append(f"🚫 Bỏ qua Sales {s['full_name']} ({email}): Nằm trong Blacklist.")
                    sales_skipped += 1
                    sales_results.append({
                        'employee_code': s['employee_code'],
                        'full_name': s['full_name'],
                        'target_email': email,
                        'status': 'SKIPPED',
                        'message': 'Email nằm trong Blacklist'
                    })
                    continue

                ok, msg_text = send_sales_debt_email(s, period=period, dry_run=False, cc_emails=cc_emails)
                if ok:
                    sales_success += 1
                else:
                    sales_fail += 1
                sales_results.append({
                    'employee_code': s['employee_code'],
                    'full_name': s['full_name'],
                    'target_email': email,
                    'status': 'SUCCESS' if ok else 'FAILED',
                    'message': msg_text
                })
        else:
            # dry_run = True và không có test_email: chỉ thống kê
            logs.append(f"ℹ️ [DRY-RUN] Không có test_email được chỉ định. Đã thống kê {len(sales_list)} Sales.")
            for s in sales_list:
                sales_results.append({
                    'employee_code': s['employee_code'],
                    'full_name': s['full_name'],
                    'target_email': s.get('email', 'N/A'),
                    'status': 'SIMULATED',
                    'total_debt': float(s['total_debt']),
                    'overdue_total': float(s['overdue_total'])
                })

    # -------------------------------------------------------------
    # 2. GỬI EMAIL CHO TRƯỞNG BU
    # -------------------------------------------------------------
    if recipient_type in ['ALL', 'MANAGERS']:
        bu_list = collect_bu_manager_debt_data(period=period, bu_code=bu_code)
        logs.append(f"📊 Tìm thấy {len(bu_list)} Trưởng BU trong phạm vi quản trị.")

        if effective_override:
            # Gửi chuyển hướng test về effective_override cho tất cả BU được chọn
            for b in bu_list:
                logs.append(f"🧪 [TEST OVERRIDE] Gửi email Trưởng BU ({b['manager_name']} - {b['bu_name']}) về {effective_override}...")
                ok, msg_text = send_bu_manager_debt_email(b, period=period, dry_run=True, override_email=effective_override, cc_emails=cc_emails)
                if ok:
                    bu_success += 1
                else:
                    bu_fail += 1
                bu_results.append({
                    'bu_code': b['bu_code'],
                    'bu_name': b['bu_name'],
                    'manager_name': b['manager_name'],
                    'target_email': effective_override,
                    'status': 'SUCCESS' if ok else 'FAILED',
                    'message': msg_text
                })
        elif not dry_run:
            # Gửi thực tế cho toàn bộ Trưởng BU
            for b in bu_list:
                manager_email = (b.get('manager_email') or '').strip()
                if not manager_email:
                    logs.append(f"⚠️ Bỏ qua Trưởng BU {b['manager_name']} ({b['bu_code']}): Không có email.")
                    bu_skipped += 1
                    bu_results.append({
                        'bu_code': b['bu_code'],
                        'bu_name': b['bu_name'],
                        'manager_name': b['manager_name'],
                        'target_email': 'N/A',
                        'status': 'SKIPPED',
                        'message': 'Không có email'
                    })
                    continue

                if manager_email.lower() in exclude_emails:
                    logs.append(f"🚫 Bỏ qua Trưởng BU {b['manager_name']} ({manager_email}): Nằm trong Blacklist.")
                    bu_skipped += 1
                    bu_results.append({
                        'bu_code': b['bu_code'],
                        'bu_name': b['bu_name'],
                        'manager_name': b['manager_name'],
                        'target_email': manager_email,
                        'status': 'SKIPPED',
                        'message': 'Email nằm trong Blacklist'
                    })
                    continue

                ok, msg_text = send_bu_manager_debt_email(b, period=period, dry_run=False, cc_emails=cc_emails)
                if ok:
                    bu_success += 1
                else:
                    bu_fail += 1
                bu_results.append({
                    'bu_code': b['bu_code'],
                    'bu_name': b['bu_name'],
                    'manager_name': b['manager_name'],
                    'target_email': manager_email,
                    'status': 'SUCCESS' if ok else 'FAILED',
                    'message': msg_text
                })
        else:
            # dry_run = True và không có test_email: chỉ thống kê
            logs.append(f"ℹ️ [DRY-RUN] Không có test_email được chỉ định. Đã thống kê {len(bu_list)} Trưởng BU.")
            for b in bu_list:
                bu_results.append({
                    'bu_code': b['bu_code'],
                    'bu_name': b['bu_name'],
                    'manager_name': b['manager_name'],
                    'target_email': b.get('manager_email', 'N/A'),
                    'status': 'SIMULATED',
                    'total_debt': float(b['total_debt']),
                    'overdue_total': float(b['overdue_total'])
                })
    summary = {
        'period': period,
        'dry_run': dry_run,
        'test_email': effective_override,
        'override_email': effective_override,
        'recipient_type': recipient_type,
        'sales_summary': {
            'success': sales_success,
            'failed': sales_fail,
            'skipped': sales_skipped,
            'details': sales_results,
        },
        'bu_summary': {
            'success': bu_success,
            'failed': bu_fail,
            'skipped': bu_skipped,
            'details': bu_results,
        },
        'logs': logs,
    }

    logs.append(f"🏁 Hoàn tất tiến trình! Sales (Thành công: {sales_success}, Lỗi: {sales_fail}), BU (Thành công: {bu_success}, Lỗi: {bu_fail})")
    return summary


def collect_executive_dashboard_data(report_date=None, period=None):
    """
    Thu thập số liệu báo cáo điều hành Executive Dashboard:
    - Top 4 KPI Cards: Doanh thu MTD, Thu nợ MTD, Dư nợ phải thu (1311), Nợ quá hạn (1311).
    - Bảng tổng hợp hiệu suất 8 BU thương mại cốt lõi.
    """
    if report_date:
        if isinstance(report_date, str):
            t_date = datetime.strptime(report_date, '%Y-%m-%d').date()
        else:
            t_date = report_date
        period = t_date.strftime('%Y-%m')
        year, month = t_date.year, t_date.month
    else:
        period = get_target_period(period)
        year, month = map(int, period.split('-'))
        today = date.today()
        if year == today.year and month == today.month:
            t_date = today
        else:
            last_day = calendar.monthrange(year, month)[1]
            t_date = date(year, month, last_day)

def format_vnd_short(val):
    """
    Format số tiền dạng rút gọn thân thiện: ví dụ 37.41 tỷ, 500 tr, 100 k, 0 đ
    """
    if val is None:
        return "0 đ"
    v = float(val)
    abs_v = abs(v)
    if abs_v >= 1_000_000_000:
        return f"{v / 1_000_000_000:,.2f} tỷ"
    elif abs_v >= 1_000_000:
        return f"{v / 1_000_000:,.0f} tr"
    elif abs_v >= 1_000:
        return f"{v / 1_000:,.0f} k"
    return f"{v:,.0f} đ"


def get_previous_working_day(ref_date=None):
    """
    Tính ngày làm việc trước đó (T-1):
    - Nếu hôm nay là Thứ Hai (weekday == 0): Lùi 2 ngày về Thứ Bảy (chu kỳ làm việc T2-T7).
    - Nếu hôm nay là Chủ Nhật (weekday == 6): Lùi 1 ngày về Thứ Bảy.
    - Các ngày Thứ Ba đến Thứ Bảy: Lùi 1 ngày về hôm qua.
    """
    if ref_date is None:
        ref_date = date.today()
    if ref_date.weekday() == 0:
        return ref_date - timedelta(days=2)
    elif ref_date.weekday() == 6:
        return ref_date - timedelta(days=1)
    else:
        return ref_date - timedelta(days=1)


def collect_executive_dashboard_data(report_date=None, period=None):
    """
    Thu thập số liệu báo cáo điều hành Executive Dashboard chuẩn 100% theo Web Dashboard (~/dashboard):
    - KHỐI 1: Top 4 KPI Cards Tổng Quan (DT theo kỳ, Thu tiền theo kỳ, Tồn kho, Nợ ngân hàng)
    - KHỐI 2: 4 Cards Tỷ trọng Doanh thu Oversea & Nội địa (MTD, YTD)
    - KHỐI 3: Bảng Tổng Hợp Hiệu Suất 8 Đơn Vị Kinh Doanh (BU)
    """
    if report_date:
        if isinstance(report_date, str):
            t_date = datetime.strptime(report_date, '%Y-%m-%d').date()
        else:
            t_date = report_date
        period = t_date.strftime('%Y-%m')
        year, month = t_date.year, t_date.month
    else:
        today = date.today()
        prev_work_day = get_previous_working_day(today)
        if period:
            year, month = map(int, period.split('-'))
            if year == today.year and month == today.month:
                t_date = prev_work_day
            else:
                last_day = calendar.monthrange(year, month)[1]
                t_date = date(year, month, last_day)
        else:
            t_date = prev_work_day
            period = t_date.strftime('%Y-%m')
            year, month = t_date.year, t_date.month

    # 1. Lấy record TỔNG TOÀN CÔNG TY (business_unit__isnull=True) từ BUPerformance
    root_perf = BUPerformance.objects.filter(business_unit__isnull=True, month=month, year=year).first()

    # KHỐI 1: Top 4 KPI Cards
    # Card 1: Doanh thu theo kỳ
    rev_actual = float(root_perf.mtd_revenue_actual or 0) if root_perf else 0.0
    rev_plan = float(root_perf.mtd_revenue_plan or 0) if root_perf else 0.0
    rev_rate = round((rev_actual / rev_plan * 100), 2) if rev_plan > 0 else 0.0
    rev_gap = rev_actual - rev_plan

    # Card 2: Thu tiền theo kỳ
    col_actual = float(root_perf.mtd_collection_actual or 0) if root_perf else 0.0
    col_plan = float(root_perf.mtd_collection_plan or 0) if root_perf else 0.0
    col_rate = round((col_actual / col_plan * 100), 2) if col_plan > 0 else 0.0
    col_gap = col_actual - col_plan

    # Card 3: Tồn kho
    inv_actual = float(root_perf.inventory_value_actual or 0) if root_perf else 0.0
    inv_plan = float(root_perf.inventory_value_plan or 0) if root_perf else 0.0
    inv_rate = round((inv_actual / inv_plan * 100), 2) if inv_plan > 0 else 0.0
    inv_gap = inv_actual - inv_plan

    # Card 4: Nợ ngân hàng
    debt_actual = float(root_perf.bank_debt_actual or 0) if root_perf else 0.0
    debt_plan = float(root_perf.bank_debt_plan or 0) if root_perf else 0.0
    debt_rate = round((debt_actual / debt_plan * 100), 2) if debt_plan > 0 else 0.0
    debt_gap = debt_actual - debt_plan

    # KHỐI 2: Doanh thu Oversea (MTD & YTD)
    mtd_ovs = float(root_perf.mtd_revenue_oversea_actual or 0) if root_perf else 0.0
    mtd_ex_ovs = float(root_perf.mtd_revenue_exclude_oversea_actual or 0) if root_perf else 0.0
    mtd_base = mtd_ovs + mtd_ex_ovs
    mtd_ovs_rate = round((mtd_ovs / mtd_base * 100), 1) if mtd_base > 0 else 0.0
    mtd_ex_ovs_rate = round((mtd_ex_ovs / mtd_base * 100), 1) if mtd_base > 0 else 0.0

    ytd_ovs = float(root_perf.ytd_revenue_oversea_actual or 0) if root_perf else 0.0
    ytd_ex_ovs = float(root_perf.ytd_revenue_exclude_oversea_actual or 0) if root_perf else 0.0
    ytd_base = ytd_ovs + ytd_ex_ovs
    ytd_ovs_rate = round((ytd_ovs / ytd_base * 100), 1) if ytd_base > 0 else 0.0
    ytd_ex_ovs_rate = round((ytd_ex_ovs / ytd_base * 100), 1) if ytd_base > 0 else 0.0

    top_kpi_cards = [
        {
            'key': 'revenue',
            'title': 'DT THEO KỲ',
            'actual_display': format_vnd_short(rev_actual),
            'plan_display': format_vnd_short(rev_plan),
            'actual_raw': rev_actual,
            'plan_raw': rev_plan,
            'rate': rev_rate,
            'progress_bar': min(rev_rate, 100.0),
            'gap_display': ('+' if rev_gap > 0 else '') + format_vnd_short(rev_gap),
            'gap_raw': rev_gap,
            'is_negative': rev_gap < 0,
            'theme_color': '#2563eb',
            'bg_color': '#eff6ff',
            'border_color': '#bfdbfe',
        },
        {
            'key': 'collection',
            'title': 'THU TIỀN THEO KỲ',
            'actual_display': format_vnd_short(col_actual),
            'plan_display': format_vnd_short(col_plan),
            'actual_raw': col_actual,
            'plan_raw': col_plan,
            'rate': col_rate,
            'progress_bar': min(col_rate, 100.0),
            'gap_display': ('+' if col_gap > 0 else '') + format_vnd_short(col_gap),
            'gap_raw': col_gap,
            'is_negative': col_gap < 0,
            'theme_color': '#16a34a',
            'bg_color': '#f0fdf4',
            'border_color': '#bbf7d0',
        },
        {
            'key': 'inventory',
            'title': 'TỒN KHO',
            'actual_display': format_vnd_short(inv_actual),
            'plan_display': f"Ngưỡng {format_vnd_short(inv_plan)}",
            'actual_raw': inv_actual,
            'plan_raw': inv_plan,
            'rate': inv_rate,
            'progress_bar': min(inv_rate, 100.0),
            'gap_display': ('+' if inv_gap > 0 else '') + format_vnd_short(inv_gap),
            'gap_raw': inv_gap,
            'is_warning': inv_gap > 0,
            'theme_color': '#d97706',
            'bg_color': '#fffbeb',
            'border_color': '#fde68a',
        },
        {
            'key': 'bank_debt',
            'title': 'NỢ NGÂN HÀNG',
            'actual_display': format_vnd_short(debt_actual),
            'plan_display': f"Ngưỡng {format_vnd_short(debt_plan)}",
            'actual_raw': debt_actual,
            'plan_raw': debt_plan,
            'rate': debt_rate,
            'progress_bar': min(debt_rate, 100.0),
            'gap_display': ('+' if debt_gap > 0 else '') + format_vnd_short(debt_gap),
            'gap_raw': debt_gap,
            'is_warning': debt_gap > 0,
            'theme_color': '#9333ea',
            'bg_color': '#faf5ff',
            'border_color': '#e9d5ff',
        },
    ]

    oversea_kpi_cards = [
        {
            'title': 'Doanh thu Oversea MTD (Thực tế)',
            'actual_display': format_vnd_short(mtd_ovs),
            'base_display': format_vnd_short(mtd_base),
            'share_rate': mtd_ovs_rate,
            'progress_bar': min(mtd_ovs_rate, 100.0),
            'theme_color': '#2563eb',
            'bg_color': '#eff6ff',
            'border_color': '#bfdbfe',
        },
        {
            'title': 'DT không gồm Oversea MTD (Thực tế)',
            'actual_display': format_vnd_short(mtd_ex_ovs),
            'base_display': format_vnd_short(mtd_base),
            'share_rate': mtd_ex_ovs_rate,
            'progress_bar': min(mtd_ex_ovs_rate, 100.0),
            'theme_color': '#0d9488',
            'bg_color': '#f0fdfa',
            'border_color': '#99f6e4',
        },
        {
            'title': 'Doanh thu Oversea YTD (Thực tế)',
            'actual_display': format_vnd_short(ytd_ovs),
            'base_display': format_vnd_short(ytd_base),
            'share_rate': ytd_ovs_rate,
            'progress_bar': min(ytd_ovs_rate, 100.0),
            'theme_color': '#2563eb',
            'bg_color': '#eff6ff',
            'border_color': '#bfdbfe',
        },
        {
            'title': 'DT không gồm Oversea YTD (Thực tế)',
            'actual_display': format_vnd_short(ytd_ex_ovs),
            'base_display': format_vnd_short(ytd_base),
            'share_rate': ytd_ex_ovs_rate,
            'progress_bar': min(ytd_ex_ovs_rate, 100.0),
            'theme_color': '#0d9488',
            'bg_color': '#f0fdfa',
            'border_color': '#99f6e4',
        },
    ]

    # KHỐI 3: Bảng 8 BU Thương mại
    target_rec_accounts = getattr(settings, 'TARGET_RECEIVABLE_ACCOUNTS', ['1311'])
    bus = BusinessUnit.objects.filter(is_main=True).order_by('code')

    bu_rows = []
    tot_bu_rev = 0.0
    tot_bu_rev_plan = 0.0
    tot_bu_col = 0.0
    tot_bu_col_plan = 0.0
    tot_bu_debt = 0.0
    tot_bu_ovd = 0.0

    for bu in bus:
        bu_ids = bu.get_all_descendant_ids()
        mgr_info = get_bu_manager_info(bu)
        mgr_name = mgr_info.get('name') or bu.manager or "—"

        b_perf = BUPerformance.objects.filter(business_unit=bu, month=month, year=year).first()
        b_rev_act = float(b_perf.mtd_revenue_actual or 0) if b_perf else 0.0
        b_rev_plan = float(b_perf.mtd_revenue_plan or 0) if b_perf else 0.0
        b_rev_rate = round((b_rev_act / b_rev_plan * 100), 1) if b_rev_plan > 0 else 0.0

        b_col_act = float(b_perf.mtd_collection_actual or 0) if b_perf else 0.0
        b_col_plan = float(b_perf.mtd_collection_plan or 0) if b_perf else 0.0
        b_col_rate = round((b_col_act / b_col_plan * 100), 1) if b_col_plan > 0 else 0.0

        rec_res = ReceivablesAgeing.objects.filter(
            reporting_period=period,
            account_code__in=target_rec_accounts,
            customer__business_unit_id__in=bu_ids
        ).aggregate(
            t=Sum('total_debt'),
            o=Sum('overdue_total')
        )
        b_t_debt = float(rec_res['t'] or 0)
        b_o_debt = float(rec_res['o'] or 0)
        b_ovd_rate = round((b_o_debt / b_t_debt * 100), 1) if b_t_debt > 0 else 0.0

        tot_bu_rev += b_rev_act
        tot_bu_rev_plan += b_rev_plan
        tot_bu_col += b_col_act
        tot_bu_col_plan += b_col_plan
        tot_bu_debt += b_t_debt
        tot_bu_ovd += b_o_debt

        bu_rows.append({
            'bu_code': bu.code,
            'bu_name': bu.name,
            'manager_name': mgr_name,
            'revenue_actual': b_rev_act,
            'revenue_plan': b_rev_plan,
            'revenue_rate': b_rev_rate,
            'collection_actual': b_col_act,
            'collection_plan': b_col_plan,
            'collection_rate': b_col_rate,
            'total_debt': b_t_debt,
            'overdue_debt': b_o_debt,
            'overdue_rate': b_ovd_rate,
        })

    # Sắp xếp 8 BU theo doanh thu thực tế giảm dần
    bu_rows.sort(key=lambda x: x['revenue_actual'], reverse=True)

    tot_bu_rev_rate = round((tot_bu_rev / tot_bu_rev_plan * 100), 1) if tot_bu_rev_plan > 0 else 0.0
    tot_bu_col_rate = round((tot_bu_col / tot_bu_col_plan * 100), 1) if tot_bu_col_plan > 0 else 0.0
    tot_bu_ovd_rate = round((tot_bu_ovd / tot_bu_debt * 100), 1) if tot_bu_debt > 0 else 0.0

    return {
        'period': period,
        'period_display': format_period_display(period),
        'report_date': t_date.strftime('%d/%m/%Y'),
        'top_kpis': top_kpi_cards,
        'oversea_kpis': oversea_kpi_cards,
        'bu_rows': bu_rows,
        'total_summary': {
            'revenue_actual': tot_bu_rev,
            'revenue_plan': tot_bu_rev_plan,
            'revenue_rate': tot_bu_rev_rate,
            'collection_actual': tot_bu_col,
            'collection_plan': tot_bu_col_plan,
            'collection_rate': tot_bu_col_rate,
            'total_debt': tot_bu_debt,
            'overdue_debt': tot_bu_ovd,
            'overdue_rate': tot_bu_ovd_rate,
        },
        'generation_time': datetime.now().strftime('%d/%m/%Y %H:%M:%S'),
        'dashboard_url': f"{get_frontend_base_url()}/dashboard?period={period}",
    }


def send_executive_dashboard_email(to_email, cc_emails=None, report_date=None, period=None, dry_run=False):
    """
    Render và gửi email Báo Cáo Điều Hành Tổng Quan (Executive Dashboard) chuẩn Web Dashboard
    """
    if not to_email or '@' not in to_email:
        return False, "Địa chỉ email người nhận không hợp lệ"

    context = collect_executive_dashboard_data(report_date=report_date, period=period)
    period_display = context['period_display']
    report_date_str = context['report_date']

    subject = f"[Hạo Phương] 📊 Báo Cáo Điều Hành Doanh Thu & Công Nợ — {period_display} (Chốt ngày {report_date_str})"
    if dry_run:
        subject = f"[TEST DRY-RUN] {subject}"

    from_email = get_formatted_from_email(override_display_name="Hạo Phương - Executive Dashboard")
    html_content = render_to_string('emails/executive_dashboard_summary.html', context)

    top_kpis = {k['key']: k for k in context['top_kpis']}
    text_content = f"""
    Kính gửi Ban Lãnh Đạo & Quý Trưởng Khối Kinh Doanh,

    Hệ thống Báo cáo Quản trị Hạo Phương xin gửi báo cáo điều hành tổng quan kỳ {period_display} (Chốt ngày {report_date_str}):

    1. TỔNG QUAN KẾT QUẢ KINH DOANH:
    - DT theo kỳ: {top_kpis.get('revenue', {}).get('actual_display')} / {top_kpis.get('revenue', {}).get('plan_display')} (Đạt {top_kpis.get('revenue', {}).get('rate')}%, lệch {top_kpis.get('revenue', {}).get('gap_display')})
    - Thu tiền theo kỳ: {top_kpis.get('collection', {}).get('actual_display')} / {top_kpis.get('collection', {}).get('plan_display')} (Đạt {top_kpis.get('collection', {}).get('rate')}%, lệch {top_kpis.get('collection', {}).get('gap_display')})
    - Tồn kho: {top_kpis.get('inventory', {}).get('actual_display')} / {top_kpis.get('inventory', {}).get('plan_display')} ({top_kpis.get('inventory', {}).get('rate')}%)
    - Nợ ngân hàng: {top_kpis.get('bank_debt', {}).get('actual_display')} / {top_kpis.get('bank_debt', {}).get('plan_display')} ({top_kpis.get('bank_debt', {}).get('rate')}%)

    2. TỶ TRỌNG DOANH THU OVERSEA:
    - Oversea MTD: {context['oversea_kpis'][0]['actual_display']} / {context['oversea_kpis'][0]['base_display']} ({context['oversea_kpis'][0]['share_rate']}%)
    - Không gồm Oversea MTD: {context['oversea_kpis'][1]['actual_display']} / {context['oversea_kpis'][1]['base_display']} ({context['oversea_kpis'][1]['share_rate']}%)
    - Oversea YTD: {context['oversea_kpis'][2]['actual_display']} / {context['oversea_kpis'][2]['base_display']} ({context['oversea_kpis'][2]['share_rate']}%)
    - Không gồm Oversea YTD: {context['oversea_kpis'][3]['actual_display']} / {context['oversea_kpis'][3]['base_display']} ({context['oversea_kpis'][3]['share_rate']}%)

    Tra cứu chi tiết trực tuyến: {context['dashboard_url']}

    Trân trọng,
    Ban Quản Trị Hệ Thống Hạo Phương.
    """

    valid_cc = [e.strip() for e in (cc_emails or []) if e and isinstance(e, str) and '@' in e]
    msg = EmailMultiAlternatives(subject, text_content, from_email, [to_email.strip()], cc=valid_cc)
    msg.attach_alternative(html_content, "text/html")

    try:
        msg.send(fail_silently=False)
        logger.info(f"✅ Đã gửi email Executive Dashboard đến: {to_email} (CC: {valid_cc})")
        return True, "Gửi email thành công"
    except Exception as e:
        logger.error(f"❌ Thất bại khi gửi email Executive Dashboard đến {to_email}: {e}")
        return False, str(e)
