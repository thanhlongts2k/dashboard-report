import os
import asyncio
import logging
from datetime import datetime
from django.conf import settings
from playwright.async_api import async_playwright
from .browser import login_to_misa, close_misa_popups
from .report_exporter import download_report_from_url

logger = logging.getLogger(__name__)

async def run_misa_automation(period_option=None):
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
            logger.info("Using USE_OPTION_EXPORT_REPORT_MISA = 2 (Hybrid Flow)")
            
            so_du_nh_url = settings.MISA_REPORTS.get('SO_DU_NH')
            if so_du_nh_url:
                prefix = 'SO_DU_NH'
                filename = f"{prefix}_{file_suffix}.xlsx"
                output_path = os.path.join(auto_imports_dir, filename)
                logger.info(f"Downloading {prefix} via step-by-step export flow...")
                try:
                    success = await download_report_from_url(page, so_du_nh_url, settings.MISA_EXPORT_SELECTOR, output_path, prefix=prefix, skip_parameters=False, period_option=period_option)
                    if not success:
                        logger.info("Retrying SO_DU_NH download after re-logging in...")
                        await login_to_misa(page, context, email, password)
                        success = await download_report_from_url(page, so_du_nh_url, settings.MISA_EXPORT_SELECTOR, output_path, prefix=prefix, skip_parameters=False, period_option=period_option)
                        
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
            
            saved_reports_to_download = [
                ('BAN_HANG', '01 - Sổ chi tiết bán hàng - Important'),
                ('MUA_HANG', '02 - Sổ chi tiết mua hàng - Important'),
                ('TON_KHO', '03 - Tổng hợp tồn kho - Important'),
                ('CONG_NO_NCC', '04 - Tổng hợp công nợ phải trả nhà cung cấp - Important'),
                ('TAI_KHOAN_CT', '06 - Sổ chi tiết các tài khoản - Important'),
            ]
            
            for prefix, report_name in saved_reports_to_download:
                filename = f"{prefix}_{file_suffix}.xlsx"
                output_path = os.path.join(auto_imports_dir, filename)
                logger.info(f"Processing saved report: '{report_name}' (Prefix: {prefix})")
                
                target_page, is_popup = await click_saved_report_link(page, report_name)
                if not target_page:
                    logger.error(f"Failed to find or click saved report link: '{report_name}'")
                    failed_count += 1
                    failed_details.append(f"{prefix} (Saved Report): Link not found")
                    continue
                    
                try:
                    success = await download_report_from_url(target_page, None, settings.MISA_EXPORT_SELECTOR, output_path, prefix=prefix, skip_parameters=True)
                    if not success:
                        logger.info("Retrying download after re-logging in...")
                        if is_popup:
                            try:
                                await target_page.close()
                            except Exception:
                                pass
                        await page.goto(settings.MISA_URL_REPORT_SAVED, timeout=30000, wait_until="load")
                        await login_to_misa(page, context, email, password)
                        await page.goto(settings.MISA_URL_REPORT_SAVED, timeout=30000, wait_until="load")
                        await close_misa_popups(page)
                        target_page, is_popup = await click_saved_report_link(page, report_name)
                        if target_page:
                            success = await download_report_from_url(target_page, None, settings.MISA_EXPORT_SELECTOR, output_path, prefix=prefix, skip_parameters=True)
                        
                    if success:
                        downloaded_count += 1
                    else:
                        failed_count += 1
                        logger.error(f"Failed to download saved report: '{report_name}'")
                        failed_details.append(f"{prefix} (Saved Report): Failed to download/login expired")
                except Exception as e:
                    failed_count += 1
                    logger.error(f"Error downloading saved report '{report_name}': {str(e)}")
                    failed_details.append(f"{prefix} (Saved Report): {str(e)}")
                finally:
                    if is_popup and target_page:
                        try:
                            logger.info("Closing report popup tab...")
                            await target_page.close()
                        except Exception as ce:
                            logger.warning(f"Failed to close popup tab: {str(ce)}")
                    
                if not is_popup:
                    logger.info(f"Returning to Saved Reports List: {settings.MISA_URL_REPORT_SAVED}")
                    try:
                        await page.goto(settings.MISA_URL_REPORT_SAVED, timeout=30000, wait_until="load")
                        await page.wait_for_load_state("domcontentloaded", timeout=10000)
                        await close_misa_popups(page)
                        await asyncio.sleep(2)
                    except Exception as e:
                        logger.warning(f"Failed to navigate back to Saved Reports List: {str(e)}")
        else:
            logger.info("Using USE_OPTION_EXPORT_REPORT_MISA = 1 (Step-by-step Flow)")
            for prefix, url in settings.MISA_REPORTS.items():
                if not url:
                    continue
                    
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
