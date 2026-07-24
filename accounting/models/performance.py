from django.db import models
from .organization import BusinessUnit, Warehouse, Product

class BUPerformance(models.Model):
    business_unit = models.ForeignKey(
        BusinessUnit, 
        on_delete=models.CASCADE, 
        null=True, 
        blank=True, 
        verbose_name="Đơn vị kinh doanh (Null = Tổng)"
    )
    month = models.PositiveSmallIntegerField(verbose_name="Tháng")
    year = models.PositiveIntegerField(verbose_name="Năm")

    mtd_revenue_plan = models.DecimalField(max_digits=18, decimal_places=2, default=0, verbose_name="Doanh thu MTD (Kế hoạch)")
    mtd_revenue_actual = models.DecimalField(max_digits=18, decimal_places=2, default=0, verbose_name="Doanh thu MTD (Thực tế)")

    mtd_collection_plan = models.DecimalField(max_digits=18, decimal_places=2, default=0, verbose_name="Thu tiền tháng (Kế hoạch)")
    mtd_collection_actual = models.DecimalField(max_digits=18, decimal_places=2, default=0, verbose_name="Thu tiền tháng (Thực tế)")

    inventory_value_plan = models.DecimalField(max_digits=18, decimal_places=2, default=0, verbose_name="Giá trị tồn kho (Kế hoạch)")
    inventory_value_actual = models.DecimalField(max_digits=18, decimal_places=2, default=0, verbose_name="Giá trị tồn kho (Thực tế)")
    inventory_opening_value = models.DecimalField(max_digits=18, decimal_places=2, default=0, verbose_name="Giá trị tồn kho đầu kỳ")
    inventory_in_value = models.DecimalField(max_digits=18, decimal_places=2, default=0, verbose_name="Giá trị nhập kho trong kỳ")
    inventory_out_value = models.DecimalField(max_digits=18, decimal_places=2, default=0, verbose_name="Giá trị xuất kho trong kỳ")

    bank_debt_plan = models.DecimalField(max_digits=18, decimal_places=2, default=0, verbose_name="Nợ ngân hàng (Kế hoạch)")
    bank_debt_actual = models.DecimalField(max_digits=18, decimal_places=2, default=0, verbose_name="Nợ ngân hàng (Thực tế)")

    opex_plan = models.DecimalField(max_digits=18, decimal_places=2, default=0, verbose_name="Chi phí vận hành (Kế hoạch)")
    opex_actual = models.DecimalField(max_digits=18, decimal_places=2, default=0, verbose_name="Chi phí vận hành (Thực tế)")

    cash_balance_plan = models.DecimalField(max_digits=18, decimal_places=2, default=0, verbose_name="Tiền cuối kỳ (Kế hoạch)")
    cash_balance_actual = models.DecimalField(max_digits=18, decimal_places=2, default=0, verbose_name="Tiền cuối kỳ (Thực tế)")

    collection_due_actual = models.DecimalField(max_digits=18, decimal_places=2, default=0, verbose_name="Đã thu (đến hạn)")
    collection_in_term_cod = models.DecimalField(max_digits=18, decimal_places=2, default=0, verbose_name="Thu trong hạn + COD")
    receivable_total = models.DecimalField(max_digits=18, decimal_places=2, default=0, verbose_name="Dư nợ cần thu")
    receivable_overdue = models.DecimalField(max_digits=18, decimal_places=2, default=0, verbose_name="Nợ quá hạn")

    ytd_revenue_actual = models.DecimalField(max_digits=18, decimal_places=2, default=0, verbose_name="Doanh thu YTD (Thực tế)")
    ytd_revenue_plan = models.DecimalField(max_digits=18, decimal_places=2, default=0, verbose_name="Doanh thu YTD (Kế hoạch)")
    ytd_collection_actual = models.DecimalField(max_digits=18, decimal_places=2, default=0, verbose_name="Thu tiền YTD (Thực tế)")
    ytd_collection_plan = models.DecimalField(max_digits=18, decimal_places=2, default=0, verbose_name="Thu tiền YTD (Kế hoạch)")
    ytd_opex_actual = models.DecimalField(max_digits=18, decimal_places=2, default=0, verbose_name="Chi phí opex YTD (Thực tế)")
    ytd_opex_plan = models.DecimalField(max_digits=18, decimal_places=2, default=0, verbose_name="Chi phí opex YTD (Kế hoạch)")

    mtd_revenue_oversea_actual = models.DecimalField(max_digits=18, decimal_places=2, default=0, verbose_name="Doanh thu Oversea MTD (Thực tế)")
    mtd_revenue_exclude_oversea_actual = models.DecimalField(max_digits=18, decimal_places=2, default=0, verbose_name="Doanh thu không bao gồm Oversea MTD (Thực tế)")
    ytd_revenue_oversea_actual = models.DecimalField(max_digits=18, decimal_places=2, default=0, verbose_name="Doanh thu Oversea YTD (Thực tế)")
    ytd_revenue_exclude_oversea_actual = models.DecimalField(max_digits=18, decimal_places=2, default=0, verbose_name="Doanh thu không bao gồm Oversea YTD (Thực tế)")

    mtd_collection_oversea_actual = models.DecimalField(max_digits=18, decimal_places=2, default=0, verbose_name="Thực thu Oversea MTD (Thực tế)")
    mtd_collection_exclude_oversea_actual = models.DecimalField(max_digits=18, decimal_places=2, default=0, verbose_name="Thực thu không bao gồm Oversea MTD (Thực tế)")
    ytd_collection_oversea_actual = models.DecimalField(max_digits=18, decimal_places=2, default=0, verbose_name="Thực thu Oversea YTD (Thực tế)")
    ytd_collection_exclude_oversea_actual = models.DecimalField(max_digits=18, decimal_places=2, default=0, verbose_name="Thực thu không bao gồm Oversea YTD (Thực tế)")

    class Meta:
        verbose_name = "Chỉ số hiệu suất BU"
        verbose_name_plural = "Bảng theo dõi hiệu suất BU"
        unique_together = ('business_unit', 'month', 'year')

    def __str__(self):
        bu_name = self.business_unit.code if self.business_unit else "TỔNG TOÀN CÔNG TY"
        return f"{bu_name} - Th{self.month}/{self.year}"


