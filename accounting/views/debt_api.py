import logging
from decimal import Decimal
from collections import defaultdict
from django.db.models import Sum, Q
from django.conf import settings
from django.utils import timezone
from rest_framework import views, permissions, status
from rest_framework.response import Response

from accounting.models import (
    BusinessUnit, BUPerformance, ReceivablesAgeing, Customer, Employee, EmployeeAssignment
)
from accounting.serializers import (
    AllBUsDebtResponseSerializer, BUDebtSummarySerializer, DebtReminderRequestSerializer
)
from accounting.services.debt_mailer import send_debt_reminders_process
from accounting.services.user_provisioner import get_user_role_info
from accounting.tasks import send_debt_reminders_task

logger = logging.getLogger(__name__)


def get_bu_manager_name(bu):
    """Lấy tên Trưởng BU chuẩn hóa (Ưu tiên đọc từ cột bu.manager trong database)"""
    if not bu:
        return "N/A"
    if bu.manager:
        return bu.manager

    # Fallback mặc định cho các BU nếu chưa điền trong DB
    manager_name_map = {
        'BU_ELEVATOR': 'ĐÀO TIẾN DŨNG',
        'BU_IBIZ PREMIUM': 'HỒ TÔN NHẬT MINH',
        'BU_IBIZ VALUE': 'NGUYỄN NGỌC HUY PHONG',
        'BU_MANUFACTURING': 'HỒ XUÂN QUANG',
        'BU_AGRITECH': 'TRẦN DUY HIẾU',
        'BU_ECO': 'TRẦN DUY HIẾU',
        'BU_Agritech - Eco': 'TRẦN DUY HIẾU',
    }
    return manager_name_map.get(bu.code, "Chưa cấu hình")


class AllBUsDebtSummaryAPIView(views.APIView):
    """
    API 1: Tổng hợp Công nợ Tất cả Business Units (All BUs Summary)
    - Route: GET /api/debt/bus/
    - Query Params:
        + period: YYYY-MM (Mặc định: kỳ mới nhất hoặc 2026-08)
        + include_all: true/false hoặc all=true (Mặc định: false - Chỉ hiện các BU có nợ quá hạn > 0)
    - Output: Danh sách BU (mặc định lọc các BU có nợ quá hạn) và Tổng Toàn Công Ty (Global).
    """
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, *args, **kwargs):
        period = request.query_params.get('period')
        if not period:
            latest_ageing = ReceivablesAgeing.objects.order_by('-reporting_period').first()
            period = latest_ageing.reporting_period if latest_ageing else timezone.now().strftime('%Y-%m')

        include_all = (
            request.query_params.get('include_all', '').lower() in ['true', '1', 'yes'] or
            request.query_params.get('all', '').lower() in ['true', '1', 'yes']
        )

        try:
            year, month = map(int, period.split('-'))
        except (ValueError, AttributeError):
            return Response(
                {"error": f"Tham số 'period' không hợp lệ: '{period}'. Định dạng yêu cầu: YYYY-MM (ví dụ: 2026-08)"},
                status=status.HTTP_400_BAD_REQUEST
            )

        # 1. Query danh sách 6 BU Kinh Doanh Cốt Lõi (Loại trừ mã mẹ HPC, Global và các khối vận hành/loại trừ)
        excluded_bu_codes = getattr(settings, 'EXCLUDED_DEBT_BU_CODES', ['ĐTCT', 'Oversea', 'VHC_HR'])
        core_bu_codes = getattr(settings, 'CORE_COMMERCIAL_BU_CODES', [
            'BU_ELEVATOR', 'BU_IBIZ PREMIUM', 'BU_ECO', 'BU_MANUFACTURING', 'BU_AGRITECH', 'BU_IBIZ VALUE'
        ])
        perfs_qs = BUPerformance.objects.filter(
            month=month, year=year
        ).exclude(
            business_unit=None
        ).exclude(
            business_unit__code='HPC'
        ).exclude(
            business_unit__code__in=excluded_bu_codes
        )
        if core_bu_codes:
            perfs_qs = perfs_qs.filter(business_unit__code__in=core_bu_codes)

        perfs = perfs_qs.select_related('business_unit').order_by('-receivable_total')

        bus_data = []
        calc_total_debt = Decimal('0')
        calc_total_due = Decimal('0')
        calc_total_overdue = Decimal('0')

        for p in perfs:
            bu = p.business_unit
            tot = p.receivable_total or Decimal('0')
            ovd = p.receivable_overdue or Decimal('0')
            due = tot - ovd if tot >= ovd else Decimal('0')
            rate = float(round(ovd / tot * 100, 2)) if tot > 0 else 0.0

            calc_total_debt += tot
            calc_total_due += due
            calc_total_overdue += ovd

            # Nếu không bật include_all, chỉ lấy các BU có phát sinh nợ quá hạn hoặc tổng nợ > 0
            if not include_all and (ovd <= 0 or tot <= 0):
                continue

            bus_data.append({
                "id": bu.id,
                "code": bu.code,
                "name": bu.name,
                "manager_name": get_bu_manager_name(bu),
                "receivable_total": tot,
                "due_total": due,
                "overdue_total": ovd,
                "overdue_rate": rate,
                "performance_id": p.id
            })

        # 2. Query Global KPI Toàn Công Ty (Luôn tính trên toàn bộ 22 BU chuẩn xác 100%)
        global_perf = BUPerformance.objects.filter(month=month, year=year, business_unit=None).first()
        g_tot = global_perf.receivable_total if global_perf else calc_total_debt
        g_ovd = global_perf.receivable_overdue if global_perf else calc_total_overdue
        g_due = g_tot - g_ovd if g_tot >= g_ovd else Decimal('0')
        g_rate = float(round(g_ovd / g_tot * 100, 2)) if g_tot > 0 else 0.0

        response_payload = {
            "period": period,
            "global_summary": {
                "receivable_total": g_tot,
                "due_total": g_due,
                "overdue_total": g_ovd,
                "overdue_rate": g_rate,
                "bu_count": len(bus_data)
            },
            "bus": bus_data
        }

        serializer = AllBUsDebtResponseSerializer(response_payload)
        return Response(serializer.data, status=status.HTTP_200_OK)


