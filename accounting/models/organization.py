from django.db import models

class Branch(models.Model):
    name = models.CharField(max_length=255, verbose_name="Chi nhánh")
    
    def __str__(self):
        return self.name

class Warehouse(models.Model):
    code = models.CharField(max_length=50, unique=True, verbose_name="Mã kho")
    name = models.CharField(max_length=255, verbose_name="Tên kho")
    business_unit = models.ForeignKey(
        "BusinessUnit",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='warehouses',
        verbose_name="Đơn vị kinh doanh sở hữu"
    )

    inventory_value_plan = models.DecimalField(max_digits=18, decimal_places=2, default=0, verbose_name="Giá trị tồn kho (Kế hoạch)")
    inventory_value_actual = models.DecimalField(max_digits=18, decimal_places=2, default=0, verbose_name="Giá trị tồn kho (Thực tế)")
    inventory_opening_value = models.DecimalField(max_digits=18, decimal_places=2, default=0, verbose_name="Giá trị tồn kho đầu kỳ")
    inventory_in_value = models.DecimalField(max_digits=18, decimal_places=2, default=0, verbose_name="Giá trị nhập kho trong kỳ")
    inventory_out_value = models.DecimalField(max_digits=18, decimal_places=2, default=0, verbose_name="Giá trị xuất kho trong kỳ")
    
    def __str__(self):
        return f"{self.code} - {self.name}"
    
    class Meta:
        verbose_name = "Kho"
        verbose_name_plural = "Danh mục kho"

class CustomerGroup(models.Model):
    code = models.CharField(max_length=50, unique=True, verbose_name="Mã nhóm khách hàng")
    name = models.CharField(max_length=255, verbose_name="Tên nhóm khách hàng")

    def __str__(self):
        return self.name

    class Meta:
        verbose_name = "Nhóm khách hàng"
        verbose_name_plural = "Danh mục nhóm khách hàng"
    
class Customer(models.Model):
    code = models.CharField(max_length=50, unique=True, verbose_name="Mã khách hàng")
    name = models.CharField(max_length=255, verbose_name="Tên khách hàng")
    group = models.ForeignKey(CustomerGroup, on_delete=models.PROTECT, null=True, blank=True)
    address = models.TextField(verbose_name="Địa điểm giao hàng")
    business_unit = models.ForeignKey(
        "BusinessUnit", 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True, 
        verbose_name="Đơn vị kinh doanh quản lý"
    )
    assigned_employee = models.ForeignKey(
        "Employee",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="assigned_customers",
        verbose_name="Nhân viên Sales phụ trách"
    )

    has_revenue = models.BooleanField(
        default=True,
        verbose_name="Có ghi nhận doanh thu"
    )

    def __str__(self):
        return f"{self.code} - {self.name}"

    class Meta:
        verbose_name = "Khách hàng"
        verbose_name_plural = "Danh mục khách hàng"
    

class MaterialGroup(models.Model):
    code = models.CharField(max_length=50, unique=True, verbose_name="Mã nhóm VTHH")
    name = models.CharField(max_length=255, verbose_name="Tên nhóm VTHH")
    origin = models.CharField(max_length=100, verbose_name="Nguồn gốc")

    def __str__(self):
        return self.name
    
class Product(models.Model):
    code = models.CharField(max_length=100, unique=True, verbose_name="Mã hàng")
    name = models.CharField(max_length=255, verbose_name="Tên hàng")
    unit = models.CharField(max_length=20, verbose_name="ĐVT")
    group = models.ForeignKey(MaterialGroup, on_delete=models.CASCADE, verbose_name="Nhóm VTHH")
    brand = models.CharField(max_length=100, blank=True, verbose_name="Nhãn hiệu (Trường mở rộng)")
    selling_price = models.DecimalField(max_digits=15, decimal_places=2, default=0, verbose_name="Đơn giá bán")

    def __str__(self):
        return self.code
    
class BusinessUnit(models.Model):
    code = models.CharField(max_length=50, unique=True, verbose_name="Mã thống kê")
    name = models.CharField(max_length=255, verbose_name="Tên thống kê")
    manager = models.CharField(max_length=255, verbose_name="Trưởng BU", null=True, blank=True)
    parent = models.ForeignKey(
        "self",
        null=True,
        blank=True,
        on_delete=models.CASCADE,
        related_name="children"
    )
    is_main = models.BooleanField(default=False, verbose_name="BU chính")

    def get_all_descendant_ids(self):
        ids = [self.id]
        for child in self.children.all():
            ids.extend(child.get_all_descendant_ids())
        return ids

    def __str__(self):
        return f"{self.code} - {self.name}"
