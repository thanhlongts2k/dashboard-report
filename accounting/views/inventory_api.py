from datetime import datetime
from django.db.models import Sum
from rest_framework import viewsets
from rest_framework.response import Response
from accounting.models import Warehouse, InventorySummary, Product, PurchaseDetail
from accounting.serializers import (
    WarehouseSerializer, InventorySummarySerializer,
    ProductSerializer, PurchaseDetailSerializer
)

class WarehouseViewSet(viewsets.ModelViewSet):
    queryset = Warehouse.objects.all().select_related('business_unit').order_by('id')
    serializer_class = WarehouseSerializer

    def _resolve_reporting_period(self, request):
        start_date = request.query_params.get('startDate') or request.query_params.get('start_date')
        end_date = request.query_params.get('endDate') or request.query_params.get('end_date')
        period = request.query_params.get('period')
        month = request.query_params.get('month')
        year = request.query_params.get('year')

        if period:
            return period.strip()[:7]
        if start_date:
            return start_date.strip()[:7]
        if end_date:
            return end_date.strip()[:7]
        if month and year:
            try:
                return f"{int(year):04d}-{int(month):02d}"
            except (ValueError, TypeError):
                pass

        latest = InventorySummary.objects.order_by('-reporting_period').values_list('reporting_period', flat=True).first()
        return latest or datetime.now().strftime('%Y-%m')

    def _get_inventory_map(self, reporting_period):
        inv_agg = InventorySummary.objects.filter(
            reporting_period=reporting_period
        ).values('warehouse_id').annotate(
            opening=Sum('opening_value'),
            in_val=Sum('in_value'),
            out_val=Sum('out_value'),
            closing=Sum('closing_value')
        )
        return {
            item['warehouse_id']: {
                'opening': float(item['opening'] or 0),
                'in_val': float(item['in_val'] or 0),
                'out_val': float(item['out_val'] or 0),
                'closing': float(item['closing'] or 0)
            }
            for item in inv_agg if item['warehouse_id'] is not None
        }

    def list(self, request, *args, **kwargs):
        reporting_period = self._resolve_reporting_period(request)
        inv_map = self._get_inventory_map(reporting_period)

        queryset = self.filter_queryset(self.get_queryset())
        for wh in queryset:
            data = inv_map.get(wh.id, {'opening': 0.0, 'in_val': 0.0, 'out_val': 0.0, 'closing': 0.0})
            wh.inventory_opening_value = data['opening']
            wh.inventory_in_value = data['in_val']
            wh.inventory_out_value = data['out_val']
            wh.inventory_value_actual = data['closing']

        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)

    def retrieve(self, request, *args, **kwargs):
        reporting_period = self._resolve_reporting_period(request)
        inv_map = self._get_inventory_map(reporting_period)

        instance = self.get_object()
        data = inv_map.get(instance.id, {'opening': 0.0, 'in_val': 0.0, 'out_val': 0.0, 'closing': 0.0})
        instance.inventory_opening_value = data['opening']
        instance.inventory_in_value = data['in_val']
        instance.inventory_out_value = data['out_val']
        instance.inventory_value_actual = data['closing']

        serializer = self.get_serializer(instance)
        return Response(serializer.data)

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
