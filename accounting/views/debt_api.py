import logging
from decimal import Decimal
from datetime import datetime
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
        'BU_SAB': 'TRẦN HỒNG QUÂN',
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

        # 1. Query danh sách 8 BU Kinh Doanh Cốt Lõi (is_main=True và các BU con trực thuộc)
        target_accounts = getattr(settings, 'TARGET_RECEIVABLE_ACCOUNTS', ['1311'])
        bus = BusinessUnit.objects.filter(is_main=True).order_by('code')
        if not bus.exists():
            bus = BusinessUnit.objects.all().order_by('code')

        bus_data = []
        calc_total_debt = Decimal('0')
        calc_total_due = Decimal('0')
        calc_total_overdue = Decimal('0')

        for bu in bus:
            bu_ids = bu.get_all_descendant_ids()
            res = ReceivablesAgeing.objects.filter(
                reporting_period=period,
                account_code__in=target_accounts,
                customer__business_unit_id__in=bu_ids
            ).aggregate(
                t=Sum('total_debt'),
                o=Sum('overdue_total'),
            )
            # Fallback nếu chưa phân tách theo TK 1311
            if res['t'] is None and res['o'] is None:
                res = ReceivablesAgeing.objects.filter(
                    reporting_period=period,
                    customer__business_unit_id__in=bu_ids
                ).aggregate(
                    t=Sum('total_debt'),
                    o=Sum('overdue_total'),
                )

            tot = res['t'] or Decimal('0')
            ovd = res['o'] or Decimal('0')
            due = tot - ovd if tot >= ovd else Decimal('0')
            rate = float(round(ovd / tot * 100, 2)) if tot > 0 else 0.0

            calc_total_debt += tot
            calc_total_due += due
            calc_total_overdue += ovd

            # Nếu không bật include_all, chỉ lấy các BU có phát sinh nợ quá hạn hoặc tổng nợ > 0
            if not include_all and (ovd <= 0 and tot <= 0):
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
                "performance_id": bu.id
            })

        # Sắp xếp các BU theo tổng nợ giảm dần
        bus_data.sort(key=lambda x: x["receivable_total"], reverse=True)

        g_rate = float(round(calc_total_overdue / calc_total_debt * 100, 2)) if calc_total_debt > 0 else 0.0

        response_payload = {
            "period": period,
            "global_summary": {
                "receivable_total": calc_total_debt,
                "due_total": calc_total_due,
                "overdue_total": calc_total_overdue,
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

        # 2. Cấp 1: Thông tin BU & Tổng Nợ BU từ ReceivablesAgeing
        bu_ids = bu.get_all_descendant_ids()
        target_rec_accounts = getattr(settings, 'TARGET_RECEIVABLE_ACCOUNTS', ['1311'])
        excluded_cust_groups = getattr(settings, 'EXCLUDED_CUSTOMER_GROUP_CODES', ['Internal'])

        res_bu = ReceivablesAgeing.objects.filter(
            reporting_period=period,
            account_code__in=target_rec_accounts,
            customer__business_unit_id__in=bu_ids
        ).aggregate(
            t=Sum('total_debt'),
            o=Sum('overdue_total'),
        )
        if res_bu['t'] is None and res_bu['o'] is None:
            res_bu = ReceivablesAgeing.objects.filter(
                reporting_period=period,
                customer__business_unit_id__in=bu_ids
            ).aggregate(
                t=Sum('total_debt'),
                o=Sum('overdue_total'),
            )

        tot_bu_debt = res_bu['t'] or Decimal('0')
        ovd_bu_debt = res_bu['o'] or Decimal('0')
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
        ageing_filter = Q(reporting_period=period, customer__business_unit_id__in=bu_ids)
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


class OverdueCustomersAPIView(views.APIView):
    """
    API: Danh sách chi tiết Khách Hàng Nợ Quá Hạn (Overdue Customers Detail)
    - Route: GET /api/reports/debt/overdue-customers/ hoặc /api/debt/overdue-customers/
    - Query Params:
        + date: YYYY-MM-DD (Mặc định: ngày hiện tại)
        + bu_code: Mã BU cần lọc (Tùy chọn, ví dụ: BU_ELEVATOR)
    - Output: Danh sách khách hàng có nợ quá hạn thật từ ReceivablesAgeing, phân loại nhóm tuổi nợ và tổng tiền khớp với Card KPI bên ngoài.
    """
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, *args, **kwargs):
        role_info = get_user_role_info(request.user) if request.user.is_authenticated else {}
        user_role = role_info.get('primary_role', 'VIEWER')
        assigned_bus = role_info.get('assigned_bus', [])
        managed_bus = role_info.get('managed_bus', [])

        date_str_raw = request.query_params.get('date')
        bu_code_filter = request.query_params.get('bu_code')

        date = timezone.now().date()
        if date_str_raw:
            parsed_date = None
            for fmt in ['%Y-%m-%d', '%d/%m/%Y', '%d-%m-%Y', '%Y/%m/%d']:
                try:
                    parsed_date = datetime.strptime(date_str_raw.strip(), fmt).date()
                    break
                except ValueError:
                    pass
            if parsed_date:
                date = parsed_date
            else:
                logger.warning(f"⚠️ [OverdueCustomersAPIView] Không thể parse date_str '{date_str_raw}', sử dụng ngày hiện tại.")

        date_str = date.strftime('%Y-%m-%d')
        req_period = date.strftime('%Y-%m')
        if not ReceivablesAgeing.objects.filter(reporting_period=req_period).exists():
            latest_rec_period = ReceivablesAgeing.objects.order_by('-reporting_period').values_list('reporting_period', flat=True).first()
            if latest_rec_period:
                req_period = latest_rec_period

        # Target account 1311
        qs = ReceivablesAgeing.objects.filter(
            reporting_period=req_period,
            account_code__startswith='1311',
            overdue_total__gt=0
        ).select_related('customer', 'customer__business_unit', 'customer__assigned_employee')

        # Fallback if no records with 1311 explicitly
        if not qs.exists():
            qs = ReceivablesAgeing.objects.filter(
                reporting_period=req_period,
                overdue_total__gt=0
            ).select_related('customer', 'customer__business_unit', 'customer__assigned_employee')

        # Filter by BU:
        # Nếu có bu_code_filter cụ thể (khác 'all'): Lọc BU đó và toàn bộ BU con
        if bu_code_filter and bu_code_filter.lower() != 'all':
            clean_bu = bu_code_filter.replace('BU_', '').strip().upper()
            matched_bu = BusinessUnit.objects.filter(
                Q(code__iexact=bu_code_filter) |
                Q(code__iexact=f"BU_{clean_bu}") |
                Q(code__iexact=clean_bu)
            ).first()
            if matched_bu:
                target_bu_ids = matched_bu.get_all_descendant_ids()
                qs = qs.filter(customer__business_unit_id__in=target_bu_ids)
            else:
                qs = qs.filter(
                    Q(customer__business_unit__code__iexact=bu_code_filter) |
                    Q(customer__business_unit__code__iexact=f"BU_{clean_bu}") |
                    Q(customer__business_unit__code__iexact=clean_bu)
                )
        else:
            # Mặc định (Tất cả BU): Chỉ lấy 8 BU thương mại cốt lõi (is_main=True), loại trừ các BU nội bộ / ngoài phạm vi như VHC_BOD
            core_bu_ids = []
            for bu in BusinessUnit.objects.filter(is_main=True):
                core_bu_ids.extend(bu.get_all_descendant_ids())
            qs = qs.filter(customer__business_unit_id__in=core_bu_ids)

        # RBAC Check
        if user_role not in ['BOD_ADMIN', 'BOD']:
            allowed_codes = set(assigned_bus + managed_bus)
            if allowed_codes:
                rbac_bu_ids = []
                for c in allowed_codes:
                    clean = c.replace('BU_', '').strip().upper()
                    b_obj = BusinessUnit.objects.filter(
                        Q(code__iexact=c) | Q(code__iexact=f"BU_{clean}") | Q(code__iexact=clean)
                    ).first()
                    if b_obj:
                        rbac_bu_ids.extend(b_obj.get_all_descendant_ids())
                if rbac_bu_ids:
                    qs = qs.filter(customer__business_unit_id__in=rbac_bu_ids)
                else:
                    qs = qs.none()
            else:
                qs = qs.none()

        # Gom nhóm theo Khách Hàng (Customer Aggregation) để tránh trùng lặp
        cust_map = {}
        for row in qs:
            c = row.customer
            c_key = c.id if c else f"ROW_{row.id}"
            c_code = c.code if c else f"KH_{row.customer_id}"
            c_name = c.name if c else f"Khách hàng {row.customer_id}"
            bu = c.business_unit if c else None
            emp = c.assigned_employee if c else None

            if c_key not in cust_map:
                cust_map[c_key] = {
                    "id": f"OVERDUE-{c_key}",
                    "customer_code": c_code,
                    "customer_name": c_name,
                    "bu_code": bu.code if bu else "UNKNOWN",
                    "bu_name": bu.name if bu else "Khác",
                    "overdue_amount": 0.0,
                    "total_debt": 0.0,
                    "undue_total": 0.0,
                    "sales_code": emp.employee_code if emp else "",
                    "sales_name": emp.full_name if emp else "Chưa phân công",
                    "overdue_0_14": 0.0,
                    "overdue_15_30": 0.0,
                    "overdue_31_60": 0.0,
                    "overdue_60_plus": 0.0,
                    "due_date": date_str,
                }

            entry = cust_map[c_key]
            entry["overdue_amount"] += float(row.overdue_total or 0)
            entry["total_debt"] += float(row.total_debt or 0)
            entry["undue_total"] += float(row.due_total or 0)
            entry["overdue_0_14"] += float(row.overdue_0_14 or 0)
            entry["overdue_15_30"] += float(row.overdue_15_30 or 0)
            entry["overdue_31_60"] += float((row.overdue_31_45 or 0) + (row.overdue_46_60 or 0))
            entry["overdue_60_plus"] += float(
                (row.overdue_61_90 or 0) + (row.overdue_91_120 or 0) + (row.overdue_above_120 or 0)
            )

        items = []
        total_overdue = 0.0

        for entry in sorted(cust_map.values(), key=lambda x: x["overdue_amount"], reverse=True):
            ovd_amt = entry["overdue_amount"]
            if ovd_amt <= 0:
                continue

            total_overdue += ovd_amt

            if entry["overdue_60_plus"] > 0:
                age_bucket = "Quá hạn sâu (> 60 ngày)"
                segment_key = "deep"
            elif entry["overdue_31_60"] > 0:
                age_bucket = "31-60 ngày"
                segment_key = "30days"
            elif entry["overdue_15_30"] > 0:
                age_bucket = "15-30 ngày"
                segment_key = "15days"
            else:
                age_bucket = "Trong tuần (1-14 ngày)"
                segment_key = "week"

            entry["age_bucket"] = age_bucket
            entry["segment_key"] = segment_key
            entry["note"] = f"Quá hạn MISA: {ovd_amt:,.0f} VND"
            items.append(entry)

        return Response({
            "date": date_str,
            "reporting_period": req_period,
            "total_overdue": total_overdue,
            "count": len(items),
            "customers": items
        })

