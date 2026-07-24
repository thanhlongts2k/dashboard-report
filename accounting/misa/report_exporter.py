import os
import asyncio
import logging
from django.conf import settings
from .browser import find_locator_in_any_frame, close_misa_popups

logger = logging.getLogger(__name__)

async def select_accounts_for_so_chi_tiet(page, accounts):
    bac_selectors = [
        "xpath=//div[contains(@class,'ms-search-account')]//div[contains(@class,'ms-combo')]//input",
        "xpath=//span[normalize-space(text())='Bậc']/following::div[contains(@class,'ms-combo')][1]//input",
        "xpath=//th[normalize-space(text())='Bậc']/preceding::input[contains(@class,'dx-texteditor-input')][1]",
        "xpath=//div[contains(@class,'ms-combo') and not(ancestor::*[contains(@class,'ms-date')])][last()]//input",
        ".ms-search-account .ms-combo input",
        "xpath=(//div[contains(@class,'param') or contains(@class,'filter')]//input[@type='text'])[last()]",
    ]
    bac_input, bac_frame = await find_locator_in_any_frame(page, bac_selectors, timeout=3000)
    if bac_input:
        logger.info("Clicking 'Bac' combobox to open options...")
        await bac_input.click(force=True)
        await asyncio.sleep(0.5)
        
        bac1_selectors = [
            "xpath=//div[contains(@class,'dx-dropdowneditor-overlay')]//div[contains(@class,'dx-item-content') and normalize-space(.)='1']",
            "xpath=//div[contains(@class,'dx-item-content') and normalize-space(text())='1']",
            "xpath=//li[contains(@class,'dx-list-item')][normalize-space(.)='1']",
            "xpath=//*[contains(@class,'ms-combo-item') or contains(@class,'ms-select-item')][normalize-space(text())='1']",
            "xpath=//div[contains(@class,'ms-dropdown')]//*[normalize-space(text())='1']"
        ]
        bac1_item, _ = await find_locator_in_any_frame(page, bac1_selectors, timeout=2000)
        if bac1_item:
            logger.info("Selecting 'Bac 1'...")
            await bac1_item.click(force=True)
        else:
            logger.warning("Could not find 'Bac 1' option. Trying keyboard input...")
            try:
                await bac_input.click(force=True)
                await asyncio.sleep(0.5)
                await page.keyboard.press("Home")
                await asyncio.sleep(0.2)
                await page.keyboard.press("ArrowDown")
                await asyncio.sleep(0.2)
                await page.keyboard.press("Enter")
                logger.info("Used keyboard ArrowDown to select Bac 1 and pressed Enter.")
            except Exception as e:
                logger.error(f"Failed to select Bac 1: {str(e)}")
        await asyncio.sleep(0.5)
    else:
        logger.warning("Could not find 'Bac' combobox. Skipping.")
    
    account_search_selectors = [
        "input[placeholder='Nhập từ khóa tìm kiếm']",
        "xpath=//input[@placeholder='Nhập từ khóa tìm kiếm']",
        "input[placeholder*='từ khóa']",
        "input[placeholder*='tìm kiếm']",
        ".ms-input-search input",
    ]
    
    for account_code in accounts:
        logger.info(f"Searching and selecting account: {account_code}")
        
        acc_input, acc_frame = await find_locator_in_any_frame(page, account_search_selectors, timeout=3000)
        if not acc_input:
            logger.warning(f"Could not find account search textbox for {account_code}. Skipping.")
            continue
        
        try:
            await acc_input.click(force=True)
            await asyncio.sleep(0.2)
            await acc_input.fill("")
            await acc_input.type(account_code)
            await asyncio.sleep(1.5)
            logger.info(f"Typed account code '{account_code}' in search box.")
        except Exception as e:
            logger.error(f"Failed to type account {account_code}: {str(e)}")
            continue
        
        clicked = False
        try:
            js_script = f"""
            (() => {{
                const rows = document.querySelectorAll('tr, [role="row"], .dx-data-row, .dx-row, .ms-tr');
                if (rows.length === 0) return false;
                
                for (const row of rows) {{
                    const cells = row.querySelectorAll('td, th, [role="cell"], .dx-cell, .ms-td');
                    let hasMatch = false;
                    for (const cell of cells) {{
                        if (cell.textContent.trim() === '{account_code}') {{
                            hasMatch = true;
                            break;
                        }}
                    }}
                    if (hasMatch) {{
                        const cb = row.querySelector('input[type="checkbox"], .dx-checkbox, .ms-checkbox, .checkbox, [role="checkbox"]');
                        if (cb) {{
                            let isChecked = false;
                            if (cb.tagName === 'INPUT') {{
                                isChecked = cb.checked;
                            }} else {{
                                isChecked = cb.classList.contains('dx-checkbox-checked') || 
                                            cb.classList.contains('is-checked') || 
                                            cb.classList.contains('checked') || 
                                            cb.getAttribute('aria-checked') === 'true' ||
                                            row.classList.contains('dx-selection') ||
                                            row.getAttribute('aria-selected') === 'true';
                            }}
                            if (!isChecked) {{ cb.click(); }}
                            return true;
                        }}
                        if (cells.length > 0) {{ cells[0].click(); return true; }}
                    }}
                }}
                
                let dataRow = rows[0];
                if (rows.length > 1 && (rows[0].closest('thead') || rows[0].querySelector('th'))) {{
                    dataRow = rows[1];
                }}
                const cb = dataRow.querySelector('input[type="checkbox"], .dx-checkbox, .ms-checkbox, .checkbox, [role="checkbox"]');
                if (cb) {{ cb.click(); return true; }}
                
                const cells = dataRow.querySelectorAll('td, [role="cell"], .dx-cell, .ms-td');
                if (cells.length > 0) {{ cells[0].click(); return true; }}
                
                return false;
            }})()
            """
            frames_to_check = [page] + page.frames
            for f in frames_to_check:
                try:
                    if await f.evaluate(js_script):
                        clicked = True
                        break
                except:
                    pass
            
            if clicked:
                logger.info(f"Successfully clicked checkbox for {account_code} via JS.")
        except Exception as e:
            logger.error(f"JS fallback for {account_code} failed: {str(e)}")

        if not clicked:
            logger.warning(f"Could not click via JS for {account_code}, trying XPath locators fallback to first row...")
            first_row_selectors = [
                "xpath=(//tr[contains(@class,'dx-row')]//div[contains(@class,'dx-checkbox')])[1]",
                "xpath=(//div[contains(@class,'dx-data-row')]//div[contains(@class,'dx-checkbox')])[1]",
                ".dx-checkbox:visible"
            ]
            first_row_cb, _ = await find_locator_in_any_frame(page, first_row_selectors, timeout=1500)
            if first_row_cb:
                await first_row_cb.click(force=True)
                logger.info(f"Clicked first row checkbox as fallback for account {account_code}.")
            else:
                logger.warning(f"Could not find any checkbox for {account_code}. Skipping to next.")
        
        await asyncio.sleep(0.5)
    
    logger.info(f"Finished selecting accounts: {accounts}")


