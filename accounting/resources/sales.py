import re
from import_export import fields
from import_export.widgets import ForeignKeyWidget, DateWidget, DecimalWidget, BooleanWidget
from accounting.models import (
    Branch, Warehouse, Customer, Employee, Product, BusinessUnit, 
    SalesTransaction, MaterialGroup, CustomerGroup
)
from .bulk import BulkCreateResource

class SalesTransactionResource(BulkCreateResource):
    # --- 1. MAPPING FIELDS ---
    posting_date = fields.Field(
        attribute='posting_date', 
        column_name='Ngày hạch toán', 
        widget=DateWidget(format='%Y-%m-%d')
    )
    doc_id = fields.Field(attribute='doc_id', column_name='Số chứng từ')
    customer = fields.Field(
        attribute='customer', 
        column_name='Mã khách hàng', 
        widget=ForeignKeyWidget(Customer, 'code')
    )
    product = fields.Field(
        attribute='product', 
        column_name='Mã hàng', 
        widget=ForeignKeyWidget(Product, 'code')
    )
    employee = fields.Field(
        attribute='employee', 
        column_name='Mã nhân viên bán hàng', 
        widget=ForeignKeyWidget(Employee, 'employee_code')
    )
    business_unit = fields.Field(
        attribute='business_unit', 
        column_name='Mã thống kê', 
        widget=ForeignKeyWidget(BusinessUnit, 'code')
    )
    warehouse = fields.Field(
        attribute='warehouse',
        column_name='Mã kho',
        widget=ForeignKeyWidget(Warehouse, 'code')
    )
    branch = fields.Field(
        attribute='branch',
        column_name='Chi nhánh',
        widget=ForeignKeyWidget(Branch, 'name')
    )
    
    # Các trường số liệu
    quantity = fields.Field(attribute='quantity', column_name='Tổng số lượng bán')
    unit_price = fields.Field(attribute='unit_price', column_name='Đơn giá')
    sales_amount = fields.Field(attribute='sales_amount', column_name='Doanh số bán')
    tax_percent = fields.Field(attribute='tax_percent', column_name='%Thuế')
    tax_amount = fields.Field(attribute='tax_amount', column_name='Thuế GTGT')
    debit_acc = fields.Field(attribute='debit_acc', column_name='TK Nợ')
    credit_acc = fields.Field(attribute='credit_acc', column_name='TK Có')
    discount_acc = fields.Field(attribute='discount_acc', column_name='TK chiết khấu')
    discount_amount = fields.Field(attribute='discount_amount', column_name='Chiết khấu')
    actual_sales = fields.Field(attribute='actual_sales', column_name='Doanh số thực tế')

    class Meta:
        model = SalesTransaction
        import_id_fields = [] 
        exclude = ('id',)
        skip_unchanged = False
        report_skipped = True

    def before_import(self, dataset, **kwargs):
        required_cols = ['Ngày hạch toán', 'Số chứng từ', 'Mã hàng']
        
        header_index = -1
        current_headers = [str(h).strip() if h else "" for h in dataset.headers]
        if not any(col in current_headers for col in required_cols):
            for i, row in enumerate(dataset):
                row_str = [str(cell).strip() if cell else "" for cell in row]
                if any(col in row_str for col in required_cols):
                    header_index = i
                    break

        if header_index >= 0:
            dataset.headers = [str(h).strip() for h in dataset[header_index]]
            for _ in range(header_index + 1):
                del dataset[0]

        idx = len(dataset) - 1
        while idx >= 0:
            val = str(dataset[idx][0]).strip() if dataset[idx][0] is not None else ""
            if "Tổng" in val or val == "" or val == "None":
                del dataset[idx]
            else:
                break
            idx -= 1

        dataset.headers = [
            re.sub(' +', ' ', str(h).replace('\ufeff', '').strip().replace('\n', ' ')) 
            if h else "" for h in dataset.headers
        ]

    def before_import_row(self, row, **kwargs):
        for key in list(row.keys()):
            if row[key] and isinstance(row[key], str):
                row[key] = row[key].strip()

        cust_code = row.get('Mã khách hàng')
        prod_code = row.get('Mã hàng')
        
        if not cust_code or not prod_code or str(cust_code).lower() == 'none':
            return None

        mat_group_code = row.get('Mã nhóm VTHH')
        material_group = None
        if mat_group_code:
            material_group, _ = MaterialGroup.objects.get_or_create(
                code=mat_group_code,
                defaults={'name': row.get('Tên nhóm VTHH') or 'N/A'}
            )

        cust_group_code = row.get('Mã nhóm khách hàng')
        cust_group = None
        if cust_group_code:
            cust_group, _ = CustomerGroup.objects.get_or_create(
                code=cust_group_code,
                defaults={'name': row.get('Tên nhóm khách hàng') or 'N/A'}
            )

        customer_defaults = {'name': row.get('Tên khách hàng') or 'N/A'}
        if cust_group:
            customer_defaults['group'] = cust_group
            
        customer_obj, created = Customer.objects.get_or_create(
            code=cust_code,
            defaults=customer_defaults
        )
        
        if not created and cust_group and not customer_obj.group:
            customer_obj.group = cust_group
            customer_obj.save(update_fields=['group'])

        Product.objects.get_or_create(
            code=prod_code,
            defaults={
                'name': row.get('Tên hàng') or 'N/A', 
                'unit': row.get('ĐVT') or 'Cái', 
                'group': material_group
            }
        )

        emp_code = row.get('Mã nhân viên bán hàng')
        if emp_code:
            Employee.objects.get_or_create(employee_code=emp_code, defaults={'full_name': row.get('Tên nhân viên bán hàng') or 'N/A'})

        bu_code = row.get('Mã thống kê')
        if bu_code:
            BusinessUnit.objects.get_or_create(code=bu_code, defaults={'name': row.get('Tên thống kê') or 'N/A'})

        if row.get('Chi nhánh'):
            Branch.objects.get_or_create(name=row.get('Chi nhánh'))

        wh_code = row.get('Mã kho')
        if wh_code:
            Warehouse.objects.get_or_create(code=wh_code, defaults={'name': row.get('Tên kho') or 'N/A'})

        actual_sales_val = row.get('Doanh số thực tế')
        try:
            actual_sales_num = float(str(actual_sales_val).replace(',', '')) if actual_sales_val else 0
        except (ValueError, TypeError):
            actual_sales_num = 0

        if not actual_sales_num:
            try:
                sales_amount = float(str(row.get('Doanh số bán') or 0).replace(',', ''))
                discount = float(str(row.get('Chiết khấu') or 0).replace(',', ''))
                return_val = float(str(row.get('Giá trị trả lại') or 0).replace(',', ''))
                discount_val = float(str(row.get('Giá trị giảm giá') or 0).replace(',', ''))
                computed = sales_amount - discount - return_val - discount_val
                row['Doanh số thực tế'] = computed if computed > 0 else sales_amount
            except (ValueError, TypeError):
                pass