class AgingMatrixAPIView(views.APIView):
    """
    API 2: Chi tiết Tuổi nợ 3 Cấp Độ (BU -> Key Accounts / Sales / Quản lý -> Khách hàng)
    - Route: GET /api/v1/accounting/debt/bus/<bu_code>/drilldown/
    - Query Params: period (YYYY-MM, mặc định: 2026-08)
    - Output: Cấp 1 (BU) -> Cấp 2 (Key Accounts / Sales / Quản lý) -> Cấp 3 (Khách hàng)
    """
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, bu_code, *args, **kwargs):
        user_info = get_user_role_info(request.user)
        user_role = user_info.get('primary_role', 'VIEWER')
        assigned_bus = user_info.get('assigned_bus', [])
        managed_bus = user_info.get('managed_bus', [])
        user_emp_code = user_info.get('employee_code')

        period = request.query_params.get('period')
        req_emp_code = (
            request.query_params.get('employee_code') or
            request.query_params.get('employee') or
            request.query_params.get('sales_code') or
            ''
        ).strip()

        if not period:
            latest_ageing = ReceivablesAgeing.objects.order_by('-reporting_period').first()
            period = latest_ageing.reporting_period if latest_ageing else timezone.now().strftime('%Y-%m')

        try:
            year, month = map(int, period.split('-'))
        except (ValueError, AttributeError):
            return Response(
                {"error": f"Tham số 'period' không hợp lệ: '{period}'. Định dạng yêu cầu: YYYY-MM"},
                status=status.HTTP_400_BAD_REQUEST
            )

        # 1. Tìm Business Unit theo mã code (Hỗ trợ linh hoạt cả mã gốc như ĐTCT, Oversea hoặc có tiền tố BU_)
        clean_bu_code = bu_code.strip()

        # SMART FALLBACK: Nếu người dùng không phải BOD_ADMIN mà yêu cầu xem 'HPC' / 'ALL' / 'GLOBAL', tự động chuyển hướng về BU đầu tiên được phân công
        if clean_bu_code.upper() in ['HPC', 'ALL', 'GLOBAL', ''] and user_role != 'BOD_ADMIN':
            if assigned_bus:
                clean_bu_code = assigned_bus[0]
            elif managed_bus:
                clean_bu_code = managed_bus[0]
            elif user_info.get('bu_code') and user_info.get('bu_code') != 'HPC':
                clean_bu_code = user_info.get('bu_code')

        bu = BusinessUnit.objects.filter(code__iexact=clean_bu_code).first()
        if not bu and clean_bu_code.upper().startswith('BU_'):
            unprefixed_code = clean_bu_code[3:].strip()
            bu = BusinessUnit.objects.filter(code__iexact=unprefixed_code).first()
        if not bu:
            bu = BusinessUnit.objects.filter(code__iexact=f"BU_{clean_bu_code}").first()

        if not bu:
            available_codes = list(BusinessUnit.objects.exclude(code='HPC').values_list('code', flat=True))
            return Response(
                {
                    "error": f"Không tìm thấy Business Unit có mã: '{bu_code}'.",
                    "available_bus": available_codes
                },
                status=status.HTTP_404_NOT_FOUND
            )

        # DEFENSE IN DEPTH: Kiểm tra quyền truy cập BU tầng Backend
        if user_role != 'BOD_ADMIN':
            is_bu_allowed = any(
                b.upper() == bu.code.upper() or
                b.upper() == clean_bu_code.upper() or
                f"BU_{b.upper()}" == bu.code.upper()
                for b in assigned_bus
            )
            if not is_bu_allowed:
                return Response(
                    {"error": f"Quyền truy cập bị từ chối. Bạn không có quyền xem dữ liệu của Business Unit '{bu.name}' ({bu.code})."},
                    status=status.HTTP_403_FORBIDDEN
                )

        # DEFENSE IN DEPTH: Kiểm tra quyền truy cập phạm vi nhân viên
        is_head_in_bu = (
            user_role == 'BOD_ADMIN' or
            any(b.upper() == bu.code.upper() or b.upper() == clean_bu_code.upper() for b in managed_bus) or
            (bu.manager and user_info.get('full_name') and bu.manager.lower() in user_info['full_name'].lower())
        )

        employee_code = req_emp_code
        if not is_head_in_bu:
            # Sales / Viewer chỉ được phép truy vấn dữ liệu của chính mình
            if user_emp_code:
                if req_emp_code and req_emp_code.lower() != user_emp_code.lower():
                    return Response(
                        {"error": "Quyền truy cập bị từ chối. Bạn chỉ có quyền xem dữ liệu khách hàng do chính mình phụ trách."},
                        status=status.HTTP_403_FORBIDDEN
                    )
                employee_code = user_emp_code

        # 2. Cấp 1: Thông tin BU & Tổng Nợ BU từ BUPerformance
        bu_perf = BUPerformance.objects.filter(business_unit=bu, month=month, year=year).first()
        tot_bu_debt = bu_perf.receivable_total if bu_perf else Decimal('0')
        ovd_bu_debt = bu_perf.receivable_overdue if bu_perf else Decimal('0')
        due_bu_debt = tot_bu_debt - ovd_bu_debt if tot_bu_debt >= ovd_bu_debt else Decimal('0')
        rate = float(round(ovd_bu_debt / tot_bu_debt * 100, 2)) if tot_bu_debt > 0 else 0.0

        tier_1_bu = {
            "id": bu.id,
            "code": bu.code,
            "name": bu.name,
            "manager_name": get_bu_manager_name(bu),
            "receivable_total": tot_bu_debt,
            "due_total": due_bu_debt,
            "overdue_total": ovd_bu_debt,
            "overdue_rate": rate
        }

        # 3. Cấp 2 & 3: Lọc chi tiết ReceivablesAgeing (Đồng bộ bộ lọc Tài khoản mục tiêu 1311 & loại trừ nhóm Internal)
        excluded_cust_groups = getattr(settings, 'EXCLUDED_CUSTOMER_GROUP_CODES', ['Internal'])
        target_rec_accounts = getattr(settings, 'TARGET_RECEIVABLE_ACCOUNTS', ['1311'])

        ageing_filter = Q(reporting_period=period, customer__business_unit=bu)
        if target_rec_accounts:
            ageing_filter &= Q(account_code__in=target_rec_accounts)
        if excluded_cust_groups:
            ageing_filter &= ~Q(customer__group__code__in=excluded_cust_groups)
        
        # Lọc theo nhân viên nếu không phải head
        if not is_head_in_bu and employee_code:
            ageing_filter &= Q(customer__assigned_employee__employee_code__iexact=employee_code)

        ageings = ReceivablesAgeing.objects.filter(ageing_filter).select_related(
            'customer', 'customer__assigned_employee'
        )

        # Aggregate per Customer
        cust_agg = {}
        for a in ageings:
            c = a.customer
            sales = c.assigned_employee
            s_code = sales.employee_code if sales else "UNASSIGNED"
            s_name = sales.full_name if sales else "Khách hàng tự do / Chưa gán Sales"

            if c.code not in cust_agg:
                cust_agg[c.code] = {
                    "customer_code": c.code,
                    "customer_name": c.name,
                    "sales_code": s_code,
                    "sales_name": s_name,
                    "no_due_limit": Decimal('0'),
                    "due_0_7": Decimal('0'),
                    "due_8_14": Decimal('0'),
                    "due_15_21": Decimal('0'),
                    "due_22_28": Decimal('0'),
                    "due_29_60": Decimal('0'),
                    "due_above_60": Decimal('0'),
                    "due_total": Decimal('0'),
                    "overdue_0_14": Decimal('0'),
                    "overdue_15_30": Decimal('0'),
                    "overdue_31_45": Decimal('0'),
                    "overdue_46_60": Decimal('0'),
                    "overdue_61_90": Decimal('0'),
                    "overdue_91_120": Decimal('0'),
                    "overdue_above_120": Decimal('0'),
                    "overdue_total": Decimal('0'),
                    "total_debt": Decimal('0')
                }

            cust_agg[c.code]["no_due_limit"] += a.no_due_limit or Decimal('0')
            cust_agg[c.code]["due_0_7"] += a.due_0_7 or Decimal('0')
            cust_agg[c.code]["due_8_14"] += a.due_8_14 or Decimal('0')
            cust_agg[c.code]["due_15_21"] += a.due_15_21 or Decimal('0')
            cust_agg[c.code]["due_22_28"] += a.due_22_28 or Decimal('0')
            cust_agg[c.code]["due_29_60"] += a.due_29_60 or Decimal('0')
            cust_agg[c.code]["due_above_60"] += a.due_above_60 or Decimal('0')
            cust_agg[c.code]["due_total"] += a.due_total or Decimal('0')

            cust_agg[c.code]["overdue_0_14"] += a.overdue_0_14 or Decimal('0')
            cust_agg[c.code]["overdue_15_30"] += a.overdue_15_30 or Decimal('0')
            cust_agg[c.code]["overdue_31_45"] += a.overdue_31_45 or Decimal('0')
            cust_agg[c.code]["overdue_46_60"] += a.overdue_46_60 or Decimal('0')
            cust_agg[c.code]["overdue_61_90"] += a.overdue_61_90 or Decimal('0')
            cust_agg[c.code]["overdue_91_120"] += a.overdue_91_120 or Decimal('0')
            cust_agg[c.code]["overdue_above_120"] += a.overdue_above_120 or Decimal('0')
            cust_agg[c.code]["overdue_total"] += a.overdue_total or Decimal('0')

            cust_agg[c.code]["total_debt"] += a.total_debt or Decimal('0')

        # Group aggregated customers by Sales
        sales_map = defaultdict(lambda: {
            "employee_code": "",
            "employee_name": "",
            "title": "Nhân viên kinh doanh",
            "role": "SALES",
            "due_total": Decimal('0'),
            "overdue_total": Decimal('0'),
            "receivable_total": Decimal('0'),
            "customers": []
        })

        for c_code, c_data in cust_agg.items():
            s_code = c_data["sales_code"]
            sales_map[s_code]["employee_code"] = s_code
            sales_map[s_code]["employee_name"] = c_data["sales_name"]
            sales_map[s_code]["due_total"] += c_data["due_total"]
            sales_map[s_code]["overdue_total"] += c_data["overdue_total"]
            sales_map[s_code]["receivable_total"] += c_data["total_debt"]
            sales_map[s_code]["customers"].append({
                "customer_code": c_data["customer_code"],
                "customer_name": c_data["customer_name"],
                "no_due_limit": c_data["no_due_limit"],
                "due_0_7": c_data["due_0_7"],
                "due_8_14": c_data["due_8_14"],
                "due_15_21": c_data["due_15_21"],
                "due_22_28": c_data["due_22_28"],
                "due_29_60": c_data["due_29_60"],
                "due_above_60": c_data["due_above_60"],
                "due_total": c_data["due_total"],
                "overdue_0_14": c_data["overdue_0_14"],
                "overdue_15_30": c_data["overdue_15_30"],
                "overdue_31_45": c_data["overdue_31_45"],
                "overdue_46_60": c_data["overdue_46_60"],
                "overdue_61_90": c_data["overdue_61_90"],
                "overdue_91_120": c_data["overdue_91_120"],
                "overdue_above_120": c_data["overdue_above_120"],
                "overdue_total": c_data["overdue_total"],
                "total_debt": c_data["total_debt"]
            })

        # Fetch employee titles
        sales_codes = [code for code in sales_map.keys() if code != 'UNASSIGNED']
        employees = Employee.objects.filter(employee_code__in=sales_codes)
        for emp in employees:
            assignment = EmployeeAssignment.objects.filter(employee=emp).select_related('title').first()
            if assignment and assignment.title:
                t_name = assignment.title.title_name
                sales_map[emp.employee_code]["title"] = t_name
                if 'giám đốc' in t_name.lower():
                    sales_map[emp.employee_code]["role"] = "CCO"
                elif 'trưởng bu' in t_name.lower():
                    sales_map[emp.employee_code]["role"] = "BU_HEAD"
                elif 'trưởng bộ phận' in t_name.lower() or 'trưởng phòng' in t_name.lower():
                    sales_map[emp.employee_code]["role"] = "MANAGER"
                else:
                    sales_map[emp.employee_code]["role"] = "SALES"

        # Check selected employee
        has_employee_filter = bool(employee_code and employee_code.upper() != 'ALL')

        # Separate Key Accounts vs BU Teams
        key_accounts_summary = None
        if '2001' in sales_map and is_head_in_bu:
            cco_data = sales_map['2001']
            cco_data["role"] = "CCO"
            cco_data["title"] = "Giám đốc kinh doanh (CCO)"
            cco_data["customer_count"] = len(cco_data["customers"])
            cco_data["customers"].sort(key=lambda x: x["total_debt"], reverse=True)
            cco_data["is_selected"] = (has_employee_filter and (
                cco_data["employee_code"].lower() == employee_code.lower() or
                cco_data["employee_name"].lower() == employee_code.lower()
            ))
            key_accounts_summary = cco_data

        bu_teams = []
        for s_code, s_info in sales_map.items():
            if s_code == '2001' and is_head_in_bu:
                continue
            # Nếu người dùng không phải Trưởng BU này, chỉ giữ lại bản ghi của chính họ
            if not is_head_in_bu and user_emp_code and s_code.lower() != user_emp_code.lower():
                continue
            s_info["customer_count"] = len(s_info["customers"])
            s_info["customers"].sort(key=lambda x: x["total_debt"], reverse=True)
            s_info["is_selected"] = (has_employee_filter and (
                s_info["employee_code"].lower() == employee_code.lower() or
                s_info["employee_name"].lower() == employee_code.lower()
            ))
            bu_teams.append(s_info)

        # Sort BU Teams by debt descending
        bu_teams.sort(key=lambda x: x["receivable_total"], reverse=True)

        # Total reconciliation
        drilldown_total = sum(s["receivable_total"] for s in sales_map.values())
        discrepancy = tot_bu_debt - drilldown_total

        response_payload = {
            "period": period,
            "selected_employee_code": employee_code if has_employee_filter else None,
            "tier_1_bu": tier_1_bu,
            "tier_2_and_3": {
                "key_accounts_summary": key_accounts_summary,
                "bu_teams": bu_teams
            },
            "reconciliation": {
                "bu_total": tot_bu_debt,
                "drilldown_total": drilldown_total,
                "discrepancy": discrepancy,
                "is_matched": (discrepancy == 0)
            }
        }

        return Response(response_payload, status=status.HTTP_200_OK)