async def click_saved_report_link(page, report_name, creator='NGUYỄN THÀNH LONG'):
    link_el = None
    target_frame = None
    
    for frame in [page] + page.frames:
        try:
            loc = frame.locator("tr, [role='row']").filter(has_text=creator).locator("span.drilldown").filter(has_text=report_name).first
            if await loc.is_visible(timeout=1000):
                link_el = loc
                target_frame = frame
                break
        except Exception:
            pass
            
        try:
            loc = frame.locator("tr, [role='row']").filter(has_text=creator).locator("span").filter(has_text=report_name).first
            if await loc.is_visible(timeout=1000):
                link_el = loc
                target_frame = frame
                break
        except Exception:
            pass

        try:
            loc = frame.locator("tr, [role='row']").filter(has_text=creator).locator("a").filter(has_text=report_name).first
            if await loc.is_visible(timeout=1000):
                link_el = loc
                target_frame = frame
                break
        except Exception:
            pass

        try:
            loc = frame.locator("tr, [role='row']").filter(has_text=creator).locator(f"text='{report_name}'").first
            if await loc.is_visible(timeout=1000):
                link_el = loc
                target_frame = frame
                break
        except Exception:
            pass

    if link_el:
        logger.info(f"Found saved report link '{report_name}' by '{creator}'. Clicking it...")
        try:
            async with page.expect_popup(timeout=3000) as popup_info:
                await link_el.click(timeout=5000)
            new_page = await popup_info.value
            logger.info("Report opened in a new tab/popup.")
            return new_page, True
        except Exception as e:
            if "timeout" in str(e).lower() and "popup" in str(e).lower():
                logger.info("Normal click succeeded (no popup). Assuming same tab navigation.")
                try:
                    await page.wait_for_load_state("load", timeout=5000)
                except Exception:
                    pass
                return page, False
                
            logger.info(f"Standard click failed: {str(e)}. Trying evaluate click...")
            try:
                async with page.expect_popup(timeout=3000) as popup_info:
                    await link_el.evaluate("el => el.click()")
                new_page = await popup_info.value
                logger.info("Report opened in a new tab/popup via evaluate click.")
                return new_page, True
            except Exception as ee:
                logger.info("Assume same tab navigation after evaluate click.")
                try:
                    await page.wait_for_load_state("load", timeout=5000)
                except Exception:
                    pass
                return page, False
            
    return None, False


