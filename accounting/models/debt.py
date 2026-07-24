from django.db import models
from .organization import Customer, Branch, BusinessUnit, Warehouse, Product, Employee

class SupplierGroup(models.Model):
    code = models.CharField(max_length=50, unique=True, verbose_name="Mã nhóm NCC")
    name = models.CharField(max_length=255, verbose_name="Tên nhóm NCC", null=True, blank=True)

    def __str__(self):
        return self.code

class Supplier(models.Model):
    code = models.CharField(max_length=50, unique=True, verbose_name="Mã nhà cung cấp")
    name = models.CharField(max_length=255, verbose_name="Tên nhà cung cấp")
    group = models.ForeignKey(SupplierGroup, on_delete=models.SET_NULL, null=True, blank=True, related_name='suppliers')

    def __str__(self):
        return f"{self.code} - {self.name}"

class SupplierDebt(models.Model):
    supplier = models.ForeignKey(Supplier, on_delete=models.CASCADE, verbose_name="Nhà cung cấp")
    
    opening_debit = models.DecimalField(max_digits=18, decimal_places=2, default=0, verbose_name="Đầu kỳ - Nợ")
    opening_credit = models.DecimalField(max_digits=18, decimal_places=2, default=0, verbose_name="Đầu kỳ - Có")
    
    incurred_debit = models.DecimalField(max_digits=18, decimal_places=2, default=0, verbose_name="Phát sinh - Nợ")
    incurred_credit = models.DecimalField(max_digits=18, decimal_places=2, default=0, verbose_name="Phát sinh - Có")
    
    closing_debit = models.DecimalField(max_digits=18, decimal_places=2, default=0, verbose_name="Cuối kỳ - Nợ")
    closing_credit = models.DecimalField(max_digits=18, decimal_places=2, default=0, verbose_name="Cuối kỳ - Có")
    
    created_at = models.DateTimeField(auto_now_add=True)
    reporting_period = models.CharField(max_length=7, db_index=True, blank=True, null=True, verbose_name="Kỳ báo cáo")

    class Meta:
        verbose_name = "Công nợ NCC"
        verbose_name_plural = "Bảng công nợ nhà cung cấp"

    def __str__(self):
        return f"{self.supplier}"


class ReceivablesAgeing(models.Model):
    customer = models.ForeignKey(Customer, on_delete=models.CASCADE, verbose_name="Khách hàng")
    branch = models.ForeignKey(Branch, on_delete=models.SET_NULL, null=True, blank=True, verbose_name="Chi nhánh")
    
    doc_date = models.DateField(verbose_name="Ngày chứng từ", null=True, blank=True)
    
    total_debt = models.DecimalField(max_digits=18, decimal_places=2, default=0, verbose_name="Tổng nợ")
    no_due_limit = models.DecimalField(max_digits=18, decimal_places=2, default=0, verbose_name="Không có hạn nợ")
    
    due_0_7 = models.DecimalField(max_digits=18, decimal_places=2, default=0, verbose_name="Trước hạn 0-7 ngày")
    due_8_14 = models.DecimalField(max_digits=18, decimal_places=2, default=0, verbose_name="Trước hạn 8-14 ngày")
    due_15_21 = models.DecimalField(max_digits=18, decimal_places=2, default=0, verbose_name="Trước hạn 15-21 ngày")
    due_22_28 = models.DecimalField(max_digits=18, decimal_places=2, default=0, verbose_name="Trước hạn 22-28 ngày")
    due_29_60 = models.DecimalField(max_digits=18, decimal_places=2, default=0, verbose_name="Trước hạn 29-60 ngày")
    due_above_60 = models.DecimalField(max_digits=18, decimal_places=2, default=0, verbose_name="Trước hạn trên 60 ngày")
    due_total = models.DecimalField(max_digits=18, decimal_places=2, default=0, verbose_name="Tổng nợ trước hạn")
    
    overdue_0_14 = models.DecimalField(max_digits=18, decimal_places=2, default=0, verbose_name="Quá hạn 0-14 ngày")
    overdue_15_30 = models.DecimalField(max_digits=18, decimal_places=2, default=0, verbose_name="Quá hạn 15-30 ngày")
    overdue_31_45 = models.DecimalField(max_digits=18, decimal_places=2, default=0, verbose_name="Quá hạn 31-45 ngày")
    overdue_46_60 = models.DecimalField(max_digits=18, decimal_places=2, default=0, verbose_name="Quá hạn 46-60 ngày")
    overdue_61_90 = models.DecimalField(max_digits=18, decimal_places=2, default=0, verbose_name="Quá hạn 61-90 ngày")
    overdue_91_120 = models.DecimalField(max_digits=18, decimal_places=2, default=0, verbose_name="Quá hạn 91-120 ngày")
    overdue_above_120 = models.DecimalField(max_digits=18, decimal_places=2, default=0, verbose_name="Quá hạn trên 120 ngày")
    overdue_total = models.DecimalField(max_digits=18, decimal_places=2, default=0, verbose_name="Tổng nợ quá hạn")
    reporting_period = models.CharField(max_length=7, db_index=True, blank=True, null=True, verbose_name="Kỳ báo cáo")

    class Meta:
        verbose_name = "Chi tiết tuổi nợ"
        verbose_name_plural = "Bảng chi tiết tuổi nợ"


class PurchaseDetail(models.Model):
    posting_date = models.DateField(verbose_name="Ngày hạch toán")
    doc_date = models.DateField(verbose_name="Ngày chứng từ")
    doc_number = models.CharField(max_length=100, verbose_name="Số chứng từ")
    description = models.TextField(null=True, blank=True, verbose_name="Diễn giải")
    
    supplier = models.ForeignKey(Supplier, on_delete=models.CASCADE, verbose_name="Nhà cung cấp")
    warehouse = models.ForeignKey(Warehouse, on_delete=models.CASCADE, verbose_name="Kho", null=True, blank=True)
    product = models.ForeignKey(Product, on_delete=models.CASCADE, verbose_name="Hàng hóa")
    business_unit = models.ForeignKey(BusinessUnit, on_delete=models.SET_NULL, null=True, blank=True, verbose_name="Mã thống kê (BU)")
    
    org_unit_code = models.CharField(max_length=100, null=True, blank=True, verbose_name="Mã đơn vị")
    org_unit_name = models.CharField(max_length=255, null=True, blank=True, verbose_name="Tên đơn vị")
    
    quantity = models.DecimalField(max_digits=18, decimal_places=2, default=0)
    unit_price = models.DecimalField(max_digits=18, decimal_places=2, default=0)
    purchase_value = models.DecimalField(max_digits=18, decimal_places=2, default=0)
    vat_value = models.DecimalField(max_digits=18, decimal_places=2, default=0)
    total_value = models.DecimalField(max_digits=18, decimal_places=2, default=0)
    
    debit_account = models.CharField(max_length=20)
    credit_account = models.CharField(max_length=20)

    class Meta:
        verbose_name = "Chi tiết mua hàng"
        verbose_name_plural = "Sổ chi tiết mua hàng"
