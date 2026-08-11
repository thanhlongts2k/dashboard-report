from import_export import fields
from import_export.widgets import ForeignKeyWidget, DateWidget, DecimalWidget
from accounting.models import Supplier, SupplierDebt, SupplierGroup, Branch, Customer, ReceivablesAgeing
from .bulk import BulkCreateResource

class SupplierDebtResource(BulkCreateResource):
    supplier = fields.Field(
        attribute='supplier',
        column_name='Mã nhà cung cấp',
        widget=ForeignKeyWidget(Supplier, 'code')
    )
    
    opening_debit = fields.Field(attribute='opening_debit', column_name='Đầu kỳ_Nợ', widget=DecimalWidget())
    opening_credit = fields.Field(attribute='opening_credit', column_name='Đầu kỳ_Có', widget=DecimalWidget())
    incurred_debit = fields.Field(attribute='incurred_debit', column_name='Phát sinh_Nợ', widget=DecimalWidget())
    incurred_credit = fields.Field(attribute='incurred_credit', column_name='Phát sinh_Có', widget=DecimalWidget())
    closing_debit = fields.Field(attribute='closing_debit', column_name='Cuối kỳ_Nợ', widget=DecimalWidget())
    closing_credit = fields.Field(attribute='closing_credit', column_name='Cuối kỳ_Có', widget=DecimalWidget())
    reporting_period = fields.Field(attribute='reporting_period', column_name='reporting_period')

    class Meta:
        model = SupplierDebt
        import_id_fields = []
        skip_unchanged = False
        report_skipped = True

    def before_import(self, dataset, **kwargs):
        header_index = -1
        for i, row in enumerate(dataset):
            row_vals = [str(c).strip() if c else "" for c in row]
            if 'Mã nhà cung cấp' in row_vals:
                header_index = i
                break
        
        if header_index >= 0:
            main_headers = dataset[header_index]
            sub_headers = dataset[header_index + 1]
            
            new_headers = []
            current_prefix = ""
            
            for m, s in zip(main_headers, sub_headers):
                m_str = str(m).strip() if m else ""
                s_str = str(s).strip() if s else ""
                
                if "Số dư đầu kỳ" in m_str: current_prefix = "Đầu kỳ"
                elif "Phát sinh" in m_str: current_prefix = "Phát sinh"
                elif "Số dư cuối kỳ" in m_str: current_prefix = "Cuối kỳ"
                
                if s_str in ["Nợ", "Có"]:
                    new_headers.append(f"{current_prefix}_{s_str}")
                else:
                    new_headers.append(m_str if m_str else s_str)
            
            dataset.headers = new_headers
            
            for _ in range(header_index + 2):
                del dataset[0]

        idx = len(dataset) - 1
        while idx >= 0:
            val = str(dataset[idx][0]).strip() if dataset[idx][0] else ""
            if "Tổng" in val or val == "" or val == "None":
                del dataset[idx]
            else:
                break
            idx -= 1

    def before_import_row(self, row, **kwargs):
        sup_code = str(row.get('Mã nhà cung cấp') or '').strip()
        group_code = str(row.get('Mã nhóm nhà cung cấp') or '').strip()
        
        if not sup_code or sup_code == 'None':
            return None

        s_group = None
        if group_code:
            s_group, _ = SupplierGroup.objects.get_or_create(code=group_code)

        Supplier.objects.get_or_create(
            code=sup_code,
            defaults={
                'name': row.get('Tên nhà cung cấp') or 'N/A',
                'group': s_group
            }
        )
        row['reporting_period'] = kwargs.get('reporting_period')


