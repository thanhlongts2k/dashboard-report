import logging
from datetime import datetime
from django.db.models import Sum
from accounting.models import Warehouse, InventorySummary

logger = logging.getLogger(__name__)

def sync_warehouse_inventory_data_logic(reporting_period=None):
    """
    Quét bảng InventorySummary của kỳ báo cáo chỉ định và cập nhật số tổng vào từng Warehouse tương ứng.
    """
    if not reporting_period:
        latest_item = InventorySummary.objects.order_by('-reporting_period').first()
        if latest_item:
            reporting_period = latest_item.reporting_period
        else:
            today = datetime.now()
            reporting_period = f"{today.year:04d}-{today.month:02d}"

    logger.info(f"Đang đồng bộ dữ liệu tồn kho cho các kho theo kỳ: {reporting_period}")
    warehouses = Warehouse.objects.all()
    
    for wh in warehouses:
        data = InventorySummary.objects.filter(
            warehouse=wh,
            reporting_period=reporting_period
        ).aggregate(
            opening=Sum('opening_value'),
            in_val=Sum('in_value'),
            out_val=Sum('out_value'),
            closing=Sum('closing_value')
        )

        wh.inventory_opening_value = data['opening'] or 0
        wh.inventory_in_value = data['in_val'] or 0
        wh.inventory_out_value = data['out_val'] or 0
        wh.inventory_value_actual = data['closing'] or 0
        wh.save()

    return f"Đã cập nhật số liệu tồn kho cho {warehouses.count()} kho theo kỳ {reporting_period}."
