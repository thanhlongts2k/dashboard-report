"""
Script Tải Báo Cáo MISA AMIS Theo Từng Cụm Tháng (01/2026 -> 09/2026)
Tích hợp State Persistence qua Checkpoint JSON 2 chiều: Tháng x Mã Báo Cáo
Hỗ trợ Resume khi gián đoạn, Auto-Import Idempotent, Recalculate KPI, và Weekly Cron-Ready.

Cách sử dụng:
  # 1. Chạy tuần tự tải nốt BAN_HANG từ Tháng 1 đến Tháng 9/2026 (tự động bỏ qua Tháng 8 đã xong):
  python scripts/download_batch_saved_reports_2026.py --from-month 2026-01 --to-month 2026-09 --reports BAN_HANG --auto-import --recalc-kpi --resume

  # 2. Thử nghiệm Nhóm 2 (SO_DU_NH, TUOI_NO_KH) cho Tháng 8/2026:
  python scripts/download_batch_saved_reports_2026.py --from-month 2026-08 --to-month 2026-08 --reports SO_DU_NH,TUOI_NO_KH --auto-import

  # 3. Chạy chế độ đồng bộ định kỳ cuối tuần (Weekly Cron):
  python scripts/download_batch_saved_reports_2026.py --weekly-sync

  # 4. Ép buộc tải lại toàn bộ (bỏ qua file đã có trong checkpoint):
  python scripts/download_batch_saved_reports_2026.py --from-month 2026-01 --to-month 2026-09 --reports BAN_HANG --force
"""

import os
import sys
import json
import argparse
import asyncio
from datetime import datetime

# Setup Django Environment
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE_DIR)
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'report2026.settings')

import django
django.setup()

from django.conf import settings
from accounting.models import BusinessUnit
from accounting.misa.automation import run_misa_automation
from accounting.misa.report_exporter import compute_cutoff_date
from accounting.tasks import auto_import_excel_from_folder, update_single_bu_performance

CHECKPOINT_DEFAULT_PATH = os.path.join(settings.BASE_DIR, 'media', 'auto_imports', 'batch_checkpoint.json')
AUTO_IMPORTS_DIR = os.path.join(settings.BASE_DIR, 'media', 'auto_imports')
SUCCESS_DIR = os.path.join(AUTO_IMPORTS_DIR, 'success')


