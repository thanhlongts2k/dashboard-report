import time
import logging
import os
from datetime import datetime
from django.db.models import Q, Sum
from django.conf import settings
from django.core.mail import EmailMessage
from rest_framework import generics, viewsets, permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.parsers import MultiPartParser, FormParser, JSONParser
from django_filters.rest_framework import DjangoFilterBackend

from accounting.models import (
    BusinessUnit, AccountDetail, ReceivablesAgeing, 
    BUPerformance, BUPerformanceDaily, BUTargetPlan, ManualAdjustment
)
from accounting.serializers import (
    BUPerformanceSerializer, BUPerformanceDailySerializer,
    PerformanceUpdateSerializer, SendEmailSerializer,
    BUTargetPlanSerializer, ManualAdjustmentSerializer
)
from accounting.filters import BUPerformanceDailyFilter, BUPerformanceFilter
from accounting.tasks import update_single_bu_performance
from accounting.services import get_formatted_from_email

logger = logging.getLogger(__name__)

class BUReportAPIView(generics.ListAPIView):
    serializer_class = BUPerformanceSerializer
    filter_backends = [DjangoFilterBackend]
    filterset_class = BUPerformanceFilter

    def get_queryset(self):
        return BUPerformance.objects.all().select_related('business_unit').order_by('-year', '-month')

    def list(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())
        if queryset.exists():
            serializer = self.get_serializer(queryset, many=True)
            return Response(serializer.data)
        else:
            return Response(
                {"message": "Không tìm thấy dữ liệu phù hợp với bộ lọc."}, 
                status=status.HTTP_404_NOT_FOUND
            )


class BUPerformanceDailyListView(generics.ListAPIView):
    serializer_class = BUPerformanceDailySerializer
    filter_backends = [DjangoFilterBackend]
    filterset_class = BUPerformanceDailyFilter

    def get_queryset(self):
        queryset = BUPerformanceDaily.objects.all().select_related(
            'performance_month__business_unit'
        ).order_by('date')
        
        if 'bu_id' not in self.request.query_params:
            queryset = queryset.filter(performance_month__business_unit__isnull=True)
            
        return queryset


