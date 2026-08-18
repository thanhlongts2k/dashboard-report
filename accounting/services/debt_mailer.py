import logging
from decimal import Decimal
from collections import defaultdict
from datetime import datetime
from django.conf import settings
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.utils import timezone
from django.db.models import Sum, Q

from accounting.models import BusinessUnit, BUPerformance, ReceivablesAgeing, Customer, Employee, EmployeeAssignment
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


def collect_sales_debt_data(period=None, bu_code=None):
    """
    Gom dữ liệu công nợ chi tiết theo từng Nhân viên Sales (Cấp 1).
    - Bộ lọc: TK 1311 (TARGET_RECEIVABLE_ACCOUNTS), 6 BU kinh doanh cốt lõi (CORE_COMMERCIAL_BU_CODES), loại trừ Oversea.
    - Chỉ lấy khách hàng có total_debt > 0.
    """
    period = get_target_period(period)
    target_accounts = getattr(settings, 'TARGET_RECEIVABLE_ACCOUNTS', ['1311'])
    core_bus = getattr(settings, 'CORE_COMMERCIAL_BU_CODES', [
        'BU_ELEVATOR', 'BU_IBIZ PREMIUM', 'BU_ECO', 'BU_MANUFACTURING', 'BU_AGRITECH', 'BU_IBIZ VALUE', 'ĐTCT'
    ])
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
    target_accounts = getattr(settings, 'TARGET_RECEIVABLE_ACCOUNTS', ['1311'])
    excluded_cust_groups = getattr(settings, 'EXCLUDED_CUSTOMER_GROUP_CODES', ['Internal'])

    bu_list_to_query = [bu_code] if bu_code else core_bus
    results = []

    for b_code in bu_list_to_query:
        bu = BusinessUnit.objects.filter(code=b_code).first()
        if not bu:
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


def send_sales_debt_email(sales_data, period, dry_run=False, test_email=None):
    """
    Render và gửi email nhắc nợ chi tiết cho Nhân viên Sales
    """
    recipient_email = test_email if (dry_run and test_email) else sales_data.get('email')
    if not recipient_email or '@' not in recipient_email:
        logger.warning(f"⚠️ Không thể gửi mail cho Sales {sales_data.get('full_name')}: Thiếu email hợp lệ.")
        return False, "Thiếu email hợp lệ"

    period_display = format_period_display(period)
    frontend_base = get_frontend_base_url()
    primary_bu = sales_data.get('primary_bu_code', '')
    bu_param = f"&bu={primary_bu}" if primary_bu else ""
    dashboard_url = f"{frontend_base}/aging?period={period}{bu_param}&employee={sales_data.get('employee_code')}"

    subject = f"[Hạo Phương] 📋 Danh Sách Công Nợ Khách Hàng Phụ Trách — {period_display} — {sales_data.get('full_name')}"
    if dry_run:
        subject = f"[TEST DRY-RUN] {subject}"

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

    msg = EmailMultiAlternatives(subject, text_content, from_email, [recipient_email])
    msg.attach_alternative(html_content, "text/html")

    try:
        msg.send(fail_silently=False)
        logger.info(f"✅ Đã gửi email nhắc nợ cho Sales: {sales_data.get('full_name')} ({recipient_email})")
        return True, "Gửi thành công"
    except Exception as e:
        logger.error(f"❌ Thất bại khi gửi email cho Sales {sales_data.get('full_name')} ({recipient_email}): {e}")
        return False, str(e)


def send_bu_manager_debt_email(bu_data, period, dry_run=False, test_email=None):
    """
    Render và gửi email báo cáo tổng hợp công nợ cho Trưởng BU
    """
    recipient_email = test_email if (dry_run and test_email) else bu_data.get('manager_email')
    if not recipient_email or '@' not in recipient_email:
        logger.warning(f"⚠️ Không thể gửi mail cho Trưởng BU {bu_data.get('manager_name')} ({bu_data.get('bu_name')}): Thiếu email hợp lệ.")
        return False, "Thiếu email hợp lệ"

    period_display = format_period_display(period)
    frontend_base = get_frontend_base_url()
    dashboard_url = f"{frontend_base}/aging?period={period}&bu={bu_data.get('bu_code')}"


    subject = f"[Hạo Phương] 📊 Báo Cáo Tổng Hợp Công Nợ Khối {bu_data.get('bu_name')} — {period_display} — Kính gửi {bu_data.get('manager_name')}"
    if dry_run:
        subject = f"[TEST DRY-RUN] {subject}"

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

    msg = EmailMultiAlternatives(subject, text_content, from_email, [recipient_email])
    msg.attach_alternative(html_content, "text/html")

    try:
        msg.send(fail_silently=False)
        logger.info(f"✅ Đã gửi email tổng hợp công nợ cho Trưởng BU: {bu_data.get('manager_name')} ({recipient_email})")
        return True, "Gửi thành công"
    except Exception as e:
        logger.error(f"❌ Thất bại khi gửi email cho Trưởng BU {bu_data.get('manager_name')} ({recipient_email}): {e}")
        return False, str(e)


