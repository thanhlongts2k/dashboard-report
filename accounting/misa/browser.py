import os
import asyncio
import logging
from django.conf import settings
from .locators import EMAIL_SELECTORS, PWD_SELECTORS, SUBMIT_SELECTORS, OTP_SELECTOR, CONCURRENT_LOGIN_SELECTORS, NHAC_LAI_SELECTORS

logger = logging.getLogger(__name__)

async def login_to_misa(page, context, email, password):
    logger.info(f"Navigating to MISA login page: {settings.MISA_AMIS_LOGIN_URL}")
    await page.goto(settings.MISA_AMIS_LOGIN_URL)
    try:
        await page.wait_for_load_state("load", timeout=10000)
    except Exception:
        pass
    
    # Check if SSO automatically logged in and redirected to home/app
    if "login" not in page.url and ("actapp.misa.vn" in page.url or "amisapp.misa.vn/app" in page.url):
        logger.info(f"SSO automatically authenticated active session. Currently on: {page.url}")
        os.makedirs(os.path.dirname(settings.MISA_BROWSER_STATE_PATH), exist_ok=True)
        await context.storage_state(path=settings.MISA_BROWSER_STATE_PATH)
        return True

    # Fill Email
    email_filled = False
    for sel in EMAIL_SELECTORS:
        try:
            if await page.locator(sel).is_visible(timeout=3000):
                await page.locator(sel).fill(email)
                email_filled = True
                logger.info(f"Filled email using selector: {sel}")
                break
        except Exception:
            continue
    if not email_filled:
        # Final check if page redirected during filling
        if "login" not in page.url and "actapp.misa.vn" in page.url:
            logger.info("Page redirected to main app during login attempt. Proceeding...")
            return True
        raise Exception("Could not find or fill MISA email input field.")
        
    # Fill Password
    pwd_filled = False
    for sel in PWD_SELECTORS:
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
    submit_clicked = False
    for sel in SUBMIT_SELECTORS:
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
        
    # Check OTP verification
    try:
        await page.locator(OTP_SELECTOR).wait_for(state="visible", timeout=7000)
        logger.warning("WARNING: MISA AMIS requires OTP verification!")
        if not settings.MISA_HEADLESS:
            print("\n" + "="*80)
            print("WARNING: MISA AMIS REQUIRES OTP VERIFICATION!")
            print("Vui long nhap ma OTP gui toi email cua ban vao trinh duyet dang mo tren man hinh.")
            print("Tich chon 'Khong hoi lai tren thiet bi nay' va bam 'Tiep tuc' de dang nhap.")
            print("He thong dang tu dong cho toi da 3 phut de ban hoan thanh...")
            print("="*80 + "\n")
            await page.locator(OTP_SELECTOR).wait_for(state="hidden", timeout=180000)
            logger.info("OTP verification completed by user (OTP input is now hidden).")
        else:
            raise Exception("MISA AMIS requires OTP verification. Please run once in headed mode (MISA_HEADLESS=False) to verify the device.")
    except Exception as e:
        if "timeout" in str(e).lower() or "timeout" in type(e).__name__.lower():
            try:
                is_visible = await page.locator(OTP_SELECTOR).is_visible()
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
    
    await handle_concurrent_login(page)
    
    os.makedirs(os.path.dirname(settings.MISA_BROWSER_STATE_PATH), exist_ok=True)
    await context.storage_state(path=settings.MISA_BROWSER_STATE_PATH)
    logger.info(f"Saved MISA browser session state to {settings.MISA_BROWSER_STATE_PATH}")


async def handle_concurrent_login(page):
    logger.info("Checking for concurrent login warning (verify) redirect...")
    for _ in range(5):
        if "verify" in page.url:
            break
        await asyncio.sleep(1)
        
    if "verify" in page.url:
        logger.warning(f"Redirected to MISA verify page: {page.url}")
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


async def find_locator_in_any_frame(page, selectors, timeout=3000, close_blockers=True):
    if isinstance(selectors, str):
        selectors = [selectors]
        
    all_variants = []
    for sel in selectors:
        if ":visible" not in sel and not sel.startswith("xpath=") and not sel.startswith("//"):
            all_variants.append(f"{sel}:visible")
        all_variants.append(sel)
        
    start_time = asyncio.get_event_loop().time()
    max_duration = timeout / 1000.0
    
    while True:
        for sel in all_variants:
            try:
                loc = page.locator(sel)
                count = await loc.count()
                for i in range(count):
                    el = loc.nth(i)
                    if await el.is_visible():
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
                        if await el.is_visible():
                            return el, frame
                except Exception:
                    continue

        if (asyncio.get_event_loop().time() - start_time) >= max_duration:
            break
            
        await asyncio.sleep(0.5)

    if close_blockers:
        logger.info("Element not found initially. Checking and closing blockers...")
        await close_misa_popups(page)
        await asyncio.sleep(0.5)
    
    return None, None


async def close_misa_popups(page):
    logger.info("Handling MISA popups/overlays...")
    
    for frame in page.frames:
        for selector in CONCURRENT_LOGIN_SELECTORS:
            try:
                locator = frame.locator(selector).first
                if await locator.is_visible(timeout=1000):
                    logger.warning("WARNING: Concurrent login detected! Clicking 'Tiếp tục đăng nhập'...")
                    await locator.click(force=True)
                    await asyncio.sleep(3.0)
            except Exception:
                pass
    
    for frame in page.frames:
        for selector in NHAC_LAI_SELECTORS:
            try:
                locator = frame.locator(selector).first
                if await locator.is_visible(timeout=1000):
                    logger.info("Found 'Nhắc lại sau' popup button. Clicking it...")
                    await locator.click(force=True)
                    await asyncio.sleep(1.0)
            except Exception:
                pass

    logger.info("Hiding MISA ad/welcome popup overlays via JS...")
    for frame in page.frames:
        try:
            await frame.evaluate("""() => {
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

                const elements = document.querySelectorAll('.popup-start-use, .popup-survey, .ms-component.con-ms-popup');
                elements.forEach(el => {
                    const text = (el.textContent || '').normalize('NFC');
                    if (text.includes('Chào') || text.includes('Thông tư 99') || text.includes('bắt đầu sử dụng') || text.includes('TT99') || text.includes('TT 99') || text.includes('Sắp hết hạn phần mềm')) {
                        el.style.display = 'none';
                        el.style.opacity = '0';
                        el.style.pointerEvents = 'none';
                    }
                });
            }""")
        except Exception:
            pass
            
    logger.info("Force-hid potential ad/expiration overlays via JS in all frames.")
    return True
