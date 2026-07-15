import os
import asyncio
import logging
from datetime import datetime
from django.conf import settings
from celery import shared_task
from django.utils import timezone
from .models import ImportLog

# Configure logger to output to stdout for debug clarity when run from shell
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
# Clear existing handlers if any to avoid duplicate logs
logger.handlers.clear()
console_handler = logging.StreamHandler()
console_handler.setLevel(logging.INFO)
formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
console_handler.setFormatter(formatter)
logger.addHandler(console_handler)
logger.propagate = False

async def login_to_misa(page, context, email, password):
    logger.info(f"Navigating to MISA login page: {settings.MISA_AMIS_LOGIN_URL}")
    await page.goto(settings.MISA_AMIS_LOGIN_URL)
    await page.wait_for_load_state("load")
    
    # Fill Email
    email_selectors = [
        "input.ap-lg-input[placeholder='Số điện thoại/email']",
        "input[placeholder*='email']",
        "input[type='email']",
        "input[name='username']",
        "#username",
        "#email"
    ]
    email_filled = False
    for sel in email_selectors:
        try:
            if await page.locator(sel).is_visible(timeout=3000):
                await page.locator(sel).fill(email)
                email_filled = True
                logger.info(f"Filled email using selector: {sel}")
                break
        except Exception:
            continue
    if not email_filled:
        raise Exception("Could not find or fill MISA email input field.")
        
    # Fill Password
    pwd_selectors = [
        "input.ap-lg-input[placeholder='Mật khẩu']",
        "input[placeholder*='khẩu']",
        "input[type='password']",
        "input[name='password']",
        "#password"
    ]
    pwd_filled = False
    for sel in pwd_selectors:
        try:
            if await page.locator(sel).is_visible(timeout=3000):
                await page.locator(sel).fill(password)
                pwd_filled = True
                logger.info(f"Filled password using selector: {sel}")
                break
        except Exception:
            continue
    if not pwd_filled:
        raise Exception("Could not find or fill MISA password input field.")
        
    # Click Submit
    submit_selectors = [
        "button.login-form-btn",
        "button[type='submit']",
        "button#submitBtn",
        "button:has-text('Đăng nhập')",
        "#submitBtn"
    ]
    submit_clicked = False
    for sel in submit_selectors:
        try:
            if await page.locator(sel).is_visible(timeout=3000):
                await page.locator(sel).click()
                submit_clicked = True
                logger.info(f"Clicked submit using selector: {sel}")
                break
        except Exception:
            continue
    if not submit_clicked:
        raise Exception("Could not find or click MISA submit button.")
        
    # Check if OTP verification is requested
    otp_selector = "input[name='otp']"
    try:
        # Wait up to 7 seconds for the OTP input to appear
        await page.locator(otp_selector).wait_for(state="visible", timeout=7000)
        
        # If it appears, prompt the user or raise an error if running headless
        logger.warning("WARNING: MISA AMIS requires OTP verification!")
        if not settings.MISA_HEADLESS:
            print("\n" + "="*80)
            print("WARNING: MISA AMIS REQUIRES OTP VERIFICATION!")
            print("Vui long nhap ma OTP gui toi email cua ban vao trinh duyet dang mo tren man hinh.")
            print("Tich chon 'Khong hoi lai tren thiet bi nay' va bam 'Tiep tuc' de dang nhap.")
            print("He thong dang tu dong cho toi da 3 phut de ban hoan thanh...")
            print("="*80 + "\n")
            
            # Wait for OTP input to disappear after user enters code and clicks Continue
            await page.locator(otp_selector).wait_for(state="hidden", timeout=180000)
            logger.info("OTP verification completed by user (OTP input is now hidden).")
        else:
            raise Exception("MISA AMIS requires OTP verification. Please run once in headed mode (MISA_HEADLESS=False) to verify the device.")
    except Exception as e:
        # Check if the exception is due to wait_for timing out (meaning no OTP requested, or user didn't enter it)
        if "timeout" in str(e).lower() or "timeout" in type(e).__name__.lower():
            # If the OTP input is still visible, it means the user timed out entering it
            try:
                is_visible = await page.locator(otp_selector).is_visible()
            except Exception:
                is_visible = False
                
            if is_visible:
                raise Exception("Timeout waiting for user to enter OTP verification code.")
            else:
                logger.info("No OTP verification screen detected. Proceeding...")
        else:
            raise e

    try:
        await page.wait_for_load_state("load", timeout=15000)
    except Exception:
        pass
    
    # Xử lý cảnh báo đăng nhập đồng thời nếu xuất hiện
    await handle_concurrent_login(page)
    
    # Save browser session state
    os.makedirs(os.path.dirname(settings.MISA_BROWSER_STATE_PATH), exist_ok=True)
    await context.storage_state(path=settings.MISA_BROWSER_STATE_PATH)
    logger.info(f"Saved MISA browser session state to {settings.MISA_BROWSER_STATE_PATH}")


async def handle_concurrent_login(page):
    """
    Kiểm tra xem có bị chuyển hướng tới trang cảnh báo đăng nhập đồng thời (verify) không,
    nếu có thì tự động click "Tiếp tục đăng nhập" để tiếp tục phiên làm việc.
    """
    logger.info("Checking for concurrent login warning (verify) redirect...")
    # Chờ tối đa 5 giây xem URL có chứa 'verify' hay không
    for _ in range(5):
        if "verify" in page.url:
            break
        await asyncio.sleep(1)
        
    if "verify" in page.url:
        logger.warning(f"Redirected to MISA verify page: {page.url}")
        # Chờ tối đa 8 giây cho nút bấm xuất hiện
        btn = page.locator("button:has-text('Tiếp tục đăng nhập'), span:has-text('Tiếp tục đăng nhập'), div:has-text('Tiếp tục đăng nhập')").first
        try:
            await btn.wait_for(state="visible", timeout=8000)
            logger.warning("Concurrent login warning detected. Clicking 'Tiếp tục đăng nhập'...")
            await btn.click(force=True)
            await page.wait_for_load_state("load", timeout=15000)
            await asyncio.sleep(3.0)
            logger.info("Successfully bypassed concurrent login warning page.")
            return True
        except Exception as e:
            logger.warning(f"Did not find or click 'Tiếp tục đăng nhập' button: {str(e)}")
    else:
        logger.info("No concurrent login warning detected.")
    return False


