import logging
from rest_framework import views, permissions, status
from rest_framework.response import Response
from django.core.exceptions import PermissionDenied

from accounting.services.sales_performance_service import get_sales_performance_data

logger = logging.getLogger(__name__)

class SalesPerformanceByEmployeeAPIView(views.APIView):
    """
    API Báo cáo Hiệu suất Doanh thu theo Nhân viên Sales (Đa cấp: Công ty -> BU -> Miền/Nhóm -> Nhân viên).
    - Route: GET /api/sales/performance-by-employee/
    - Query Params:
        + date: YYYY-MM-DD (Ngày chốt báo cáo, ví dụ 2026-08-31)
        + period: YYYY-MM (Kỳ báo cáo, ví dụ 2026-08)
        + bu_code: Mã BU cụ thể (hoặc 'ALL' / để trống)
    - Phân quyền (RBAC):
        + BOD_ADMIN / is_superuser: Xem toàn bộ công ty hoặc lọc từng BU.
        + BU_HEAD: Chỉ xem các BU được phân quyền quản lý (managed_bus).
    """
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, *args, **kwargs):
        target_date = request.query_params.get('date')
        period = request.query_params.get('period')
        bu_code = request.query_params.get('bu_code')
        if bu_code:
            bu_code = bu_code.strip()

        try:
            data = get_sales_performance_data(
                target_date=target_date,
                period=period,
                bu_code=bu_code,
                user=request.user
            )
            return Response(data, status=status.HTTP_200_OK)
        except PermissionDenied as e:
            logger.warning(f"SalesPerformance RBAC Denied for user {request.user.username}: {e}")
            return Response(
                {"success": False, "detail": str(e)},
                status=status.HTTP_403_FORBIDDEN
            )
        except Exception as e:
            logger.exception(f"Lỗi khi tính toán Sales Performance Report: {e}")
            return Response(
                {"success": False, "detail": f"Lỗi hệ thống khi tính toán báo cáo: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
