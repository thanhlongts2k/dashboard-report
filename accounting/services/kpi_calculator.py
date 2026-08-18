import logging
import calendar
from decimal import Decimal
from datetime import datetime, timedelta
from django.db.models import Sum, Q
from django.conf import settings
from accounting.models import (
    BusinessUnit, BUPerformance, InventorySummary, 
    SalesTransaction, AccountDetail, BUPerformanceDaily, 
    BankBalance, BUTargetPlan, ManualAdjustment
)

logger = logging.getLogger(__name__)

def is_under_oversea(bu):
    curr = bu
    while curr:
        if curr.code == 'Oversea':
            return True
        curr = curr.parent
    return False

def update_single_bu_performance(bu_id, month=None, year=None, target_date_str=None):
    # --- 1. XỬ LÝ THỜI GIAN ---
    today = datetime.now()
    month = int(month) if month else today.month
    year = int(year) if year else today.year
    
    if target_date_str:
        target_date = datetime.strptime(target_date_str, '%Y-%m-%d').date()
    else:
        if month == today.month and year == today.year:
            target_date = today.date()
        else:
            last_day = calendar.monthrange(year, month)[1]
            target_date = datetime(year, month, last_day).date()

    # --- 2. XÁC ĐỊNH PHẠM VI (GLOBAL / SUB-BU) & LOẠI TRỪ ---
    excluded_bu_codes = getattr(settings, 'EXCLUDED_BU_CODES', [])
    excluded_bu_ids = []
    if excluded_bu_codes:
        excluded_bus = BusinessUnit.objects.filter(code__in=excluded_bu_codes)
        for ex_bu in excluded_bus:
            excluded_bu_ids.extend(ex_bu.get_all_descendant_ids())

    is_global = False
    is_under_oversea_branch = False
    bu_ids = []
    if bu_id is None:
        is_global = True
    else:
        bu = BusinessUnit.objects.filter(id=bu_id).first()
        if bu:
            is_global = False
            is_under_oversea_branch = is_under_oversea(bu)
            bu_ids = bu.get_all_descendant_ids()
            if bu.code not in excluded_bu_codes:
                bu_ids = [bid for bid in bu_ids if bid not in excluded_bu_ids]

    excluded_cust_group_codes = getattr(settings, 'EXCLUDED_CUSTOMER_GROUP_CODES', [])
    customer_rev_filter = Q(customer__has_revenue=True)
    if excluded_cust_group_codes:
        customer_rev_filter &= ~Q(customer__group__code__in=excluded_cust_group_codes)

    oversea_cust_group_codes = getattr(settings, 'OVERSEA_CUSTOMER_GROUP_CODES', ['Oversea'])
    if not is_global:
        if is_under_oversea_branch:
            customer_rev_filter &= Q(customer__group__code__in=oversea_cust_group_codes)
        else:
            customer_rev_filter &= ~Q(customer__group__code__in=oversea_cust_group_codes)

    # --- 3. TÍNH DOANH THU & THỰC THU (LŨY KẾ THÁNG) ---
    base_filter = Q(posting_date__month=month, posting_date__year=year) & customer_rev_filter

    inventory_filter = Q(reporting_period=f"{year:04d}-{month:02d}")
    if is_global:
        if excluded_bu_ids:
            inventory_filter &= ~Q(warehouse__business_unit_id__in=excluded_bu_ids)
    else:
        inventory_filter &= Q(warehouse__business_unit_id__in=bu_ids)

    inv_data = InventorySummary.objects.filter(inventory_filter).aggregate(
        opening=Sum('opening_value'),
        in_val=Sum('in_value'),
        out_val=Sum('out_value'),
        closing=Sum('closing_value')
    )
    
    inventory_actual = inv_data['closing'] or 0

    if is_global:
        if excluded_bu_ids:
            base_filter &= ~Q(business_unit_id__in=excluded_bu_ids)
    elif not is_under_oversea_branch:
        base_filter &= Q(business_unit_id__in=bu_ids)

    excluded_doc_id_prefixes = getattr(settings, 'EXCLUDED_DOC_ID_PREFIXES', [])
    if excluded_doc_id_prefixes:
        for prefix in excluded_doc_id_prefixes:
            base_filter &= ~Q(doc_id__istartswith=prefix)

    if excluded_cust_group_codes:
        base_filter &= ~Q(customer__group__code__in=excluded_cust_group_codes)

    sales_qs = SalesTransaction.objects.filter(base_filter)
    rev_actual = sales_qs.aggregate(total=Sum('actual_sales'))['total'] or 0

    sales_oversea_qs = sales_qs.filter(customer__group__code__in=oversea_cust_group_codes)
    rev_oversea_actual = sales_oversea_qs.aggregate(total=Sum('actual_sales'))['total'] or 0
    rev_exclude_oversea_actual = rev_actual - rev_oversea_actual

    account_qs = AccountDetail.objects.filter(base_filter)
    cash_cond = Q(account_number__startswith='111') | Q(account_number__startswith='112')
    offset_cond = Q(offset_account__startswith='1311') | Q(offset_account__startswith='1312')
    
    match_qs = account_qs.filter(cash_cond & offset_cond)
    sums = match_qs.aggregate(d=Sum('debit_amount'), c=Sum('credit_amount'))
    coll_actual = (sums['d'] or 0) - (sums['c'] or 0)

    match_oversea_qs = match_qs.filter(customer__group__code__in=oversea_cust_group_codes)
    sums_oversea = match_oversea_qs.aggregate(d=Sum('debit_amount'), c=Sum('credit_amount'))
    coll_oversea_actual = (sums_oversea['d'] or 0) - (sums_oversea['c'] or 0)
    coll_exclude_oversea_actual = coll_actual - coll_oversea_actual

    opex_trans_filter = Q(posting_date__month=month, posting_date__year=year, posting_date__lte=target_date)
    if is_global:
        if excluded_bu_ids:
            opex_trans_filter &= ~Q(business_unit_id__in=excluded_bu_ids)
    else:
        opex_trans_filter &= Q(business_unit_id__in=bu_ids)

    opex_trans_qs = AccountDetail.objects.filter(opex_trans_filter).filter(
        Q(account_number__startswith='641') | Q(account_number__startswith='642')
    )
    opex_trans_actual = opex_trans_qs.aggregate(total=Sum('debit_amount'))['total'] or 0

    target_plan = BUTargetPlan.objects.filter(business_unit_id=bu_id, month=month, year=year).first()
    existing_perf = BUPerformance.objects.filter(
        business_unit_id=bu_id,
        month=month,
        year=year
    ).first()
    
    if target_plan and target_plan.month_opex_target > 0:
        curr_opex_plan = Decimal(str(target_plan.month_opex_target))
    else:
        curr_opex_plan = Decimal(str(existing_perf.opex_plan)) if existing_perf else Decimal('0')

    last_day_val = calendar.monthrange(year, month)[1]
    
    existing_daily = BUPerformanceDaily.objects.filter(performance_month=existing_perf) if existing_perf else None
    existing_sum = Decimal(str(existing_daily.aggregate(total=Sum('daily_opex_plan'))['total'] or 0)) if existing_daily else Decimal('0')
    
    redistribute_plan = False
    if not existing_daily or existing_daily.count() != last_day_val:
        redistribute_plan = True
    elif abs(existing_sum - curr_opex_plan) > Decimal('0.01'):
        redistribute_plan = True
        
    if redistribute_plan:
        plan_elapsed = (curr_opex_plan / Decimal(last_day_val)) * Decimal(target_date.day)
    else:
        plan_elapsed = Decimal(str(existing_daily.filter(date__lte=target_date).aggregate(total=Sum('daily_opex_plan'))['total'] or 0))

    opex_trans_actual = Decimal(str(opex_trans_actual))
    opex_actual = plan_elapsed + opex_trans_actual

    from accounting.models import ReceivablesAgeing
    ageing_filter = Q(reporting_period=f"{year:04d}-{month:02d}")
    
    target_rec_accounts = getattr(settings, 'TARGET_RECEIVABLE_ACCOUNTS', ['1311'])
    if target_rec_accounts:
        ageing_filter &= Q(account_code__in=target_rec_accounts)

    if excluded_cust_group_codes:
        ageing_filter &= ~Q(customer__group__code__in=excluded_cust_group_codes)

    if not is_global:
        if is_under_oversea_branch:
            ageing_filter &= Q(customer__group__code__in=oversea_cust_group_codes)


    if is_global:
        if excluded_bu_ids:
            ageing_filter &= ~Q(customer__business_unit_id__in=excluded_bu_ids)
    elif is_under_oversea_branch:
        if excluded_bu_ids:
            ageing_filter &= ~Q(customer__business_unit_id__in=excluded_bu_ids)
    else:
        ageing_filter &= Q(customer__business_unit_id__in=bu_ids)
    
    rec_data = ReceivablesAgeing.objects.filter(ageing_filter).aggregate(
        total=Sum('total_debt'),
        overdue=Sum('overdue_total'),
    )
    receivable_total = rec_data['total'] or 0
    receivable_overdue = rec_data['overdue'] or 0

    overdue_customers = ReceivablesAgeing.objects.filter(
        ageing_filter, 
        overdue_total__gt=0
    ).values_list('customer_id', flat=True)

    month_due_qs = AccountDetail.objects.filter(
        base_filter,
        customer_id__in=overdue_customers
    ).filter(cash_cond & offset_cond)
    sums_due = month_due_qs.aggregate(d=Sum('debit_amount'), c=Sum('credit_amount'))
    collection_due_actual = (sums_due['d'] or 0) - (sums_due['c'] or 0)

    collection_in_term_cod = coll_actual - collection_due_actual

    ledger_filter = Q(posting_date__month=month, posting_date__year=year)
    if is_global:
        if excluded_bu_ids:
            ledger_filter &= ~Q(business_unit_id__in=excluded_bu_ids)
    else:
        ledger_filter &= Q(business_unit_id__in=bu_ids)

    last_111 = AccountDetail.objects.filter(ledger_filter, account_number='111').order_by('posting_date', 'id').last()
    last_112 = AccountDetail.objects.filter(ledger_filter, account_number='112').order_by('posting_date', 'id').last()
    
    cash_bal_111 = last_111.balance_debit if last_111 else 0
    cash_bal_112 = last_112.balance_debit if last_112 else 0
    
    reporting_period = f"{year:04d}-{month:02d}"
    excluded_accs = getattr(settings, 'MISA_EXCLUDED_BANK_ACCOUNTS', ['113611393939'])
    excluded_balance = 0
    if excluded_accs:
        excluded_balance = BankBalance.objects.filter(
            reporting_month=reporting_period,
            bank_account_number__in=excluded_accs
        ).aggregate(total=Sum('balance'))['total'] or 0
        
    cash_balance_actual = (cash_bal_111 + cash_bal_112) - excluded_balance

    last_341 = AccountDetail.objects.filter(ledger_filter, account_number='341').order_by('posting_date', 'id').last()
    bank_debt_actual = last_341.balance_credit if last_341 else 0

    target_plan = BUTargetPlan.objects.filter(business_unit_id=bu_id, month=month, year=year).first()
    
    enable_adj = getattr(settings, 'ENABLE_MANUAL_ADJUSTMENTS', False)
    if enable_adj:
        if is_global:
            adjustments = ManualAdjustment.objects.filter(month=month, year=year, is_active=True)
        else:
            adjustments = ManualAdjustment.objects.filter(business_unit_id=bu_id, month=month, year=year, is_active=True)
    else:
        adjustments = ManualAdjustment.objects.none()
        
    def apply_adj(base_val, metric_code):
        met_adjs = adjustments.filter(metric_type=metric_code)
        res = base_val
        for adj in met_adjs:
            if adj.adjustment_type == 'ADDITION':
                res += adj.amount
            elif adj.adjustment_type == 'DEDUCTION':
                res -= adj.amount
            elif adj.adjustment_type == 'OVERWRITE':
                res = adj.amount
        return res

    rev_actual = apply_adj(rev_actual, 'REVENUE')
    coll_actual = apply_adj(coll_actual, 'COLLECTION')
    receivable_total = apply_adj(receivable_total, 'RECEIVABLES_DUE')
    receivable_overdue = apply_adj(receivable_overdue, 'RECEIVABLES_OVERDUE')
    inventory_actual = apply_adj(inventory_actual, 'INVENTORY')
    cash_balance_actual = apply_adj(cash_balance_actual, 'CASH')
    bank_debt_actual = apply_adj(bank_debt_actual, 'BANK_DEBT')
    opex_actual = apply_adj(opex_actual, 'OPEX')

    rev_exclude_oversea_actual = rev_actual - rev_oversea_actual
    coll_exclude_oversea_actual = coll_actual - coll_oversea_actual

    defaults_dict = {
        'mtd_revenue_actual': rev_actual,
        'mtd_collection_actual': coll_actual,
        'collection_due_actual': collection_due_actual,
        'collection_in_term_cod': collection_in_term_cod,
        'receivable_total': receivable_total,
        'receivable_overdue': receivable_overdue,
        'inventory_opening_value': inv_data['opening'] or 0,
        'inventory_in_value': inv_data['in_val'] or 0,
        'inventory_out_value': inv_data['out_val'] or 0,
        'inventory_value_actual': inventory_actual,
        'cash_balance_actual': cash_balance_actual,
        'bank_debt_actual': bank_debt_actual,
        'mtd_revenue_oversea_actual': rev_oversea_actual,
        'mtd_revenue_exclude_oversea_actual': rev_exclude_oversea_actual,
        'mtd_collection_oversea_actual': coll_oversea_actual,
        'mtd_collection_exclude_oversea_actual': coll_exclude_oversea_actual,
        'opex_actual': opex_actual,
    }

    if target_plan:
        if target_plan.month_revenue_target > 0: defaults_dict['mtd_revenue_plan'] = target_plan.month_revenue_target
        if target_plan.month_collection_target > 0: defaults_dict['mtd_collection_plan'] = target_plan.month_collection_target
        if target_plan.month_inventory_target > 0: defaults_dict['inventory_value_plan'] = target_plan.month_inventory_target
        if target_plan.month_cash_target > 0: defaults_dict['cash_balance_plan'] = target_plan.month_cash_target
        if target_plan.month_bank_debt_target > 0: defaults_dict['bank_debt_plan'] = target_plan.month_bank_debt_target
        if target_plan.month_opex_target > 0: defaults_dict['opex_plan'] = target_plan.month_opex_target

    performance, _ = BUPerformance.objects.update_or_create(
        business_unit_id=bu_id,
        month=month,
        year=year,
        defaults=defaults_dict
    )

    prev_perf = None
    if month > 1:
        prev_perf = BUPerformance.objects.filter(
            business_unit_id=bu_id,
            month=month - 1,
            year=year
        ).first()

    performance.ytd_revenue_actual = (prev_perf.ytd_revenue_actual if prev_perf else 0) + performance.mtd_revenue_actual
    performance.ytd_revenue_plan = (prev_perf.ytd_revenue_plan if prev_perf else 0) + performance.mtd_revenue_plan
    performance.ytd_collection_actual = (prev_perf.ytd_collection_actual if prev_perf else 0) + performance.mtd_collection_actual
    performance.ytd_collection_plan = (prev_perf.ytd_collection_plan if prev_perf else 0) + performance.mtd_collection_plan
    performance.ytd_opex_actual = (prev_perf.ytd_opex_actual if prev_perf else 0) + performance.opex_actual
    performance.ytd_opex_plan = (prev_perf.ytd_opex_plan if prev_perf else 0) + performance.opex_plan
    performance.ytd_revenue_oversea_actual = (prev_perf.ytd_revenue_oversea_actual if prev_perf else 0) + performance.mtd_revenue_oversea_actual
    performance.ytd_revenue_exclude_oversea_actual = (prev_perf.ytd_revenue_exclude_oversea_actual if prev_perf else 0) + performance.mtd_revenue_exclude_oversea_actual
    performance.ytd_collection_oversea_actual = (prev_perf.ytd_collection_oversea_actual if prev_perf else 0) + performance.mtd_collection_oversea_actual
    performance.ytd_collection_exclude_oversea_actual = (prev_perf.ytd_collection_exclude_oversea_actual if prev_perf else 0) + performance.mtd_collection_exclude_oversea_actual
    performance.save()

    next_month = month + 1
    while next_month <= 12:
        next_perf = BUPerformance.objects.filter(
            business_unit_id=bu_id,
            month=next_month,
            year=year
        ).first()
        if next_perf:
            curr_perf = BUPerformance.objects.filter(
                business_unit_id=bu_id,
                month=next_month - 1,
                year=year
            ).first()
            if curr_perf:
                next_perf.ytd_revenue_actual = curr_perf.ytd_revenue_actual + next_perf.mtd_revenue_actual
                next_perf.ytd_revenue_plan = curr_perf.ytd_revenue_plan + next_perf.mtd_revenue_plan
                next_perf.ytd_collection_actual = curr_perf.ytd_collection_actual + next_perf.mtd_collection_actual
                next_perf.ytd_collection_plan = curr_perf.ytd_collection_plan + next_perf.mtd_collection_plan
                next_perf.ytd_opex_actual = curr_perf.ytd_opex_actual + next_perf.opex_actual
                next_perf.ytd_opex_plan = curr_perf.ytd_opex_plan + next_perf.opex_plan
                next_perf.ytd_revenue_oversea_actual = curr_perf.ytd_revenue_oversea_actual + next_perf.mtd_revenue_oversea_actual
                next_perf.ytd_revenue_exclude_oversea_actual = curr_perf.ytd_revenue_exclude_oversea_actual + next_perf.mtd_revenue_exclude_oversea_actual
                next_perf.ytd_collection_oversea_actual = curr_perf.ytd_collection_oversea_actual + next_perf.mtd_collection_oversea_actual
                next_perf.ytd_collection_exclude_oversea_actual = curr_perf.ytd_collection_exclude_oversea_actual + next_perf.mtd_collection_exclude_oversea_actual
                next_perf.save()
            next_month += 1
        else:
            break

    last_day_val = calendar.monthrange(year, month)[1]
    last_day_of_month = datetime(year, month, last_day_val).date()
    
    existing_daily = BUPerformanceDaily.objects.filter(performance_month=performance)
    existing_sum = Decimal(str(existing_daily.aggregate(total=Sum('daily_opex_plan'))['total'] or 0))
    
    redistribute_plan = False
    if existing_daily.count() != last_day_val:
        redistribute_plan = True
    elif abs(existing_sum - performance.opex_plan) > Decimal('0.01'):
        redistribute_plan = True
        
    daily_plan_val = Decimal(str(performance.opex_plan)) / Decimal(last_day_val)
    
    current_date = datetime(year, month, 1).date()
    while current_date <= last_day_of_month:
        daily_filter = Q(posting_date=current_date)
        if is_global:
            if excluded_bu_ids:
                daily_filter &= ~Q(business_unit_id__in=excluded_bu_ids)
        else:
            daily_filter &= Q(business_unit_id__in=bu_ids)
            
        if redistribute_plan:
            d_opex_plan = daily_plan_val
        else:
            existing_d = existing_daily.filter(date=current_date).first()
            d_opex_plan = existing_d.daily_opex_plan if existing_d else daily_plan_val

        if current_date <= target_date:
            daily_sales_filter = daily_filter & customer_rev_filter
            if excluded_doc_id_prefixes:
                for prefix in excluded_doc_id_prefixes:
                    daily_sales_filter &= ~Q(doc_id__istartswith=prefix)

            daily_rev = SalesTransaction.objects.filter(daily_sales_filter).aggregate(
                total=Sum('actual_sales')
            )['total'] or 0

            daily_acc_qs = AccountDetail.objects.filter(daily_filter & customer_rev_filter).filter(cash_cond & offset_cond)
            daily_sums = daily_acc_qs.aggregate(d=Sum('debit_amount'), c=Sum('credit_amount'))
            daily_coll = (daily_sums['d'] or 0) - (daily_sums['c'] or 0)
            
            daily_opex_act = AccountDetail.objects.filter(daily_filter).filter(
                Q(account_number__startswith='641') | Q(account_number__startswith='642')
            ).aggregate(total=Sum('debit_amount'))['total'] or 0
        else:
            daily_rev = 0
            daily_coll = 0
            daily_opex_act = 0

        BUPerformanceDaily.objects.update_or_create(
            performance_month=performance,
            date=current_date,
            defaults={
                'daily_revenue': daily_rev,
                'daily_collection': daily_coll,
                'daily_opex_plan': d_opex_plan,
                'daily_opex_actual': daily_opex_act,
            }
        )
        current_date += timedelta(days=1)

    if not is_global:
        try:
            update_single_bu_performance(None, month=month, year=year, target_date_str=target_date.strftime('%Y-%m-%d'))
        except Exception as cascade_err:
            logger.warning(f"Lỗi khi tự động cập nhật Tổng công ty từ BU con ({cascade_err})")

    bu_name = "TỔNG CÔNG TY" if is_global else f"Business Unit {bu_id}"
    return f"Updated {bu_name}: Month Rev={rev_actual} | All days up to {target_date} updated"