async def find_locator_in_any_frame(page, selectors, timeout=3000):
    """
    Finds a locator from a list of selectors in any frame on the page.
    Returns the locator and the frame it was found in, or (None, None).
    """
    if isinstance(selectors, str):
        selectors = [selectors]
        
    # Generate variants with :visible filter first to prioritize visible elements
    all_variants = []
    for sel in selectors:
        if ":visible" not in sel and not sel.startswith("xpath=") and not sel.startswith("//"):
            all_variants.append(f"{sel}:visible")
        all_variants.append(sel)
        
    # First check: search with short timeout
    for sel in all_variants:
        try:
            loc = page.locator(sel)
            count = await loc.count()
            for i in range(count):
                el = loc.nth(i)
                if await el.is_visible(timeout=200):
                    return el, page
        except Exception:
            pass
            
        for frame in page.frames:
            if frame == page.main_frame:
                continue
            try:
                loc = frame.locator(sel)
                count = await loc.count()
                for i in range(count):
                    el = loc.nth(i)
                    if await el.is_visible(timeout=200):
                        return el, frame
            except Exception:
                continue
                
    # If not found, run close_misa_popups to clear blockers, and try again with full timeout
    logger.info("Element not found initially. Checking and closing blockers...")
    await close_misa_popups(page)
    await asyncio.sleep(0.5)
    
    # Try again with full timeout
    for sel in all_variants:
        try:
            loc = page.locator(sel)
            count = await loc.count()
            for i in range(count):
                el = loc.nth(i)
                if await el.is_visible(timeout=timeout):
                    return el, page
        except Exception:
            pass
            
        for frame in page.frames:
            if frame == page.main_frame:
                continue
            try:
                loc = frame.locator(sel)
                count = await loc.count()
                for i in range(count):
                    el = loc.nth(i)
                    if await el.is_visible(timeout=timeout):
                        return el, frame
            except Exception:
                continue
                
    return None, None


async def close_misa_popups(page):
    logger.info("Handling MISA popups/overlays...")
    
    # Click "Tiếp tục đăng nhập" if concurrent login warning page appears
    concurrent_selectors = [
        "button:has-text('Tiếp tục đăng nhập')",
        "span:has-text('Tiếp tục đăng nhập')",
        "text='Tiếp tục đăng nhập'",
        "div:has-text('Tiếp tục đăng nhập')"
    ]
    for frame in page.frames:
        for selector in concurrent_selectors:
            try:
                locator = frame.locator(selector).first
                if await locator.is_visible(timeout=1000):
                    logger.warning("WARNING: Concurrent login detected! Clicking 'Tiếp tục đăng nhập'...")
                    await locator.click(force=True)
                    await asyncio.sleep(3.0)
            except Exception:
                pass
    
    # Click "Nhắc lại sau" button if it exists
    nhac_lai_selectors = [
        "text='Nhắc lại sau'",
        "button:has-text('Nhắc lại sau')",
        "span:has-text('Nhắc lại sau')",
        "div:has-text('Nhắc lại sau')"
    ]
    for frame in page.frames:
        for selector in nhac_lai_selectors:
            try:
                locator = frame.locator(selector).first
                if await locator.is_visible(timeout=1000):
                    logger.info("Found 'Nhắc lại sau' popup button. Clicking it...")
                    await locator.click(force=True)
                    await asyncio.sleep(1.0)
            except Exception:
                pass

    logger.info("Hiding MISA ad/welcome popup overlays via JS...")
    # Force hide ONLY ad/getting started/expiration overlays via JS in all frames
    for frame in page.frames:
        try:
            await frame.evaluate("""() => {
                // Close concurrent login popup box if it has the warning text
                const popups = document.querySelectorAll('.ms-popup, .ms-message-box, .dx-dialog-wrapper');
                popups.forEach(el => {
                    const text = (el.textContent || '').normalize('NFC');
                    if (text.includes('Đã có máy khác sử dụng') || text.includes('tiếp tục làm việc trên máy này')) {
                        const closeBtn = el.querySelector('button, .ms-button, .dx-button, [role="button"]');
                        if (closeBtn) {
                            closeBtn.click();
                        }
                    }
                });

                // Hide wrapper blocks and popups that contain ad/welcome/expiration texts
                const elements = document.querySelectorAll('.ms-popup--wrapper, .ms-popup, .popup-start-use, .popup-survey, .ms-component.con-ms-popup');
                elements.forEach(el => {
                    const text = (el.textContent || '').normalize('NFC');
                    if (text.includes('Chào') || text.includes('Thông tư 99') || text.includes('bắt đầu sử dụng') || text.includes('phần mềm AMIS') || text.includes('TT99') || text.includes('TT 99') || text.includes('Sắp hết hạn phần mềm')) {
                        el.style.display = 'none';
                        el.style.opacity = '0';
                        el.style.pointerEvents = 'none';
                    }
                });
                
                // Hide ad backdrop overlays
                const backdrops = document.querySelectorAll('.ms-popup-box-background, .ms-popup--background');
                backdrops.forEach(el => {
                    el.style.display = 'none';
                    el.style.opacity = '0';
                    el.style.pointerEvents = 'none';
                });
            }""")
        except Exception:
            pass
            
    logger.info("Force-hid potential ad/expiration overlays/backgrounds via JS in all frames.")
    return True