def send_debt_reminders_process(period=None, dry_run=True, test_email=None, bu_code=None, recipient_type='ALL'):
    """
    Tiến trình điều phối chính gửi Email Nhắc Nợ Phân Cấp:
    - period: YYYY-MM (Mặc định kỳ mới nhất)
    - dry_run: True/False (Mặc định True để an toàn)
    - test_email: Email nhận thử nghiệm khi dry_run=True
    - bu_code: Chỉ định 1 BU (Tùy chọn)
    - recipient_type: 'ALL', 'SALES', 'MANAGERS'
    """
    period = get_target_period(period)
    recipient_type = (recipient_type or 'ALL').upper()

    logs = []
    logs.append(f"🚀 Bắt đầu tiến trình gửi email nhắc nợ cho kỳ {period} [Chế độ: {'DRY-RUN' if dry_run else 'THỰC TẾ (LIVE)'}]")
    if test_email:
        logs.append(f"📧 Email nhận test chỉ định: {test_email}")

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

        # Nếu ở chế độ dry-run có test_email: chỉ gửi 1 email mẫu đại diện
        if dry_run and test_email:
            if sales_list:
                sample_sales = sales_list[0]
                logs.append(f"🧪 [DRY-RUN] Gửi email mẫu Sales ({sample_sales['full_name']}) về {test_email}...")
                ok, msg_text = send_sales_debt_email(sample_sales, period=period, dry_run=True, test_email=test_email)
                if ok:
                    sales_success += 1
                else:
                    sales_fail += 1
                sales_results.append({
                    'employee_code': sample_sales['employee_code'],
                    'full_name': sample_sales['full_name'],
                    'target_email': test_email,
                    'status': 'SUCCESS' if ok else 'FAILED',
                    'message': msg_text
                })
        elif not dry_run:
            # Gửi thực tế cho toàn bộ Sales
            for s in sales_list:
                if not s.get('email'):
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

                ok, msg_text = send_sales_debt_email(s, period=period, dry_run=False)
                if ok:
                    sales_success += 1
                else:
                    sales_fail += 1
                sales_results.append({
                    'employee_code': s['employee_code'],
                    'full_name': s['full_name'],
                    'target_email': s['email'],
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

        # Nếu ở chế độ dry-run có test_email: chỉ gửi 1 email mẫu đại diện
        if dry_run and test_email:
            if bu_list:
                sample_bu = bu_list[0]
                logs.append(f"🧪 [DRY-RUN] Gửi email mẫu Trưởng BU ({sample_bu['manager_name']} - {sample_bu['bu_name']}) về {test_email}...")
                ok, msg_text = send_bu_manager_debt_email(sample_bu, period=period, dry_run=True, test_email=test_email)
                if ok:
                    bu_success += 1
                else:
                    bu_fail += 1
                bu_results.append({
                    'bu_code': sample_bu['bu_code'],
                    'bu_name': sample_bu['bu_name'],
                    'manager_name': sample_bu['manager_name'],
                    'target_email': test_email,
                    'status': 'SUCCESS' if ok else 'FAILED',
                    'message': msg_text
                })
        elif not dry_run:
            # Gửi thực tế cho toàn bộ Trưởng BU
            for b in bu_list:
                if not b.get('manager_email'):
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

                ok, msg_text = send_bu_manager_debt_email(b, period=period, dry_run=False)
                if ok:
                    bu_success += 1
                else:
                    bu_fail += 1
                bu_results.append({
                    'bu_code': b['bu_code'],
                    'bu_name': b['bu_name'],
                    'manager_name': b['manager_name'],
                    'target_email': b['manager_email'],
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
        'test_email': test_email,
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
