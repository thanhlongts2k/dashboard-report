import os
import asyncio
import logging
from datetime import datetime
from django.conf import settings
from playwright.async_api import async_playwright
from .browser import login_to_misa, close_misa_popups, click_saved_report_link
from .report_exporter import download_report_from_url, merge_tuoi_no_kh_excel_files

logger = logging.getLogger(__name__)

async def run_misa_automation(period_option=None, prefix_filter=None):
    """Chạy tự động tải báo cáo MISA. Nếu prefix_filter được truyền vào, chỉ tải đúng 1 loại báo cáo khớp tiền tố đó."""
    email = settings.MISA_EMAIL
    password = settings.MISA_PASSWORD
    headless = settings.MISA_HEADLESS
    
    if not email or not password:
        raise Exception("MISA_EMAIL and MISA_PASSWORD must be configured in settings/.env")

    auto_imports_dir = os.path.join(settings.BASE_DIR, 'media', 'auto_imports')
    os.makedirs(auto_imports_dir, exist_ok=True)

    async with async_playwright() as p:
        logger.info(f"Launching Playwright Chromium (headless={headless})...")
        browser = await p.chromium.launch(
            headless=headless,
            args=[
                '--disable-blink-features=AutomationControlled',
                '--no-sandbox',
                '--disable-setuid-sandbox'
            ]
        )
        
        context = None
        state_path = settings.MISA_BROWSER_STATE_PATH
        if os.path.exists(state_path):
            try:
                logger.info(f"Loading existing browser state from: {state_path}")
                context = await browser.new_context(
                    storage_state=state_path,
                    viewport={'width': 1366, 'height': 768},
                    user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
                )
            except Exception as e:
                logger.warning(f"Failed to load storage_state: {e}. Creating clean context...")
                context = await browser.new_context(
                    viewport={'width': 1366, 'height': 768},
                    user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
                )
        else:
            context = await browser.new_context(
                viewport={'width': 1366, 'height': 768},
                user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
            )

        context.set_default_timeout(30000)
        
        # Inject Smart Anti-Popup Engine script globally across all pages and sub-frames
        from .browser import get_global_anti_popup_script
        try:
            await context.add_init_script(get_global_anti_popup_script())
            logger.info("Successfully injected Global Smart Anti-Popup Engine script into browser context.")
        except Exception as e:
            logger.warning(f"Could not inject init script: {e}")

        page = await context.new_page()
        
        try:
            logger.info("Verifying session state by navigating to MISA home...")
            await page.goto("https://actapp.misa.vn/", timeout=30000, wait_until="load")
            await asyncio.sleep(3)
            
            if "login" in page.url or "sso" in page.url or "id.misa.vn" in page.url or "amisapp.misa.vn/login" in page.url:
                logger.info("Session expired. Logging in...")
                await login_to_misa(page, context, email, password)
            else:
                logger.info("Existing session is valid!")
        except Exception as e:
            logger.warning(f"Error checking session, re-logging in: {str(e)}")
            await login_to_misa(page, context, email, password)

        file_suffix = datetime.now().strftime('%Y%m%d_%H%M%S')
        downloaded_count = 0
        failed_count = 0
        failed_details = []

        use_saved_reports_option = getattr(settings, 'USE_OPTION_EXPORT_REPORT_MISA', 2) == 2
        
        if use_saved_reports_option:
            logger.info("Using USE_OPTION_EXPORT_REPORT_MISA = 2 (Saved Reports Flow)")
            if prefix_filter:
                logger.info(f"[prefix_filter] Only processing prefix: '{prefix_filter}'")
            
            # 1. Danh sách các báo cáo đơn lẻ từ MISA Saved Reports
            standard_saved_reports = [
                ('BAN_HANG', '01 - Sổ chi tiết bán hàng'),
                ('MUA_HANG', '02 - Sổ chi tiết mua hàng'),
                ('TON_KHO', '03 - Tổng hợp tồn kho'),
                ('CONG_NO_NCC', '04 - Tổng hợp công nợ phải trả nhà cung cấp'),
                ('TAI_KHOAN_CT', '05 - Sổ chi tiết các tài khoản'),
                ('SO_DU_NH', '07 - Bảng kê số dư ngân hàng'),
            ]

            needs_saved_reports = not prefix_filter or prefix_filter in [p for p, _ in standard_saved_reports] or prefix_filter == 'TUOI_NO_KH'

            if needs_saved_reports:
                logger.info(f"Navigating to MISA Saved Reports List: {settings.MISA_URL_REPORT_SAVED}")
                try:
                    await page.goto(settings.MISA_URL_REPORT_SAVED, timeout=30000, wait_until="load")
                except Exception as e:
                    logger.warning(f"Navigation to Saved Reports List timed out or failed: {str(e)}")
                try:
                    await page.wait_for_load_state("domcontentloaded", timeout=10000)
                except Exception:
                    pass
                
                await close_misa_popups(page)
                await asyncio.sleep(2)
                
                # A. Tải lần lượt các báo cáo đơn lẻ
                for prefix, report_name in standard_saved_reports:
                    if prefix_filter and prefix != prefix_filter:
                        continue
                    filename = f"{prefix}_{file_suffix}.xlsx"
                    output_path = os.path.join(auto_imports_dir, filename)
                    logger.info(f"Processing saved report: '{report_name}' (Prefix: {prefix})")
                    
                    # Đảm bảo page đang ở ReportSavedList
                    try:
                        if not page.url.startswith(settings.MISA_URL_REPORT_SAVED):
                            logger.info(f"Ensuring page is at Saved Reports List: {settings.MISA_URL_REPORT_SAVED}")
                            await page.goto(settings.MISA_URL_REPORT_SAVED, timeout=30000, wait_until="load")
                            await close_misa_popups(page)
                    except Exception:
                        pass

                    target_page, is_popup = await click_saved_report_link(page, report_name)
                    if not target_page:
                        logger.error(f"Failed to find or click saved report link: '{report_name}'")
                        failed_count += 1
                        failed_details.append(f"{prefix} (Saved Report): Link not found")
                        continue
                        
                    try:
                        success = await download_report_from_url(target_page, None, settings.MISA_EXPORT_SELECTOR, output_path, prefix=prefix, skip_parameters=True)
                        if success:
                            downloaded_count += 1
                        else:
                            failed_count += 1
                            logger.error(f"Failed to download saved report: '{report_name}'")
                            failed_details.append(f"{prefix} (Saved Report): Failed to download")
                    except Exception as e:
                        failed_count += 1
                        logger.error(f"Error downloading saved report '{report_name}': {str(e)}")
                        failed_details.append(f"{prefix} (Saved Report): {str(e)}")
                    finally:
                        if is_popup and target_page:
                            try:
                                logger.info("Closing report popup tab to free RAM...")
                                await target_page.close()
                            except Exception as ce:
                                logger.warning(f"Failed to close popup tab: {str(ce)}")
                        
                        # Luôn đảm bảo page quay lại Saved Reports List an toàn
                        try:
                            if not page.url.startswith(settings.MISA_URL_REPORT_SAVED):
                                logger.info(f"Returning to Saved Reports List: {settings.MISA_URL_REPORT_SAVED}")
                                await page.goto(settings.MISA_URL_REPORT_SAVED, timeout=30000, wait_until="load")
                                await page.wait_for_load_state("domcontentloaded", timeout=10000)
                                await close_misa_popups(page)
                                await asyncio.sleep(1.5)
                        except Exception as e:
                            logger.warning(f"Failed to navigate back to Saved Reports List: {str(e)}")

                # B. Tải và gộp Tuổi nợ TUOI_NO_KH (131 và 1311)
                if not prefix_filter or prefix_filter == 'TUOI_NO_KH':
                    logger.info("[TUOI_NO_KH] Processing Tuoi No multi-account saved reports (131 & 1311)...")
                    tuoi_no_saved_reports = [
                        ('131', '06 - Chi tiết công nợ phải thu theo tuổi nợ 131'),
                        ('1311', '06 - Chi tiết công nợ phải thu theo tuổi nợ 1311'),
                    ]
                    acc_file_map = {}
                    scratch_dir = os.path.join(settings.BASE_DIR, 'scratch', 'temp_tuoi_no')
                    os.makedirs(scratch_dir, exist_ok=True)

                    for acc_code, report_name in tuoi_no_saved_reports:
                        temp_file = os.path.join(scratch_dir, f"temp_TUOI_NO_KH_{acc_code}.xlsx")
                        logger.info(f"[TUOI_NO_KH] Downloading saved report '{report_name}' -> {temp_file}")
                        
                        # Đảm bảo page đang ở ReportSavedList
                        try:
                            if not page.url.startswith(settings.MISA_URL_REPORT_SAVED):
                                logger.info(f"Ensuring page is at Saved Reports List: {settings.MISA_URL_REPORT_SAVED}")
                                await page.goto(settings.MISA_URL_REPORT_SAVED, timeout=30000, wait_until="load")
                                await close_misa_popups(page)
                        except Exception:
                            pass

                        target_page, is_popup = await click_saved_report_link(page, report_name)
                        if not target_page:
                            logger.error(f"Failed to find or click saved report link: '{report_name}'")
                            continue

                        try:
                            success = await download_report_from_url(target_page, None, settings.MISA_EXPORT_SELECTOR, temp_file, prefix='TUOI_NO_KH', skip_parameters=True)
                            if success and os.path.exists(temp_file):
                                acc_file_map[acc_code] = temp_file
                        except Exception as e:
                            logger.error(f"Error downloading '{report_name}': {str(e)}")
                        finally:
                            if is_popup and target_page:
                                try:
                                    logger.info("Closing report popup tab to free RAM...")
                                    await target_page.close()
                                except Exception as ce:
                                    logger.warning(f"Failed to close popup tab: {str(ce)}")

                            try:
                                if not page.url.startswith(settings.MISA_URL_REPORT_SAVED):
                                    logger.info(f"Returning to Saved Reports List: {settings.MISA_URL_REPORT_SAVED}")
                                    await page.goto(settings.MISA_URL_REPORT_SAVED, timeout=30000, wait_until="load")
                                    await page.wait_for_load_state("domcontentloaded", timeout=10000)
                                    await close_misa_popups(page)
                                    await asyncio.sleep(1.5)
                            except Exception as e:
                                logger.warning(f"Failed to navigate back to Saved Reports List: {str(e)}")

                    if acc_file_map:
                        final_tuoi_no_path = os.path.join(auto_imports_dir, f"TUOI_NO_KH_{file_suffix}.xlsx")
                        merged = merge_tuoi_no_kh_excel_files(acc_file_map, final_tuoi_no_path)
                        if merged and os.path.exists(final_tuoi_no_path):
                            downloaded_count += 1
                            logger.info(f"[TUOI_NO_KH] SUCCESS: Created merged file: {final_tuoi_no_path} ({os.path.getsize(final_tuoi_no_path)} bytes)")
                        else:
                            failed_count += 1
                            failed_details.append("TUOI_NO_KH: Failed to merge 131 and 1311")
                    else:
                        failed_count += 1
                        failed_details.append("TUOI_NO_KH: No temp files downloaded for 131/1311")

            # 2. Tải Master Data trực tiếp từ URL (Khách hàng & Nhân viên)
            master_data_reports = [
                ('DANH_SACH_KHACH_HANG', getattr(settings, 'MISA_URL_CUSTOMER', 'https://actapp.misa.vn/app/DI/DICustomer')),
                ('DANH_SACH_NHAN_VIEN', getattr(settings, 'MISA_URL_EMPLOYEE', 'https://actapp.misa.vn/app/DI/DIEmployee')),
            ]
            for prefix, url in master_data_reports:
                if prefix_filter and prefix != prefix_filter and prefix.replace('DANH_SACH_', '') != prefix_filter:
                    continue
                filename = f"{prefix}_{file_suffix}.xlsx"
                output_path = os.path.join(auto_imports_dir, filename)
                logger.info(f"Downloading Master Data '{prefix}' from URL: {url}")
                try:
                    success = await download_report_from_url(page, url, settings.MISA_EXPORT_SELECTOR, output_path, prefix=prefix, skip_parameters=True)
                    if success:
                        downloaded_count += 1
                    else:
                        failed_count += 1
                        failed_details.append(f"{prefix}: Failed to export Master Data")
                except Exception as e:
                    failed_count += 1
                    logger.error(f"Error downloading Master Data '{prefix}': {str(e)}")
                    failed_details.append(f"{prefix}: {str(e)}")
        else:
            logger.info("Using USE_OPTION_EXPORT_REPORT_MISA = 1 (Step-by-step Flow)")
            if prefix_filter:
                logger.info(f"[prefix_filter] Only processing prefix: '{prefix_filter}'")
            # Lọc danh sách báo cáo theo prefix_filter nếu được truyền vào
            reports_to_run = {
                k: v for k, v in settings.MISA_REPORTS.items()
                if v and (not prefix_filter or k == prefix_filter)
            }
            if not reports_to_run:
                logger.warning(f"No reports matched prefix_filter='{prefix_filter}'. Available prefixes: {list(settings.MISA_REPORTS.keys())}")
            for prefix, url in reports_to_run.items():
                filename = f"{prefix}_{file_suffix}.xlsx"
                output_path = os.path.join(auto_imports_dir, filename)
                
                try:
                    success = await download_report_from_url(page, url, settings.MISA_EXPORT_SELECTOR, output_path, prefix=prefix, skip_parameters=False, period_option=period_option)
                    if not success:
                        logger.info("Retrying download after re-logging in...")
                        await login_to_misa(page, context, email, password)
                        success = await download_report_from_url(page, url, settings.MISA_EXPORT_SELECTOR, output_path, prefix=prefix, skip_parameters=False, period_option=period_option)
                        
                    if success:
                        downloaded_count += 1
                    else:
                        failed_count += 1
                        logger.error(f"Failed to download report for prefix {prefix}")
                        failed_details.append(f"{prefix}: Failed to download/login expired")
                except Exception as e:
                    failed_count += 1
                    logger.error(f"Error downloading report for prefix {prefix}: {str(e)}")
                    failed_details.append(f"{prefix}: {str(e)}")
                    
        await browser.close()
        
        result_msg = f"SUCCESS: Downloaded {downloaded_count} reports. Failed {failed_count} reports."
        if failed_count > 0 and failed_details:
            result_msg += " Errors: " + "; ".join(failed_details)
        return result_msg
