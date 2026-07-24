import re
from import_export import fields
from import_export.widgets import ForeignKeyWidget, DateWidget, DecimalWidget, BooleanWidget
from accounting.models import Branch, Customer, BusinessUnit, AccountDetail, BankBalance
from .bulk import BulkCreateResource

class AccountDetailResource(BulkCreateResource):
    posting_date = fields.Field(attribute='posting_date', column_name='Ngày hạch toán', widget=DateWidget(format='%Y-%m-%d'))
    doc_id = fields.Field(attribute='doc_id', column_name='Số chứng từ')
    customer = fields.Field(
        attribute='customer',
        column_name='Mã đối tượng',
        widget=ForeignKeyWidget(Customer, 'code')
    )
    
    business_unit = fields.Field(
        attribute='business_unit', 
        column_name='Mã thống kê', 
        widget=ForeignKeyWidget(BusinessUnit, 'code')
    )
    branch = fields.Field(
        attribute='branch', 
        column_name='Chi nhánh', 
        widget=ForeignKeyWidget(Branch, 'name')
    )

    account_number = fields.Field(attribute='account_number', column_name='Tài khoản')
    account_name = fields.Field(attribute='account_name', column_name='Tên tài khoản')
    offset_account = fields.Field(attribute='offset_account', column_name='TK đối ứng')
    
    debit_amount = fields.Field(attribute='debit_amount', column_name='Phát sinh Nợ', widget=DecimalWidget())
    credit_amount = fields.Field(attribute='credit_amount', column_name='Phát sinh Có', widget=DecimalWidget())
    balance_debit = fields.Field(attribute='balance_debit', column_name='Dư Nợ', widget=DecimalWidget())
    balance_credit = fields.Field(attribute='balance_credit', column_name='Dư Có', widget=DecimalWidget())
    unit_code = fields.Field(attribute='unit_code', column_name='Mã đơn vị')
    unit_name = fields.Field(attribute='unit_name', column_name='Tên đơn vị')
    unreasonable_cost = fields.Field(attribute='unreasonable_cost', column_name='CP không hợp lý', widget=BooleanWidget())

    class Meta:
        model = AccountDetail
        fields = (
            'posting_date', 'doc_id', 'account_number', 'account_name', 'offset_account', 
            'debit_amount', 'credit_amount', 'balance_debit', 'balance_credit',
            'business_unit', 'branch', 'customer', 'unit_code', 'unit_name', 'unreasonable_cost'
        )
        import_id_fields = []
        skip_unchanged = False

    def before_import(self, dataset, **kwargs):
        header_index = -1
        for i, row in enumerate(dataset):
            if 'Ngày hạch toán' in [str(c).strip() for c in row if c]:
                header_index = i
                break
        
        if header_index >= 0:
            dataset.headers = [str(h).strip() for h in dataset[header_index]]
            for _ in range(header_index + 1):
                del dataset[0]

        idx = len(dataset) - 1
        while idx >= 0:
            row_str = " ".join([str(c) for c in dataset[idx] if c])
            if "Số dư đầu kỳ" in row_str or "Cộng" in row_str or not dataset[idx][2]:
                del dataset[idx]
            idx -= 1

    def before_import_row(self, row, **kwargs):
        bu_code = str(row.get('Mã thống kê') or '').strip()
        branch_name = str(row.get('Chi nhánh') or '').strip()

        cust_code = str(row.get('Mã đối tượng') or '').strip()
        cust_name = str(row.get('Tên đối tượng') or '').strip()

        if cust_code and cust_code not in ['', 'None', 'nan']:
            Customer.objects.get_or_create(
                code=cust_code,
                defaults={'name': cust_name if cust_name else 'N/A'}
            )
            row['Mã đối tượng'] = cust_code
        else:
            row['Mã đối tượng'] = None

        row['Tài khoản'] = row.get('Tài khoản')
        row['TK đối ứng'] = row.get('TK đối ứng')
        
        if bu_code and bu_code not in ['None', '', 'nan']:
            BusinessUnit.objects.get_or_create(
                code=bu_code, 
                defaults={'name': str(row.get('Tên thống kê') or 'N/A')}
            )
            row['Mã thống kê'] = bu_code
        else:
            row['Mã thống kê'] = None
            
        if branch_name and branch_name not in ['None', '', 'nan']:
            Branch.objects.get_or_create(name=branch_name)
            row['Chi nhánh'] = branch_name
        else:
            row['Chi nhánh'] = None


class BankBalanceResource(BulkCreateResource):
    bank_account_number = fields.Field(attribute='bank_account_number', column_name='Số tài khoản')
    bank_name = fields.Field(attribute='bank_name', column_name='Tên ngân hàng')
    opening_balance = fields.Field(attribute='opening_balance', column_name='Số dư đầu kỳ', widget=DecimalWidget())
    debit_amount = fields.Field(attribute='debit_amount', column_name='Phát sinh Nợ', widget=DecimalWidget())
    credit_amount = fields.Field(attribute='credit_amount', column_name='Phát sinh Có', widget=DecimalWidget())
    balance = fields.Field(attribute='balance', column_name='Số dư cuối kỳ', widget=DecimalWidget())
    reporting_month = fields.Field(attribute='reporting_month', column_name='reporting_month')

    class Meta:
        model = BankBalance
        import_id_fields = []
        skip_unchanged = False

    def before_import(self, dataset, **kwargs):
        if dataset.headers:
            normalized_headers = []
            for h in dataset.headers:
                h_norm = str(h).strip().lower()
                if 'tài khoản' in h_norm or 'số tài khoản' in h_norm or 'stk' in h_norm:
                    normalized_headers.append('Số tài khoản')
                elif 'tên ngân hàng' in h_norm or 'tên tài khoản' in h_norm:
                    normalized_headers.append('Tên ngân hàng')
                elif 'dư đầu kỳ' in h_norm or 'số dư đầu kỳ' in h_norm:
                    normalized_headers.append('Số dư đầu kỳ')
                elif 'phát sinh nợ' in h_norm:
                    normalized_headers.append('Phát sinh Nợ')
                elif 'phát sinh có' in h_norm:
                    normalized_headers.append('Phát sinh Có')
                elif 'dư cuối kỳ' in h_norm or 'số dư cuối kỳ' in h_norm or 'số dư quy đổi' in h_norm or 'số dư' in h_norm:
                    normalized_headers.append('Số dư cuối kỳ')
                else:
                    normalized_headers.append(h)
            dataset.headers = normalized_headers

        idx = len(dataset) - 1
        while idx >= 0:
            row_dict = dict(zip(dataset.headers, dataset[idx]))
            acc_num = str(row_dict.get('Số tài khoản') or '').strip()
            
            is_valid = True
            if not acc_num or acc_num == 'None':
                is_valid = False
            else:
                if not re.search(r'\d{3,}', acc_num):
                    is_valid = False
            
            if not is_valid:
                del dataset[idx]
            idx -= 1

    def before_import_row(self, row, **kwargs):
        reporting_period = kwargs.get('reporting_period')
        row['reporting_month'] = reporting_period
