from import_export import fields
from import_export.widgets import ForeignKeyWidget, DateWidget
from accounting.models import (
    Warehouse, BusinessUnit, MaterialGroup, Product,
    Supplier, SupplierGroup, PurchaseDetail
)
from .bulk import BulkCreateResource

class PurchaseDetailResource(BulkCreateResource):
    supplier = fields.Field(
        attribute='supplier',
        column_name='Mã nhà cung cấp',
        widget=ForeignKeyWidget(Supplier, 'code')
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
    product = fields.Field(
        attribute='product',
        column_name='Mã hàng',
        widget=ForeignKeyWidget(Product, 'code')
    )
    
    posting_date = fields.Field(attribute='posting_date', column_name='Ngày hạch toán', widget=DateWidget(format='%Y-%m-%d'))
    doc_date = fields.Field(attribute='doc_date', column_name='Ngày chứng từ', widget=DateWidget(format='%Y-%m-%d'))

    class Meta:
        model = PurchaseDetail
        import_id_fields = []
        skip_unchanged = False
        fields = (
            'posting_date', 'doc_date', 'doc_number', 'description',
            'supplier', 'warehouse', 'product', 'business_unit',
            'org_unit_code', 'org_unit_name', 'quantity', 'unit_price',
            'purchase_value', 'vat_value', 'total_value',
            'debit_account', 'credit_account'
        )

    def before_import(self, dataset, **kwargs):
        header_idx = -1
        for i, row in enumerate(dataset):
            if 'Ngày hạch toán' in [str(c).strip() for c in row if c]:
                header_idx = i
                break
        
        if header_idx >= 0:
            dataset.headers = [str(h).strip() for h in dataset[header_idx]]
            for _ in range(header_idx + 1):
                del dataset[0]
        
        idx = len(dataset) - 1
        while idx >= 0:
            row_content = "".join([str(c) for c in dataset[idx] if c and str(c).strip()])
            if any(x in row_content for x in ["Tổng", "Cộng", "Số dòng"]) or not row_content:
                del dataset[idx]
            else:
                break
            idx -= 1

    def before_import_row(self, row, **kwargs):
        prod_code = str(row.get('Mã hàng') or '').strip()
        if not prod_code or prod_code == 'None':
            return None

        group_raw = str(row.get('Tên nhóm VTHH') or 'Khác').strip()
        g_code = group_raw.split('/')[-1].strip()
        group_obj, _ = MaterialGroup.objects.get_or_create(
            code=g_code, defaults={'name': group_raw}
        )

        product_obj, _ = Product.objects.get_or_create(
            code=prod_code,
            defaults={
                'name': str(row.get('Tên hàng') or 'N/A'),
                'unit': str(row.get('ĐVT') or 'Cái'),
                'group': group_obj,
                'brand': str(row.get('Nguồn gốc') or '')
            }
        )
        row['Mã hàng'] = product_obj.code

        bu_code = str(row.get('Mã thống kê') or '').strip()
        if bu_code:
            bu_obj, _ = BusinessUnit.objects.get_or_create(
                code=bu_code,
                defaults={'name': str(row.get('Tên thống kê') or bu_code)}
            )
            row['Mã thống kê'] = bu_obj.code

        sup_code = str(row.get('Mã nhà cung cấp') or '').strip()
        if sup_code:
            s_group_code = str(row.get('Mã nhóm nhà cung cấp') or '').strip()
            s_group_name = str(row.get('Tên nhóm nhà cung cấp') or '').strip()
            
            if s_group_code:
                s_group_obj, _ = SupplierGroup.objects.get_or_create(
                    code=s_group_code,
                    defaults={'name': s_group_name or s_group_code}
                )
            else:
                s_group_obj, _ = SupplierGroup.objects.get_or_create(
                    code="OTHER",
                    defaults={'name': "Chưa phân loại"}
                )
            
            sup_obj, _ = Supplier.objects.get_or_create(
                code=sup_code,
                defaults={
                    'name': str(row.get('Tên nhà cung cấp') or 'N/A'),
                    'group': s_group_obj
                }
            )
            row['Mã nhà cung cấp'] = sup_obj.code

        wh_code = str(row.get('Mã kho') or '').strip()
        if wh_code:
            wh_obj, _ = Warehouse.objects.get_or_create(
                code=wh_code,
                defaults={'name': str(row.get('Tên kho') or 'N/A')}
            )
            row['Mã kho'] = wh_obj.code

        row['org_unit_code'] = str(row.get('Mã đơn vị') or '').strip()
        row['org_unit_name'] = str(row.get('Tên đơn vị') or '').strip()

        row['doc_number'] = str(row.get('Số chứng từ') or '').strip()
        row['description'] = str(row.get('Diễn giải') or row.get('Diễn giải chung') or '').strip()
        row['quantity'] = row.get('Số lượng mua') or 0
        row['unit_price'] = row.get('Đơn giá') or 0
        row['purchase_value'] = row.get('Giá trị mua') or 0
        row['vat_value'] = row.get('Thuế GTGT') or 0
        row['total_value'] = row.get('Giá trị nhập kho/Tổng giá trị') or 0
        row['debit_account'] = str(row.get('TK Nợ') or '').strip()
        row['credit_account'] = str(row.get('TK Có') or '').strip()

        return row
