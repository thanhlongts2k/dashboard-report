from accounting.tasks import update_single_bu_performance
from rest_framework import viewsets, generics
import pandas as pd
from datetime import datetime
from django.db.models import Q, Sum
from .models import (
    Branch, Warehouse, Customer, Employee, InventorySummary,
    Product, BusinessUnit, SalesTransaction, Supplier, SupplierDebt, SupplierGroup,
    ReceivablesAgeing, AccountDetail, BUPerformance, BUPerformanceDaily
)
from .serializers import *
from .filters import BUPerformanceDailyFilter, BUPerformanceFilter

from knox.views import LoginView as KnoxLoginView
from rest_framework import permissions, status
from django.contrib.auth import authenticate, login
from rest_framework.response import Response
from rest_framework.views import APIView
from django_filters.rest_framework import DjangoFilterBackend

from google.oauth2 import id_token
from google.auth.transport import requests as google_requests
from django.contrib.auth.models import User
from django.conf import settings

class LoginAPI(KnoxLoginView):
    permission_classes = [permissions.AllowAny]

    def post(self, request, format=None):
        username = request.data.get('username')
        password = request.data.get('password')

        user = authenticate(username=username, password=password)
        if not user:
            return Response({'error': 'Sai tài khoản hoặc mật khẩu'}, status=400)

        login(request, user)
        return super().post(request, format=None)

