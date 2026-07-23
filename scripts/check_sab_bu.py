"""
Script kiểm tra xem có BU hoặc Khách hàng / Chứng từ nào có Mã hoặc Tên chứa 'SAB' trong CSDL và file Excel Bán hàng hay không.
"""
import os, sys, glob
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), '.venv', 'Lib', 'site-packages'))
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'report2026.settings')
django.setup()

from accounting.models import BusinessUnit, SalesTransaction, Customer, ImportLog
from django.db.models import Q, Sum

def check_sab():
    out = []
    out.append("=== 1. KIỂM TRA BẢNG BUSINESSUNIT (DANH MỤC BU) ===")
    sab_bus = BusinessUnit.objects.filter(Q(code__icontains='SAB') | Q(name__icontains='SAB'))
    if sab_bus.exists():
        for bu in sab_bus:
            out.append(f"[FOUND BU] ID: {bu.id} | Mã: {bu.code} | Tên: {bu.name} | BU Cha: {bu.parent}")
    else:
        out.append("--> KHÔNG TÌM THẤY bất kỳ BU nào có mã hoặc tên chứa 'SAB' trong bảng BusinessUnit.")

    out.append("\n=== 2. KIỂM TRA BẢNG SALESTRANSACTION (GIAO DỊCH BÁN HÀNG) ===")
    sab_tx_bu = SalesTransaction.objects.filter(
        Q(business_unit__code__icontains='SAB') | Q(business_unit__name__icontains='SAB')
    )
    out.append(f"-> Giao dịch có BU chứa 'SAB': {sab_tx_bu.count()} bản ghi.")

    sab_tx_cust = SalesTransaction.objects.filter(
        Q(customer__code__icontains='SAB') | Q(customer__name__icontains='SAB')
    )
    out.append(f"-> Giao dịch có Khách hàng chứa 'SAB': {sab_tx_cust.count()} bản ghi.")
    if sab_tx_cust.exists():
        cust_totals = sab_tx_cust.values('customer__code', 'customer__name', 'business_unit__code').annotate(total=Sum('actual_sales'))
        for c in cust_totals:
            out.append(f"   [KH SAB] Mã: {c['customer__code']} | Tên: {c['customer__name']} | Chi nhánh BU MISA: {c['business_unit__code']} | Doanh số: {c['total']:,.0f} VNĐ")

    out.append("\n=== 3. KIỂM TRA FILE EXCEL BAN_HANG MỚI NẠP ===")
    search_dirs = [
        os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'media', 'auto_imports'),
        os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'media', 'auto_imports', 'success'),
    ]
    
    excel_files = []
    for d in search_dirs:
        if os.path.exists(d):
            excel_files.extend(glob.glob(os.path.join(d, 'BAN_HANG*.xlsx')))

    out.append(f"Tìm thấy {len(excel_files)} file Excel BAN_HANG trong media/auto_imports.")
    
    try:
        import pandas as pd
        for filepath in excel_files[:5]: # Check top 5 recent files
            fname = os.path.basename(filepath)
            out.append(f"\n--- Đang đọc file: {fname} ---")
            df = pd.read_excel(filepath)
            
            # Search all string columns for 'SAB'
            sab_mask = False
            for col in df.columns:
                sab_mask |= df[col].astype(str).str.contains('SAB', case=False, na=False)
            
            sab_rows = df[sab_mask]
            out.append(f"-> Tìm thấy {len(sab_rows)} dòng chứa từ khóa 'SAB' trong file {fname}.")
            if len(sab_rows) > 0:
                cols_to_show = [c for c in df.columns if any(k in str(c).lower() for k in ['mã', 'tên', 'chi nhánh', 'đối tượng', 'thống kê', 'doanh'])]
                out.append(sab_rows[cols_to_show[:6]].head(10).to_string())

    except Exception as e:
        out.append(f"Lỗi khi đọc file Excel qua pandas: {e}")

    result_str = "\n".join(out)
    sys.stdout.buffer.write(result_str.encode('utf-8'))

if __name__ == '__main__':
    check_sab()
