from rest_framework import viewsets
from accounting.models import Warehouse, InventorySummary, Product, PurchaseDetail
from accounting.serializers import (
    WarehouseSerializer, InventorySummarySerializer,
    ProductSerializer, PurchaseDetailSerializer
)

class WarehouseViewSet(viewsets.ModelViewSet):
    queryset = Warehouse.objects.all()
    serializer_class = WarehouseSerializer

class InventorySummaryViewSet(viewsets.ModelViewSet):
    queryset = InventorySummary.objects.all()
    serializer_class = InventorySummarySerializer

class ProductViewSet(viewsets.ModelViewSet):
    queryset = Product.objects.all()
    serializer_class = ProductSerializer

class PurchaseDetailViewSet(viewsets.ModelViewSet):
    queryset = PurchaseDetail.objects.all().select_related(
        'supplier', 'business_unit', 'product', 'warehouse'
    ).order_by('-posting_date')
    serializer_class = PurchaseDetailSerializer
    filterset_fields = ['supplier__code', 'business_unit__code', 'warehouse__code']
