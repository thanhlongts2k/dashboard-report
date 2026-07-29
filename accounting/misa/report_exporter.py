import os
import asyncio
import logging
from django.conf import settings
from accounting.misa.browser import find_locator_in_any_frame, close_misa_popups

logger = logging.getLogger(__name__)

async def ensure_all_items_selected(page_or_frame):
    """
    Tự động kiểm tra và tích chọn 'Chọn tất cả' các vật tư/khách hàng/nhà cung cấp trong modal tham số.
    CHỈ click nút 'Chọn tất cả' / Header Checkbox, KHÔNG click dòng lẻ để tránh bỏ chọn Tất cả.
    """
    logger.info("Ensuring all items/materials 'Chọn tất cả' header checkboxes are checked...")
    return await check_all_select_all_checkboxes(page_or_frame)

async def dismiss_misa_warning_if_any(page):
    """
    Tự động phát hiện và bấm 'Đóng'/'Đồng ý' nếu MISA hiện popup cảnh báo 'Chưa chọn vật tư hàng hóa'.
    """
    try:
        warning_modal = page.locator(".ms-message-box, .dx-dialog-content, [role='dialog']:has-text('vật tư'), [role='dialog']:has-text('chưa chọn'), div:has-text('Bạn chưa chọn')").first
        if await warning_modal.is_visible(timeout=1500):
            logger.warning("DETECTED MISA WARNING POPUP: 'Chưa chọn vật tư hàng hóa' / 'Bạn chưa chọn'!")
            try:
                ss_path = os.path.join(settings.BASE_DIR, 'scratch', 'screenshots', 'error_vattuhanghoa.png')
                os.makedirs(os.path.dirname(ss_path), exist_ok=True)
                await page.screenshot(path=ss_path)
            except Exception:
                pass
            
            close_btn = warning_modal.locator("button:has-text('Đồng ý'), button:has-text('Đóng'), .ms-button-primary, span:has-text('Đóng')").first
            if await close_btn.is_visible(timeout=1500):
                await close_btn.click(force=True)
                await asyncio.sleep(1.0)
                logger.info("Dismissed MISA warning popup. Retrying item selection...")
                return True
    except Exception as e:
        logger.debug(f"No warning popup detected: {e}")
    return False

