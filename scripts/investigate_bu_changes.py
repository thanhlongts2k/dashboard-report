"""
Script Investigate BU Code Modifications (Transfers) between DB and Live MISA
Without BU code filtering on Live MISA dataset
Exports bu_changed_investigation.csv
"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), '.venv', 'Lib', 'site-packages'))
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'report2026.settings')
django.setup()

import pandas as pd
from django.conf import settings
from accounting.models import SalesTransaction, BusinessUnit

def investigate_bu_changes():
    out = ["=== CHƯƠNG TRÌNH ĐIỀU TRA CHỨNG TỪ BỊ KẾ TOÁN ĐỔI MÃ BỘ PHẬN (BU TRANSFER) ==="]

    # 1. Target BUs in DB: BU_MANUFACTURING and BU_ELEVATOR
    mfg = BusinessUnit.objects.filter(code='BU_MANUFACTURING').first()
    ele = BusinessUnit.objects.filter(code='BU_ELEVATOR').first()

    target_bu_ids = set()
    for bu in [mfg, ele]:
        if bu:
            ids = bu.get_all_descendant_ids()
            target_bu_ids.update(ids)

    # Load DB Frozen Data for BU_MANUFACTURING & BU_ELEVATOR
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

    out.append(f"1. Dữ liệu DB (Elevator & Manufacturing): {len(df_frozen)} unique doc_ids | Tổng tiền DB: {df_frozen['old_amount_db'].sum():18,.0f} VNĐ")

    # 2. Read RAW MISA Excel directly using pandas without BU filtering
    live_excel_path = os.path.join(settings.BASE_DIR, 'media', 'auto_imports', 'LIVE_MISA_BAN_HANG_2026_ALL.xlsx')
    if not os.path.exists(live_excel_path):
        out.append(f"File {live_excel_path} does not exist!")
        sys.stdout.buffer.write("\n".join(out).encode('utf-8'))
        return

    df_misa_raw_file = pd.read_excel(live_excel_path, header=None)
    
    header_row_idx = 0
    for idx, row in df_misa_raw_file.iterrows():
        row_str_vals = [str(val) for val in row.values if pd.notna(val)]
        if any('Số chứng từ' in val for val in row_str_vals):
            header_row_idx = idx
            break

    df_misa = pd.read_excel(live_excel_path, skiprows=header_row_idx)
    df_misa.columns = [str(col).replace('\ufeff', '').strip() for col in df_misa.columns]

    doc_col = next((c for c in df_misa.columns if 'Số chứng từ' in c), None)
    bu_col = next((c for c in df_misa.columns if 'Mã thống kê' in c or 'Mã đơn vị' in c or 'Bộ phận' in c), None)
    amount_col = next((c for c in df_misa.columns if 'Doanh số thực tế' in c or 'Doanh số bán' in c or 'Thành tiền' in c), None)

    out.append(f"Excel Columns identified -> doc_col: '{doc_col}' | bu_col: '{bu_col}' | amount_col: '{amount_col}'")

    raw_misa_list = []
    for _, row in df_misa.iterrows():
        d_val = str(row.get(doc_col, '') or '').strip().upper()
        if d_val and d_val not in ['NAN', 'NONE', 'TỔNG', 'CỘNG'] and not d_val.startswith('TỔNG'):
            b_val = str(row.get(bu_col, '') or '').strip()
            if b_val in ['NAN', 'NONE']:
                b_val = ''
            try:
                a_val = float(row.get(amount_col, 0) or 0)
                if pd.isna(a_val):
                    a_val = 0.0
            except (ValueError, TypeError):
                a_val = 0.0
                
            raw_misa_list.append({
                'doc_id': d_val,
                'business_unit_misa': b_val,
                'new_amount_misa': a_val
            })

    df_raw_misa = pd.DataFrame(raw_misa_list)
    if not df_raw_misa.empty:
        df_raw_misa['business_unit_misa'] = df_raw_misa['business_unit_misa'].fillna('')
        df_raw_misa = df_raw_misa.groupby('doc_id', as_index=False).agg({
            'business_unit_misa': 'first',
            'new_amount_misa': 'sum'
        })
    else:
        df_raw_misa = pd.DataFrame(columns=['doc_id', 'business_unit_misa', 'new_amount_misa'])

    out.append(f"2. Dữ liệu MISA LIVE Thô (TOÀN BỘ 2026): {len(df_raw_misa)} unique doc_ids | Tổng tiền MISA: {df_raw_misa['new_amount_misa'].sum():18,.0f} VNĐ")

    # 3. INNER JOIN qua khóa doc_id
    df_inner = pd.merge(df_frozen, df_raw_misa, on='doc_id', how='inner')
    df_inner['business_unit_db'] = df_inner['business_unit_db'].fillna('')
    df_inner['business_unit_misa'] = df_inner['business_unit_misa'].fillna('')
    out.append(f"3. Tổng số chứng từ khớp trong INNER JOIN: {len(df_inner)}")

    # 4. Lọc danh sách chứng từ bị Kế toán 'chuyển khẩu' (business_unit_db != business_unit_misa)
    df_changed = df_inner[df_inner['business_unit_db'] != df_inner['business_unit_misa']].copy()

    out.append("\n" + "="*80)
    out.append(f"🎯 KẾT QUẢ ĐIỀU TRA CHỨNG TỪ BỊ ĐỔI MÃ BỘ PHẬN (BU TRANSFER):")
    out.append(f"   - Tổng số chứng từ bị Kế toán đổi mã bộ phận : {len(df_changed)} chứng từ")
    out.append(f"   - Tổng Doanh thu DB của các chứng từ bị đổi mã: {df_changed['old_amount_db'].sum():18,.0f} VNĐ")
    out.append(f"   - Tổng Doanh thu MISA mới sau khi bị đổi mã  : {df_changed['new_amount_misa'].sum():18,.0f} VNĐ")
    out.append("="*80)

    if not df_changed.empty:
        out.append("\nChi tiết chuyển giao mã bộ phận:")
        grouped = df_changed.groupby(['business_unit_db', 'business_unit_misa']).agg(
            count=('doc_id', 'count'),
            total_db=('old_amount_db', 'sum'),
            total_misa=('new_amount_misa', 'sum')
        ).reset_index()
        for _, row in grouped.iterrows():
            db_code = str(row['business_unit_db'])
            misa_code = str(row['business_unit_misa'])
            cnt = int(row['count'])
            t_db = float(row['total_db'])
            t_misa = float(row['total_misa'])
            out.append(f"   - {db_code:<20} -> {misa_code:<25}: {cnt:3d} CT | DB: {t_db:15,.0f} VNĐ | MISA: {t_misa:15,.0f} VNĐ")

    out_cols = ['doc_id', 'business_unit_db', 'business_unit_misa', 'old_amount_db', 'new_amount_misa']
    csv_path = os.path.join(settings.BASE_DIR, 'bu_changed_investigation.csv')
    df_changed_export = df_changed[out_cols].sort_values(by='old_amount_db', ascending=False)
    df_changed_export.to_csv(csv_path, index=False, encoding='utf-8-sig')

    out.append(f"\n✅ ĐÃ XUẤT FILE CSV THÀNH CÔNG TẠI: {csv_path}")
    sys.stdout.buffer.write("\n".join(out).encode('utf-8'))

if __name__ == '__main__':
    investigate_bu_changes()