async def download_report_from_url(page, report_url, export_selector, output_path, prefix=None, skip_parameters=False, period_option=None):
    if report_url:
        logger.info(f"Navigating to report URL: {report_url}")
        try:
            await page.goto(report_url, timeout=30000, wait_until="load")
        except Exception as e:
            logger.warning(f"Navigation to report URL timed out or failed: {str(e)}")
            
        try:
            await page.wait_for_load_state("domcontentloaded", timeout=10000)
        except Exception:
            pass
        
        logger.info("Waiting 5s to check for SPA routing redirect...")
        await asyncio.sleep(5)
        
        logger.info(f"Current Page URL: {page.url}")
        title = ""
        try:
            title = await page.title()
            logger.info(f"Current Page Title: {title}")
        except Exception as e:
            logger.warning(f"Could not get page title: {str(e)}")
            
        if "home" in page.url or "dashboard" in page.url or "Tong quan" in title or "T\u1ed5ng quan" in title:
            logger.info("Auto-redirected to home page. Hiding popups on home page and returning to report URL...")
            await close_misa_popups(page)
            await asyncio.sleep(1)
            
            logger.info(f"Re-navigating to report URL: {report_url}")
            try:
                await page.goto(report_url, timeout=30000, wait_until="load")
            except Exception as e:
                logger.warning(f"Re-navigation to report URL timed out or failed: {str(e)}")
            try:
                await page.wait_for_load_state("domcontentloaded", timeout=10000)
            except Exception:
                pass
            await asyncio.sleep(3)
            logger.info(f"New Page URL: {page.url}")
    else:
        logger.info("No report_url provided. Reusing current page state.")
        
    try:
        logger.info(f"Number of frames: {len(page.frames)}")
        for idx, f in enumerate(page.frames):
            logger.info(f"Frame {idx}: name='{f.name}', url='{f.url}'")
    except Exception as e:
        logger.warning(f"Failed to list frames: {str(e)}")
        
    if "login" in page.url or "sso" in page.url or "id.misa.vn" in page.url or "amisapp.misa.vn/login" in page.url:
        logger.warning("Redirected to login page. Session might be expired.")
        return False
        
    try:
        logger.info("Waiting for initial page elements to appear...")
        await asyncio.sleep(3)
        await close_misa_popups(page)
        await asyncio.sleep(1)
        
        if skip_parameters:
            logger.info("Waiting 40s for the saved report to load...")
            await asyncio.sleep(40)
            await close_misa_popups(page)
            await asyncio.sleep(1)
        else:
            param_btn_selectors = [
                "button:has-text('Chọn tham số')",
                ".btn:has-text('Chọn tham số')",
                "div.ms-button:has-text('Chọn tham số')",
                "span:has-text('Chọn tham số')",
                ".dx-button-content:has-text('Chọn tham số')"
            ]
            param_btn, frame = await find_locator_in_any_frame(page, param_btn_selectors, timeout=5000)
            if not param_btn:
                for f in page.frames:
                    try:
                        locator = f.locator("//*[contains(text(), 'Chọn tham số')]").first
                        if await locator.is_visible(timeout=1000):
                            param_btn = locator
                            frame = f
                            break
                    except Exception:
                        continue
                        
            if param_btn:
                logger.info(f"Clicking 'Chon tham so' button in frame: {getattr(frame, 'name', 'main') or getattr(frame, 'url', '')}")
                await param_btn.click(force=True)
            else:
                logger.warning("Could not find 'Chon tham so' button. It might already be opened.")
            await asyncio.sleep(1.5)
            
            logger.info("Clicking 'Bao gom so lieu chi nhanh phu thuoc' checkbox...")
            try:
                target_frame_for_checkbox = frame if frame else page
                checkbox_label = target_frame_for_checkbox.locator("label:has-text('Bao gồm số liệu chi nhánh phụ thuộc')").first
                if await checkbox_label.count() == 0:
                    checkbox_label = target_frame_for_checkbox.locator("label:has-text('chi nhánh phụ thuộc')").first

                if await checkbox_label.count() > 0:
                    checkbox_span = checkbox_label.locator("span.ms-checkbox").first
                    is_already_checked = False
                    if await checkbox_span.count() > 0:
                        span_class = await checkbox_span.get_attribute("class") or ""
                        is_already_checked = "checked-true" in span_class
                        logger.info(f"Checkbox span class: '{span_class}', is_already_checked={is_already_checked}")
                    else:
                        checkbox_input = checkbox_label.locator("input[type='checkbox']").first
                        if await checkbox_input.count() > 0:
                            is_already_checked = await checkbox_input.is_checked()
                            logger.info(f"Checkbox input is_checked={is_already_checked}")

                    if not is_already_checked:
                        logger.info("Checkbox not checked yet. Clicking label to toggle ON...")
                        await checkbox_label.click(force=True)
                        await asyncio.sleep(1.0)
                        if await checkbox_span.count() > 0:
                            span_class_after = await checkbox_span.get_attribute("class") or ""
                            logger.info(f"Checkbox span class after click: '{span_class_after}'")
                    else:
                        logger.info("Checkbox is ALREADY checked. Skipping click to avoid unchecking.")
                else:
                    logger.warning("Could not find 'Bao gom so lieu chi nhanh phu thuoc' checkbox label.")
            except Exception as e:
                logger.warning(f"Error handling 'chi nhanh phu thuoc' checkbox: {str(e)}")

            if prefix == 'TAI_KHOAN_CT':
                logger.info("Handling account selection for Sổ Chi Tiết Các Tài Khoản (TAI_KHOAN_CT)...")
                try:
                    await select_accounts_for_so_chi_tiet(page, ["111", "112", "341"])
                except Exception as e:
                    logger.error(f"Error selecting accounts for TAI_KHOAN_CT: {str(e)}")

            target_period = period_option if period_option else getattr(settings, 'MISA_REPORT_PERIOD_OPTION', 'Năm nay')
            period_selectors = [
                f"text='{target_period}'",
                f"div:has-text('{target_period}')",
                f"span:has-text('{target_period}')"
            ]
            period_el, _ = await find_locator_in_any_frame(page, period_selectors, timeout=2000)
            if period_el:
                await period_el.click(force=True)
                await asyncio.sleep(0.5)

            view_btn_selectors = [
                "button:has-text('Đồng ý')",
                "button:has-text('Xem báo cáo')",
                "div.ms-button:has-text('Đồng ý')",
                "div.ms-button:has-text('Xem báo cáo')",
                "span:has-text('Đồng ý')",
                "span:has-text('Xem báo cáo')"
            ]
            view_btn, _ = await find_locator_in_any_frame(page, view_btn_selectors, timeout=5000)
            if view_btn:
                logger.info("Clicking 'Dong y' / 'Xem bao cao' button...")
                await view_btn.click(force=True)
                logger.info("Waiting 45s for report data to load...")
                await asyncio.sleep(45)
            else:
                logger.warning("Could not find 'Dong y' / 'Xem bao cao' button.")
                
        await close_misa_popups(page)
        await asyncio.sleep(1)
        
        logger.info("Looking for export button...")
        export_selectors = [
            export_selector,
            "div.ms-button:has-text('Xuất khẩu')",
            "button:has-text('Xuất khẩu')",
            "span:has-text('Xuất khẩu')",
            "i.icon-export",
            "div[title*='Xuất khẩu']",
            "button[title*='Xuất khẩu']"
        ]
        
        export_btn, frame = await find_locator_in_any_frame(page, export_selectors, timeout=5000)
        if not export_btn:
            for f in page.frames:
                try:
                    locator = f.locator("//*[contains(text(), 'Xuất khẩu')]").first
                    if await locator.is_visible(timeout=1000):
                        export_btn = locator
                        frame = f
                        break
                except Exception:
                    continue

        if not export_btn:
            logger.error("Could not find export button in any frame.")
            return False

        logger.info(f"Clicking export button in frame: {getattr(frame, 'name', 'main') or getattr(frame, 'url', '')}")
        
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        
        async with page.expect_download(timeout=60000) as download_info:
            await export_btn.click(force=True)
            await asyncio.sleep(1)
            
            excel_item_selectors = [
                "text='Excel'",
                "div:has-text('Excel')",
                "span:has-text('Excel')",
                "li:has-text('Excel')",
                "a:has-text('Excel')"
            ]
            excel_item, _ = await find_locator_in_any_frame(page, excel_item_selectors, timeout=3000)
            if excel_item:
                logger.info("Found Excel menu option. Clicking it...")
                await excel_item.click(force=True)
            else:
                logger.info("No specific Excel dropdown item found or direct download triggered.")
        
        download = await download_info.value
        await download.save_as(output_path)
        logger.info(f"Successfully downloaded report to: {output_path}")
        return True

    except Exception as e:
        logger.error(f"Error during report download: {str(e)}")
        return False