class ReceivablesAgeingResource(BulkCreateResource):
    customer = fields.Field(attribute='customer', column_name='Mã khách hàng', widget=ForeignKeyWidget(Customer, 'code'))
    branch = fields.Field(attribute='branch', column_name='Chi nhánh', widget=ForeignKeyWidget(Branch, 'name'))
    doc_date = fields.Field(attribute='doc_date', column_name='Ngày chứng từ', widget=DateWidget(format='%Y-%m-%d'))
    
    total_debt = fields.Field(attribute='total_debt', column_name='Tổng nợ', widget=DecimalWidget())
    no_due_limit = fields.Field(attribute='no_due_limit', column_name='Không có hạn nợ', widget=DecimalWidget())
    due_0_7 = fields.Field(attribute='due_0_7', column_name='Nợ trước hạn_0-7 ngày', widget=DecimalWidget())
    due_8_14 = fields.Field(attribute='due_8_14', column_name='Nợ trước hạn_8-14 ngày', widget=DecimalWidget())
    due_15_21 = fields.Field(attribute='due_15_21', column_name='Nợ trước hạn_15-21 ngày', widget=DecimalWidget())
    due_22_28 = fields.Field(attribute='due_22_28', column_name='Nợ trước hạn_22-28 ngày', widget=DecimalWidget())
    due_29_60 = fields.Field(attribute='due_29_60', column_name='Nợ trước hạn_29-60 ngày', widget=DecimalWidget())
    due_above_60 = fields.Field(attribute='due_above_60', column_name='Nợ trước hạn_Trên 60 ngày', widget=DecimalWidget())
    due_total = fields.Field(attribute='due_total', column_name='Nợ trước hạn_Tổng', widget=DecimalWidget())
    
    overdue_0_14 = fields.Field(attribute='overdue_0_14', column_name='Nợ quá hạn_1-14 ngày', widget=DecimalWidget())
    overdue_15_30 = fields.Field(attribute='overdue_15_30', column_name='Nợ quá hạn_15-30 ngày', widget=DecimalWidget())
    overdue_31_45 = fields.Field(attribute='overdue_31_45', column_name='Nợ quá hạn_31-45 ngày', widget=DecimalWidget())
    overdue_46_60 = fields.Field(attribute='overdue_46_60', column_name='Nợ quá hạn_46-60 ngày', widget=DecimalWidget())
    overdue_61_90 = fields.Field(attribute='overdue_61_90', column_name='Nợ quá hạn_61-90 ngày', widget=DecimalWidget())
    overdue_91_120 = fields.Field(attribute='overdue_91_120', column_name='Nợ quá hạn_91-120 ngày', widget=DecimalWidget())
    overdue_above_120 = fields.Field(attribute='overdue_above_120', column_name='Nợ quá hạn_Trên 120 ngày', widget=DecimalWidget())
    overdue_total = fields.Field(attribute='overdue_total', column_name='Nợ quá hạn_Tổng', widget=DecimalWidget())
    
    reporting_period = fields.Field(attribute='reporting_period', column_name='reporting_period')
    account_code = fields.Field(attribute='account_code', column_name='Tài khoản')

    class Meta:
        model = ReceivablesAgeing
        import_id_fields = []
        skip_unchanged = False

    def before_import(self, dataset, **kwargs):
        header_idx = -1
        for i, row in enumerate(dataset):
            if 'Mã khách hàng' in [str(c).strip() for c in row if c]:
                header_idx = i
                break
        
        if header_idx >= 0:
            h_main = dataset[header_idx]
            h_sub = dataset[header_idx + 1]
            final_headers = []
            prefix = ""
            for m, s in zip(h_main, h_sub):
                m_s, s_s = str(m or "").strip(), str(s or "").strip()
                if "Nợ trước hạn" in m_s: prefix = "Nợ trước hạn_"
                elif "Nợ quá hạn" in m_s: prefix = "Nợ quá hạn_"
                elif m_s != "": prefix = ""
                
                final_headers.append(f"{prefix}{s_s}" if prefix and s_s else (m_s if m_s else s_s))
            
            dataset.headers = final_headers
            for _ in range(header_idx + 2): del dataset[0]

        idx = len(dataset) - 1
        while idx >= 0:
            val = str(dataset[idx][0]).strip()
            if "Tổng" in val or not val or val == "None": del dataset[idx]
            else: break
            idx -= 1

    def before_import_row(self, row, **kwargs):
        cust_code = str(row.get('Mã khách hàng') or '').strip()
        br_name = str(row.get('Chi nhánh') or '').strip()
        if cust_code and cust_code not in ['', 'None', 'nan']:
            Customer.objects.get_or_create(code=cust_code, defaults={'name': row.get('Tên khách hàng') or 'N/A'})
            row['Mã khách hàng'] = cust_code
        else:
            row['Mã khách hàng'] = None
            
        if br_name and br_name not in ['', 'None', 'nan']:
            Branch.objects.get_or_create(name=br_name)
            row['Chi nhánh'] = br_name
        else:
            row['Chi nhánh'] = None

        row['reporting_period'] = kwargs.get('reporting_period')
