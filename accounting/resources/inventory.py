from import_export import fields
from import_export.widgets import ForeignKeyWidget, DecimalWidget
from accounting.models import Warehouse, Product, MaterialGroup, InventorySummary
from .bulk import BulkCreateResource

class InventorySummaryResource(BulkCreateResource):
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
    reporting_period = fields.Field(attribute='reporting_period', column_name='reporting_period')
    
    opening_quantity = fields.Field(attribute='opening_quantity', column_name='Đầu kỳ_Số lượng', widget=DecimalWidget())
    opening_value = fields.Field(attribute='opening_value', column_name='Đầu kỳ_Giá trị', widget=DecimalWidget())
    
    in_quantity = fields.Field(attribute='in_quantity', column_name='Nhập kho_Số lượng', widget=DecimalWidget())
    in_value = fields.Field(attribute='in_value', column_name='Nhập kho_Giá trị', widget=DecimalWidget())
    
    out_quantity = fields.Field(attribute='out_quantity', column_name='Xuất kho_Số lượng', widget=DecimalWidget())
    out_value = fields.Field(attribute='out_value', column_name='Xuất kho_Giá trị', widget=DecimalWidget())

    closing_quantity = fields.Field(attribute='closing_quantity', column_name='Cuối kỳ_Số lượng', widget=DecimalWidget())
    closing_value = fields.Field(attribute='closing_value', column_name='Cuối kỳ_Giá trị', widget=DecimalWidget())

    class Meta:
        model = InventorySummary
        import_id_fields = []
        skip_unchanged = False

    def before_import(self, dataset, **kwargs):
        header_idx = -1
        for i, row in enumerate(dataset):
            if 'Mã hàng' in [str(c).strip() for c in row if c]:
                header_idx = i
                break
        
        if header_idx >= 0:
            main_h = dataset[header_idx]
            sub_h = dataset[header_idx + 1]
            new_headers = []
            current_main = ""
            
            for m, s in zip(main_h, sub_h):
                m_s = str(m or "").strip()
                s_s = str(s or "").strip()
                
                if m_s in ["Đầu kỳ", "Nhập kho", "Xuất kho", "Cuối kỳ"]:
                    current_main = m_s
                
                if s_s in ["Số lượng", "Giá trị", "SL mua hàng", "Giá trị mua hàng", "SL bán hàng", "Giá trị bán hàng"]:
                    new_headers.append(f"{current_main}_{s_s}")
                else:
                    val = m_s if m_s else s_s
                    new_headers.append(val)
                    if m_s not in ["", "Đầu kỳ", "Nhập kho", "Xuất kho", "Cuối kỳ"]:
                        current_main = ""
            
            dataset.headers = new_headers
            for _ in range(header_idx + 2):
                del dataset[0]

        idx = len(dataset) - 1
        while idx >= 0:
            row_content = "".join([str(c) for c in dataset[idx] if c])
            if "Tổng" in row_content or not row_content or "Cộng" in row_content:
                del dataset[idx]
            else:
                break
            idx -= 1

    def before_import_row(self, row, **kwargs):
        prod_code = str(row.get('Mã hàng') or '').strip()
        if not prod_code or prod_code == 'None':
            return None

        wh_code = str(row.get('Mã kho') or '').strip()
        if wh_code:
            Warehouse.objects.get_or_create(
                code=wh_code[:255], 
                defaults={'name': str(row.get('Tên kho') or 'N/A')[:500]}
            )

        group_raw = str(row.get('Nhóm VTHH') or 'Khác').strip()
        parts = group_raw.split('/')
        
        g_code = parts[-1].strip()[:255]
        g_name = group_raw[:500]

        group_obj, _ = MaterialGroup.objects.get_or_create(
            code=g_code, 
            defaults={'name': g_name}
        )

        selling_price = 0
        try:
            selling_price = float(row.get('Đơn giá bán 1') or 0)
        except Exception:
            pass

        Product.objects.update_or_create(
            code=prod_code[:500],
            defaults={
                'name': str(row.get('Tên hàng') or 'N/A')[:255],
                'unit': str(row.get('ĐVT') or 'Cái')[:20],
                'group': group_obj,
                'brand': str(row.get('Nguồn gốc') or '')[:100],
                'selling_price': selling_price,
            }
        )

        try:
            opening_qty = float(row.get('Đầu kỳ_Số lượng') or 0)
            in_qty = float(row.get('Nhập kho_Số lượng') or 0)
            out_qty = float(row.get('Xuất kho_Số lượng') or 0)
            closing_qty = float(row.get('Cuối kỳ_Số lượng') or 0)

            if not row.get('Đầu kỳ_Giá trị'):
                row['Đầu kỳ_Giá trị'] = opening_qty * selling_price
            if not row.get('Nhập kho_Giá trị'):
                row['Nhập kho_Giá trị'] = in_qty * selling_price
            if not row.get('Xuất kho_Giá trị'):
                row['Xuất kho_Giá trị'] = out_qty * selling_price
            if not row.get('Cuối kỳ_Giá trị'):
                row['Cuối kỳ_Giá trị'] = closing_qty * selling_price
        except Exception:
            pass

        row['Mã hàng'] = prod_code
        row['Mã kho'] = wh_code
        row['reporting_period'] = kwargs.get('reporting_period')
        return row