class CustomerResource(BulkCreateResource):
    group = fields.Field(
        attribute='group',
        column_name='Mã nhóm khách hàng',
        widget=ForeignKeyWidget(CustomerGroup, 'code')
    )
    business_unit = fields.Field(
        attribute='business_unit',
        column_name='Mã thống kê',
        widget=ForeignKeyWidget(BusinessUnit, 'code')
    )
    
    code = fields.Field(attribute='code', column_name='Mã khách hàng')
    name = fields.Field(attribute='name', column_name='Tên khách hàng')
    address = fields.Field(attribute='address', column_name='Địa điểm giao hàng')
    has_revenue = fields.Field(
        attribute='has_revenue',
        column_name='Có ghi nhận doanh thu',
        widget=BooleanWidget(),
        default=True
    )

    class Meta:
        model = Customer
        import_id_fields = ['code']
        fields = ('code', 'name', 'group', 'address', 'business_unit', 'has_revenue')
        skip_unchanged = True
        report_skipped = True

    def before_import_row(self, row, **kwargs):
        g_code = str(row.get('Mã nhóm khách hàng') or '').strip()
        g_name = str(row.get('Tên nhóm khách hàng') or '').strip()
        if g_code and g_code != 'None' and g_code != '':
            CustomerGroup.objects.get_or_create(
                code=g_code,
                defaults={'name': g_name if g_name else g_code}
            )

        bu_code = str(row.get('Mã thống kê') or '').strip()
        bu_name = str(row.get('Tên thống kê') or '').strip()
        if bu_code and bu_code != 'None' and bu_code != '':
            BusinessUnit.objects.get_or_create(
                code=bu_code,
                defaults={'name': bu_name if bu_name else bu_code}
            )

        for key in ['Mã khách hàng', 'Tên khách hàng', 'Địa điểm giao hàng']:
            if row.get(key) and isinstance(row[key], str):
                row[key] = row[key].strip()
