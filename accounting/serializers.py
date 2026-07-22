from rest_framework import serializers
from .models import (
    BUPerformance, BUPerformanceDaily, Branch, PurchaseDetail, Warehouse, Customer, Employee, InventorySummary,
    Product, BusinessUnit, SalesTransaction, Supplier, SupplierDebt, SupplierGroup, AccountDetail, ReceivablesAgeing
)

class BranchSerializer(serializers.ModelSerializer):
    class Meta:
        model = Branch
        fields = '__all__'

class WarehouseSerializer(serializers.ModelSerializer):
    class Meta:
        model = Warehouse
        fields = '__all__'

class CustomerSerializer(serializers.ModelSerializer):
    class Meta:
        model = Customer
        fields = '__all__'

class EmployeeSerializer(serializers.ModelSerializer):
    class Meta:
        model = Employee
        fields = '__all__'

class ProductSerializer(serializers.ModelSerializer):
    class Meta:
        model = Product
        fields = '__all__'

class BusinessUnitSerializer(serializers.ModelSerializer):
    class Meta:
        model = BusinessUnit
        fields = '__all__'

class SalesTransactionSerializer(serializers.ModelSerializer):
    # Hiển thị tên thay vì ID khi xem chi tiết (Read-only)
    customer_name = serializers.ReadOnlyField(source='customer.name')
    product_name = serializers.ReadOnlyField(source='product.name')
    employee_name = serializers.ReadOnlyField(source='employee.name')
    bu_manager = serializers.ReadOnlyField(source='business_unit.manager')

    class Meta:
        model = SalesTransaction
        fields = '__all__'

class SupplierDebtSerializer(serializers.ModelSerializer):
    supplier_name = serializers.CharField(source='supplier.name', read_only=True)
    supplier_code = serializers.CharField(source='supplier.code', read_only=True)

    class Meta:
        model = SupplierDebt
        fields = '__all__'

class SupplierGroupSerializer(serializers.ModelSerializer):
    class Meta:
        model = SupplierGroup
        fields = '__all__'

class SupplierSerializer(serializers.ModelSerializer):
    class Meta:
        model = Supplier
        fields = '__all__'

class AccountDetailSerializer(serializers.ModelSerializer):
    branch_name = serializers.CharField(source='branch.name', read_only=True)
    business_unit_code = serializers.CharField(source='business_unit.code', read_only=True)

    class Meta:
        model = AccountDetail
        fields = '__all__'

class ReceivablesAgeingSerializer(serializers.ModelSerializer):
    customer_code = serializers.CharField(source='customer.code', read_only=True)
    customer_name = serializers.CharField(source='customer.name', read_only=True)
    branch_name = serializers.CharField(source='branch.name', read_only=True)

    class Meta:
        model = ReceivablesAgeing
        fields = '__all__'

class PurchaseDetailSerializer(serializers.ModelSerializer):
    supplier_info = SupplierSerializer(source='supplier', read_only=True)
    bu_info = BusinessUnitSerializer(source='business_unit', read_only=True)
    product_name = serializers.ReadOnlyField(source='product.name')
    warehouse_name = serializers.ReadOnlyField(source='warehouse.name')

    class Meta:
        model = PurchaseDetail
        fields = '__all__'

class BUPerformanceSerializer(serializers.ModelSerializer):
    bu_name = serializers.SerializerMethodField()
    bu_code = serializers.SerializerMethodField()
    
    # Tính % hoàn thành kế hoạch
    revenue_kpi = serializers.SerializerMethodField()
    collection_kpi = serializers.SerializerMethodField()
    inventory_vs_plan = serializers.SerializerMethodField()

    class Meta:
        model = BUPerformance
        fields = '__all__' # Hoặc liệt kê cụ thể các trường

    def _calculate_ratio(self, actual, plan):
        if plan and plan > 0:
            return round((actual / plan) * 100, 2)
        return 0

    def get_bu_name(self, obj):
        return obj.business_unit.name if obj.business_unit else "Tổng công ty"

    def get_bu_code(self, obj):
        return obj.business_unit.code if obj.business_unit else "Global"

    def get_revenue_kpi(self, obj):
        return self._calculate_ratio(obj.mtd_revenue_actual, obj.mtd_revenue_plan)

    def get_collection_kpi(self, obj):
        return self._calculate_ratio(obj.mtd_collection_actual, obj.mtd_collection_plan)

    def get_inventory_vs_plan(self, obj):
        return self._calculate_ratio(obj.inventory_value_actual, obj.inventory_value_plan)
    
class BUPerformanceDailySerializer(serializers.ModelSerializer):
    bu_code = serializers.CharField(source='performance_month.business_unit.code', read_only=True)
    
    class Meta:
        model = BUPerformanceDaily
        fields = [
            'id', 
            'date', 
            'daily_revenue', 
            'daily_collection', 
            'bu_code'
        ]


class PerformanceUpdateSerializer(serializers.Serializer):
    bu_id = serializers.IntegerField(required=False, allow_null=True)
    month = serializers.IntegerField(min_value=1, max_value=12, required=False)
    year = serializers.IntegerField(min_value=2000, required=False)
    target_date = serializers.DateField(required=False, format="%Y-%m-%d")


class InventorySummarySerializer(serializers.ModelSerializer):
    class Meta:
        model = InventorySummary
        fields = '__all__'


class GoogleLoginSerializer(serializers.Serializer):
    id_token = serializers.CharField(required=True, help_text="Google ID token (JWT) trả về từ Google Sign-In SDK trên Frontend")


class SendEmailSerializer(serializers.Serializer):
    file = serializers.FileField(required=False, allow_null=True)
    file_name = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    from_name = serializers.CharField(required=False, allow_blank=True, allow_null=True, help_text="Tên hiển thị người gửi (Alias/Display Name)")
    from_email = serializers.EmailField(required=False, allow_blank=True, allow_null=True, help_text="Địa chỉ email phản hồi (Reply-To)")
    to_emails = serializers.CharField(required=True)
    subject = serializers.CharField(required=True)
    message = serializers.CharField(required=True)

    def validate_to_emails(self, value):
        if not value:
            raise serializers.ValidationError("Danh sách email nhận không được để trống.")
        
        # Hỗ trợ phân tách nếu là chuỗi phân tách bằng dấu phẩy
        if isinstance(value, str):
            emails = [email.strip() for email in value.split(',') if email.strip()]
        elif isinstance(value, list):
            emails = [email.strip() for email in value if isinstance(email, str) and email.strip()]
        else:
            raise serializers.ValidationError("to_emails phải là dạng danh sách hoặc chuỗi phân tách bằng dấu phẩy.")
            
        if not emails:
            raise serializers.ValidationError("Không tìm thấy địa chỉ email nhận hợp lệ.")
            
        from django.core.validators import validate_email
        from django.core.exceptions import ValidationError
        for email in emails:
            try:
                validate_email(email)
            except ValidationError:
                raise serializers.ValidationError(f"Địa chỉ email không hợp lệ: {email}")
        return emails

    def validate_file(self, value):
        if value:
            # Giới hạn 20MB = 20 * 1024 * 1024 bytes
            max_size = 20 * 1024 * 1024
            if value.size > max_size:
                raise serializers.ValidationError("Kích thước file đính kèm không được vượt quá 20MB.")
        return value