# Alias tương thích ngược 100%
BUDebt3TierDrilldownAPIView = AgingMatrixAPIView


class SendDebtRemindersAPIView(views.APIView):
    """
    API 3: Kích Hoạt Gửi Email Nhắc Nợ Phân Cấp (Debt Reminder Automation)
    - Route: POST /api/debt/notifications/send-reminders/
    - Request Body (JSON):
        {
            "period": "2026-08",                 // Tùy chọn (Mặc định: kỳ mới nhất)
            "dry_run": true,                     // Mặc định: true (Chế độ an toàn)
            "test_email": "test@haophuong.com",  // Tùy chọn (Nhận mail test khi dry_run=true)
            "bu_code": "BU_ELEVATOR",            // Tùy chọn (Giới hạn theo BU)
            "recipient_type": "ALL",             // 'ALL', 'SALES', 'MANAGERS'
            "send_async": false                  // true để chạy ngầm qua Celery
        }
    - Response: Thống kê chi tiết số mail đã gửi, trạng thái từng người nhận và nhật ký logs.
    """
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, *args, **kwargs):
        user_info = get_user_role_info(request.user)
        primary_role = user_info.get('primary_role', 'VIEWER')

        if primary_role not in ['BOD_ADMIN', 'BU_HEAD']:
            return Response(
                {"error": "Quyền truy cập bị từ chối. Chỉ có BOD_ADMIN hoặc BU_HEAD mới được phép kích hoạt gửi email nhắc nợ."},
                status=status.HTTP_403_FORBIDDEN
            )

        serializer = DebtReminderRequestSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(
                {"error": "Dữ liệu yêu cầu không hợp lệ", "details": serializer.errors},
                status=status.HTTP_400_BAD_REQUEST
            )

        validated_data = serializer.validated_data
        period = validated_data.get('period')
        dry_run = validated_data.get('dry_run', True)
        test_email = validated_data.get('test_email')
        bu_code = validated_data.get('bu_code')
        recipient_type = validated_data.get('recipient_type', 'ALL')
        send_async = validated_data.get('send_async', False)

        if primary_role == 'BU_HEAD':
            managed_bus = [b.upper() for b in user_info.get('managed_bus', [])]
            if bu_code:
                clean_bu = bu_code.strip().upper()
                if clean_bu not in managed_bus and f"BU_{clean_bu}" not in managed_bus:
                    return Response(
                        {"error": f"Quyền truy cập bị từ chối. Trưởng BU chỉ được phép gửi email nhắc nợ cho các BU thuộc quyền quản lý ({', '.join(user_info.get('managed_bus', []))})."},
                        status=status.HTTP_403_FORBIDDEN
                    )
            else:
                if len(managed_bus) == 1:
                    bu_code = user_info['managed_bus'][0]
                elif len(managed_bus) > 1:
                    return Response(
                        {"error": f"Vui lòng chỉ định tham số 'bu_code' trong danh sách BU bạn quản lý ({', '.join(user_info.get('managed_bus', []))})."},
                        status=status.HTTP_400_BAD_REQUEST
                    )

        logger.info(
            f"📨 [API Trigger] Gửi email nhắc nợ (period={period}, dry_run={dry_run}, "
            f"test_email={test_email}, bu_code={bu_code}, recipient_type={recipient_type}, async={send_async})"
        )

        if send_async:
            task = send_debt_reminders_task.delay(
                period=period,
                dry_run=dry_run,
                test_email=test_email,
                bu_code=bu_code,
                recipient_type=recipient_type
            )
            return Response(
                {
                    "message": "Đã tiếp nhận yêu cầu và đưa vào hàng đợi Celery thành công.",
                    "task_id": task.id,
                    "params": {
                        "period": period,
                        "dry_run": dry_run,
                        "test_email": test_email,
                        "bu_code": bu_code,
                        "recipient_type": recipient_type
                    }
                },
                status=status.HTTP_202_ACCEPTED
            )

        # Chạy đồng bộ (Sync)
        try:
            result = send_debt_reminders_process(
                period=period,
                dry_run=dry_run,
                test_email=test_email,
                bu_code=bu_code,
                recipient_type=recipient_type
            )
            return Response(result, status=status.HTTP_200_OK)
        except Exception as e:
            logger.error(f"❌ Lỗi trong quá trình xử lý gửi email nhắc nợ: {e}", exc_info=True)
            return Response(
                {"error": f"Lỗi hệ thống khi gửi email nhắc nợ: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