class BUPerformanceDaily(models.Model):
    performance_month = models.ForeignKey(
        BUPerformance, 
        on_delete=models.CASCADE, 
        related_name='daily_logs'
    )
    date = models.DateField(verbose_name="Ngày")
    
    daily_revenue = models.DecimalField(max_digits=18, decimal_places=2, default=0, verbose_name="Doanh thu trong ngày")
    daily_collection = models.DecimalField(max_digits=18, decimal_places=2, default=0, verbose_name="Thực thu trong ngày")
    daily_opex_plan = models.DecimalField(max_digits=18, decimal_places=2, default=0, verbose_name="Chi phí opex ngày (Kế hoạch)")
    daily_opex_actual = models.DecimalField(max_digits=18, decimal_places=2, default=0, verbose_name="Chi phí opex ngày (Thực tế)")

    class Meta:
        verbose_name = "Hiệu suất BU theo ngày"
        unique_together = ('performance_month', 'date')
        ordering = ['-date']


class InventorySummary(models.Model):
    warehouse = models.ForeignKey(Warehouse, on_delete=models.CASCADE, verbose_name="Kho")
    product = models.ForeignKey(Product, on_delete=models.CASCADE, verbose_name="Hàng hóa")
    
    opening_quantity = models.DecimalField(max_digits=18, decimal_places=2, default=0, verbose_name="Đầu kỳ - SL")
    opening_value = models.DecimalField(max_digits=18, decimal_places=2, default=0, verbose_name="Đầu kỳ - Giá trị")
    
    in_quantity = models.DecimalField(max_digits=18, decimal_places=2, default=0, verbose_name="Nhập kho - SL")
    in_value = models.DecimalField(max_digits=18, decimal_places=2, default=0, verbose_name="Nhập kho - Giá trị")
    
    out_quantity = models.DecimalField(max_digits=18, decimal_places=2, default=0, verbose_name="Xuất kho - SL")
    out_value = models.DecimalField(max_digits=18, decimal_places=2, default=0, verbose_name="Xuất kho - Giá trị")
    
    closing_quantity = models.DecimalField(max_digits=18, decimal_places=2, default=0, verbose_name="Cuối kỳ - SL")
    closing_value = models.DecimalField(max_digits=18, decimal_places=2, default=0, verbose_name="Cuối kỳ - Giá trị")

    ext_field1 = models.CharField(max_length=255, null=True, blank=True, verbose_name="Trường mở rộng 1")
    ext_field2 = models.CharField(max_length=255, null=True, blank=True, verbose_name="Trường mở rộng 2")

    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Ngày tạo")
    reporting_period = models.CharField(max_length=7, db_index=True, blank=True, null=True, verbose_name="Kỳ báo cáo")

    class Meta:
        verbose_name = "Hàng tồn kho"
        verbose_name_plural = "Danh mục kho (chi tiết hàng có tại kho)"