class GoogleLoginAPI(KnoxLoginView):
    permission_classes = [permissions.AllowAny]

    def post(self, request, format=None):
        serializer = GoogleLoginSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        token = serializer.validated_data['id_token']
        client_id = getattr(settings, 'GOOGLE_CLIENT_ID', None)

        try:
            # 1. Xác thực ID token trực tiếp với máy chủ Google
            id_info = id_token.verify_oauth2_token(
                token,
                google_requests.Request(),
                audience=client_id if client_id else None
            )

            email = id_info.get('email')
            name = id_info.get('name', '')
            given_name = id_info.get('given_name', '')
            family_name = id_info.get('family_name', '')

            if not email:
                return Response({'error': 'Google ID token không chứa email hợp lệ.'}, status=status.HTTP_400_BAD_REQUEST)

            # 2. Tìm người dùng đã có hoặc tự động tạo User mới trong Django DB
            user, created = User.objects.get_or_create(
                username=email,
                defaults={
                    'email': email,
                    'first_name': given_name or name,
                    'last_name': family_name,
                    'is_active': True
                }
            )

            if not user.is_active:
                return Response({'error': 'Tài khoản người dùng đã bị khóa.'}, status=status.HTTP_400_BAD_REQUEST)

            # 3. Đăng nhập session & tạo Knox Token
            login(request, user)
            return super().post(request, format=None)

        except ValueError as e:
            return Response({'error': f'Google ID token không hợp lệ hoặc đã hết hạn: {str(e)}'}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return Response({'error': f'Lỗi hệ thống khi xác thực Google: {str(e)}'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

class BranchViewSet(viewsets.ModelViewSet):
    queryset = Branch.objects.all()
    serializer_class = BranchSerializer

class WarehouseViewSet(viewsets.ModelViewSet):
    queryset = Warehouse.objects.all()
    serializer_class = WarehouseSerializer

class CustomerViewSet(viewsets.ModelViewSet):
    queryset = Customer.objects.all()
    serializer_class = CustomerSerializer

class EmployeeViewSet(viewsets.ModelViewSet):
    queryset = Employee.objects.all()
    serializer_class = EmployeeSerializer

class ProductViewSet(viewsets.ModelViewSet):
    queryset = Product.objects.all()
    serializer_class = ProductSerializer

class BusinessUnitViewSet(viewsets.ModelViewSet):
    queryset = BusinessUnit.objects.all()
    serializer_class = BusinessUnitSerializer

    def get_queryset(self):
        queryset = BusinessUnit.objects.all()
        is_main = self.request.query_params.get("is_main")

        if is_main in ["true", "false"]:
            queryset = queryset.filter(is_main=(is_main == "true"))

        return queryset

class SalesTransactionViewSet(viewsets.ModelViewSet):
    queryset = SalesTransaction.objects.all()
    serializer_class = SalesTransactionSerializer

class SupplierViewSet(viewsets.ModelViewSet):
    queryset = Supplier.objects.all()
    serializer_class = SupplierSerializer

class SupplierGroupViewSet(viewsets.ModelViewSet):
    queryset = SupplierGroup.objects.all()
    serializer_class = SupplierGroupSerializer

class SupplierDebtViewSet(viewsets.ModelViewSet):
    queryset = SupplierDebt.objects.all()
    serializer_class = SupplierDebtSerializer

class InventorySummaryViewSet(viewsets.ModelViewSet):
    queryset = InventorySummary.objects.all()
    serializer_class = InventorySummarySerializer

class AccountDetailViewSet(viewsets.ModelViewSet):
    queryset = AccountDetail.objects.all().order_by('-id')
    serializer_class = AccountDetailSerializer
    # Thêm bộ lọc nếu cần (ví dụ lọc theo Business Unit)
    filterset_fields = ['business_unit__code']

class ReceivablesAgeingViewSet(viewsets.ModelViewSet):
    queryset = ReceivablesAgeing.objects.all().order_by('-id')
    serializer_class = ReceivablesAgeingSerializer
    search_fields = ['customer__code', 'customer__name']

class PurchaseDetailViewSet(viewsets.ModelViewSet):
    queryset = PurchaseDetail.objects.all().select_related(
        'supplier', 'business_unit', 'product', 'warehouse'
    ).order_by('-posting_date')
    serializer_class = PurchaseDetailSerializer
    filterset_fields = ['supplier__code', 'business_unit__code', 'warehouse__code']


class BUReportAPIView(generics.ListAPIView):
    """
    API lấy danh sách dữ liệu hiệu suất (KPI) tháng của các Đơn vị kinh doanh (BU).

    ### QUY TẮC LỌC THEO ĐƠN VỊ (bu_id):
    - Nếu KHÔNG truyền `bu_id`, hoặc truyền `?bu_id=all`: Hệ thống lấy báo cáo của tất cả các BU và Tổng công ty.
    - Nếu truyền `?bu_id=null` hoặc bỏ trống giá trị `?bu_id=`: Hệ thống lọc lấy báo cáo của Tổng công ty (BU gốc/không có BU cha).
    - Nếu truyền `bu_id` hợp lệ (Ví dụ: `?bu_id=70`): Hệ thống lọc chính xác theo BU đó.

    ### CÁC THAM SỐ LỌC (Query Parameters):
    Hỗ trợ kết hợp các tham số lọc động dưới đây bằng dấu `&`:
    
    1. **Lọc theo quãng ngày (Date Range):**
       - `start_date`: Ngày bắt đầu (Format: YYYY-MM-DD). Ví dụ: `?start_date=2026-06-22`
       - `end_date`: Ngày kết thúc (Format: YYYY-MM-DD). Ví dụ: `?end_date=2026-06-28`
       *(Bộ lọc tự động tính toán các tháng/năm giao thoa với khoảng ngày này)*

    2. **Lọc theo tháng / năm cố định:**
       - `month`: Tháng cần lấy dữ liệu (Số từ 1-12). Ví dụ: `?month=6`
       - `year`: Năm cần lấy dữ liệu (Số có 4 chữ số). Ví dụ: `?year=2026`

    3. **Các bộ lọc khác:**
       - `only_roots`: Truyền `true` để chỉ lấy báo cáo của các BU cấp cao nhất (không có BU cha).
    """
    serializer_class = BUPerformanceSerializer
    filter_backends = [DjangoFilterBackend]
    filterset_class = BUPerformanceFilter

    def get_queryset(self):
        # Khởi tạo query gốc tối ưu SQL chống lỗi N+1 Query
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
    """
    API lấy danh sách dữ liệu hiệu suất chi tiết theo từng ngày (doanh thu, thực thu) của Business Unit (BU).

    ### QUY TẮC LỌC THEO ĐƠN VỊ (bu_id):
    - Nếu KHÔNG truyền `bu_id`, hoặc truyền `?bu_id=0`, `?bu_id=null`: Hệ thống tự động hiểu là lọc theo **Tổng công ty** (business_unit__isnull=True).
    - Nếu truyền `bu_id` hợp lệ (Ví dụ: `?bu_id=70`): Hệ thống lọc chính xác theo BU đó.

    ### CÁC THAM SỐ LỌC (Query Parameters):
    Fen Front-end có thể kết hợp linh hoạt các param dưới đây bằng dấu `&`:
    
    1. **Lọc theo quãng ngày (Date Range - Khuyên dùng cho lọc theo tuần/khoảng thời gian):**
       - `start_date`: Ngày bắt đầu (Format: YYYY-MM-DD). Ví dụ: `?start_date=2026-06-22`
       - `end_date`: Ngày kết thúc (Format: YYYY-MM-DD). Ví dụ: `?end_date=2026-06-28`
       *(Để lọc theo TUẦN, Front-end tự tính ngày đầu tuần và cuối tuần rồi truyền vào cặp param này)*

    2. **Lọc theo tháng / năm cố định (Nếu không dùng quãng ngày):**
       - `month`: Tháng cần lấy dữ liệu (Số từ 1-12). Ví dụ: `?month=6`
       - `year`: Năm cần lấy dữ liệu (Số có 4 chữ số). Ví dụ: `?year=2026`

    ### VÍ DỤ GỌI API:
    - **Lấy dữ liệu tuần này của Tổng công ty (Giả sử từ 22/06 đến 28/06):**
      `GET /api/bu-performance/daily/?start_date=2026-06-22&end_date=2026-06-28`
      
    - **Lấy dữ liệu tuần trước của BU có ID = 70:**
      `GET /api/bu-performance/daily/?bu_id=70&start_date=2026-06-15&end_date=2026-06-21`
      
    - **Lấy toàn bộ dữ liệu tháng 6/2026 của Tổng công ty:**
      `GET /api/bu-performance/daily/?month=6&year=2026`
    """
    serializer_class = BUPerformanceDailySerializer
    filter_backends = [DjangoFilterBackend]
    filterset_class = BUPerformanceDailyFilter

    # def get_queryset(self):
    #     """
    #     Cho phép lọc dữ liệu qua URL params:
    #     ?bu_id=1&month=1&year=2026
    #     """
    #     queryset = BUPerformanceDaily.objects.all().select_related(
    #         'performance_month__business_unit'
    #     )
        
    #     bu_id = self.request.query_params.get('bu_id')
    #     month = self.request.query_params.get('month')
    #     year = self.request.query_params.get('year')

    #     # Lọc theo BU (Nếu không truyền bu_id hoặc bu_id=0/null thì lấy Tổng công ty)
    #     if bu_id:
    #         queryset = queryset.filter(performance_month__business_unit_id=bu_id)
    #     else:
    #         queryset = queryset.filter(performance_month__business_unit__isnull=True)

    #     # Lọc theo tháng/năm
    #     if month:
    #         queryset = queryset.filter(date__month=month)
    #     if year:
    #         queryset = queryset.filter(date__year=year)

    #     return queryset.order_by('date')

    def get_queryset(self):
        # Khởi tạo query gốc với select_related để tối ưu SQL chống lỗi N+1
        queryset = BUPerformanceDaily.objects.all().select_related(
            'performance_month__business_unit'
        ).order_by('date')
        
        # Xử lý fallback cho trường hợp client hoàn toàn KHÔNG truyền param `bu_id`
        if 'bu_id' not in self.request.query_params:
            queryset = queryset.filter(performance_month__business_unit__isnull=True)
            
        return queryset
    
class BUPerformanceUpdateAPIView(APIView):
    """
    API để yêu cầu tính toán và cập nhật lại chỉ số hiệu suất (KPI) thực tế cho một Đơn vị kinh doanh (BU).
    
    Phương thức: POST
    Dữ liệu yêu cầu (Request Body - JSON):
    - `bu_id` (Integer, Optional): ID của Đơn vị kinh doanh cần cập nhật. Nếu truyền `null`, hệ thống sẽ cập nhật cho Tổng công ty.
    - `month` (Integer, Optional): Tháng cần cập nhật (Mặc định là tháng hiện tại).
    - `year` (Integer, Optional): Năm cần cập nhật (Mặc định là năm hiện tại).
    - `target_date` (Date string 'YYYY-MM-DD', Optional): Ngày mốc kết thúc tính toán.
    
    Hàm xử lý đồng bộ (Synchronous) và trả về thông tin kết quả tính toán chi tiết ngay lập tức.
    """
    def post(self, request):
        serializer = PerformanceUpdateSerializer(data=request.data)
        
        if serializer.is_valid():
            bu_id = serializer.validated_data.get('bu_id')
            month = serializer.validated_data.get('month')
            year = serializer.validated_data.get('year')
            target_date = serializer.validated_data.get('target_date')

            # Chuyển target_date thành string để gửi vào task nếu có
            target_date_str = target_date.strftime('%Y-%m-%d') if target_date else None

            try:
                # GỌI TASK chạy ngầm bất đồng bộ (Celery) để tránh 504 Gateway Timeout
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


class DashboardCollectionByBUAPIView(APIView):
    """
    GET /api/dashboard/collection-by-bu/?date=YYYY-MM-DD

    Trả về 5 chỉ số thu nợ theo từng BU chính (is_main=True) cho 1 ngày:
      - receivable_total       : Dư nợ cần thu (snapshot hiện tại của ReceivablesAgeing)
      - commitment_overdue     : Cam kết (quá hạn) — dùng tạm overdue_total
      - collected_due          : Đã thu (đến hạn) — phát sinh trên KH có nợ quá hạn
      - collected_in_term_cod  : Thu trong hạn + COD = Tổng thu - Đã thu đến hạn
      - total_collected        : Tổng thu trong ngày
    """

    def get(self, request):
        date_str = request.query_params.get('date')
        if not date_str:
            return Response(
                {"error": "Tham số 'date' là bắt buộc (định dạng YYYY-MM-DD)."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        try:
            date = datetime.strptime(date_str, '%Y-%m-%d').date()
        except ValueError:
            return Response(
                {"error": "Định dạng date không hợp lệ. Dùng YYYY-MM-DD."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        cash_cond = Q(account_number__startswith='111') | Q(account_number__startswith='112')
        offset_cond = Q(offset_account__startswith='1311') | Q(offset_account__startswith='1312')

        rows = []
        sum_recv = sum_commit = sum_due = sum_term = sum_total = 0

        # Lấy các BU "chính" để báo cáo dashboard. Ưu tiên cờ is_main; nếu chưa BU nào tick,
        # rơi xuống fallback: lấy BU con (cấp 2) của BU gốc duy nhất (vd HPC).
        bu_qs = BusinessUnit.objects.filter(is_main=True)
        if not bu_qs.exists():
            roots = BusinessUnit.objects.filter(parent__isnull=True)
            if roots.count() == 1:
                bu_qs = BusinessUnit.objects.filter(parent=roots.first())
            else:
                bu_qs = BusinessUnit.objects.filter(parent__isnull=False)

        for bu in bu_qs.order_by('code'):
            bu_ids = bu.get_all_descendant_ids()

            # 1. Dư nợ & Cam kết — đi qua Customer.business_unit (giống tasks.py)
            rec = ReceivablesAgeing.objects.filter(
                customer__business_unit_id__in=bu_ids
            ).aggregate(
                total=Sum('total_debt'),
                overdue=Sum('overdue_total'),
            )
            receivable_total = rec['total'] or 0
            commitment_overdue = rec['overdue'] or 0
            
            # 2. Đã thu (đến hạn) — thực thu từ các khách hàng có nợ quá hạn
            overdue_customers = ReceivablesAgeing.objects.filter(
                customer__business_unit_id__in=bu_ids,
                overdue_total__gt=0
            ).values_list('customer_id', flat=True)

            collected_due_qs = AccountDetail.objects.filter(
                posting_date=date,
                customer_id__in=overdue_customers
            ).filter(cash_cond & offset_cond)
            sums_due = collected_due_qs.aggregate(d=Sum('debit_amount'), c=Sum('credit_amount'))
            collected_due = (sums_due['d'] or 0) - (sums_due['c'] or 0)

            # 3. Tổng thu trong ngày — qua AccountDetail.business_unit
            collection_qs = AccountDetail.objects.filter(
                posting_date=date,
                business_unit_id__in=bu_ids,
            ).filter(cash_cond & offset_cond)
            total_sums = collection_qs.aggregate(d=Sum('debit_amount'), c=Sum('credit_amount'))
            total_collected = (total_sums['d'] or 0) - (total_sums['c'] or 0)

            # 4. Thu trong hạn + COD = Tổng thu - Đã thu đến hạn
            collected_in_term_cod = total_collected - collected_due

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
            "rows": rows,
            "totals": {
                "receivable_total": sum_recv,
                "commitment_overdue": sum_commit,
                "collected_due": sum_due,
                "collected_in_term_cod": sum_term,
                "total_collected": sum_total,
            },
        })


from rest_framework.parsers import MultiPartParser, FormParser, JSONParser
from django.core.mail import EmailMessage
from django.conf import settings
import logging

logger = logging.getLogger(__name__)

class SendEmailAPIView(APIView):
    """
    POST /api/reports/send-email/
    API hỗ trợ gửi email từ Frontend với tùy chọn tệp đính kèm.
    Yêu cầu xác thực Token Knox mặc định (permission_classes = [permissions.IsAuthenticated]).
    """
    permission_classes = [permissions.IsAuthenticated]
    parser_classes = (MultiPartParser, FormParser, JSONParser)

    def post(self, request, *args, **kwargs):
        import time
        from datetime import datetime
        import os
        
        start_time = time.time()
        timing_steps = []
        
        def add_timing(step_name):
            elapsed = time.time() - start_time
            timing_steps.append(f"[{datetime.now().strftime('%H:%M:%S.%f')}] {step_name} (elapsed: {elapsed:.3f}s)")
            
        add_timing("1. Bắt đầu nhận request gửi email")
        
        # Giá trị mặc định phòng trường hợp validation thất bại không bị NameError ở block finally
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
        
        # Lấy from_name và from_email từ request
        requested_name = validated_data.get('from_name')
        requested_from = validated_data.get('from_email')
        
        # Email SMTP gốc sử dụng để phát tin
        smtp_user = getattr(settings, 'EMAIL_HOST_USER', None) or getattr(settings, 'DEFAULT_FROM_EMAIL', None) or 'noreply@example.com'
        
        # Xác định Tên Alias hiển thị (Display Name): Ưu tiên requested_name -> EMAIL_DISPLAY_NAME -> Tên mặc định
        default_display_name = getattr(settings, 'EMAIL_DISPLAY_NAME', 'Hao Phuong Reporting System')
        display_name = requested_name.strip() if (requested_name and requested_name.strip()) else default_display_name
        
        # Định dạng chuẩn RFC 5322: "Tên Hiển Thị (Alias)" <diachi_smtp@gmail.com>
        from_email = f'"{display_name}" <{smtp_user}>'
            
        uploaded_file = request.FILES.get('file')
        file_name = validated_data.get('file_name')
        
        # Tên file đính kèm nếu có
        attachment_name = (file_name or uploaded_file.name) if uploaded_file else 'None'
        
        error_msg = ""
        
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
            error_msg = str(e)
            add_timing(f"Lỗi gửi email: {str(e)}")
            logger.error(f"Lỗi khi gửi email: {str(e)}", exc_info=True)
            return Response({
                "status": "error",
                "message": f"Không thể gửi email: {str(e)}"
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
            
        finally:
            total_elapsed = time.time() - start_time
            # Ghi nhật ký vào file email_send.log ở thư mục gốc
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
                
            # Ghi nhật ký chi tiết thời gian xử lý (Timing) vào file email_timing.log ở thư mục gốc
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

