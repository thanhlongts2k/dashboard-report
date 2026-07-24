from rest_framework import viewsets
from accounting.models import ReceivablesAgeing, Supplier, SupplierGroup, SupplierDebt
from accounting.serializers import (
    ReceivablesAgeingSerializer, SupplierSerializer,
    SupplierGroupSerializer, SupplierDebtSerializer
)

class ReceivablesAgeingViewSet(viewsets.ModelViewSet):
    queryset = ReceivablesAgeing.objects.all().order_by('-id')
    serializer_class = ReceivablesAgeingSerializer
    search_fields = ['customer__code', 'customer__name']

class SupplierViewSet(viewsets.ModelViewSet):
    queryset = Supplier.objects.all()
    serializer_class = SupplierSerializer

class SupplierGroupViewSet(viewsets.ModelViewSet):
    queryset = SupplierGroup.objects.all()
    serializer_class = SupplierGroupSerializer

class SupplierDebtViewSet(viewsets.ModelViewSet):
    queryset = SupplierDebt.objects.all()
    serializer_class = SupplierDebtSerializer
