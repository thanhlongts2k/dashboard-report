from django.db import models
from .organization import BusinessUnit, Warehouse, Product
from .employee import Employee

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


class EmployeeReceivableSummary(models.Model):
    employee = models.ForeignKey('Employee', on_delete=models.CASCADE, related_name='receivable_summaries', verbose_name="Nhân viên")
    department = models.ForeignKey('Department', on_delete=models.SET_NULL, null=True, blank=True, related_name='employee_receivable_summaries', verbose_name="Phòng ban")
    reporting_period = models.CharField(max_length=7, db_index=True, verbose_name="Kỳ báo cáo")
    is_manager = models.BooleanField(default=False, verbose_name="Là Quản lý nhóm/Trưởng phòng")

    # Chỉ số công nợ cá nhân (Own Debt)
    own_total_debt = models.DecimalField(max_digits=18, decimal_places=2, default=0, verbose_name="Tổng nợ cá nhân")
    own_due_total = models.DecimalField(max_digits=18, decimal_places=2, default=0, verbose_name="Nợ trong hạn cá nhân")
    own_overdue_total = models.DecimalField(max_digits=18, decimal_places=2, default=0, verbose_name="Nợ quá hạn cá nhân")
    own_overdue_above_60 = models.DecimalField(max_digits=18, decimal_places=2, default=0, verbose_name="Nợ quá hạn >60 ngày (cá nhân)")
    own_overdue_above_120 = models.DecimalField(max_digits=18, decimal_places=2, default=0, verbose_name="Nợ xấu >120 ngày (cá nhân)")

    # Chỉ số công nợ nhóm / quản lý (Team / Managed Debt - Cộng dồn đệ quy)
    team_total_debt = models.DecimalField(max_digits=18, decimal_places=2, default=0, verbose_name="Tổng nợ cả nhóm")
    team_due_total = models.DecimalField(max_digits=18, decimal_places=2, default=0, verbose_name="Nợ trong hạn cả nhóm")
    team_overdue_total = models.DecimalField(max_digits=18, decimal_places=2, default=0, verbose_name="Nợ quá hạn cả nhóm")
    team_overdue_above_120 = models.DecimalField(max_digits=18, decimal_places=2, default=0, verbose_name="Nợ xấu cả nhóm (>120 ngày)")
    subordinate_count = models.IntegerField(default=0, verbose_name="Số nhân viên cấp dưới")

    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Ngày tạo")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Ngày cập nhật")

    class Meta:
        db_table = 'employee_receivable_summaries'
        verbose_name = "Công nợ Nhân viên & Quản lý"
        verbose_name_plural = "Bảng tổng hợp công nợ Nhân viên & Quản lý"
        unique_together = ('employee', 'reporting_period')

    def __str__(self):
        role = "Quản lý" if self.is_manager else "Sales"
        return f"{self.employee.full_name} ({role}) - Kỳ {self.reporting_period}"


class SalesTarget(models.Model):
    employee = models.ForeignKey(
        Employee, 
        on_delete=models.CASCADE, 
        related_name='sales_targets',
        verbose_name="Nhân viên Sales"
    )
    business_unit = models.ForeignKey(
        BusinessUnit, 
        on_delete=models.CASCADE, 
        related_name='sales_targets',
        verbose_name="Đơn vị kinh doanh (BU)"
    )
    region = models.CharField(max_length=100, verbose_name="Miền / Khối (e.g. Miền Bắc, Miền Nam, BU ECO...)")
    sales_group = models.CharField(max_length=100, verbose_name="Nhóm hàng (e.g. Miền Bắc_Elevator, Miền Nam_Premium...)")
    period = models.CharField(max_length=7, db_index=True, verbose_name="Kỳ báo cáo (YYYY-MM)")
    
    month_target = models.DecimalField(max_digits=18, decimal_places=2, default=0, verbose_name="Kế hoạch Tháng")
    year_target = models.DecimalField(max_digits=18, decimal_places=2, default=0, verbose_name="Kế hoạch Năm")
    prev_target = models.DecimalField(max_digits=18, decimal_places=2, default=0, verbose_name="Kế hoạch Lũy kế các tháng trước (T1..T-1)")
    
    display_order = models.PositiveIntegerField(default=0, verbose_name="Thứ tự hiển thị")
    is_active = models.BooleanField(default=True, verbose_name="Đang áp dụng")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Ngày tạo")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Ngày cập nhật")

    class Meta:
        db_table = 'sales_targets'
        verbose_name = "Chỉ tiêu Sales"
        verbose_name_plural = "Bảng Quản lý Chỉ tiêu Sales (Sales Targets)"
        unique_together = ('employee', 'business_unit', 'period')
        ordering = ['business_unit', 'display_order', 'id']

    def __str__(self):
        return f"{self.employee.full_name} ({self.sales_group}) - Kỳ {self.period}"