async def remove_nhat_branches(page):
    """
    Loại bỏ các tag chi nhánh có chứa ký tự '_Nhật' trong ô chọn Chi nhánh (MISA parameter form).
    (Phục hồi 100% pre-commit 773e281~1)
    """
    logger.info("Scrutinizing and removing all branch tags containing '_Nhật'...")
    total_removed = 0
    tag_xpath = "//*[contains(text(), '_Nhật')]/ancestor::*[contains(concat(' ', normalize-space(@class), ' '), ' selected-item ') or contains(concat(' ', normalize-space(@class), ' '), ' dx-tag ') or contains(concat(' ', normalize-space(@class), ' '), ' ms-tag ') or contains(concat(' ', normalize-space(@class), ' '), ' dx-tag-content ') or contains(concat(' ', normalize-space(@class), ' '), ' ms-tag-content ') or contains(concat(' ', normalize-space(@class), ' '), ' badge ')]"

    for frame in [page] + [f for f in page.frames if f != page.main_frame]:
        try:
            tag_containers = frame.locator(f"xpath={tag_xpath}")
            count = await tag_containers.count()
            if count > 0:
                logger.info(f"Found {count} branch tags containing '_Nhật' in frame.")
                for attempt in range(15):
                    tag_containers = frame.locator(f"xpath={tag_xpath}")
                    count = await tag_containers.count()
                    if count == 0:
                        break
                    clicked_any = False
                    for i in range(count):
                        tag = tag_containers.nth(i)
                        if await tag.is_visible():
                            close_btn = tag.locator("xpath=.//*[contains(@class, 'close') or contains(@class, 'remove') or contains(@class, 'clear') or contains(@class, 'dx-tag-remove-button') or contains(@class, 'mi-close') or text()='x' or text()='×']").first
                            if await close_btn.count() > 0 and await close_btn.is_visible():
                                logger.info("Removing branch tag containing '_Nhật' (click close button)")
                                await close_btn.click(force=True)
                                await asyncio.sleep(0.5)
                                clicked_any = True
                                total_removed += 1
                                break
                            else:
                                box = await tag.bounding_box()
                                if box:
                                    logger.info("Removing branch tag containing '_Nhật' (click right edge coordinates)")
                                    await page.mouse.click(box['x'] + box['width'] - 10, box['y'] + box['height'] / 2)
                                    await asyncio.sleep(0.5)
                                    clicked_any = True
                                    total_removed += 1
                                    break
                    if not clicked_any:
                        break
        except Exception as e:
            logger.warning(f"Error removing '_Nhật' branch tags in frame: {e}")

    # Sweep JS chip elements for any extra chips
    try:
        js_sweep = """
        (() => {
            let count = 0;
            const tags = Array.from(document.querySelectorAll('.ms-tag, .ms-chip, .dx-tag, [class*="tag"], [class*="chip"]'));
            tags.forEach(tag => {
                const text = (tag.textContent || '').normalize('NFC').trim();
                if ((text.includes('_Nhật') || text.includes('FUJI') || text.includes('Nippon')) && text.length < 80) {
                    const closeBtn = tag.querySelector('.ms-tag-close, .icon-close, .ms-tag-remove, .dx-tag-remove-button, [class*="close"], [class*="remove"], i, svg, span.x');
                    if (closeBtn) {
                        closeBtn.click();
                        count++;
                    } else {
                        tag.click();
                        count++;
                    }
                }
            });
            return count;
        })()
        """
        for frame in [page] + [f for f in page.frames if f != page.main_frame]:
            js_count = await frame.evaluate(js_sweep)
            if isinstance(js_count, int) and js_count > 0:
                total_removed += js_count
    except Exception:
        pass

    if total_removed > 0:
        logger.info(f"SUCCESS: Total removed {total_removed} branch tags containing '_Nhật'.")
        return True
    else:
        logger.info("Checked 'Chi nhánh' box: No branch tags containing '_Nhật' found.")
        return False

async def check_all_select_all_checkboxes(page):
    """
    Chỉ tích chọn ô checkbox nằm NGAY KẾ BÊN chữ 'Chọn tất cả' (ví dụ: 'Chọn tất cả 31355 vật tư được chọn').
    Thực hiện chậm lại 1 giây giữa các lần click theo đúng yêu cầu của người dùng.
    """
    logger.info("Targeting standalone checkboxes next to 'Chọn tất cả' text (with 1.0s delay between clicks)...")
    total_checked = 0
    js_script = """
    async () => {
        let clickedCount = 0;
        const popups = document.querySelectorAll('div.ms-popup, div.dx-popup-content, div.con-ms-popup, div.ms-dialog');
        const containers = popups.length > 0 ? popups : [document.body];
        
        for (const container of containers) {
            const textNodes = Array.from(container.querySelectorAll('*')).filter(el => {
                if (el.tagName === 'TH' || el.closest('th') || el.closest('thead')) return false;
                if (el.children.length > 3) return false;
                const txt = (el.textContent || '').normalize('NFC').trim();
                return txt.includes('Chọn tất cả');
            });
            
            for (const node of textNodes) {
                const wrapper = node.closest('.con-ms-checkbox, .ms-checkbox--content, label, div.flex, div.row, div') || node.parentElement;
                if (!wrapper || wrapper.tagName === 'TH' || wrapper.closest('th')) continue;
                
                const cb = wrapper.querySelector('span.ms-checkbox, input[type="checkbox"], div.dx-checkbox-icon') || 
                           (wrapper.parentElement ? wrapper.parentElement.querySelector('span.ms-checkbox, input[type="checkbox"], div.dx-checkbox-icon') : null);
                
                if (cb) {
                    const spanClass = cb.getAttribute('class') || '';
                    const wrapperClass = wrapper.getAttribute('class') || '';
                    const inputChecked = cb.tagName === 'INPUT' ? cb.checked : false;
                    
                    const isAlreadyChecked = spanClass.includes('checked-true') || 
                                             spanClass.includes('dx-checkbox-checked') || 
                                             wrapperClass.includes('checked-true') || 
                                             inputChecked;
                    
                    if (!isAlreadyChecked && cb.offsetWidth > 0 && cb.offsetHeight > 0) {
                        cb.click();
                        clickedCount++;
                        await new Promise(resolve => setTimeout(resolve, 1000));
                    }
                }
            }
        }
        return clickedCount;
    }
    """
    for frame in [page] + [f for f in page.frames if f != page.main_frame]:
        try:
            cnt = await frame.evaluate(js_script)
            if isinstance(cnt, int) and cnt > 0:
                total_checked += cnt
        except Exception:
            pass
    logger.info(f"Successfully checked {total_checked} standalone 'Chọn tất cả' checkboxes (with 1.0s delay).")
    return total_checked