async def select_accounts_for_so_chi_tiet(page, accounts):
    """
    Thay thế bước 'Chọn tất cả' cho báo cáo Sổ Chi Tiết Các Tài Khoản:
    1. Chọn Bậc = 1 (combobox góc trên phải của bảng chọn tài khoản)
    2. Dùng textbox 'Nhập từ khóa tìm kiếm' để lọc và click chọn từng tài khoản (111, 112, 341)
    
    Dựa trên screenshot thực tế của MISA GLAccountLedger:
    - Combobox Bậc: không có label kế bên, nằm ở góc trên phải bảng tài khoản
    - Textbox tìm kiếm: placeholder = 'Nhập từ khóa tìm kiếm'
    - Chọn tài khoản: click vào ô số tài khoản trong bảng (khớp chính xác)
    """
    # Chọn Bậc = 1
    # Combobox Bậc nằm ở góc phải, thường có class ms-combo hoặc dx-selectbox
    bac_selectors = [
        "xpath=//div[contains(@class,'ms-search-account')]//div[contains(@class,'ms-combo')]//input",
        "xpath=//span[normalize-space(text())='Bậc']/following::div[contains(@class,'ms-combo')][1]//input",
        "xpath=//th[normalize-space(text())='Bậc']/preceding::input[contains(@class,'dx-texteditor-input')][1]",
        "xpath=//div[contains(@class,'ms-combo') and not(ancestor::*[contains(@class,'ms-date')])][last()]//input",
        ".ms-search-account .ms-combo input",
        # Selector dự phòng: input cuối cùng trong vùng tham số (trước bảng tài khoản)
        "xpath=(//div[contains(@class,'param') or contains(@class,'filter')]//input[@type='text'])[last()]",
    ]
    bac_input, bac_frame = await find_locator_in_any_frame(page, bac_selectors, timeout=3000)
    if bac_input:
        logger.info("Clicking 'Bac' combobox to open options...")
        await bac_input.click(force=True)
        await asyncio.sleep(0.5)
        
        # Tìm option "1" trong dropdown (chọn chính xác bậc 1, không phải 10, 11...)
        # Tìm option "1" trong dropdown (chọn chính xác bậc 1, không phải 10, 11...)
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
                # Combobox này readonly nên không dùng fill/type được, chỉ dùng phím điều hướng
                await bac_input.click(force=True)
                await asyncio.sleep(0.5)
                # MISA Bac thường là: "Tất cả", "1", "2", "3"...
                # Nhấn Home để về "Tất cả", rồi ArrowDown để xuống "1"
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
    
    # Textbox tìm kiếm: placeholder = 'Nhập từ khóa tìm kiếm' (xác nhận từ screenshot thực tế)
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
        
        # Xóa nội dung cũ, nhập mã tài khoản và chờ bảng lọc kết quả
        try:
            # Click và dùng phím xóa thay vì fill("") vì có thể textbox có custom clear
            await acc_input.click(force=True)
            await asyncio.sleep(0.2)
            await acc_input.fill("")
            await acc_input.type(account_code)
            await asyncio.sleep(1.5)  # Tăng thời gian chờ bảng filter hiển thị kết quả
            logger.info(f"Typed account code '{account_code}' in search box.")
        except Exception as e:
            logger.error(f"Failed to type account {account_code}: {str(e)}")
            continue
        
        # Click vào CHECKBOX của ô Số tài khoản khớp CHÍNH XÁC
        clicked = False
        try:
            # Chạy script JS để quét toàn bộ DOM, tìm mọi loại table row
            js_script = f"""
            (() => {{
                const rows = document.querySelectorAll('tr, [role="row"], .dx-data-row, .dx-row, .ms-tr');
                if (rows.length === 0) return false;
                
                // Thử tìm chính xác theo text
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
                
                // Nếu là bảng grid tài khoản thì search 3 số + Bậc 1 sẽ ra 1 dòng duy nhất -> Click dòng đầu tiên
                // Bỏ qua dòng header (thường là row đầu tiên của thead), lấy dòng data đầu tiên
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
            # Chạy JS trên page chính và TẤT CẢ các iframe
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
    """
    Tìm và click vào link báo cáo đã lưu có tên tương ứng của người tạo chỉ định.
    Tìm kiếm trong trang chính và tất cả các frames.
    Trả về (clicked_page, is_popup) trong đó clicked_page là page chứa báo cáo (có thể là tab mới).
    """
    link_el = None
    target_frame = None
    
    for frame in [page] + page.frames:
        try:
            # 1. Tìm thẻ <span class="drilldown"> chứa tên báo cáo trong dòng tr chứa tên người tạo
            loc = frame.locator("tr, [role='row']").filter(has_text=creator).locator("span.drilldown").filter(has_text=report_name).first
            if await loc.is_visible(timeout=1000):
                link_el = loc
                target_frame = frame
                break
        except Exception:
            pass
            
        try:
            # 2. Dự phòng 1: Tìm thẻ <span> bất kỳ chứa tên báo cáo trong dòng của người tạo
            loc = frame.locator("tr, [role='row']").filter(has_text=creator).locator("span").filter(has_text=report_name).first
            if await loc.is_visible(timeout=1000):
                link_el = loc
                target_frame = frame
                break
        except Exception:
            pass

        try:
            # 3. Dự phòng 2: Tìm thẻ <a> chứa tên báo cáo trong dòng của người tạo
            loc = frame.locator("tr, [role='row']").filter(has_text=creator).locator("a").filter(has_text=report_name).first
            if await loc.is_visible(timeout=1000):
                link_el = loc
                target_frame = frame
                break
        except Exception:
            pass

        try:
            # 4. Dự phòng 3: Tìm bất kỳ phần tử nào chứa tên báo cáo trong dòng của người tạo
            loc = frame.locator("tr, [role='row']").filter(has_text=creator).locator(f"text='{report_name}'").first
            if await loc.is_visible(timeout=1000):
                link_el = loc
                target_frame = frame
                break
        except Exception:
            pass

    if link_el:
        logger.info(f"Found saved report link '{report_name}' by '{creator}'. Clicking it...")
        
        # 1. Thử click chuẩn bằng Playwright (có thể bị che bởi popup ẩn)
        try:
            # Lắng nghe popup nếu có
            async with page.expect_popup(timeout=3000) as popup_info:
                await link_el.click(timeout=5000)
            new_page = await popup_info.value
            logger.info("Report opened in a new tab/popup.")
            return new_page, True
        except Exception as e:
            # Nếu click thành công nhưng không mở tab mới -> Đã chuyển hướng cùng tab!
            if "timeout" in str(e).lower() and "popup" in str(e).lower():
                logger.info("Normal click succeeded (no popup). Assuming same tab navigation.")
                try:
                    await page.wait_for_load_state("load", timeout=5000)
                except Exception:
                    pass
                return page, False
                
            # Nếu click bị lỗi (ví dụ: bị che khuất bởi overlay quảng cáo)
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


async def download_report_from_url(page, report_url, export_selector, output_path, prefix=None, skip_parameters=False):
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
        
        # Wait to check if MISA auto-redirects us to the home screen
        logger.info("Waiting 5s to check for SPA routing redirect...")
        await asyncio.sleep(5)
        
        # Debug logging and screenshot
        logger.info(f"Current Page URL: {page.url}")
        title = ""
        try:
            title = await page.title()
            logger.info(f"Current Page Title: {title}")
        except Exception as e:
            logger.warning(f"Could not get page title: {str(e)}")
            
        # Check if we got redirected to the home/dashboard screen
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
        
    # Print the frames structure
    try:
        logger.info(f"Number of frames: {len(page.frames)}")
        for idx, f in enumerate(page.frames):
            logger.info(f"Frame {idx}: name='{f.name}', url='{f.url}'")
    except Exception as e:
        logger.warning(f"Failed to list frames: {str(e)}")
        
    try:
        debug_dir = os.path.join(settings.BASE_DIR, 'media', 'debug')
        os.makedirs(debug_dir, exist_ok=True)
        screenshot_path = os.path.join(debug_dir, "navigated.png")
        await page.screenshot(path=screenshot_path)
        logger.info(f"Saved navigation debug screenshot to: {screenshot_path}")
    except Exception as e:
        logger.warning(f"Failed to capture debug screenshot: {str(e)}")
    
    # Check if we got redirected to login page
    if "login" in page.url or "sso" in page.url or "id.misa.vn" in page.url or "amisapp.misa.vn/login" in page.url:
        logger.warning("Redirected to login page. Session might be expired.")
        return False
        
    try:
        # Wait for page elements to appear in any frame
        logger.info("Waiting for initial page elements to appear...")
        await asyncio.sleep(3)
        
        # Step 1: Close welcome popup
        await close_misa_popups(page)
        await asyncio.sleep(1)
        
        try:
            debug_dir = os.path.join(settings.BASE_DIR, 'media', 'debug')
            screenshot_path = os.path.join(debug_dir, "after_popups.png")
            await page.screenshot(path=screenshot_path)
            logger.info(f"Saved after_popups debug screenshot to: {screenshot_path}")
        except Exception as e:
            logger.warning(f"Failed to capture after_popups screenshot: {str(e)}")
        
        if skip_parameters:
            # For Saved Reports, skip choosing parameters and wait 40 seconds to let report load fully
            logger.info("Waiting 40s for the saved report to load...")
            await asyncio.sleep(40)
            await close_misa_popups(page)
            await asyncio.sleep(1)
        else:
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
                        
            if param_btn:
                logger.info(f"Clicking 'Chon tham so' button in frame: {getattr(frame, 'name', 'main') or getattr(frame, 'url', '')}")
                await param_btn.click(force=True)
            else:
                logger.warning("Could not find 'Chon tham so' button. It might already be opened.")
            await asyncio.sleep(1.5)  # Tăng thêm để dialog có thời gian render đầy đủ
            
            # Step 3: Check "Bao gồm số liệu chi nhánh phụ thuộc" checkbox
            logger.info("Clicking 'Bao gom so lieu chi nhanh phu thuoc' checkbox...")
            try:
                target_frame_for_checkbox = frame if frame else page
                # Tìm thẻ label chứa text "Bao gồm số liệu chi nhánh phụ thuộc"
                # Cấu trúc HTML thực tế: <label class="ms-component con-ms-checkbox"><input type="checkbox" class="ms-checkbox--input">...<span>Bao gồm...</span></label>
                checkbox_label = target_frame_for_checkbox.locator("label:has-text('Bao gồm số liệu chi nhánh phụ thuộc')").first
                if await checkbox_label.count() == 0:
                    # Thử fallback với text chứa chữ 'chi nhánh phụ thuộc'
                    checkbox_label = target_frame_for_checkbox.locator("label:has-text('chi nhánh phụ thuộc')").first

                if await checkbox_label.count() > 0:
                    # Kiểm tra trạng thái checked thông qua class của span bên trong
                    # MISA dùng class "ms-checkbox-border-checked-true" khi được check và "ms-checkbox-border-checked-false" khi chưa
                    checkbox_span = checkbox_label.locator("span.ms-checkbox").first
                    is_already_checked = False
                    if await checkbox_span.count() > 0:
                        span_class = await checkbox_span.get_attribute("class") or ""
                        is_already_checked = "checked-true" in span_class
                        logger.info(f"Checkbox span class: '{span_class}', is_already_checked={is_already_checked}")
                    else:
                        # Fallback: kiểm tra qua input checkbox bên trong label
                        checkbox_input = checkbox_label.locator("input[type='checkbox']").first
                        if await checkbox_input.count() > 0:
                            is_already_checked = await checkbox_input.is_checked()
                            logger.info(f"Checkbox input is_checked={is_already_checked}")

                    if not is_already_checked:
                        logger.info("Checkbox not checked yet. Clicking label to toggle ON...")
                        await checkbox_label.click(force=True)
                        await asyncio.sleep(1.0)
                        # Xác nhận trạng thái sau khi click
                        if await checkbox_span.count() > 0:
                            span_class_after = await checkbox_span.get_attribute("class") or ""
                            logger.info(f"Checkbox span class after click: '{span_class_after}'")
                            if "checked-true" not in span_class_after:
                                logger.warning("Checkbox may not have been checked! Trying JS click on input...")
                                checkbox_input = checkbox_label.locator("input[type='checkbox']").first
                                if await checkbox_input.count() > 0:
                                    await checkbox_input.evaluate("el => el.click()")
                                    await asyncio.sleep(0.5)
                    else:
                        logger.info("'Bao gom so lieu chi nhanh phu thuoc' is already checked, skipping.")
                else:
                    logger.warning("Could not find 'Bao gom so lieu chi nhanh phu thuoc' label/checkbox.")
            except Exception as chk_err:
                logger.warning(f"Error handling 'Bao gom so lieu chi nhanh phu thuoc' checkbox: {chk_err}")
            # Debug: chụp ảnh giao diện sau khi click checkbox để kiểm tra trạng thái
            try:
                debug_dir = os.path.join(settings.BASE_DIR, 'media', 'debug')
                screenshot_path = os.path.join(debug_dir, "after_checkbox_click.png")
                await page.screenshot(path=screenshot_path)
                logger.info(f"Saved after_checkbox_click screenshot to: {screenshot_path}")
            except Exception:
                pass
            await asyncio.sleep(3.0)  # Đợi 3 giây để giao diện cập nhật và tải danh sách chi nhánh phụ thuộc


            # Step 3.1: Loại bỏ các chi nhánh có chứa "_Nhật"
            logger.info("Checking for branch tags containing '_Nhật' to remove...")
            target_frame = frame if frame else page
            try:
                # Đợi tối đa 3 giây cho các branch tag xuất hiện trên giao diện
                for wait_attempt in range(6):
                    # Chỉ khớp chính xác các thẻ tag đơn lẻ đại diện cho chi nhánh (ví dụ class dx-tag, ms-tag, selected-item, dx-tag-content...)
                    # Tránh class "item" hay "tag" chung chung để không nhận diện sai sang các container cha hoặc ô checkbox
                    tag_xpath = "//*[contains(text(), '_Nhật')]/ancestor::*[contains(concat(' ', normalize-space(@class), ' '), ' selected-item ') or contains(concat(' ', normalize-space(@class), ' '), ' dx-tag ') or contains(concat(' ', normalize-space(@class), ' '), ' ms-tag ') or contains(concat(' ', normalize-space(@class), ' '), ' dx-tag-content ') or contains(concat(' ', normalize-space(@class), ' '), ' ms-tag-content ') or contains(concat(' ', normalize-space(@class), ' '), ' badge ')]"
                    tag_containers = target_frame.locator(f"xpath={tag_xpath}")
                    count = await tag_containers.count()
                    if count > 0:
                        logger.info(f"Found {count} branch tags containing '_Nhật' after waiting.")
                        break
                    await asyncio.sleep(0.5)

                for attempt in range(15):  # Click tối đa 15 lần
                    tag_xpath = "//*[contains(text(), '_Nhật')]/ancestor::*[contains(concat(' ', normalize-space(@class), ' '), ' selected-item ') or contains(concat(' ', normalize-space(@class), ' '), ' dx-tag ') or contains(concat(' ', normalize-space(@class), ' '), ' ms-tag ') or contains(concat(' ', normalize-space(@class), ' '), ' dx-tag-content ') or contains(concat(' ', normalize-space(@class), ' '), ' ms-tag-content ') or contains(concat(' ', normalize-space(@class), ' '), ' badge ')]"
                    tag_containers = target_frame.locator(f"xpath={tag_xpath}")
                    count = await tag_containers.count()
                    
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
                                break
                            else:
                                box = await tag.bounding_box()
                                if box:
                                    logger.info("Removing branch tag containing '_Nhật' (click right edge coordinates)")
                                    await page.mouse.click(box['x'] + box['width'] - 10, box['y'] + box['height'] / 2)
                                    await asyncio.sleep(0.5)
                                    clicked_any = True
                                    break
                    if not clicked_any:
                        logger.info("Finished filtering branch tags (no more visible '_Nhật' tags found).")
                        break
            except Exception as e:
                logger.warning(f"Error while deselecting '_Nhật' branches: {e}")
            
            # Step 4: Choose "Kỳ báo cáo" -> "Tháng này"
            skip_ky_bao_cao = (prefix == 'TUOI_NO_KH')
            ky_baocao_selectors = [
                "xpath=//label[contains(text(), 'Kỳ báo cáo')]/following-sibling::div//input",
                "xpath=//div[contains(text(), 'Kỳ báo cáo')]/following-sibling::div//input",
                "xpath=//label[contains(text(), 'Kỳ báo cáo')]/ancestor::div[contains(@class, 'ms-combo')]//input",
                "xpath=//div[contains(text(), 'Kỳ báo cáo')]/ancestor::div[contains(@class, 'ms-combo')]//input",
                ".ms-combo input[placeholder*='Kỳ báo cáo']",
                "input[placeholder*='Kỳ báo cáo']"
            ]
            ky_input, frame = await find_locator_in_any_frame(page, ky_baocao_selectors, timeout=3000)
            if not ky_input:
                for f in page.frames:
                    try:
                        label_locator = f.locator("text='Kỳ báo cáo'").first
                        if await label_locator.is_visible(timeout=1000):
                            ky_input = f.locator("xpath=//node()[contains(text(), 'Kỳ báo cáo')]/following::input[1]").first
                            frame = f
                            break
                    except Exception:
                        continue
                        
            if skip_ky_bao_cao:
                logger.info(f"[{prefix}] Skipping 'Ky bao cao' selection as requested.")
            elif ky_input:
                logger.info("Clicking 'Ky bao cao' combobox to open options...")
                await ky_input.click(force=True)
                await asyncio.sleep(0.3)
                
                try:
                    arrow = frame.locator("xpath=//label[contains(text(), 'Kỳ báo cáo')]/following-sibling::div//*[contains(@class, 'arrow') or contains(@class, 'icon') or contains(@class, 'button')]").first
                    if await arrow.is_visible(timeout=1000):
                        logger.info("Clicking combobox arrow icon...")
                        await arrow.click(force=True)
                        await asyncio.sleep(0.5)
                except Exception as e:
                    logger.debug(f"Failed to click combo arrow: {str(e)}")
                
                thang_nay_selectors = [
                    "text='Tháng này'",
                    ".dx-list-item-content:has-text('Tháng này')",
                    ".ms-combo-item:has-text('Tháng này')",
                    "div[role='option']:has-text('Tháng này')",
                    "li:has-text('Tháng này')",
                    "xpath=//div[contains(@class, 'dx-item-content') and text()='Tháng này']"
                ]
                thang_nay_item, option_frame = await find_locator_in_any_frame(page, thang_nay_selectors, timeout=3000)
                if thang_nay_item:
                    logger.info("Selecting 'Thang nay' from dropdown list...")
                    await thang_nay_item.click(force=True)
                else:
                    logger.warning("Could not find 'Thang nay' option in dropdown list. Trying keyboard search...")
                    try:
                        await ky_input.click(click_count=3)
                        await page.keyboard.press("Backspace")
                        await asyncio.sleep(0.2)
                        await ky_input.type("Tháng này")
                        await asyncio.sleep(0.5)
                        await page.keyboard.press("ArrowDown")
                        await asyncio.sleep(0.2)
                        await page.keyboard.press("Enter")
                        logger.info("Typed 'Tháng này' and pressed Enter.")
                    except Exception as e:
                        logger.error(f"Failed to fill 'Tháng này': {str(e)}")
            else:
                logger.warning("Could not find 'Ky bao cao' input combobox.")
            await asyncio.sleep(0.5)
            
            # Step 5: Chọn tất cả (default) hoặc chọn Bậc + tài khoản cụ thể (TAI_KHOAN_CT)
            if prefix == 'TAI_KHOAN_CT':
                target_accounts = getattr(settings, 'MISA_SO_CHI_TIET_ACCOUNTS', ['111', '112', '341', '641', '642'])
                logger.info(f"[TAI_KHOAN_CT] Running custom account selection: Bac 1 + accounts {target_accounts}")
                await select_accounts_for_so_chi_tiet(page, accounts=target_accounts)
            else:
                select_all_selectors = [
                    "text='Chọn tất cả'",
                    "label:has-text('Chọn tất cả')",
                    "span:has-text('Chọn tất cả')",
                    "div:has-text('Chọn tất cả')",
                    ".ms-checkbox:has-text('Chọn tất cả')"
                ]
                select_all_btn, frame = await find_locator_in_any_frame(page, select_all_selectors, timeout=3000)
                if select_all_btn:
                    is_already_checked = False
                    try:
                        parent = frame.locator("xpath=//node()[contains(text(), 'Chọn tất cả')]/ancestor::*[contains(@class, 'checkbox') or contains(@class, 'checked')]").first
                        if await parent.count() > 0:
                            parent_class = await parent.get_attribute("class")
                            if parent_class and ("checked" in parent_class or "active" in parent_class):
                                is_already_checked = True
                    except Exception:
                        pass
                        
                    if not is_already_checked:
                        logger.info("Clicking 'Chon tat ca' checkbox...")
                        await select_all_btn.click(force=True)
                    else:
                        logger.info("'Chon tat ca' is already checked.")
                else:
                    logger.warning("Could not find 'Chon tat ca' checkbox.")
            await asyncio.sleep(0.5)
            
            # Step 6: Click "Xem báo cáo"
            view_report_selectors = [
                "button:has-text('Xem báo cáo')",
                ".btn:has-text('Xem báo cáo')",
                "div.ms-button:has-text('Xem báo cáo')",
                "span:has-text('Xem báo cáo')",
                "button:has-text('Đồng ý')",
                ".dx-button-content:has-text('Xem báo cáo')"
            ]
            view_report_btn, frame = await find_locator_in_any_frame(page, view_report_selectors, timeout=3000)
            if view_report_btn:
                logger.info("Clicking 'Xem bao cao' button...")
                await view_report_btn.click(force=True)
            else:
                raise Exception("Could not find 'Xem bao cao' button.")
                
            # Wait 10 seconds as requested
            logger.info("Waiting 10s for the report to load...")
            await asyncio.sleep(10)

            # Chọn bánh răng -> Chọn mẫu chuẩn. (Chỉ áp dụng cho báo cáo bán hàng BAN_HANG)
            if prefix == 'BAN_HANG':
                logger.info("[BAN_HANG] Selecting 'Mẫu chuẩn.' template...")
                gear_selectors = [
                    ".mi-setting__list-bold", # Cụ thể nút bánh răng cài đặt của lưới báo cáo MISA (mi-24 mi-setting__list-bold)
                    "div.mi-setting__list-bold",
                    "xpath=//div[contains(@class, 'mi-setting__list-bold')]",
                    "xpath=//div[contains(@class, 'mi-setting') and not(contains(@class, 'header-icon')) and not(contains(@class, 'mi-setting-2__nav'))]"
                ]
                # Chờ bảng báo cáo tải xong (ẩn loading panel)
                for loading_sel in [".dx-loadpanel", ".loading", ".ms-loading"]:
                    try:
                        await page.locator(loading_sel).first.wait_for(state="hidden", timeout=10000)
                    except Exception:
                        pass
                
                # Chờ nút bánh răng xuất hiện (timeout tăng lên 30s)
                gear_btn, frame = await find_locator_in_any_frame(page, gear_selectors, timeout=30000)
                if gear_btn:
                    logger.info("Clicking gear settings button...")
                    await gear_btn.click(force=True)
                    await asyncio.sleep(1.5)
                    
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
                        # Fallback: đợi tối đa 4 giây cho bộ chọn text xuất hiện
                        mau_chuan_item = page.locator("text=Mẫu chuẩn.").first
                        try:
                            await mau_chuan_item.wait_for(state="visible", timeout=4000)
                        except Exception:
                            mau_chuan_item = None
                            
                    if mau_chuan_item:
                        logger.info("Selecting 'Mẫu chuẩn.' template option...")
                        await mau_chuan_item.click(force=True)
                        await asyncio.sleep(5.0)  # Chờ 5 giây để tải lại mẫu chuẩn
                    else:
                        logger.warning("Could not find 'Mẫu chuẩn.' option in settings menu.")
                else:
                    logger.warning("Could not find gear settings button.")
        
        
        # Step 7: Click the Excel icon dropdown button
        excel_btn_selectors = [
            ".mi-export__excel-bold",
            ".mi-excel",
            ".mi-icon-excel",
            ".mi-export",
            "[title*='Xuất Excel']",
            "[title*='Xuất khẩu']",
            ".icon-excel",
            ".btn-excel",
            ".dx-button-content .mi-excel",
            "i.mi-excel",
            "span.mi-excel"
        ]
        
        if export_selector:
            excel_btn_selectors.insert(0, export_selector)
            
        # Open download manager to clear old files before exporting
        logger.info("Opening download manager to clear old history...")
        download_manager_selectors = [
            "div.ms-download",
            "div.icon-feature-download",
            ".ms-download",
            ".icon-feature-download",
            ".mi-download",
            ".mi-cloud-download",
            ".mi-download-list",
            "i[class*='download']",
            "span[class*='download']",
            "xpath=//div[contains(@class, 'footer')]//div[contains(@class, 'download')]"
        ]
        manager_btn, manager_frame = await find_locator_in_any_frame(page, download_manager_selectors, timeout=4000)
        if manager_btn:
            await manager_btn.click(force=True)
            await asyncio.sleep(2.0)
            
            # Retry xóa lịch sử download tối đa 3 lần để đảm bảo panel sạch trước khi export
            for clear_attempt in range(3):
                # Check if there are any download entries in the panel
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
                # Click "Xóa hết lịch sử tải tệp" if visible
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
                    
                    # Handle confirmation popup dialog "Có" button
                    confirm_btn_selectors = [
                        "button:has-text('Có')",
                        ".ms-button:has-text('Có')",
                        ".dx-button-content:has-text('Có')",
                        "text='Có'",
                        "span:has-text('Có')",
                        ".popup-confirm button:has-text('Có')"
                    ]
                    confirm_btn, confirm_frame = await find_locator_in_any_frame(page, confirm_btn_selectors, timeout=3000)
                    if confirm_btn:
                        logger.info("Clicking 'Có' on deletion confirmation popup...")
                        await confirm_btn.click(force=True)
                        await asyncio.sleep(2.0)
                    else:
                        logger.warning("Could not find confirmation 'Có' button. Waiting before retry...")
                        await asyncio.sleep(1.5)
                else:
                    logger.warning(f"Could not find 'Xóa hết' button on attempt {clear_attempt + 1}.")
                    await asyncio.sleep(1.0)
                    break
            else:
                logger.warning("Could not fully clear download history after 3 attempts. Proceeding anyway.")
                
            # Close download manager panel
            logger.info("Closing download manager panel...")
            await manager_btn.click(force=True)
            await asyncio.sleep(1.0)
            
        excel_btn, frame = await find_locator_in_any_frame(page, excel_btn_selectors, timeout=5000)
        if not excel_btn:
            raise Exception("Could not find the Excel icon dropdown button on the report page.")
            
        logger.info("Clicking the Excel icon dropdown button...")
        await excel_btn.click(force=True)
        await asyncio.sleep(2.5)
        
        # Step 8: Click the "Xuất Excel (dạng dữ liệu)" option if it exists
        dropdown_selectors = [
            "text='Xuất Excel (dạng dữ liệu)'",
            "span:has-text('Xuất Excel (dạng dữ liệu)')",
            "div:has-text('Xuất Excel (dạng dữ liệu)')",
            ".dx-menu-item-text:has-text('Xuất Excel (dạng dữ liệu)')",
            # Fallback: khớp text chứa "dữ liệu" để phòng MISA đổi tên nhẹ
            "xpath=//*[contains(text(), 'dạng dữ liệu')]",
            "xpath=//*[contains(text(), 'd\u1ea1ng d\u1eef li\u1ec7u')]",
        ]
        excel_triggered = False
        dropdown_item, dropdown_frame = await find_locator_in_any_frame(page, dropdown_selectors, timeout=3000)
        
        # Nếu lần đầu không tìm thấy dropdown, thử click lại nút Excel và tìm lại
        if not dropdown_item:
            logger.warning("Dropdown 'Xuất Excel (dạng dữ liệu)' not visible after first click. Re-clicking Excel button to retry...")
            await excel_btn.click(force=True)
            await asyncio.sleep(2.5)
            dropdown_item, dropdown_frame = await find_locator_in_any_frame(page, dropdown_selectors, timeout=4000)

        if dropdown_item:
            logger.info("Clicking 'Xuat Excel (dang du lieu)' option...")
            await dropdown_item.click(force=True)
            await asyncio.sleep(2.5)
            excel_triggered = True
        else:
            logger.warning("Dropdown 'Xuất Excel (dạng dữ liệu)' option not found after retry. Checking for options dialog directly...")

        # Xử lý popup "Tùy chọn" nếu xuất hiện SAU KHI đã click menu dropdown (không phải thay thế menu dropdown)
        # QUAN TRỌNG: Chỉ click "Đồng ý" nếu đã tìm thấy và click dropdown option trước đó,
        # hoặc đây là loại báo cáo không có dropdown (direct export)
        agree_btn_selectors = [
            "button:has-text('Đồng ý')",
            ".btn:has-text('Đồng ý')",
            ".ms-button:has-text('Đồng ý')",
            "span:has-text('Đồng ý')",
            ".dx-button-content:has-text('Đồng ý')",
            "text='Đồng ý'"
        ]
        agree_btn, agree_frame = await find_locator_in_any_frame(page, agree_btn_selectors, timeout=5000)
        if agree_btn:
            logger.info("Found 'Đồng ý' button (Options dialog). Clicking it to start export...")
            await agree_btn.click(force=True)
            await asyncio.sleep(2.0)
            excel_triggered = True
            
        if not excel_triggered:
            logger.warning("Neither Excel option nor 'Đồng ý' button was clicked. Checking for blockers/warning popups...")
            await close_misa_popups(page)
            raise Exception("Failed to trigger Excel export. The action might have been blocked by a concurrent login warning or dialog.")

            
        # Step 9 & 10: Wait for 50 seconds first for background generation, then open download panel
        logger.info("Waiting 50 seconds for MISA to generate the report in the background...")
        await asyncio.sleep(50)
        
        download_manager_selectors = [
            "div.ms-download",
            "div.icon-feature-download",
            ".ms-download",
            ".icon-feature-download",
            ".mi-download",
            ".mi-cloud-download",
            ".mi-download-list",
            "i[class*='download']",
            "span[class*='download']",
            "xpath=//div[contains(@class, 'footer')]//div[contains(@class, 'download')]"
        ]
        
        # Check if download panel is already visible (indicator check)
        panel_open = False
        try:
            for panel_indicator in ["Tải tệp Excel, tệp in,...", "Đang tạo đường dẫn tải tệp...", "Đường dẫn tải tệp sẽ hết hạn"]:
                indicator = page.locator(f"text='{panel_indicator}'").first
                if await indicator.is_visible(timeout=500):
                    panel_open = True
                    logger.info(f"Download manager panel is already open (indicator: '{panel_indicator}').")
                    break
        except Exception:
            pass
            
        if not panel_open:
            logger.info("Opening download manager panel...")
            manager_btn, manager_frame = await find_locator_in_any_frame(page, download_manager_selectors, timeout=4000)
            if manager_btn:
                await manager_btn.click(force=True)
                await asyncio.sleep(2.0)
            else:
                logger.warning("Could not find download manager button. Checking if 'Tải tệp' is visible anyway.")
                
        # Wait up to an additional 40 seconds (checking every 2 seconds) for exactly ONE new "Tải tệp" entry to appear
        # Strategy: wait until panel has at least 1 entry, then click ONLY the FIRST (newest) entry's download button
        logger.info("Waiting for a NEW 'Tải tệp' button to appear in the download panel (newest entry only)...")
        
        download_btn = None
        frame = None
        
        # Selectors targeting the FIRST (topmost/newest) download entry's action button
        # MISA renders entries newest-first; we always click the first entry to avoid stale old ones
        first_entry_selectors = [
            # Try to click 'Tải tệp' inside the FIRST item row of the download list
            "xpath=(//span[text()='Tải tệp'] | //a[text()='Tải tệp'] | //div[text()='Tải tệp'])[1]",
            "xpath=(//span[contains(text(),'Tải tệp')] | //a[contains(text(),'Tải tệp')])[1]",
        ]
        # Fallback broad selectors (used only after verifying just 1 entry exists)
        broad_download_selectors = [
            "text='Tải tệp'",
            "span:has-text('Tải tệp')",
            "a:has-text('Tải tệp')",
            "button:has-text('Tải tệp')",
            "text='Tải xuống'",
            "span:has-text('Tải xuống')",
            "a:has-text('Tải xuống')",
            "button:has-text('Tải xuống')",
            "text='Tải về'",
            "span:has-text('Tải về')",
            "a:has-text('Tải về')",
            "button:has-text('Tải về')",
        ]
        
        for attempt in range(20):
            # Capture debug screenshot periodically
            if attempt % 3 == 0:
                try:
                    debug_dir = os.path.join(settings.BASE_DIR, 'media', 'debug')
                    screenshot_path = os.path.join(debug_dir, f"download_panel_check_{attempt}.png")
                    await page.screenshot(path=screenshot_path)
                    logger.info(f"Saved download check screenshot to: {screenshot_path}")
                except Exception as se:
                    logger.warning(f"Failed to capture loop screenshot: {str(se)}")
                    
            # Always try the first-entry xpath selectors first
            download_btn, frame = await find_locator_in_any_frame(page, first_entry_selectors, timeout=1000)
            if download_btn:
                logger.info(f"Found newest 'Tải tệp' button (first entry) after {attempt * 2} seconds.")
                break
            await asyncio.sleep(2)
            
        if not download_btn:
            # Fallback: try broad selectors — but log a warning about potential stale entries
            logger.warning("Could not find first-entry download button. Falling back to broad search (may pick stale entry).")
            download_btn, frame = await find_locator_in_any_frame(page, broad_download_selectors, timeout=3000)
            if not download_btn:
                # Last resort: search all frames
                for f in page.frames:
                    try:
                        locator = f.locator("text='Tải tệp'").first
                        if await locator.is_visible(timeout=1000):
                            download_btn = locator
                            frame = f
                            break
                    except Exception:
                        continue
                    
        if not download_btn:
            raise Exception("Could not find the 'Tải tệp' button to download the report after waiting.")
            
        logger.info("Clicking the 'Tải tệp' button (first/newest entry) and waiting for Playwright download event...")
        async with page.expect_download(timeout=45000) as download_info:
            await download_btn.click(force=True)
            
        download = await download_info.value
        await download.save_as(output_path)
        logger.info(f"Successfully downloaded and saved report to: {output_path}")
        
        # Close the download panel to clean up UI
        try:
            manager_btn, manager_frame = await find_locator_in_any_frame(page, download_manager_selectors, timeout=2000)
            if manager_btn:
                logger.info("Closing download manager panel...")
                await manager_btn.click(force=True)
                await asyncio.sleep(1.0)
        except Exception as ce:
            logger.warning(f"Failed to close download manager panel: {str(ce)}")
            
        return True
    except Exception as e:
        logger.error(f"Error in download_report_from_url: {str(e)}")
        try:
            debug_dir = os.path.join(settings.BASE_DIR, 'media', 'debug')
            screenshot_path = os.path.join(debug_dir, "error.png")
            await page.screenshot(path=screenshot_path)
            logger.info(f"Saved error debug screenshot to: {screenshot_path}")
        except Exception as se:
            logger.warning(f"Failed to capture error screenshot: {str(se)}")
        raise e


async def run_misa_automation():
    from playwright.async_api import async_playwright
    
    email = settings.MISA_EMAIL
    password = settings.MISA_PASSWORD
    
    if not email or not password:
        logger.error("MISA_EMAIL or MISA_PASSWORD is not configured in settings/env.")
        return "ERROR: Credentials not configured."
        
    auto_imports_dir = os.path.join(settings.BASE_DIR, 'media', 'auto_imports')
    os.makedirs(auto_imports_dir, exist_ok=True)
    
    async with async_playwright() as p:
        channel = getattr(settings, 'MISA_BROWSER_CHANNEL', 'chrome')
        launch_kwargs = {
            "headless": settings.MISA_HEADLESS,
        }
        if channel:
            launch_kwargs["channel"] = channel
            
        logger.info(f"Launching browser with options: {launch_kwargs}")
        browser = await p.chromium.launch(**launch_kwargs)
        
        # Check if browser state file exists
        if os.path.exists(settings.MISA_BROWSER_STATE_PATH):
            logger.info("Loading existing browser session state...")
            context = await browser.new_context(
                storage_state=settings.MISA_BROWSER_STATE_PATH,
                viewport={"width": 1280, "height": 800}
            )
        else:
            logger.info("No existing session state found. Starting fresh context...")
            context = await browser.new_context(viewport={"width": 1280, "height": 800})
            
        page = await context.new_page()
        
        # Test navigation to verify if we are logged in
        test_url = None
        for prefix, url in settings.MISA_REPORTS.items():
            if url:
                test_url = url
                break
                
        logged_in = False
        if test_url:
            try:
                logger.info(f"Navigating to test URL to verify login: {test_url}")
                await page.goto(test_url, timeout=20000, wait_until="load")
                try:
                    await page.wait_for_load_state("domcontentloaded", timeout=5000)
                except Exception:
                    pass
                
                current_url = page.url
                if "login" not in current_url and "sso" not in current_url and "id.misa.vn" not in current_url:
                    logged_in = True
                    logger.info(f"Already logged in via restored session. Current URL: {current_url}")
            except Exception as e:
                logger.warning(f"Failed verification navigation: {str(e)}")
                # Check current URL even if timed out
                current_url = page.url
                if "login" not in current_url and "sso" not in current_url and "id.misa.vn" not in current_url:
                    logged_in = True
                    logger.info(f"Navigation timed out but URL looks logged in: {current_url}")
                
        if not logged_in:
            logger.info("Proceeding to log in to MISA AMIS...")
            await login_to_misa(page, context, email, password)
        else:
            # Xử lý cảnh báo đăng nhập đồng thời đối với phiên làm việc được khôi phục
            await handle_concurrent_login(page)
            
        # Download each configured report
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        downloaded_count = 0
        failed_count = 0
        failed_details = []
        
        use_option = getattr(settings, 'USE_OPTION_EXPORT_REPORT_MISA', 1)
        if use_option == 2:
            logger.info("Using USE_OPTION_EXPORT_REPORT_MISA = 2 (Saved Reports Flow)")
            # 1. Download TUOI_NO_KH directly (excluded from saved reports list)
            tuoi_no_kh_url = settings.MISA_REPORTS.get('TUOI_NO_KH')
            if tuoi_no_kh_url:
                prefix = 'TUOI_NO_KH'
                filename = f"{prefix}_{timestamp}.xlsx"
                output_path = os.path.join(auto_imports_dir, filename)
                logger.info(f"Downloading {prefix} via step-by-step export flow...")
                try:
                    success = await download_report_from_url(page, tuoi_no_kh_url, settings.MISA_EXPORT_SELECTOR, output_path, prefix=prefix, skip_parameters=False)
                    if not success:
                        logger.info("Retrying TUOI_NO_KH download after re-logging in...")
                        await login_to_misa(page, context, email, password)
                        success = await download_report_from_url(page, tuoi_no_kh_url, settings.MISA_EXPORT_SELECTOR, output_path, prefix=prefix, skip_parameters=False)
                        
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
            
            # 2. Go to Saved Reports URL
            logger.info(f"Navigating to MISA Saved Reports List: {settings.MISA_URL_REPORT_SAVED}")
            try:
                await page.goto(settings.MISA_URL_REPORT_SAVED, timeout=30000, wait_until="load")
            except Exception as e:
                logger.warning(f"Navigation to Saved Reports List timed out or failed: {str(e)}")
            try:
                await page.wait_for_load_state("domcontentloaded", timeout=10000)
            except Exception:
                pass
            
            # Close popups on saved reports page
            await close_misa_popups(page)
            await asyncio.sleep(2)
            
            # 3. Process remaining 5 reports
            saved_reports_to_download = [
                ('BAN_HANG', '01 - Sổ chi tiết bán hàng - Important'),
                ('MUA_HANG', '02 - Sổ chi tiết mua hàng - Important'),
                ('TON_KHO', '03 - Tổng hợp tồn kho - Important'),
                ('CONG_NO_NCC', '04 - Tổng hợp công nợ phải trả nhà cung cấp - Important'),
                ('TAI_KHOAN_CT', '06 - Sổ chi tiết các tài khoản - Important'),
            ]
            
            for prefix, report_name in saved_reports_to_download:
                filename = f"{prefix}_{timestamp}.xlsx"
                output_path = os.path.join(auto_imports_dir, filename)
                logger.info(f"Processing saved report: '{report_name}' (Prefix: {prefix})")
                
                # Click the report link (handles opening in a new tab)
                target_page, is_popup = await click_saved_report_link(page, report_name)
                if not target_page:
                    logger.error(f"Failed to find or click saved report link: '{report_name}'")
                    failed_count += 1
                    failed_details.append(f"{prefix} (Saved Report): Link not found")
                    continue
                    
                # Download using skip_parameters=True and report_url=None
                try:
                    success = await download_report_from_url(target_page, None, settings.MISA_EXPORT_SELECTOR, output_path, prefix=prefix, skip_parameters=True)
                    if not success:
                        # Retry: go to saved reports page, re-login, click and try again
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
                    # Clean up: close the popup tab if it was opened in a new tab
                    if is_popup and target_page:
                        try:
                            logger.info("Closing report popup tab...")
                            await target_page.close()
                        except Exception as ce:
                            logger.warning(f"Failed to close popup tab: {str(ce)}")
                    
                # Navigate back to Saved Reports List ONLY if it was same-tab navigation
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
                    
                filename = f"{prefix}_{timestamp}.xlsx"
                output_path = os.path.join(auto_imports_dir, filename)
                
                try:
                    success = await download_report_from_url(page, url, settings.MISA_EXPORT_SELECTOR, output_path, prefix=prefix, skip_parameters=False)
                    if not success:
                        # Retry once after logging in again
                        logger.info("Retrying download after re-logging in...")
                        await login_to_misa(page, context, email, password)
                        success = await download_report_from_url(page, url, settings.MISA_EXPORT_SELECTOR, output_path, prefix=prefix, skip_parameters=False)
                        
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


@shared_task(name="accounting.tasks.download_misa_reports")
def download_misa_reports_task():
    logger.info("Starting MISA report download task...")
    start_time = timezone.now()
    
    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
    try:
        result_msg = loop.run_until_complete(run_misa_automation())
        logger.info(f"MISA automation run finished: {result_msg}")
        
        ImportLog.objects.create(
            file_name="MISA_Playwright_Automation",
            status='SUCCESS' if "SUCCESS" in result_msg else 'ERROR',
            message=result_msg,
            start_time=start_time,
            end_time=timezone.now()
        )
        return result_msg
    except Exception as e:
        err_msg = f"MISA Playwright Automation Failed: {str(e)}"
        logger.error(err_msg)
        ImportLog.objects.create(
            file_name="MISA_Playwright_Automation",
            status='ERROR',
            message=err_msg,
            start_time=start_time,
            end_time=timezone.now()
        )
        raise e


@shared_task(name="accounting.tasks.misa_pipeline_master")
def misa_pipeline_master():
    logger.info("Starting MISA Pipeline Master Task...")
    
    # Run the download task synchronously in this Celery worker
    download_result = download_misa_reports_task()
    logger.info(f"Download task finished with result: {download_result}")
    
    # Import the excel files from folder
    from .tasks import auto_import_excel_from_folder
    import_result = auto_import_excel_from_folder()
    logger.info(f"Import task finished with result: {import_result}")
    
    return f"MISA Pipeline completed. Download: {download_result}. Import: {import_result}"
