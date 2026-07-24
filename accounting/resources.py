# Backward-compatibility wrapper module for accounting.resources package
# All resource definitions have been modularized into accounting/resources/ directory

from .resources import (
    BulkCreateResource,
    SalesTransactionResource,
    CustomerResource,
    PurchaseDetailResource,
    AccountDetailResource,
    BankBalanceResource,
    SupplierDebtResource,
    ReceivablesAgeingResource,
    InventorySummaryResource,
)

__all__ = [
    'BulkCreateResource',
    'SalesTransactionResource',
    'CustomerResource',
    'PurchaseDetailResource',
    'AccountDetailResource',
    'BankBalanceResource',
    'SupplierDebtResource',
    'ReceivablesAgeingResource',
    'InventorySummaryResource',
]