from django.contrib import admin
from import_export.admin import ImportExportModelAdmin
from .models import (
    BUPerformance, BUPerformanceDaily, Branch, PurchaseDetail, Warehouse, Customer, Employee, 
    Department, JobTitle, EmployeeAssignment,
    Product, BusinessUnit, SalesTransaction, Supplier, SupplierDebt, SupplierGroup,
    AccountDetail, ReceivablesAgeing, InventorySummary, ImportLog, CustomerGroup, BankBalance,
    BUTargetPlan, ManualAdjustment
)
from .resources import (
    PurchaseDetailResource, SalesTransactionResource, SupplierDebtResource, 
    AccountDetailResource, ReceivablesAgeingResource, InventorySummaryResource,
    CustomerResource
)
from .tasks import update_single_bu_performance, sync_warehouse_inventory_data
from django.contrib import admin, messages
from datetime import datetime
import calendar

# Cấu hình hiển thị cho BusinessUnit (Có trưởng BU)
@admin.register(BusinessUnit)
class BusinessUnitAdmin(admin.ModelAdmin):
    list_display = ('code', 'name', 'manager')
    search_fields = ('code', 'name', 'manager')

# Cấu hình hiển thị cho Giao dịch bán hàng
@admin.register(SalesTransaction)
class SalesTransactionAdmin(ImportExportModelAdmin):
    resource_class = SalesTransactionResource
    # 1. Các cột hiển thị ngoài danh sách
    list_display = (
        'doc_id', 'posting_date', 'customer', 'product', 
        'quantity', 'sales_amount', 'actual_sales', 'employee'
    )
    
    # 2. Bộ lọc nhanh bên tay phải
    list_filter = ('posting_date', 'branch', 'warehouse', 'business_unit')
    
    # 3. Ô tìm kiếm
    search_fields = ('doc_id', 'customer__name', 'product__name', 'employee__name')
    
    # 4. Gom nhóm các trường khi chỉnh sửa/thêm mới
    fieldsets = (
        ('Thông tin chứng từ', {
            'fields': ('posting_date', 'doc_id', 'branch', 'warehouse', 'business_unit')
        }),
        ('Thông tin đối tượng', {
            'fields': ('customer', 'product', 'employee')
        }),
        ('Số liệu tài chính', {
            'fields': (
                ('quantity', 'unit_price'), 
                ('sales_amount', 'actual_sales'),
                ('tax_percent', 'tax_amount'),
                ('discount_amount', 'discount_acc')
            )
        }),
        ('Kế toán', {
            'fields': ('debit_acc', 'credit_acc'),
            'classes': ('collapse',), # Cho phép ẩn/hiện cho gọn
        }),
    )

# Đăng ký các bảng danh mục còn lại một cách nhanh chóng
@admin.register(CustomerGroup)
class CustomerGroupAdmin(admin.ModelAdmin):
    list_display = ('code', 'name')
    search_fields = ('code', 'name')

@admin.register(Customer)
class CustomerAdmin(ImportExportModelAdmin):
    resource_class = CustomerResource
    list_display = ('code', 'name', 'group_name')
    search_fields = ('code', 'name', 'group__name')

    @admin.display(description="Nhóm khách hàng", ordering="group__name")
    def group_name(self, obj):
        return obj.group.name if obj.group else "-"

@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ('code', 'name', 'unit')
    search_fields = ('code', 'name')