async def select_accounts_for_so_chi_tiet(page, accounts=['111', '112', '341', '641', '642']):
    """
    Tự động chọn Bậc = 1 và chọn từng tài khoản trong báo cáo Sổ chi tiết các tài khoản (TAI_KHOAN_CT).
    Phục hồi 100% logic commit 57a0e59:
    1. Chọn Bậc = 1 qua combobox (với các fallback selector + keyboard navigation)
    2. Với TỪNG tài khoản: gõ mã tài khoản vào ô tìm kiếm 'Nhập từ khóa tìm kiếm', chờ bảng lọc, rồi click checkbox dòng khớp bằng JS.
    """
    logger.info(f"[TAI_KHOAN_CT] Setting Account Level = 1 and selecting accounts: {accounts}")

    # --- Bước 1: Chọn Bậc = 1 ---
    bac_selectors = [
        "xpath=//div[contains(@class,'ms-search-account')]//div[contains(@class,'ms-combo')]//input",
        "xpath=//span[normalize-space(text())='Bậc']/following::div[contains(@class,'ms-combo')][1]//input",
        "xpath=//th[normalize-space(text())='Bậc']/preceding::input[contains(@class,'dx-texteditor-input')][1]",
        "xpath=//div[contains(@class,'ms-combo') and not(ancestor::*[contains(@class,'ms-date')])][last()]//input",
        ".ms-search-account .ms-combo input",
        "xpath=(//div[contains(@class,'param') or contains(@class,'filter')]//input[@type='text'])[last()]",
    ]
    bac_input, _ = await find_locator_in_any_frame(page, bac_selectors, timeout=3000)
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
            logger.warning("Could not find 'Bac 1' option. Using keyboard ArrowDown fallback...")
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
        logger.warning("Could not find 'Bac' combobox. Skipping Bac selection.")

    # --- Bước 2: Với TỪNG tài khoản, dùng ô tìm kiếm để lọc rồi click ---
    account_search_selectors = [
        "input[placeholder='Nhập từ khóa tìm kiếm']",
        "xpath=//input[@placeholder='Nhập từ khóa tìm kiếm']",
        "input[placeholder*='từ khóa']",
        "input[placeholder*='tìm kiếm']",
        ".ms-input-search input",
    ]

    for account_code in accounts:
        logger.info(f"[TAI_KHOAN_CT] Searching and selecting account: {account_code}")

        acc_input, _ = await find_locator_in_any_frame(page, account_search_selectors, timeout=3000)
        if not acc_input:
            logger.warning(f"Could not find account search textbox for {account_code}. Skipping.")
            continue

        try:
            await acc_input.click(force=True)
            await asyncio.sleep(0.2)
            await acc_input.fill("")
            await acc_input.type(account_code)
            await asyncio.sleep(1.5)  # Chờ bảng filter hiển thị kết quả
            logger.info(f"Typed account code '{account_code}' in search box.")
        except Exception as e:
            logger.error(f"Failed to type account {account_code}: {str(e)}")
            continue

        # Click checkbox của dòng khớp chính xác bằng JS (quét toàn bộ DOM)
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

                // Nếu sau khi filter chỉ còn 1 dòng data -> click dòng đầu tiên
                let dataRow = rows[0];
                if (rows.length > 1 && (rows[0].closest('thead') || rows[0].querySelector('th'))) {{
                    dataRow = rows[1];
                }}
                const cb = dataRow.querySelector('input[type="checkbox"], .dx-checkbox, .ms-checkbox, .checkbox, [role="checkbox"]');
                if (cb) {{ cb.click(); return true; }}
                const cells2 = dataRow.querySelectorAll('td, [role="cell"], .dx-cell, .ms-td');
                if (cells2.length > 0) {{ cells2[0].click(); return true; }}
                return false;
            }})()
            """
            frames_to_check = [page] + page.frames
            for f in frames_to_check:
                try:
                    if await f.evaluate(js_script):
                        clicked = True
                        break
                except Exception:
                    pass

            if clicked:
                logger.info(f"Successfully clicked checkbox for account {account_code} via JS.")
        except Exception as e:
            logger.error(f"JS fallback for {account_code} failed: {str(e)}")

        if not clicked:
            logger.warning(f"Could not click via JS for {account_code}, trying XPath first-row fallback...")
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
                logger.warning(f"Could not find any checkbox for {account_code}. Skipping.")

        await asyncio.sleep(0.5)

    logger.info(f"[TAI_KHOAN_CT] Finished selecting accounts: {accounts}")

async def download_report_from_url(page, report_url, export_selector, output_path, prefix=None, skip_parameters=False, period_option=None):
    """
    Phục hồi 100% luồng thao tác Playwright pre-commit 773e281~1.
    """
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
        try:
            title = await page.title()
            logger.info(f"Current Page Title: {title}")
        except Exception:
            pass
            
        if "home" in page.url or "dashboard" in page.url:
            logger.info("Auto-redirected to home page. Returning to report URL...")
            await close_misa_popups(page)
            await asyncio.sleep(1)
            await page.goto(report_url, timeout=30000, wait_until="load")
            await asyncio.sleep(3)

    if "login" in page.url or "sso" in page.url or "id.misa.vn" in page.url or "amisapp.misa.vn/login" in page.url:
        logger.warning("Redirected to login page. Session might be expired.")
        return False
        
    try:
        logger.info("Waiting for initial page elements to appear...")
        await asyncio.sleep(3)
        await close_misa_popups(page)
        await asyncio.sleep(1)
        
        if not skip_parameters:
            # Step 2: Click "Chọn tham số" button
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
                        
            os.makedirs(os.path.join(settings.BASE_DIR, 'scratch', 'screenshots'), exist_ok=True)
            ss_dir = os.path.join(settings.BASE_DIR, 'scratch', 'screenshots')

            if param_btn:
                logger.info(f"Clicking 'Chon tham so' button in frame: {getattr(frame, 'name', 'main') or getattr(frame, 'url', '')}")
                await param_btn.click(force=True)
                await asyncio.sleep(1.5)
                try:
                    await page.screenshot(path=os.path.join(ss_dir, "01_opened_parameter_modal.png"))
                except Exception:
                    pass
            else:
                logger.warning("Could not find 'Chon tham so' button. It might already be opened.")
            
            # Step 3: Check "Bao gồm số liệu chi nhánh phụ thuộc" checkbox
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

                    if not is_already_checked:
                        logger.info("Checkbox not checked yet. Clicking label to toggle ON...")
                        await checkbox_label.click(force=True)
                        await asyncio.sleep(1.0)
                        # Xác nhận trạng thái sau khi click (100% Commit 57a0e59)
                        if await checkbox_span.count() > 0:
                            span_class_after = await checkbox_span.get_attribute("class") or ""
                            logger.info(f"Checkbox span class after click: '{span_class_after}'")
                            if "checked-true" not in span_class_after:
                                logger.warning("Checkbox may not have been checked! Trying JS click on input as fallback...")
                                checkbox_input_fb = checkbox_label.locator("input[type='checkbox']").first
                                if await checkbox_input_fb.count() > 0:
                                    await checkbox_input_fb.evaluate("el => el.click()")
                                    await asyncio.sleep(0.5)
                    else:
                        logger.info("'Bao gom so lieu chi nhanh phu thuoc' is already checked, skipping.")
                try:
                    await page.screenshot(path=os.path.join(ss_dir, "02_checked_branch_option.png"))
                except Exception:
                    pass
            except Exception as chk_err:
                logger.warning(f"Error handling 'Bao gom so lieu chi nhanh phu thuoc' checkbox: {chk_err}")
            await asyncio.sleep(2.0)

            # Step 3.1: Remove branch tags containing '_Nhật'
            try:
                await remove_nhat_branches(page)
                try:
                    await page.screenshot(path=os.path.join(ss_dir, "03_removed_nhat_tags.png"))
                except Exception:
                    pass
            except Exception as e:
                logger.error(f"Error removing '_Nhật' branches: {str(e)}")

            if prefix == 'TAI_KHOAN_CT':
                try:
                    accounts_to_select = getattr(settings, 'MISA_SO_CHI_TIET_ACCOUNTS', ['111', '112', '341', '641', '642'])
                    await select_accounts_for_so_chi_tiet(page, accounts_to_select)
                    try:
                        await page.screenshot(path=os.path.join(ss_dir, "06_account_level_and_5_accs.png"))
                    except Exception:
                        pass
                except Exception as e:
                    logger.error(f"Error selecting accounts for TAI_KHOAN_CT: {str(e)}")

            # Step 4: Choose Period ("Tháng này" or "Năm nay") — skip for TUOI_NO_KH (100% Commit 57a0e59)
            skip_ky_bao_cao = (prefix == 'TUOI_NO_KH')
            target_period = period_option if period_option else getattr(settings, 'MISA_REPORT_PERIOD_OPTION', 'Tháng này')
            logger.info(f"Setting report period to: '{target_period}'...")
            ky_baocao_selectors = [
                "xpath=//label[contains(text(), 'Kỳ báo cáo')]/ancestor::div[contains(@class, 'ms-combo')]//input",
                "xpath=//div[contains(text(), 'Kỳ báo cáo')]/ancestor::div[contains(@class, 'ms-combo')]//input",
                "xpath=//label[contains(text(), 'Kỳ')]/following::div[contains(@class,'ms-combo')][1]//input",
                ".ms-combo input[placeholder*='Kỳ']"
            ]
            ky_input, frame = await find_locator_in_any_frame(page, ky_baocao_selectors, timeout=3000)
            if skip_ky_bao_cao:
                logger.info(f"[{prefix}] Skipping 'Ky bao cao' selection as per commit 57a0e59 logic.")
            elif ky_input:
                try:
                    await ky_input.click(force=True)
                    await asyncio.sleep(0.5)
                except Exception:
                    pass

                exact_period_selectors = [
                    f"xpath=//div[contains(@class,'dx-dropdowneditor-overlay') or contains(@class,'ms-combo') or contains(@class,'dx-overlay-content')]//*[contains(@class,'dx-item-content') or contains(@class,'ms-combo-item') or contains(@class,'dx-list-item-content')][normalize-space(text())='{target_period}']",
                    f"xpath=//*[contains(@class,'dx-item-content') or contains(@class,'ms-combo-item') or contains(@class,'dx-list-item-content')][normalize-space(text())='{target_period}']",
                    f"text='{target_period}'"
                ]
                period_el, _ = await find_locator_in_any_frame(page, exact_period_selectors, timeout=3000, close_blockers=False)
                if period_el:
                    try:
                        await period_el.click(force=True)
                        logger.info(f"Selected period '{target_period}' successfully.")
                    except Exception as pe:
                        logger.warning(f"Could not click period element: {str(pe)}")
                else:
                    logger.warning(f"Could not find '{target_period}' in dropdown. Trying keyboard type fallback...")
                    try:
                        await ky_input.click(force=True, click_count=3)
                        await ky_input.type(target_period)
                        await asyncio.sleep(0.5)
                        await page.keyboard.press("Enter")
                        logger.info(f"Typed '{target_period}' and pressed Enter as fallback.")
                    except Exception as e:
                        logger.error(f"Failed to fill '{target_period}': {str(e)}")
            else:
                logger.warning("Could not find 'Ky bao cao' input combobox.")

            try:
                await page.screenshot(path=os.path.join(ss_dir, "04_selected_period.png"))
            except Exception:
                pass

            # Step 5: Check ALL "Chọn tất cả" checkboxes and ensure items selected (skip for TAI_KHOAN_CT as per commit 57a0e59)
            if prefix != 'TAI_KHOAN_CT':
                await ensure_all_items_selected(frame if frame else page)
                await check_all_select_all_checkboxes(page)
                try:
                    await page.screenshot(path=os.path.join(ss_dir, "05_checked_select_all.png"))
                except Exception:
                    pass

            # Step 6: Click "Đồng ý" / "Xem báo cáo" button
            view_btn_selectors = [
                "button:has-text('Đồng ý')",
                "button:has-text('Xem báo cáo')",
                "div.ms-button:has-text('Đồng ý')",
                "div.ms-button:has-text('Xem báo cáo')"
            ]
            view_btn, _ = await find_locator_in_any_frame(page, view_btn_selectors, timeout=5000)
            if view_btn:
                logger.info("Clicking 'Dong y' / 'Xem bao cao' button...")
                await view_btn.click(force=True)
                await asyncio.sleep(1.5)

                # Check if MISA warning popup appears ("Chưa chọn vật tư...", "Bạn chưa chọn...")
                if await dismiss_misa_warning_if_any(page):
                    logger.info("Re-checking all item checkboxes and re-clicking 'Đồng ý'...")
                    await ensure_all_items_selected(page)
                    await check_all_select_all_checkboxes(page)
                    view_btn_retry, _ = await find_locator_in_any_frame(page, view_btn_selectors, timeout=3000)
                    if view_btn_retry:
                        await view_btn_retry.click(force=True)
                        await asyncio.sleep(1.5)

                logger.info("Waiting 20s for report data to load...")
                await asyncio.sleep(20)

        # Step 6.5: Select template "Mẫu chuẩn." (gear icon settings) for BAN_HANG only (100% Commit 57a0e59)
        if prefix == 'BAN_HANG':
            logger.info("[BAN_HANG] Selecting 'Mẫu chuẩn.' template via gear settings button...")
            gear_selectors = [
                ".mi-setting__list-bold",  # Nút bánh răng cài đặt của lưới báo cáo MISA
                "div.mi-setting__list-bold",
                "xpath=//div[contains(@class, 'mi-setting__list-bold')]",
                "xpath=//div[contains(@class, 'mi-setting') and not(contains(@class, 'header-icon')) and not(contains(@class, 'mi-setting-2__nav'))]"
            ]
            for loading_sel in [".dx-loadpanel", ".loading", ".ms-loading"]:
                try:
                    await page.locator(loading_sel).first.wait_for(state="hidden", timeout=10000)
                except Exception:
                    pass

            # Chờ nút bánh răng xuất hiện (timeout 30s để đảm bảo báo cáo lớn kịp tải)
            gear_btn, _ = await find_locator_in_any_frame(page, gear_selectors, timeout=30000)
            if gear_btn:
                logger.info("Clicking gear settings button...")
                await gear_btn.click(force=True)
                await asyncio.sleep(1.5)

                # Tìm item "Mẫu chuẩn." trên page (không dùng gear_frame — tránh tìm sai frame, khhớp 57a0e59)
                mau_chuan_item = None
                for sel in ["text=Mẫu chuẩn.", "xpath=//span[contains(text(), 'Mẫu chuẩn.')]"]:
                    loc = page.locator(sel).first
                    try:
                        if await loc.is_visible(timeout=1000):
                            mau_chuan_item = loc
                            break
                    except Exception:
                        continue

                if not mau_chuan_item:
                    # Fallback: đợi tối đa 4 giây cho dropdown menu render xong rồi thử lại (khhớp 57a0e59)
                    mau_chuan_item = page.locator("text=Mẫu chuẩn.").first
                    try:
                        await mau_chuan_item.wait_for(state="visible", timeout=4000)
                    except Exception:
                        mau_chuan_item = None

                if mau_chuan_item:
                    logger.info("Selecting 'Mẫu chuẩn.' template option...")
                    await mau_chuan_item.click(force=True)
                    await asyncio.sleep(5.0)  # Chờ 5 giây để tải lại mẫu chuẩn (khhớp 57a0e59)
                else:
                    logger.warning("Could not find 'Mẫu chuẩn.' option in settings menu.")
            else:
                logger.warning("Could not find gear settings button.")

        # Step 7: Open download manager to clear old history before exporting (100% Commit 57a0e59)
        logger.info("Opening download manager to clear old history...")
        download_manager_selectors = [
            "div.ms-download",
            "div.icon-feature-download",
            ".ms-download",
            ".icon-feature-download",
            ".mi-download",
            ".mi-cloud-download"
        ]
        manager_btn, manager_frame = await find_locator_in_any_frame(page, download_manager_selectors, timeout=4000)
        if manager_btn:
            await manager_btn.click(force=True)
            await asyncio.sleep(2.0)

            for clear_attempt in range(3):
                has_entries = False
                tai_tep_check = page.locator("text='Tải tệp'").first
                try:
                    has_entries = await tai_tep_check.is_visible(timeout=1500)
                except Exception:
                    pass

                if not has_entries:
                    logger.info(f"Download panel is clean (attempt {clear_attempt + 1}). No old entries to remove.")
                    break

                logger.info(f"Found old entries in download panel (attempt {clear_attempt + 1}). Clearing...")
                clear_btn_selectors = [
                    "text='Xóa hết lịch sử tải tệp'",
                    ".clear-all",
                    ".clear-all--text",
                    "div:has-text('Xóa hết lịch sử tải tệp')"
                ]
                clear_btn, clear_frame = await find_locator_in_any_frame(page, clear_btn_selectors, timeout=2000)
                if clear_btn:
                    logger.info("Clicking 'Xóa hết lịch sử tải tệp' to clear old downloads...")
                    await clear_btn.click(force=True)
                    await asyncio.sleep(1.5)

                    confirm_btn_selectors = [
                        "button:has-text('Có')",
                        ".ms-button:has-text('Có')",
                        ".dx-button-content:has-text('Có')",
                        "text='Có'",
                        "span:has-text('Có')"
                    ]
                    confirm_btn, confirm_frame = await find_locator_in_any_frame(page, confirm_btn_selectors, timeout=3000)
                    if confirm_btn:
                        logger.info("Clicking 'Có' on deletion confirmation popup...")
                        await confirm_btn.click(force=True)
                        await asyncio.sleep(2.0)
                    else:
                        await asyncio.sleep(1.5)
                else:
                    await asyncio.sleep(1.0)
                    break

            logger.info("Closing download manager panel...")
            await manager_btn.click(force=True)
            await asyncio.sleep(1.0)

        # Step 8: Click Excel icon dropdown button (100% Commit 57a0e59)
        logger.info("Looking for Excel export icon dropdown button...")
        excel_btn_selectors = [
            ".mi-export__excel-bold",
            ".mi-excel",
            ".mi-icon-excel",
            ".mi-export",
            "[title*='Xuất Excel']",
            "[title*='Xuất khẩu']",
            ".icon-excel",
            ".btn-excel",
            "button:has-text('Xuất khẩu')",
            "div.ms-dropdown:has-text('Xuất khẩu')"
        ]
        if export_selector:
            excel_btn_selectors.insert(0, export_selector)

        excel_btn, frame = await find_locator_in_any_frame(page, excel_btn_selectors, timeout=10000, close_blockers=False)
        if not excel_btn:
            for f in page.frames:
                try:
                    locator = f.locator("xpath=//*[contains(@class,'mi-excel') or contains(@class,'export') or contains(text(),'Xuất khẩu')]").first
                    if await locator.is_visible(timeout=2000):
                        excel_btn = locator
                        frame = f
                        break
                except Exception:
                    continue

        if not excel_btn:
            logger.error("Could not find Excel icon dropdown button in any frame.")
            return False

        logger.info(f"Clicking Excel icon button in frame: {getattr(frame, 'name', 'main') or getattr(frame, 'url', '')}")
        await excel_btn.click(force=True)
        await asyncio.sleep(2.5)

        # Step 8: Click "Xuất Excel (dạng dữ liệu)" or "Excel" option
        dropdown_selectors = [
            "text='Xuất Excel (dạng dữ liệu)'",
            "span:has-text('Xuất Excel (dạng dữ liệu)')",
            "div:has-text('Xuất Excel (dạng dữ liệu)')",
            ".dx-menu-item-text:has-text('Xuất Excel (dạng dữ liệu)')",
            "xpath=//*[contains(text(), 'dạng dữ liệu')]",
            "text='Excel'",
            "span:has-text('Excel')",
            "div:has-text('Excel')"
        ]
        dropdown_item, _ = await find_locator_in_any_frame(page, dropdown_selectors, timeout=4000, close_blockers=False)
        if dropdown_item:
            logger.info("Clicking 'Xuất Excel (dạng dữ liệu)' dropdown item...")
            await dropdown_item.click(force=True)
            await asyncio.sleep(2.5)

        # Check for options dialog "Đồng ý" button
        agree_btn_selectors = [
            "button:has-text('Đồng ý')",
            ".btn:has-text('Đồng ý')",
            ".ms-button:has-text('Đồng ý')",
            "span:has-text('Đồng ý')"
        ]
        agree_btn, _ = await find_locator_in_any_frame(page, agree_btn_selectors, timeout=4000, close_blockers=False)
        if agree_btn:
            logger.info("Found 'Đồng ý' button in options dialog. Clicking it...")
            await agree_btn.click(force=True)
            await asyncio.sleep(2.0)

        # Step 9: Open download manager panel if not open and click "Tải tệp" (100% Commit 57a0e59)
        logger.info("Waiting 20 seconds for MISA to generate file in background...")
        await asyncio.sleep(20)

        panel_open = False
        try:
            for panel_indicator in ["Tải tệp Excel, tệp in,...", "Đang tạo đường dẫn tải tệp...", "Đường dẫn tải tệp sẽ hết hạn"]:
                for f in [page] + page.frames:
                    indicator = f.locator(f"text='{panel_indicator}'").first
                    if await indicator.is_visible(timeout=300):
                        panel_open = True
                        logger.info(f"Download manager panel is already open (indicator: '{panel_indicator}').")
                        break
                if panel_open:
                    break
        except Exception:
            pass

        download_manager_selectors = [
            "div.ms-download",
            "div.icon-feature-download",
            ".ms-download",
            ".icon-feature-download",
            ".mi-download",
            ".mi-cloud-download"
        ]

        if not panel_open:
            logger.info("Opening download manager panel via download icon...")
            manager_btn, _ = await find_locator_in_any_frame(page, download_manager_selectors, timeout=4000)
            if manager_btn:
                await manager_btn.click(force=True)
                await asyncio.sleep(2.0)
            else:
                logger.warning("Could not find download manager button. Checking if 'Tải tệp' is visible anyway.")

        first_entry_selectors = [
            "xpath=(//span[text()='Tải tệp'] | //a[text()='Tải tệp'] | //div[text()='Tải tệp'])[1]",
            "xpath=(//span[contains(text(),'Tải tệp')] | //a[contains(text(),'Tải tệp')])[1]",
        ]

        download_btn = None
        for attempt in range(20):
            download_btn, _ = await find_locator_in_any_frame(page, first_entry_selectors, timeout=1000)
            if download_btn:
                logger.info(f"Found newest 'Tải tệp' button (first entry) after attempt {attempt + 1}.")
                break
            await asyncio.sleep(1.5)

        if not download_btn:
            logger.error("Could not find the 'Tải tệp' button in download manager panel after waiting.")
            return False

        logger.info("Clicking 'Tải tệp' button and waiting for Playwright download event (Commit 57a0e59)...")
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        async with page.expect_download(timeout=45000) as download_info:
            await download_btn.click(force=True)

        download = await download_info.value
        await download.save_as(output_path)
        logger.info(f"SUCCESS: Successfully downloaded and saved report to: {output_path}")

        # Close download manager panel to clean UI
        try:
            manager_btn, _ = await find_locator_in_any_frame(page, download_manager_selectors, timeout=2000)
            if manager_btn:
                logger.info("Closing download manager panel...")
                await manager_btn.click(force=True)
                await asyncio.sleep(1.0)
        except Exception:
            pass

        return True

    except Exception as e:
        logger.error(f"Error during report download: {str(e)}")
        return False