class BatchCheckpointManager:
    """
    Quản lý trạng thái tiến trình tải và nạp batch vào đĩa (State Persistence)
    theo cấu trúc ma trận 2 chiều: Tháng x Mã Báo Cáo.
    """

    def __init__(self, checkpoint_path=CHECKPOINT_DEFAULT_PATH):
        self.checkpoint_path = checkpoint_path
        os.makedirs(os.path.dirname(self.checkpoint_path), exist_ok=True)
        self.data = self._load()

    def _load(self):
        if os.path.exists(self.checkpoint_path):
            try:
                with open(self.checkpoint_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    if "months" in data:
                        cleaned_months = {}
                        for k, v in data["months"].items():
                            if k in ["null", "None", ""]:
                                continue
                            # Tự động migrate cấu trúc 1 chiều cũ sang 2 chiều
                            if "reports" not in v:
                                v["reports"] = {}
                                if v.get("download") == "DONE" or v.get("status") == "COMPLETED":
                                    v["reports"]["BAN_HANG"] = {
                                        "download": v.get("download", "DONE"),
                                        "file_path": v.get("file_path"),
                                        "file_size": v.get("file_size", 0),
                                        "import": v.get("import", v.get("import_status", "DONE")),
                                        "updated_at": v.get("updated_at")
                                    }
                            cleaned_months[k] = v
                        data["months"] = cleaned_months
                    return data
            except Exception as e:
                print(f"⚠️ Không thể đọc file checkpoint cũ ({e}), khởi tạo checkpoint mới.")
        return {
            "last_updated": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "current_running_month": None,
            "current_running_report": None,
            "months": {}
        }

    def save(self):
        self.data["last_updated"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        tmp_path = self.checkpoint_path + ".tmp"
        with open(tmp_path, 'w', encoding='utf-8') as f:
            json.dump(self.data, f, ensure_ascii=False, indent=2)
        os.replace(tmp_path, self.checkpoint_path)

    def set_current(self, month_str, report_code=None):
        self.data["current_running_month"] = month_str
        self.data["current_running_report"] = report_code
        if month_str and month_str not in self.data["months"]:
            self.data["months"][month_str] = {
                "status": "PENDING",
                "reconciled": False,
                "reports": {},
                "updated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            }
        if month_str and report_code:
            m = self.data["months"][month_str]
            if "reports" not in m:
                m["reports"] = {}
            if report_code not in m["reports"]:
                m["reports"][report_code] = {
                    "download": "PENDING",
                    "file_path": None,
                    "file_size": 0,
                    "import": "PENDING",
                    "error": None,
                    "updated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                }
        self.save()

    def update_report(self, month_str, report_code, **kwargs):
        if not month_str or not report_code:
            return
        if month_str not in self.data["months"]:
            self.data["months"][month_str] = {
                "status": "PENDING",
                "reconciled": False,
                "reports": {},
                "updated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            }
        m = self.data["months"][month_str]
        if "reports" not in m:
            m["reports"] = {}
        if report_code not in m["reports"]:
            m["reports"][report_code] = {
                "download": "PENDING",
                "file_path": None,
                "file_size": 0,
                "import": "PENDING",
                "error": None
            }
        r = m["reports"][report_code]
        for k, v in kwargs.items():
            r[k] = v
            if k == "import_status":
                r["import"] = v
        r["updated_at"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        m["updated_at"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self.save()

    def update_month_meta(self, month_str, **kwargs):
        if not month_str or month_str not in self.data["months"]:
            return
        for k, v in kwargs.items():
            self.data["months"][month_str][k] = v
        self.data["months"][month_str]["updated_at"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self.save()

    def get_report_status(self, month_str, report_code):
        m = self.data["months"].get(month_str, {})
        return m.get("reports", {}).get(report_code, {})

    def is_report_done(self, month_str, report_code, auto_import=False):
        rep = self.get_report_status(month_str, report_code)
        if not rep:
            return False
        if rep.get("download") != "DONE":
            return False
        if auto_import and rep.get("import") != "DONE":
            return False
        return True

    def is_month_fully_done(self, month_str, report_codes, auto_import=False, recalc_kpi=False):
        m = self.data["months"].get(month_str)
        if not m:
            return False
        for r_code in report_codes:
            if not self.is_report_done(month_str, r_code, auto_import=auto_import):
                return False
        if recalc_kpi and not m.get("reconciled", False):
            return False
        return True

    def reset_active_period(self, month_str, report_codes):
        """Xóa cờ DONE cho tháng hiện hành để buộc đồng bộ lại mỗi ngày."""
        if month_str not in self.data["months"]:
            return
        m = self.data["months"][month_str]
        m["status"] = "PENDING_DAILY_SYNC"
        m["reconciled"] = False
        for code in report_codes:
            if code in m.get("reports", {}):
                m["reports"][code]["download"] = "PENDING"
                m["reports"][code]["import"] = "PENDING"
        m["updated_at"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self.save()
        print(f"  🔄 [ACTIVE PERIOD RESET] Đã xóa cờ DONE cho tháng {month_str} ({len(report_codes)} báo cáo). Sẵn sàng đồng bộ lại.")


def generate_month_list(from_month_str, to_month_str):
    """Sinh danh sách các chuỗi tháng 'YYYY-MM' từ from_month đến to_month."""
    try:
        from_y, from_m = map(int, from_month_str.split('-'))
        to_y, to_m = map(int, to_month_str.split('-'))
    except Exception as e:
        raise ValueError(f"Định dạng tháng không hợp lệ (cần YYYY-MM): {e}")

    months = []
    curr_y, curr_m = from_y, from_m
    while (curr_y < to_y) or (curr_y == to_y and curr_m <= to_m):
        months.append(f"{curr_y:04d}-{curr_m:02d}")
        curr_m += 1
        if curr_m > 12:
            curr_m = 1
            curr_y += 1
    return months


def find_existing_file_for_month(prefix, year, month):
    """Kiểm tra xem file báo cáo mới tải về cho tháng đã tồn tại trong media/auto_imports chưa."""
    month_suffix = f"{year:04d}{month:02d}"
    candidate_names = [
        f"{prefix}_{month_suffix}.xlsx",
    ]
    for fname in candidate_names:
        fpath = os.path.join(AUTO_IMPORTS_DIR, fname)
        if os.path.exists(fpath) and os.path.getsize(fpath) > 2000:
            return fpath
    return None


def is_active_period(month_str):
    """
    Kiểm tra xem một kỳ tháng có phải là tháng hiện tại hoặc tương lai không.
    Tháng active TUYỆT ĐỐI KHÔNG được khóa bằng DONE trong checkpoint.
    Mỗi lần đồng bộ phải tải lại snapshot mới nhất.
    """
    now = datetime.now()
    try:
        y, m = map(int, month_str.split('-'))
        return (y > now.year) or (y == now.year and m >= now.month)
    except Exception:
        return False


def run_batch_pipeline(from_month='2026-01', to_month='2026-09', reports='BAN_HANG',
                       auto_import=False, recalc_kpi=False, only_download=False,
                       force=False, resume=True, checkpoint_file=CHECKPOINT_DEFAULT_PATH,
                       cutoff_date_override=None, daily_sync=False):
    
    checkpoint = BatchCheckpointManager(checkpoint_file)
    month_list = generate_month_list(from_month, to_month)
    REPORT_GROUPS = {
        'GROUP_1': ['BAN_HANG', 'MUA_HANG', 'TAI_KHOAN_CT', 'TON_KHO', 'CONG_NO_NCC'],
        'GROUP_2': ['SO_DU_NH', 'TUOI_NO_KH'],
        'GROUP_3': ['DANH_SACH_KHACH_HANG', 'DANH_SACH_NHAN_VIEN'],
        'ALL': ['BAN_HANG', 'MUA_HANG', 'TAI_KHOAN_CT', 'TON_KHO', 'CONG_NO_NCC', 'SO_DU_NH', 'TUOI_NO_KH', 'DANH_SACH_KHACH_HANG', 'DANH_SACH_NHAN_VIEN']
    }
    raw_prefixes = [r.strip() for r in reports.split(',') if r.strip()]
    report_prefixes = []
    for r in raw_prefixes:
        if r.upper() in REPORT_GROUPS:
            report_prefixes.extend(REPORT_GROUPS[r.upper()])
        else:
            report_prefixes.append(r)
    report_prefixes = list(dict.fromkeys(report_prefixes))

    print("=" * 80)
    print(f"🚀 KHỞI ĐỘNG BATCH MISA DOWNLOAD & SYNC: KỲ {from_month} -> {to_month}")
    print(f"📋 Danh sách báo cáo ({len(report_prefixes)}): {report_prefixes}")
    print(f"💾 Checkpoint File (2D Matrix): {checkpoint_file}")
    print(f"⚙️  Tùy chọn: auto_import={auto_import}, recalc_kpi={recalc_kpi}, only_download={only_download}, resume={resume}, force={force}")
    if cutoff_date_override:
        print(f"🎯 Cutoff Date Override: '{cutoff_date_override}'")
    print("=" * 80)

    total_months = len(month_list)
    success_months = []
    skipped_months = []
    failed_items = []

    for m_idx, month_str in enumerate(month_list, 1):
        year, month = map(int, month_str.split('-'))
        month_suffix = f"{year:04d}{month:02d}"
        period_str = f"Tháng {month}"

        # === PERMANENT FIX: ACTIVE PERIOD PROTECTION ===
        # Tháng đang diễn ra (hiện tại hoặc tương lai): Không bao giờ được skip bởi checkpoint.
        # Mỗi lần chạy daily-sync phải tải lại snapshot mới nhất.
        period_is_active = is_active_period(month_str)
        if daily_sync and period_is_active:
            # Reset checkpoint của tháng này trước khi chạy
            checkpoint.reset_active_period(month_str, report_prefixes)
            force_this_period = True  # Buộc download + import lại
            print(f"  ⚡ [DAILY SYNC] Kỳ {month_str} là tháng hiện hành → Reset checkpoint, tải snapshot mới.")
        else:
            force_this_period = force

        if cutoff_date_override:
            cutoff_date = cutoff_date_override
        elif daily_sync and period_is_active:
            # Daily sync: luôn dùng ngày hôm nay làm cutoff cho tháng hiện hành
            cutoff_date = datetime.now().strftime("%d/%m/%Y")
            print(f"  📅 [DAILY SYNC] Cutoff tự động = ngày hôm nay: '{cutoff_date}'")
        else:
            cutoff_date = compute_cutoff_date(custom_period_suffix=month_suffix)

        print("\n" + "-" * 75)
        print(f"📌 [{m_idx}/{total_months}] TIẾN HÀNH XỬ LÝ KỲ: {month_str} (MISA Period: '{period_str}' | Cutoff Date: '{cutoff_date}')")
        print("-" * 75)

        month_all_reports_done = True

        for r_idx, prefix in enumerate(report_prefixes, 1):
            checkpoint.set_current(month_str, prefix)
            rep_status = checkpoint.get_report_status(month_str, prefix)
            rep_done = checkpoint.is_report_done(month_str, prefix, auto_import=auto_import)

            # Kiểm tra file trên đĩa
            existing_file = find_existing_file_for_month(prefix, year, month)
            if existing_file and not rep_status.get("file_path"):
                checkpoint.update_report(
                    month_str, prefix,
                    download="DONE",
                    file_path=existing_file,
                    file_size=os.path.getsize(existing_file)
                )
                rep_status = checkpoint.get_report_status(month_str, prefix)
                rep_done = checkpoint.is_report_done(month_str, prefix, auto_import=auto_import)

            if resume and not force_this_period and rep_done:
                if period_is_active:
                    # ACTIVE PERIOD: Không bao giờ skip - tháng đang chạy luôn cần refresh
                    print(f"  🔄 [ACTIVE PERIOD] Kỳ {month_str} là tháng hiện hành → Bỏ qua skip, tải lại snapshot.")
                else:
                    print(f"  ⏭️ [RESUME SKIP] Kỳ {month_str} - Báo cáo '{prefix}' đã hoàn tất. Bỏ qua.")
                    continue

            target_file_path = existing_file
            download_needed = force_this_period or (rep_status.get("download") != "DONE") or (not existing_file) or (daily_sync and period_is_active)

            # 1. BƯỚC TẢI FILE TỪ MISA
            if download_needed:
                is_snapshot = prefix in ['SO_DU_NH', 'TUOI_NO_KH']
                param_desc = f"Cutoff='{cutoff_date}'" if is_snapshot else f"Period='{period_str}'"
                print(f"  🌐 [BƯỚC 1/3 - TẢI MISA] [{r_idx}/{len(report_prefixes)}] Đang tải '{prefix}' ({param_desc})...")
                checkpoint.update_report(month_str, prefix, download="IN_PROGRESS")

                try:
                    res_msg = asyncio.run(run_misa_automation(
                        period_option=period_str,
                        prefix_filter=prefix,
                        use_saved_reports=True,
                        custom_period_suffix=month_suffix,
                        output_dir=AUTO_IMPORTS_DIR,
                        cutoff_date=cutoff_date
                    ))
                    print(f"    -> Kết quả MISA ({prefix}): {res_msg}")

                    expected_file = os.path.join(AUTO_IMPORTS_DIR, f"{prefix}_{month_suffix}.xlsx")
                    if os.path.exists(expected_file) and os.path.getsize(expected_file) > 2000:
                        # FAIL-FAST: Kiểm tra mốc ngày chốt trong subtitle file Excel
                        if prefix == 'TUOI_NO_KH' and cutoff_date:
                            import openpyxl
                            wb_chk = openpyxl.load_workbook(expected_file, read_only=True)
                            ws_chk = wb_chk.active
                            sub_text = ""
                            for r_chk in range(1, 6):
                                val_c1 = ws_chk.cell(row=r_chk, column=1).value
                                if val_c1 and "Đến ngày" in str(val_c1):
                                    sub_text = str(val_c1).strip()
                                    break
                            wb_chk.close()
                            
                            if cutoff_date not in sub_text:
                                err_msg = (
                                    f"🚨 [CRITICAL FAIL-FAST] File {os.path.basename(expected_file)} có subtitle ngày "
                                    f"'{sub_text}' KHÔNG KHỚP với ngày cutoff yêu cầu '{cutoff_date}'. "
                                    f"Dữ liệu bị đóng băng/MISA không nhận tham số. Dừng tiến trình ngay lập tức!"
                                )
                                print(f"    ❌ {err_msg}")
                                checkpoint.update_report(month_str, prefix, download="FAILED", error=err_msg)
                                raise RuntimeError(err_msg)

                        target_file_path = expected_file
                        file_size = os.path.getsize(expected_file)
                        checkpoint.update_report(
                            month_str, prefix,
                            download="DONE",
                            file_path=expected_file,
                            file_size=file_size,
                            error=None
                        )
                        print(f"    ✅ Đã tải file thành công: {os.path.basename(expected_file)} ({file_size:,} bytes)")

                    else:
                        found = find_existing_file_for_month(prefix, year, month)
                        if found:
                            target_file_path = found
                            checkpoint.update_report(
                                month_str, prefix,
                                download="DONE",
                                file_path=found,
                                file_size=os.path.getsize(found),
                                error=None
                            )
                            print(f"    ✅ Phát hiện file khớp: {os.path.basename(found)}")
                        else:
                            raise RuntimeError(f"Không tìm thấy file {prefix}_{month_suffix}.xlsx sau khi tải")

                except Exception as dl_err:
                    err_msg = f"Lỗi tải MISA {prefix} kỳ {month_str}: {dl_err}"
                    print(f"    ❌ {err_msg}")
                    checkpoint.update_report(month_str, prefix, download="FAILED", error=str(dl_err))
                    failed_items.append((month_str, prefix, err_msg))
                    month_all_reports_done = False
                    continue
            else:
                print(f"  ⚡ [DOWNLOAD CACHED] [{r_idx}/{len(report_prefixes)}] '{prefix}' đã có file: {os.path.basename(target_file_path)} ({os.path.getsize(target_file_path):,} bytes)")

            if only_download:
                continue

            # 2. BƯỚC NẠP VÀO DATABASE (AUTO-IMPORT)
            if auto_import and target_file_path:
                import_needed = force_this_period or (rep_status.get("import") != "DONE") or (daily_sync and period_is_active)
                if import_needed:
                    print(f"  📥 [BƯỚC 2/3 - IMPORT DB] Đang nạp {os.path.basename(target_file_path)} vào CSDL...")
                    checkpoint.update_report(month_str, prefix, import_status="IN_PROGRESS")
                    try:
                        import_res = auto_import_excel_from_folder(specific_file=target_file_path)
                        print(f"    -> Kết quả Import: {import_res}")

                        succ_path = os.path.join(SUCCESS_DIR, os.path.basename(target_file_path))
                        final_path = succ_path if os.path.exists(succ_path) else target_file_path

                        checkpoint.update_report(
                            month_str, prefix,
                            import_status="DONE",
                            file_path=final_path,
                            error=None
                        )
                        print(f"    ✅ Nạp dữ liệu {prefix} tháng {month_str} thành công!")
                    except Exception as imp_err:
                        err_msg = f"Lỗi nạp Excel {prefix} tháng {month_str}: {imp_err}"
                        print(f"    ❌ {err_msg}")
                        checkpoint.update_report(month_str, prefix, import_status="FAILED", error=str(imp_err))
                        failed_items.append((month_str, prefix, err_msg))
                        month_all_reports_done = False
                        continue
                else:
                    print(f"  ⚡ [IMPORT CACHED] Dữ liệu {prefix} tháng {month_str} đã nạp DB trước đó.")

        # 3. BƯỚC TÍNH TOÁN LẠI KPI DASHBOARD (sau khi duyệt xong các báo cáo trong tháng)
        if recalc_kpi and month_all_reports_done and not only_download:
            month_meta = checkpoint.data["months"].get(month_str, {})
            recalc_needed = force or not month_meta.get("reconciled", False)
            if recalc_needed:
                print(f"\n  📊 [BƯỚC 3/3 - RECALC KPI] Tính toán lại KPI Tổng công ty & 22 BU kỳ {month}/{year}...")
                try:
                    msg_corp = update_single_bu_performance(bu_id=None, month=month, year=year)
                    print(f"    - Tổng công ty: {msg_corp}")
                    for bu in BusinessUnit.objects.all():
                        update_single_bu_performance(bu_id=bu.id, month=month, year=year)
                    checkpoint.update_month_meta(month_str, reconciled=True, status="COMPLETED")
                    print(f"    ✅ Đã tính lại toàn bộ KPI tháng {month}/{year}!")
                except Exception as kpi_err:
                    print(f"    ⚠️ Lỗi tính KPI tháng {month_str}: {kpi_err}")
            else:
                print(f"  ⚡ [KPI CACHED] KPI tháng {month_str} đã được tính toán.")

        if month_all_reports_done:
            checkpoint.update_month_meta(month_str, status="COMPLETED")
            success_months.append(month_str)

    checkpoint.set_current(None, None)

    print("\n" + "=" * 80)
    print("🏁 TỔNG KẾT TIẾN TRÌNH BATCH MISA:")
    print(f"  - Tổng số tháng chỉ định: {total_months}")
    print(f"  - Thành công: {len(success_months)} tháng: {success_months}")
    print(f"  - Thất bại / Dở dang: {len(failed_items)} mục: {failed_items}")
    print(f"  - File Checkpoint 2D hiện tại: {checkpoint_file}")
    print("=" * 80)

    return len(failed_items) == 0


def main():
    if hasattr(sys.stdout, 'reconfigure'):
        try:
            sys.stdout.reconfigure(encoding='utf-8')
        except Exception:
            pass

    parser = argparse.ArgumentParser(
        description="Script tải batch báo cáo MISA AMIS theo dải tháng (01/2026 -> 09/2026) có Checkpoint 2D State Persistence."
    )
    parser.add_argument('--from-month', default='2026-01', help="Tháng bắt đầu (định dạng YYYY-MM, mặc định: 2026-01)")
    parser.add_argument('--to-month', default='2026-09', help="Tháng kết thúc (định dạng YYYY-MM, mặc định: 2026-09)")
    parser.add_argument('--reports', default='BAN_HANG', help="Danh sách prefix báo cáo phân cách dấu phẩy (mặc định: BAN_HANG)")
    parser.add_argument('--auto-import', action='store_true', help="Tự động nạp file Excel vào DB ngay sau khi tải")
    parser.add_argument('--recalc-kpi', action='store_true', help="Tự động tính toán lại KPI Dashboard cho từng tháng")
    parser.add_argument('--only-download', action='store_true', help="Chỉ tải file về máy, không nạp DB và không tính KPI")
    parser.add_argument('--force', action='store_true', help="Bắt buộc tải lại và nạp lại toàn bộ, bỏ qua checkpoint cũ")
    parser.add_argument('--resume', action='store_true', help="Tự động resume từ checkpoint (mặc định)")
    parser.add_argument('--no-resume', dest='resume', action='store_false', help="Tắt tính năng tự động resume từ checkpoint")
    parser.add_argument('--checkpoint-file', default=CHECKPOINT_DEFAULT_PATH, help="Đường dẫn lưu file JSON checkpoint")
    parser.add_argument('--cutoff-date', default=None, help="Mốc ngày chốt snapshot tùy chỉnh (DD/MM/YYYY), ví dụ: 05/09/2026")
    parser.add_argument('--weekly-sync', action='store_true', help="Chế độ chạy tự động định kỳ cuối tuần (đồng bộ YTD, auto-import, recalc KPI)")
    parser.add_argument('--daily-sync', action='store_true', help="Chế độ đồng bộ hàng ngày: Tự động reset checkpoint tháng hiện hành và lấy cutoff = ngày hôm nay. Không bao giờ skip Active Period.")
    parser.set_defaults(resume=True)

    args = parser.parse_args()

    # Xử lý cờ --weekly-sync
    if args.weekly_sync:
        now = datetime.now()
        args.from_month = f"{now.year}-01"
        args.to_month = now.strftime("%Y-%m")
        args.auto_import = True
        args.recalc_kpi = True
        args.resume = True
        if args.reports == 'BAN_HANG':
            args.reports = 'GROUP_1,GROUP_2'
        print(f"⏰ [WEEKLY SYNC MODE ACTIVATED] Đồng bộ tuần tự từ đầu năm {args.from_month} đến tháng hiện tại {args.to_month} (Báo cáo: {args.reports})...")

    # Xử lý cờ --daily-sync
    if args.daily_sync:
        now = datetime.now()
        current_month = now.strftime("%Y-%m")
        # Daily sync chỉ đồng bộ tháng hiện tại, báo cáo công nợ nhạy cảm
        if args.from_month == '2026-01':  # Nếu chưa override từ weekly_sync
            args.from_month = current_month
        args.to_month = current_month
        args.auto_import = True
        args.resume = True
        if args.reports == 'BAN_HANG':  # Default, chưa được set
            args.reports = 'TUOI_NO_KH'  # Daily sync ưu tiên công nợ
        print(f"\n📅 [DAILY SYNC MODE] Kỳ hiện tại: {current_month}")
        print(f"   Cutoff tự động = ngày hôm nay: {now.strftime('%d/%m/%Y')}")
        print(f"   Báo cáo: {args.reports}")
        print(f"   Active Period Protection: BẬT (tháng {current_month} sẽ không bị skip)\n")

    success = run_batch_pipeline(
        from_month=args.from_month,
        to_month=args.to_month,
        reports=args.reports,
        auto_import=args.auto_import,
        recalc_kpi=args.recalc_kpi,
        only_download=args.only_download,
        force=args.force,
        resume=args.resume,
        checkpoint_file=args.checkpoint_file,
        cutoff_date_override=args.cutoff_date,
        daily_sync=args.daily_sync
    )

    sys.exit(0 if success else 1)


if __name__ == '__main__':
    main()
