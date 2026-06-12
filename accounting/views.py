from accounting.tasks import update_single_bu_performance
from rest_framework import viewsets, generics
import pandas as pd
from datetime import datetime
from django.db.models import Q, Sum
from .models import (
    Branch, Warehouse, Customer, Employee, InventorySummary,
    Product, BusinessUnit, SalesTransaction, Supplier, SupplierDebt, SupplierGroup,
    ReceivablesAgeing, AccountDetail
)
from .serializers import *
from knox.views import LoginView as KnoxLoginView
from rest_framework import permissions, status
from django.contrib.auth import authenticate, login
from rest_framework.response import Response
from rest_framework.views import APIView

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


class BUReportAPIView(APIView):
    """
    APIView để truy xuất dữ liệu báo cáo hiệu suất (KPI) tháng của các Đơn vị kinh doanh (BU).
    
    Hỗ trợ các tham số lọc động (Query Parameters):
    - `month`: Tháng cần lấy dữ liệu (Ví dụ: ?month=6).
    - `year`: Năm cần lấy dữ liệu (Ví dụ: ?year=2026).
    - `bu_id`: Lọc theo Đơn vị kinh doanh (BU):
        - 'null' hoặc bỏ trống: Lấy báo cáo của Tổng công ty (BU gốc/không có BU cha).
        - 'all': Lấy báo cáo của tất cả các BU và Tổng công ty.
        - [ID]: Lấy báo cáo của riêng BU có ID tương ứng.
    - `only_roots`: 'true' để chỉ lấy báo cáo của các BU cấp cao nhất (không có BU cha).
    """
    def get(self, request):
        # 1. Lấy tham số lọc từ query params
        month = request.query_params.get('month')
        year = request.query_params.get('year')
        bu_id = request.query_params.get('bu_id')
        only_roots = request.query_params.get('only_roots')

        # 2. Khởi tạo filter động dựa trên tham số truyền vào
        filters = {}
        
        # Chỉ thêm vào filter nếu người dùng có truyền tham số
        if month and month.isdigit():
            filters['month'] = int(month)
        if year and year.isdigit():
            filters['year'] = int(year)
        
        # 3. Xử lý logic Business Unit (Quan trọng)
        # Nếu bu_id là 'all' hoặc không truyền gì cả -> Lấy tất cả (không lọc BU)
        # Nếu bu_id là 'null' -> Lấy bản ghi Tổng công ty
        # Nếu bu_id là số -> Lấy theo ID của BU đó
        
        if bu_id == 'null' or bu_id == '':
            filters['business_unit__isnull'] = True
        elif bu_id and bu_id != 'all':
            filters['business_unit_id'] = bu_id
        # Nếu bu_id='all' hoặc không có bu_id trong params thì không thêm vào filters -> lấy hết

        if only_roots == 'true':
            # Chỉ lấy những bản ghi Performance mà BU của nó không có parent
            filters['business_unit__parent__isnull'] = True

        # 4. Sử dụng .filter() thay vì .get() để tránh lỗi khi có nhiều bản ghi
        queryset = BUPerformance.objects.filter(**filters).order_by('-year', '-month')

        if queryset.exists():
            # many=True cho phép serializer xử lý một danh sách bản ghi
            serializer = BUPerformanceSerializer(queryset, many=True)
            return Response(serializer.data)
        else:
            return Response(
                {"message": "Không tìm thấy dữ liệu phù hợp với bộ lọc."}, 
                status=status.HTTP_404_NOT_FOUND
            )
        

class BUPerformanceDailyListView(generics.ListAPIView):
    """
    APIView để lấy danh sách dữ liệu hiệu suất chi tiết theo từng ngày (doanh thu, thực thu) của BU.
    
    Hỗ trợ các tham số lọc động (Query Parameters):
    - `bu_id`: ID của Đơn vị kinh doanh (Nếu bỏ trống, mặc định lọc theo Tổng công ty).
    - `month`: Tháng cần lấy dữ liệu (Ví dụ: ?month=6).
    - `year`: Năm cần lấy dữ liệu (Ví dụ: ?year=2026).
    """
    serializer_class = BUPerformanceDailySerializer

    def get_queryset(self):
        """
        Cho phép lọc dữ liệu qua URL params:
        ?bu_id=1&month=1&year=2026
        """
        queryset = BUPerformanceDaily.objects.all().select_related(
            'performance_month__business_unit'
        )
        
        bu_id = self.request.query_params.get('bu_id')
        month = self.request.query_params.get('month')
        year = self.request.query_params.get('year')

        # Lọc theo BU (Nếu không truyền bu_id hoặc bu_id=0/null thì lấy Tổng công ty)
        if bu_id:
            queryset = queryset.filter(performance_month__business_unit_id=bu_id)
        else:
            queryset = queryset.filter(performance_month__business_unit__isnull=True)

        # Lọc theo tháng/năm
        if month:
            queryset = queryset.filter(date__month=month)
        if year:
            queryset = queryset.filter(date__year=year)

        return queryset.order_by('date')
    
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
                # GỌI TASK: 
                # Cách 1: Chạy ngay lập tức (Sync) để lấy kết quả trả về API
                result = update_single_bu_performance(
                    bu_id=bu_id, 
                    month=month, 
                    year=year, 
                    target_date_str=target_date_str
                )
                
                # Cách 2: Nếu muốn chạy ngầm (Async) qua Celery
                # update_single_bu_performance.delay(bu_id, month, year, target_date_str)
                # result = "Task has been queued"

                return Response({
                    "status": "success",
                    "message": result
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
            # 1. Dư nợ & Cam kết — đi qua Customer.business_unit (giống tasks.py)
            rec = ReceivablesAgeing.objects.filter(
                customer__business_unit=bu
            ).aggregate(
                total=Sum('total_debt'),
                overdue=Sum('overdue_total'),
                due_now=Sum('due_total'),
            )
            receivable_total = rec['total'] or 0
            commitment_overdue = rec['overdue'] or 0
            # 2. Đã thu (đến hạn) — theo pattern tasks.py dùng due_total từ ReceivablesAgeing
            collected_due = rec['due_now'] or 0

            # 3. Tổng thu trong ngày — qua AccountDetail.business_unit (đã có sẵn từ import)
            collection_qs = AccountDetail.objects.filter(
                posting_date=date,
                business_unit=bu,
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