class BUPerformanceUpdateAPIView(APIView):
    def post(self, request):
        serializer = PerformanceUpdateSerializer(data=request.data)
        
        if serializer.is_valid():
            bu_id = serializer.validated_data.get('bu_id')
            month = serializer.validated_data.get('month')
            year = serializer.validated_data.get('year')
            target_date = serializer.validated_data.get('target_date')

            target_date_str = target_date.strftime('%Y-%m-%d') if target_date else None

            try:
                update_single_bu_performance.delay(
                    bu_id=bu_id, 
                    month=month, 
                    year=year, 
                    target_date_str=target_date_str
                )
                
                return Response({
                    "status": "success",
                    "message": "Tiến trình tính toán hiệu suất đã được xếp hàng đợi chạy ngầm (Celery)."
                }, status=status.HTTP_200_OK)

            except Exception as e:
                return Response({
                    "status": "error",
                    "message": str(e)
                }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


from django.db.models import Q, Sum, Max
from django.utils import timezone
from accounting.services.user_provisioner import get_user_role_info


class DashboardCollectionByBUAPIView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        role_info = get_user_role_info(request.user) if request.user.is_authenticated else {}
        user_role = role_info.get('primary_role', 'VIEWER')
        assigned_bus = role_info.get('assigned_bus', [])
        managed_bus = role_info.get('managed_bus', [])

        cash_cond = Q(account_number__startswith='111') | Q(account_number__startswith='112')
        offset_cond = Q(offset_account__startswith='1311')

        # 1. Xác định ngày phát sinh thu tiền gần nhất trong CSDL
        latest_ad_date = AccountDetail.objects.filter(cash_cond & offset_cond).aggregate(
            max_date=Max('posting_date')
        )['max_date']

        date_str = request.query_params.get('date')
        if not date_str:
            date = latest_ad_date or timezone.now().date()
            date_str = date.strftime('%Y-%m-%d')
        else:
            try:
                date = datetime.strptime(date_str, '%Y-%m-%d').date()
            except ValueError:
                return Response(
                    {"error": "Định dạng date không hợp lệ. Dùng YYYY-MM-DD."},
                    status=status.HTTP_400_BAD_REQUEST,
                )

        # 2. Xác định kỳ báo cáo phù hợp cho ReceivablesAgeing
        req_period = date.strftime('%Y-%m')
        if not ReceivablesAgeing.objects.filter(reporting_period=req_period).exists():
            latest_rec_period = ReceivablesAgeing.objects.order_by('-reporting_period').values_list('reporting_period', flat=True).first()
            if latest_rec_period:
                req_period = latest_rec_period

        rows = []
        sum_recv = sum_commit = sum_due = sum_term = sum_total = 0

        bu_qs = BusinessUnit.objects.filter(is_main=True)
        if not bu_qs.exists():
            roots = BusinessUnit.objects.filter(parent__isnull=True)
            if roots.count() == 1:
                bu_qs = BusinessUnit.objects.filter(parent=roots.first())
            else:
                bu_qs = BusinessUnit.objects.filter(parent__isnull=False)

        # 3. RBAC: Lọc danh sách BU theo quyền hạn của tài khoản
        if user_role not in ['BOD_ADMIN', 'BOD']:
            allowed_codes = set(assigned_bus + managed_bus)
            if allowed_codes:
                bu_qs = bu_qs.filter(
                    Q(code__in=allowed_codes) |
                    Q(code__in=[f"BU_{c}" for c in allowed_codes]) |
                    Q(code__in=[c.replace('BU_', '') for c in allowed_codes])
                )

        for bu in bu_qs.order_by('code'):
            bu_ids = bu.get_all_descendant_ids()

            # Ưu tiên lọc công nợ theo tài khoản 1311
            rec = ReceivablesAgeing.objects.filter(
                reporting_period=req_period,
                account_code__startswith='1311',
                customer__business_unit_id__in=bu_ids
            ).aggregate(
                total=Sum('total_debt'),
                overdue=Sum('overdue_total'),
            )
            if rec['total'] is None and rec['overdue'] is None:
                rec = ReceivablesAgeing.objects.filter(
                    reporting_period=req_period,
                    customer__business_unit_id__in=bu_ids
                ).aggregate(
                    total=Sum('total_debt'),
                    overdue=Sum('overdue_total'),
                )

            receivable_total = rec['total'] or 0
            commitment_overdue = rec['overdue'] or 0

            overdue_customers = ReceivablesAgeing.objects.filter(
                reporting_period=req_period,
                customer__business_unit_id__in=bu_ids,
                overdue_total__gt=0
            ).values_list('customer_id', flat=True)

            collected_due_qs = AccountDetail.objects.filter(
                posting_date=date,
                customer_id__in=overdue_customers
            ).filter(cash_cond & offset_cond)
            sums_due = collected_due_qs.aggregate(d=Sum('debit_amount'), c=Sum('credit_amount'))
            collected_due = (sums_due['d'] or 0) - (sums_due['c'] or 0)

            # Lọc mở rộng cả business_unit_id và customer__business_unit_id để không sót chứng từ
            collection_qs = AccountDetail.objects.filter(
                posting_date=date,
            ).filter(
                Q(business_unit_id__in=bu_ids) | Q(customer__business_unit_id__in=bu_ids)
            ).filter(cash_cond & offset_cond)
            total_sums = collection_qs.aggregate(d=Sum('debit_amount'), c=Sum('credit_amount'))
            total_collected = (total_sums['d'] or 0) - (total_sums['c'] or 0)

            collected_in_term_cod = max(0, total_collected - collected_due)

            rows.append({
                "bu_id": bu.id,
                "bu_code": bu.code,
                "bu_name": bu.name,
                "receivable_total": receivable_total,
                "commitment_overdue": commitment_overdue,
                "collected_due": collected_due,
                "collected_in_term_cod": collected_in_term_cod,
                "total_collected": total_collected,
            })

            sum_recv += receivable_total
            sum_commit += commitment_overdue
            sum_due += collected_due
            sum_term += collected_in_term_cod
            sum_total += total_collected

        return Response({
            "date": date_str,
            "latest_available_date": latest_ad_date.strftime('%Y-%m-%d') if latest_ad_date else date_str,
            "has_data": sum_total > 0,
            "reporting_period": req_period,
            "rows": rows,
            "totals": {
                "receivable_total": sum_recv,
                "commitment_overdue": sum_commit,
                "collected_due": sum_due,
                "collected_in_term_cod": sum_term,
                "total_collected": sum_total,
            },
        })


class SendEmailAPIView(APIView):
    permission_classes = [permissions.IsAuthenticated]
    parser_classes = (MultiPartParser, FormParser, JSONParser)

    def post(self, request, *args, **kwargs):
        start_time = time.time()
        timing_steps = []
        
        def add_timing(step_name):
            elapsed = time.time() - start_time
            timing_steps.append(f"[{datetime.now().strftime('%H:%M:%S.%f')}] {step_name} (elapsed: {elapsed:.3f}s)")
            
        add_timing("1. Bắt đầu nhận request gửi email")
        
        subject = "N/A"
        message = "N/A"
        to_emails = []
        from_email = "N/A"
        requested_from = "None"
        attachment_name = "None"
        status_str = "SUCCESS"
        
        serializer = SendEmailSerializer(data=request.data)
        if not serializer.is_valid():
            status_str = f"VALIDATION_FAILED: {serializer.errors}"
            add_timing("Dữ liệu request không hợp lệ (Validation Failed)")
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        
        add_timing("2. Kiểm tra/Validate dữ liệu xong")
        
        validated_data = serializer.validated_data
        to_emails = validated_data['to_emails']
        subject = validated_data['subject']
        message = validated_data['message']
        
        requested_name = validated_data.get('from_name')
        requested_from = validated_data.get('from_email')
        
        from_email = get_formatted_from_email(override_display_name=requested_name)
            
        uploaded_file = request.FILES.get('file')
        file_name = validated_data.get('file_name')
        
        attachment_name = (file_name or uploaded_file.name) if uploaded_file else 'None'
        
        try:
            add_timing("3. Bắt đầu khởi tạo đối tượng EmailMessage")
            email = EmailMessage(
                subject=subject,
                body=message,
                from_email=from_email,
                to=to_emails,
                reply_to=[requested_from] if requested_from else None
            )
            
            if uploaded_file:
                add_timing(f"4. Bắt đầu đọc file đính kèm từ bộ nhớ ({uploaded_file.size} bytes)")
                file_content = uploaded_file.read()
                add_timing("5. Đọc file xong, bắt đầu đính kèm (attach) vào EmailMessage")
                email.attach(attachment_name, file_content, uploaded_file.content_type)
                add_timing("6. Đính kèm file thành công")
                
            add_timing("7. Bắt đầu thực thi lệnh email.send() gửi qua máy chủ SMTP")
            email.send(fail_silently=False)
            add_timing("8. Máy chủ SMTP xác nhận gửi thư thành công")
            
            return Response({
                "status": "success",
                "message": "Gửi email thành công."
            }, status=status.HTTP_200_OK)
            
        except Exception as e:
            status_str = f"ERROR: {str(e)}"
            add_timing(f"Lỗi gửi email: {str(e)}")
            logger.error(f"Lỗi khi gửi email: {str(e)}", exc_info=True)
            return Response({
                "status": "error",
                "message": f"Không thể gửi email: {str(e)}"
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
            
        finally:
            total_elapsed = time.time() - start_time
            try:
                log_file_path = os.path.join(settings.BASE_DIR, 'email_send.log')
                timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                to_str = ', '.join(to_emails) if isinstance(to_emails, list) else str(to_emails)
                
                log_entry = (
                    f"[{timestamp}]\n"
                    f"From: {from_email} (Requested: {requested_from or 'None'})\n"
                    f"To: {to_str}\n"
                    f"Subject: {subject}\n"
                    f"Message: {message}\n"
                    f"File: {attachment_name}\n"
                    f"Status: {status_str}\n"
                    f"{'-'*50}\n"
                )
                with open(log_file_path, 'a', encoding='utf-8') as f:
                    f.write(log_entry)
            except Exception as log_err:
                logger.error(f"Lỗi ghi log file email_send.log: {str(log_err)}")
                
            try:
                timing_file_path = os.path.join(settings.BASE_DIR, 'email_timing.log')
                timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                
                timing_entry = (
                    f"==================================================\n"
                    f"THỜI GIAN GỬI EMAIL: {timestamp}\n"
                    f"Chủ đề: {subject}\n"
                    f"File đính kèm: {attachment_name}\n"
                    f"Tổng thời gian xử lý: {total_elapsed:.3f}s\n"
                    f"Trạng thái cuối cùng: {status_str}\n"
                    f"Nhật ký chi tiết các bước thực hiện:\n"
                    + "\n".join(timing_steps) + "\n"
                    f"==================================================\n\n"
                )
                with open(timing_file_path, 'a', encoding='utf-8') as f:
                    f.write(timing_entry)
            except Exception as log_err:
                logger.error(f"Lỗi ghi log file email_timing.log: {str(log_err)}")


class BUTargetPlanViewSet(viewsets.ModelViewSet):
    queryset = BUTargetPlan.objects.all().order_by('-year', '-month')
    serializer_class = BUTargetPlanSerializer
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['month', 'year', 'business_unit']

    def perform_create(self, serializer):
        instance = serializer.save(updated_by=self.request.user if self.request.user.is_authenticated else None)
        bu_id = instance.business_unit.id if instance.business_unit else None
        update_single_bu_performance(bu_id, month=instance.month, year=instance.year)

    def perform_update(self, serializer):
        instance = serializer.save(updated_by=self.request.user if self.request.user.is_authenticated else None)
        bu_id = instance.business_unit.id if instance.business_unit else None
        update_single_bu_performance(bu_id, month=instance.month, year=instance.year)


class ManualAdjustmentViewSet(viewsets.ModelViewSet):
    queryset = ManualAdjustment.objects.all().order_by('-year', '-month', '-created_at')
    serializer_class = ManualAdjustmentSerializer
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['month', 'year', 'business_unit', 'metric_type', 'is_active']

    def perform_create(self, serializer):
        instance = serializer.save(created_by=self.request.user if self.request.user.is_authenticated else None)
        bu_id = instance.business_unit.id if instance.business_unit else None
        update_single_bu_performance(bu_id, month=instance.month, year=instance.year)

    def perform_update(self, serializer):
        instance = serializer.save()
        bu_id = instance.business_unit.id if instance.business_unit else None
        update_single_bu_performance(bu_id, month=instance.month, year=instance.year)
