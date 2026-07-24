from django.db import models
from django.contrib.auth.models import User
from .organization import BusinessUnit

class BUTargetPlan(models.Model):
    business_unit = models.ForeignKey(
        BusinessUnit,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        verbose_name="Đơn vị kinh doanh (Null = Tổng)"
    )
    month = models.PositiveSmallIntegerField(verbose_name="Tháng")
    year = models.PositiveIntegerField(verbose_name="Năm")
    manager = models.CharField(max_length=255, null=True, blank=True, verbose_name="Người phụ trách")

    year_revenue_target = models.DecimalField(max_digits=18, decimal_places=2, default=0, verbose_name="Mục tiêu Doanh thu Năm")
    month_revenue_target = models.DecimalField(max_digits=18, decimal_places=2, default=0, verbose_name="Mục tiêu Doanh thu Tháng")

    year_collection_target = models.DecimalField(max_digits=18, decimal_places=2, default=0, verbose_name="Mục tiêu Thu tiền Năm")
    month_collection_target = models.DecimalField(max_digits=18, decimal_places=2, default=0, verbose_name="Mục tiêu Thu tiền Tháng")

    year_inventory_target = models.DecimalField(max_digits=18, decimal_places=2, default=0, verbose_name="Mục tiêu Tồn kho Năm")
    month_inventory_target = models.DecimalField(max_digits=18, decimal_places=2, default=0, verbose_name="Mục tiêu Tồn kho Tháng")

    year_cash_target = models.DecimalField(max_digits=18, decimal_places=2, default=0, verbose_name="Mục tiêu Tiền cuối kỳ Năm")
    month_cash_target = models.DecimalField(max_digits=18, decimal_places=2, default=0, verbose_name="Mục tiêu Tiền cuối kỳ Tháng")

    year_bank_debt_target = models.DecimalField(max_digits=18, decimal_places=2, default=0, verbose_name="Mục tiêu Nợ ngân hàng Năm")
    month_bank_debt_target = models.DecimalField(max_digits=18, decimal_places=2, default=0, verbose_name="Mục tiêu Nợ ngân hàng Tháng")

    year_opex_target = models.DecimalField(max_digits=18, decimal_places=2, default=0, verbose_name="Mục tiêu Chi phí vận hành Năm")
    month_opex_target = models.DecimalField(max_digits=18, decimal_places=2, default=0, verbose_name="Mục tiêu Chi phí vận hành Tháng")

    note = models.TextField(null=True, blank=True, verbose_name="Ghi chú")
    updated_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, verbose_name="Kế toán cập nhật")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Chỉ tiêu Kế hoạch BU"
        verbose_name_plural = "Bảng Quản lý Chỉ tiêu Kế hoạch (Targets)"
        unique_together = ('business_unit', 'month', 'year')

    def __str__(self):
        bu_code = self.business_unit.code if self.business_unit else "TỔNG TOÀN CÔNG TY"
        return f"Mục tiêu {bu_code} - Th{self.month}/{self.year}"


class ManualAdjustment(models.Model):
    METRIC_CHOICES = (
        ('REVENUE', 'Doanh thu MTD'),
        ('COLLECTION', 'Thu tiền MTD'),
        ('RECEIVABLES_DUE', 'Phải thu trong hạn'),
        ('RECEIVABLES_OVERDUE', 'Phải thu quá hạn'),
        ('PAYABLES', 'Phải trả nhà cung cấp'),
        ('INVENTORY', 'Hàng tồn kho'),
        ('CASH', 'Tiền cuối kỳ'),
        ('BANK_DEBT', 'Nợ ngân hàng'),
        ('OPEX', 'Chi phí vận hành OPEX'),
    )
    ADJUSTMENT_TYPES = (
        ('ADDITION', 'Cộng (+)'),
        ('DEDUCTION', 'Trừ (-)'),
        ('OVERWRITE', 'Ghi đè (=)'),
    )
    business_unit = models.ForeignKey(
        BusinessUnit,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        verbose_name="Đơn vị kinh doanh (Null = Tổng)"
    )
    month = models.PositiveSmallIntegerField(verbose_name="Tháng")
    year = models.PositiveIntegerField(verbose_name="Năm")
    metric_type = models.CharField(max_length=50, choices=METRIC_CHOICES, verbose_name="Chỉ tiêu tài chính")
    adjustment_type = models.CharField(max_length=20, choices=ADJUSTMENT_TYPES, default='ADDITION', verbose_name="Loại điều chỉnh")
    amount = models.DecimalField(max_digits=18, decimal_places=2, default=0, verbose_name="Số tiền điều chỉnh (VNĐ)")
    reason = models.CharField(max_length=500, verbose_name="Lý do điều chỉnh (e.g. Doanh thu Elevator Hisa-FJT ngoài MISA)")
    source_file = models.FileField(upload_to='adjustments_files/', null=True, blank=True, verbose_name="File đính kèm / Chứng từ")
    is_active = models.BooleanField(default=True, verbose_name="Kích hoạt (Bật/Tắt)")
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, verbose_name="Kế toán tạo")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Thời gian tạo")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Thời gian cập nhật")

    class Meta:
        verbose_name = "Điều chỉnh Phát sinh Ngoại bảng"
        verbose_name_plural = "Bảng Điều chỉnh Phát sinh Ngoại bảng (Off-MISA)"

    def __str__(self):
        bu_code = self.business_unit.code if self.business_unit else "TỔNG TOÀN CÔNG TY"
        return f"Điều chỉnh {self.get_metric_type_display()} {bu_code} - Th{self.month}/{self.year}: {self.amount:,.0f} VNĐ"


class ImportLog(models.Model):
    STATUS_CHOICES = (
        ('SUCCESS', '✅'),
        ('ERROR', '❌'),
        ('NOTFOUND', '⚠️'),
    )
    file_name = models.CharField(max_length=255, verbose_name="Tên file / Tiến trình")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, verbose_name="Trạng thái")
    message = models.TextField(verbose_name="Nội dung chi tiết")
    start_time = models.DateTimeField(verbose_name="Thời gian bắt đầu", null=True, blank=True)
    end_time = models.DateTimeField(verbose_name="Thời gian hoàn thành", null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Thời gian tạo")

    class Meta:
        verbose_name = "Lịch sử Import"
        verbose_name_plural = "Lịch sử Import dữ liệu"
        ordering = ['-start_time', '-created_at']

    def __str__(self):
        from django.utils import timezone
        local_time = timezone.localtime(self.start_time) if self.start_time else None
        start_str = local_time.strftime('%Y-%m-%d %H:%M:%S') if local_time else 'N/A'
        return f"{self.file_name} - {self.status} - {start_str}"
