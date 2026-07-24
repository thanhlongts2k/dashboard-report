from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    BUPerformanceUpdateAPIView, BranchViewSet, InventorySummaryViewSet, WarehouseViewSet, CustomerViewSet, 
    EmployeeViewSet, ProductViewSet, BusinessUnitViewSet,
    SalesTransactionViewSet, SupplierViewSet, SupplierDebtViewSet, SupplierGroupViewSet, AccountDetailViewSet, ReceivablesAgeingViewSet, PurchaseDetailViewSet,
    BUTargetPlanViewSet, ManualAdjustmentViewSet
)
from .views import LoginAPI, GoogleLoginAPI, BUReportAPIView, BUPerformanceDailyListView, DashboardCollectionByBUAPIView, SendEmailAPIView


# Khởi tạo router của Django Rest Framework
router = DefaultRouter()
router.register(r'branches', BranchViewSet)
router.register(r'warehouses', WarehouseViewSet)
router.register(r'customers', CustomerViewSet)
router.register(r'employees', EmployeeViewSet)
router.register(r'products', ProductViewSet)
router.register(r'business-units', BusinessUnitViewSet)
router.register(r'transactions', SalesTransactionViewSet)
router.register(r'suppliers', SupplierViewSet)
router.register(r'supplier-groups', SupplierGroupViewSet)
router.register(r'supplier-debts', SupplierDebtViewSet)
router.register(r'account-details', AccountDetailViewSet)
router.register(r'receivables-ageing', ReceivablesAgeingViewSet)
router.register(r'purchase-details', PurchaseDetailViewSet)
router.register(r'inventory-summaries', InventorySummaryViewSet)
router.register(r'target-plans', BUTargetPlanViewSet)
router.register(r'adjustments', ManualAdjustmentViewSet)

# Danh sách URL của App
urlpatterns = [
    path('', include(router.urls)),
    path('login/', LoginAPI.as_view()),
    path('google-login/', GoogleLoginAPI.as_view(), name='google_login_api'),
    path('auth/', include('knox.urls')),
    path('bu-performance/', BUReportAPIView.as_view(), name='bu_performance_api'),
    path('performance/daily/', BUPerformanceDailyListView.as_view(), name='performance_daily_list'),
    path('update-performance/', BUPerformanceUpdateAPIView.as_view(), name='api_update_performance'),
    path('dashboard/collection-by-bu/', DashboardCollectionByBUAPIView.as_view(), name='dashboard_collection_by_bu'),
    path('reports/send-email/', SendEmailAPIView.as_view(), name='send_email_api'),
]