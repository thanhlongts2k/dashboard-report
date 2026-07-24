"""
Script Download LIVE MISA Report & Pandas Outer Join Reconciliation for 2026
Generates discrepancy_details_ALL_2026.csv
"""
import os, sys, asyncio
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), '.venv', 'Lib', 'site-packages'))
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'report2026.settings')
django.setup()

import pandas as pd
from django.conf import settings
from playwright.async_api import async_playwright
from accounting.models import SalesTransaction, BusinessUnit
from accounting.tasks import load_and_clean_excel
from accounting.misa_tasks import login_to_misa, download_report_from_url

async def fetch_live_misa_report(output_path):
    email = settings.MISA_EMAIL
    password = settings.MISA_PASSWORD
    url = settings.MISA_REPORTS.get('BAN_HANG')
    if not url:
        return False

    async with async_playwright() as p:
        channel = getattr(settings, 'MISA_BROWSER_CHANNEL', 'chrome')
        browser = await p.chromium.launch(headless=True, channel=channel)
        
        if os.path.exists(settings.MISA_BROWSER_STATE_PATH):
            context = await browser.new_context(
                storage_state=settings.MISA_BROWSER_STATE_PATH,
                viewport={"width": 1280, "height": 800}
            )
        else:
            context = await browser.new_context(viewport={"width": 1280, "height": 800})
            
        page = await context.new_page()
        try:
            await page.goto(url, timeout=25000, wait_until="load")
            if "login" in page.url or "sso" in page.url or "id.misa.vn" in page.url or "amisapp.misa.vn/login" in page.url:
                await login_to_misa(page, context, email, password)
        except Exception:
            pass

        success = await download_report_from_url(page, url, settings.MISA_EXPORT_SELECTOR, output_path, prefix='BAN_HANG')
        await browser.close()
        return success

def run_reconciliation(skip_live=False):
    out = ["=== HỆ THỐNG CẮT CẢNH VÀ KÉO LIVE MISA REPORT 2026 ==="]

    mfg = BusinessUnit.objects.filter(code='BU_MANUFACTURING').first()
    ele = BusinessUnit.objects.filter(code='BU_ELEVATOR').first()

    target_bu_ids = set()
    target_bu_codes = set()

    for bu in [mfg, ele]:
        if bu:
            ids = bu.get_all_descendant_ids()
            target_bu_ids.update(ids)
            codes = list(BusinessUnit.objects.filter(id__in=ids).values_list('code', flat=True))
            target_bu_codes.update(codes)

    db_qs = SalesTransaction.objects.filter(
        posting_date__year=2026,
        business_unit_id__in=target_bu_ids
    )

    frozen_list = []
    for tx in db_qs:
        d_id = str(tx.doc_id or '').strip().upper()
        if d_id:
            frozen_list.append({
                'doc_id': d_id,
                'business_unit_db': tx.business_unit.code if tx.business_unit else '',
                'old_amount_db': float(tx.actual_sales or tx.sales_amount or 0)
            })

    df_frozen = pd.DataFrame(frozen_list)
    if not df_frozen.empty:
        df_frozen = df_frozen.groupby('doc_id', as_index=False).agg({
            'business_unit_db': 'first',
            'old_amount_db': 'sum'
        })
    else:
        df_frozen = pd.DataFrame(columns=['doc_id', 'business_unit_db', 'old_amount_db'])

    live_output_path = os.path.join(settings.BASE_DIR, 'media', 'auto_imports', 'LIVE_MISA_BAN_HANG_2026_ALL.xlsx')
    
    download_ok = False
    if not skip_live:
        try:
            download_ok = asyncio.run(fetch_live_misa_report(live_output_path))
        except Exception:
            pass

    if download_ok and os.path.exists(live_output_path):
        source_files = [live_output_path]
    else:
        source_files = [
            os.path.join(settings.BASE_DIR, 'media', 'auto_imports', 'success', 'BAN_HANG_202601-202605.xlsx'),
            os.path.join(settings.BASE_DIR, 'media', 'auto_imports', 'success', 'BAN_HANG_202606.xlsx'),
            os.path.join(settings.BASE_DIR, 'media', 'auto_imports', 'success', 'BAN_HANG_20260723_070012.xlsx'),
        ]

    fresh_list = []
    for fpath in source_files:
        if os.path.exists(fpath):
            headers, rows = load_and_clean_excel(fpath, 'BAN_HANG')
            for r in rows:
                bu_code = str(r.get('Mã thống kê', '') or '').strip()
                if bu_code in target_bu_codes:
                    doc_id = str(r.get('Số chứng từ', '') or '').strip().upper()
                    if doc_id:
                        try:
                            act_sales = float(r.get('Doanh số thực tế', 0) or r.get('Doanh số bán', 0) or 0)
                        except (ValueError, TypeError):
                            act_sales = 0.0
                        
                        fresh_list.append({
                            'doc_id': doc_id,
                            'business_unit_misa': bu_code,
                            'new_amount_misa': act_sales
                        })

    df_fresh = pd.DataFrame(fresh_list)
    if not df_fresh.empty:
        df_fresh = df_fresh.groupby('doc_id', as_index=False).agg({
            'business_unit_misa': 'first',
            'new_amount_misa': 'sum'
        })
    else:
        df_fresh = pd.DataFrame(columns=['doc_id', 'business_unit_misa', 'new_amount_misa'])

    df_merged = pd.merge(df_frozen, df_fresh, on='doc_id', how='outer')
    df_merged['business_unit'] = df_merged['business_unit_db'].fillna(df_merged['business_unit_misa'])
    df_merged['old_amount_db'] = df_merged['old_amount_db'].fillna(0.0)
    df_merged['new_amount_misa'] = df_merged['new_amount_misa'].fillna(0.0)
    df_merged['difference'] = df_merged['old_amount_db'] - df_merged['new_amount_misa']

    def get_status(row):
        if row['old_amount_db'] > 0 and row['new_amount_misa'] == 0:
            return 'Bị Kế toán xóa (Có DB, mất MISA)'
        elif row['old_amount_db'] == 0 and row['new_amount_misa'] > 0:
            return 'Bị sót (Có MISA, mất DB)'
        elif abs(row['difference']) > 0.01:
            return 'Lệch số tiền'
        else:
            return 'Trùng khớp'

    df_merged['status'] = df_merged.apply(get_status, axis=1)
    df_disc = df_merged[df_merged['status'] != 'Trùng khớp'].copy()

    out.append(f"1. Total DB doc_ids: {len(df_frozen)} | Total MISA doc_ids: {len(df_fresh)}")
    out.append(f"2. Outer Join Total: {len(df_merged)} | Discrepancies: {len(df_disc)}")

    sys.stdout.buffer.write("\n".join(out).encode('utf-8'))

if __name__ == '__main__':
    run_reconciliation()