admin.site.register(Branch)
@admin.register(Warehouse)
class WarehouseAdmin(admin.ModelAdmin):
    list_display = (
        'code', 'name', 'business_unit', 
        'inventory_opening_value', 'inventory_in_value', 
        'inventory_out_value', 'inventory_value_actual'
    )
    list_filter = ('business_unit',)
    search_fields = ('code', 'name', 'business_unit__code', 'business_unit__name')
    actions = ['trigger_sync_inventory']

    @admin.action(description='🔄 Đồng bộ tồn kho từ Inventory Summary')
    def trigger_sync_inventory(self, request, queryset):
        # queryset chứa các Warehouse được tích chọn
        count = queryset.count()
        
        # Gọi hàm xử lý (có thể truyền queryset vào hàm hoặc xử lý tại đây)
        for wh in queryset:
            # Bạn có thể gọi trực tiếp logic tính toán cho từng kho
            from django.db.models import Sum
            from .models import InventorySummary
            
            data = InventorySummary.objects.filter(warehouse=wh).aggregate(
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

        self.message_user(
            request, 
            f"Đã cập nhật dữ liệu tồn kho thành công cho {count} kho.", 
            messages.SUCCESS
        )
@admin.register(Department)
class DepartmentAdmin(admin.ModelAdmin):
    list_display = ('department_code', 'department_name', 'parent_department')
    search_fields = ('department_code', 'department_name')
    list_filter = ('parent_department',)


@admin.register(JobTitle)
class JobTitleAdmin(admin.ModelAdmin):
    list_display = ('title_id', 'title_name')
    search_fields = ('title_name',)


class EmployeeAssignmentInline(admin.TabularInline):
    model = EmployeeAssignment
    extra = 1
    fields = ('department', 'title', 'start_date', 'end_date')


@admin.register(Employee)
class EmployeeAdmin(admin.ModelAdmin):
    list_display = ('employee_code', 'full_name', 'gender', 'date_of_birth', 'identity_number', 'phone_number', 'email', 'is_active')
    search_fields = ('employee_code', 'full_name', 'identity_number', 'email', 'phone_number')
    list_filter = ('gender', 'is_active')
    inlines = [EmployeeAssignmentInline]


@admin.register(EmployeeAssignment)
class EmployeeAssignmentAdmin(admin.ModelAdmin):
    list_display = ('assignment_id', 'employee', 'department', 'title', 'start_date', 'end_date')
    search_fields = ('employee__employee_code', 'employee__full_name', 'department__department_name', 'title__title_name')
    list_filter = ('department', 'title', 'start_date', 'end_date')

class BUPerformanceDailyInline(admin.TabularInline):
    model = BUPerformanceDaily
    extra = 0 # Không hiện các dòng trống để thêm mới
    fields = ('date', 'daily_revenue', 'daily_collection', 'daily_opex_plan', 'daily_opex_actual')
    readonly_fields = ('date', 'daily_revenue', 'daily_collection', 'daily_opex_actual')
    can_delete = False
    
    # Sắp xếp ngày mới nhất lên đầu
    ordering = ('-date',)

@admin.register(BUPerformance)
class BUPerformanceAdmin(admin.ModelAdmin):
    list_display = ('__str__', 'opex_plan', 'opex_actual', 'mtd_revenue_actual', 'mtd_collection_actual', 'year', 'month')
    list_filter = ('year', 'month', 'business_unit')
    inlines = [BUPerformanceDailyInline]
    
    def save_related(self, request, form, formsets, change):
        # 1. Lưu formset của các ngày trước để cập nhật DB
        super().save_related(request, form, formsets, change)
        
        obj = form.instance
        daily_formset = formsets[0]  # BUPerformanceDailyInline
        
        # Đếm số ngày trong tháng
        import calendar
        days_in_month = calendar.monthrange(obj.year, obj.month)[1]
        
        # 2. Xử lý đồng bộ 2 chiều:
        # TH 1: Người dùng chỉnh sửa chi tiết Kế hoạch ngày (daily_opex_plan) trong Formset
        daily_changed = False
        for f in daily_formset.forms:
            if f.has_changed() and 'daily_opex_plan' in f.changed_data:
                daily_changed = True
                break
                
        if daily_changed:
            # Cộng dồn tất cả các ngày con để cập nhật ngược lại opex_plan của dòng cha
            total_plan = sum(d.daily_opex_plan for d in obj.daily_logs.all())
            if obj.opex_plan != total_plan:
                obj.opex_plan = total_plan
                obj.save(update_fields=['opex_plan'])
                
        # TH 2: Người dùng sửa Kế hoạch tháng (opex_plan) trên bảng cha
        elif 'opex_plan' in form.changed_data:
            # Chia đều kế hoạch tháng cho số ngày
            daily_plan_val = obj.opex_plan / days_in_month
            obj.daily_logs.all().update(daily_opex_plan=daily_plan_val)
    actions = ['trigger_update_data', 'recalculate_company_total']

    @admin.action(description='🚀 Cập nhật số liệu thực tế (Tháng & Ngày)')
    def trigger_update_data(self, request, queryset):
        success_count = 0
        today = datetime.now().date()
        
        for obj in queryset:
            try:
                # 1. Xác định ngày mục tiêu (target_date)
                # Nếu là tháng/năm hiện tại thì lấy ngày hôm nay
                if obj.month == today.month and obj.year == today.year:
                    target_date = today
                else:
                    # Nếu là tháng cũ, lấy ngày cuối cùng của tháng đó để chốt số liệu
                    last_day = calendar.monthrange(obj.year, obj.month)[1]
                    target_date = datetime(obj.year, obj.month, last_day).date()

                # 2. Gọi hàm xử lý (nên dùng .delay nếu chạy qua Celery)
                # Ở đây gọi trực tiếp để tránh lỗi kết nối Redis nếu hệ thống chưa ổn định
                update_single_bu_performance(
                    bu_id=obj.business_unit.id if obj.business_unit else None,
                    month=obj.month,
                    year=obj.year,
                    target_date_str=target_date.strftime('%Y-%m-%d')
                )
                
                success_count += 1
            except Exception as e:
                self.message_user(
                    request, 
                    f"Lỗi khi cập nhật dòng {obj}: {str(e)}", 
                    messages.ERROR
                )
                continue

        self.message_user(
            request, 
            f"Đã cập nhật thành công số liệu cho {success_count} mục (Bao gồm bảng Tháng và Ngày).", 
            messages.SUCCESS
        )

    @admin.action(description='🏢 Cập nhật Số liệu Tổng Toàn Công Ty (TOTAL_CORP)')
    def recalculate_company_total(self, request, queryset):
        periods = set((obj.month, obj.year) for obj in queryset)
        for m, y in periods:
            update_single_bu_performance(None, month=m, year=y)
        self.message_user(
            request, 
            f"✅ Đã cập nhật thành công Số liệu Tổng Toàn Công Ty cho {len(periods)} kỳ báo cáo chọn!", 
            messages.SUCCESS
        )

@admin.register(SupplierDebt)
class SupplierDebtAdmin(ImportExportModelAdmin):
    resource_class = SupplierDebtResource
    list_display = ('supplier', 'opening_debit', 'opening_credit', 'incurred_debit', 'incurred_credit', 'closing_debit', 'closing_credit')
    search_fields = ('supplier__code', 'supplier__name')

admin.site.register(Supplier)
admin.site.register(SupplierGroup)

@admin.register(AccountDetail)
class AccountDetailAdmin(ImportExportModelAdmin):
    resource_class = AccountDetailResource
    list_display = ('posting_date', 'doc_id', 'account_number', 'debit_amount', 'credit_amount', 'branch', 'business_unit')
    list_filter = ('branch', 'business_unit', 'account_number')
    search_fields = ('doc_id', 'account_number')
    

@admin.register(ReceivablesAgeing)
class ReceivablesAgeingAdmin(ImportExportModelAdmin):
    resource_class = ReceivablesAgeingResource
    list_display = ('customer', 'doc_date', 'total_debt', 'overdue_total', 'branch')
    search_fields = ('customer__name', 'customer__code')
    list_filter = ('branch', 'doc_date')

@admin.register(InventorySummary)
class InventorySummaryAdmin(ImportExportModelAdmin):
    resource_class = InventorySummaryResource
    list_display = ('warehouse', 'product', 'opening_quantity', 'closing_quantity', 'closing_value')
    list_filter = ('warehouse', 'product__group')
    search_fields = ('product__code', 'product__name', 'warehouse__name', 'warehouse__code')

@admin.register(PurchaseDetail)
class PurchaseDetailAdmin(ImportExportModelAdmin):
    resource_class = PurchaseDetailResource # Kết nối với Full Code Resource ở turn trước
    
    # Hiển thị các cột quan trọng ra danh sách
    list_display = (
        'posting_date', 'doc_number', 'supplier', 'product', 
        'quantity', 'total_value', 'business_unit', 'org_unit_name'
    )
    
    # Bộ lọc bên phải màn hình
    list_filter = ('posting_date', 'business_unit', 'warehouse', 'supplier')
    
    # Ô tìm kiếm
    search_fields = ('doc_number', 'product__code', 'product__name', 'supplier__name')
    
    # Phân nhóm giao diện nhập liệu
    fieldsets = (
        ('Thông tin chứng từ', {
            'fields': ('posting_date', 'doc_date', 'doc_number', 'description')
        }),
        ('Đối tượng & Danh mục', {
            'fields': ('supplier', 'warehouse', 'product', 'business_unit')
        }),
        ('Đơn vị (Lưu trực tiếp)', {
            'fields': ('org_unit_code', 'org_unit_name')
        }),
        ('Số liệu tài chính', {
            'fields': (('quantity', 'unit_price'), ('purchase_value', 'vat_value', 'total_value'), ('debit_account', 'credit_account'))
        }),
    )


@admin.register(ImportLog)
class ImportLogAdmin(admin.ModelAdmin):
    list_display = ('id', 'start_time', 'end_time', 'file_name', 'status', 'short_message')
    list_filter = ('status', 'start_time', 'end_time')
    search_fields = ('file_name', 'message')
    readonly_fields = ('start_time', 'end_time', 'created_at', 'file_name', 'status', 'message')

    def has_delete_permission(self, request, obj=None):
        # Không cho phép xóa log
        return False

    def has_add_permission(self, request):
        # Không cho phép thêm mới
        return False

    def has_change_permission(self, request, obj=None):
        # Không cho phép sửa đổi
        return False

    @admin.display(description="Nội dung chi tiết")
    def short_message(self, obj):
        if obj.message and len(obj.message) > 150:
            return obj.message[:150] + "..."
        return obj.message or ""


# Custom hiển thị cho TaskResult (Celery Results)
from django_celery_results.models import TaskResult
from django_celery_results.admin import TaskResultAdmin

try:
    admin.site.unregister(TaskResult)
except admin.sites.NotRegistered:
    pass

@admin.register(TaskResult)
class CustomTaskResultAdmin(TaskResultAdmin):
    list_display = ('task_id', 'task_name', 'date_done', 'status', 'short_result')

    @admin.display(description="Kết quả / Log trả về")
    def short_result(self, obj):
        result_str = obj.result or ""
        import json
        try:
            decoded = json.loads(result_str)
            if isinstance(decoded, str):
                result_str = decoded
        except Exception:
            pass
        if len(result_str) > 100:
            return result_str[:100] + "..."
        return result_str


@admin.register(BankBalance)
class BankBalanceAdmin(admin.ModelAdmin):
    list_display = ('bank_account_number', 'bank_name', 'balance', 'reporting_month')
    list_filter = ('reporting_month', 'bank_name')
    search_fields = ('bank_account_number', 'bank_name')


@admin.register(BUTargetPlan)
class BUTargetPlanAdmin(admin.ModelAdmin):
    list_display = (
        'get_bu_display', 'month', 'year', 'manager',
        'month_revenue_target', 'month_collection_target', 'month_opex_target', 'updated_at'
    )
    list_filter = ('year', 'month', 'business_unit')
    search_fields = ('business_unit__code', 'business_unit__name', 'manager', 'note')
    
    @admin.display(description="Đơn vị kinh doanh")
    def get_bu_display(self, obj):
        return obj.business_unit.code if obj.business_unit else "TỔNG TOÀN CÔNG TY"

    def save_model(self, request, obj, form, change):
        if not obj.updated_by:
            obj.updated_by = request.user
        super().save_model(request, obj, form, change)
        # Recalculate KPI for this BU and period
        bu_id = obj.business_unit.id if obj.business_unit else None
        update_single_bu_performance(bu_id, month=obj.month, year=obj.year)
        messages.success(request, f"✅ Đã cập nhật Chỉ tiêu và tính toán lại KPI thành công cho {self.get_bu_display(obj)} Th{obj.month}/{obj.year}!")


@admin.register(ManualAdjustment)
class ManualAdjustmentAdmin(admin.ModelAdmin):
    list_display = (
        'get_bu_display', 'metric_type', 'adjustment_type', 'amount',
        'month', 'year', 'reason', 'is_active', 'created_by', 'created_at'
    )
    list_filter = ('is_active', 'metric_type', 'adjustment_type', 'year', 'month', 'business_unit')
    search_fields = ('reason', 'business_unit__code', 'business_unit__name')
    actions = ['recalculate_performance']

    @admin.display(description="Đơn vị kinh doanh")
    def get_bu_display(self, obj):
        return obj.business_unit.code if obj.business_unit else "TỔNG TOÀN CÔNG TY"

    def save_model(self, request, obj, form, change):
        if not obj.created_by:
            obj.created_by = request.user
        super().save_model(request, obj, form, change)
        bu_id = obj.business_unit.id if obj.business_unit else None
        update_single_bu_performance(bu_id, month=obj.month, year=obj.year)
        messages.success(request, f"✅ Đã lưu khoản điều chỉnh và cập nhật KPI cho {self.get_bu_display(obj)} Th{obj.month}/{obj.year}!")

    @admin.action(description="🔄 recalculate - Kích hoạt tính lại KPI cho các khoản điều chỉnh chọn")
    def recalculate_performance(self, request, queryset):
        count = 0
        for obj in queryset:
            bu_id = obj.business_unit.id if obj.business_unit else None
            update_single_bu_performance(bu_id, month=obj.month, year=obj.year)
            count += 1
        messages.success(request, f"✅ Đã recalculate lại KPI thành công cho {count} khoản điều chỉnh!")