from django.db import models
from .organization import Customer, Product, Employee, Warehouse, Branch, BusinessUnit

class SalesTransaction(models.Model):
    posting_date = models.DateField(verbose_name="Ngày hạch toán")
    doc_id = models.CharField(max_length=100, verbose_name="Số chứng từ")
    
    customer = models.ForeignKey(Customer, on_delete=models.CASCADE, verbose_name="Khách hàng")
    product = models.ForeignKey(Product, on_delete=models.CASCADE, verbose_name="Hàng hóa")
    employee = models.ForeignKey(Employee, on_delete=models.SET_NULL, null=True, verbose_name="Nhân viên")
    warehouse = models.ForeignKey(Warehouse, on_delete=models.SET_NULL, null=True, verbose_name="Kho")
    branch = models.ForeignKey(Branch, on_delete=models.SET_NULL, null=True, verbose_name="Chi nhánh")
    business_unit = models.ForeignKey(BusinessUnit, on_delete=models.SET_NULL, null=True, verbose_name="BU")

    quantity = models.FloatField(default=0, verbose_name="Tổng số lượng bán")
    unit_price = models.DecimalField(max_digits=15, decimal_places=2, default=0, verbose_name="Đơn giá")
    sales_amount = models.DecimalField(max_digits=15, decimal_places=2, default=0, verbose_name="Doanh số bán")
    tax_percent = models.FloatField(default=0, verbose_name="% Thuế")
    tax_amount = models.DecimalField(max_digits=15, decimal_places=2, default=0, verbose_name="Thuế GTGT")
    
    debit_acc = models.CharField(max_length=20, verbose_name="TK Nợ")
    credit_acc = models.CharField(max_length=20, verbose_name="TK Có")
    discount_acc = models.CharField(max_length=20, null=True, blank=True, verbose_name="TK Chiết khấu")
    discount_amount = models.DecimalField(max_digits=15, decimal_places=2, default=0, verbose_name="Chiết khấu")

    actual_sales = models.DecimalField(max_digits=15, decimal_places=2, default=0, verbose_name="Doanh số thực tế")

    def __str__(self):
        return f"{self.doc_id} - {self.customer.name}"
    
    class Meta:
        verbose_name = "Chi tiết bán hàng"
        verbose_name_plural = "Bảng chi tiết bán hàng"


class AccountDetail(models.Model):
    posting_date = models.DateField(verbose_name="Ngày hạch toán", null=True, blank=True)
    doc_id = models.CharField(max_length=50, verbose_name="Số chứng từ")
    
    account_number = models.CharField(max_length=20, verbose_name="Tài khoản")
    account_name = models.CharField(max_length=255, verbose_name="Tên tài khoản")
    offset_account = models.CharField(max_length=20, verbose_name="TK đối ứng", null=True, blank=True)
    
    debit_amount = models.DecimalField(max_digits=18, decimal_places=2, default=0, verbose_name="Phát sinh Nợ")
    credit_amount = models.DecimalField(max_digits=18, decimal_places=2, default=0, verbose_name="Phát sinh Có")
    balance_debit = models.DecimalField(max_digits=18, decimal_places=2, default=0, verbose_name="Dư Nợ")
    balance_credit = models.DecimalField(max_digits=18, decimal_places=2, default=0, verbose_name="Dư Có")
    
    business_unit = models.ForeignKey(BusinessUnit, on_delete=models.SET_NULL, null=True, blank=True, verbose_name="Mã thống kê")
    branch = models.ForeignKey(Branch, on_delete=models.SET_NULL, null=True, blank=True, verbose_name="Chi nhánh")
    
    unit_code = models.CharField(max_length=50, verbose_name="Mã đơn vị", null=True, blank=True)
    unit_name = models.CharField(max_length=255, verbose_name="Tên đơn vị", null=True, blank=True)
    unreasonable_cost = models.BooleanField(default=False, verbose_name="CP không hợp lý")

    customer = models.ForeignKey(
        Customer,
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True, 
        verbose_name="Khách hàng (Đối tượng)"
    )

    class Meta:
        verbose_name = "Sổ chi tiết các tài khoản 111, 112, 341"
        verbose_name_plural = "Sổ chi tiết các tài khoản 111, 112, 341"


class BankBalance(models.Model):
    bank_account_number = models.CharField(max_length=50, verbose_name="Số tài khoản ngân hàng")
    bank_name = models.CharField(max_length=255, verbose_name="Tên ngân hàng")
    opening_balance = models.DecimalField(max_digits=18, decimal_places=2, default=0, verbose_name="Số dư đầu kỳ")
    debit_amount = models.DecimalField(max_digits=18, decimal_places=2, default=0, verbose_name="Phát sinh Nợ")
    credit_amount = models.DecimalField(max_digits=18, decimal_places=2, default=0, verbose_name="Phát sinh Có")
    balance = models.DecimalField(max_digits=18, decimal_places=2, default=0, verbose_name="Số dư cuối kỳ")
    reporting_month = models.CharField(max_length=7, db_index=True, verbose_name="Tháng báo cáo")

    class Meta:
        verbose_name = "Bảng kê số dư ngân hàng"
        verbose_name_plural = "Bảng kê số dư ngân hàng"
        unique_together = ('bank_account_number', 'reporting_month')

    def __str__(self):
        return f"{self.bank_account_number} - {self.reporting_month}: {self.balance:,.2f}"
