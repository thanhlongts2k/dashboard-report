# Locators and Selectors for MISA AMIS Playwright Automation

EMAIL_SELECTORS = [
    "input.ap-lg-input[placeholder='Số điện thoại/email']",
    "input[placeholder*='email']",
    "input[type='email']",
    "input[name='username']",
    "#username",
    "#email"
]

PWD_SELECTORS = [
    "input.ap-lg-input[placeholder='Mật khẩu']",
    "input[placeholder*='khẩu']",
    "input[type='password']",
    "input[name='password']",
    "#password"
]

SUBMIT_SELECTORS = [
    "button.login-form-btn",
    "button[type='submit']",
    "button#submitBtn",
    "button:has-text('Đăng nhập')",
    "#submitBtn"
]

OTP_SELECTOR = "input[name='otp']"

CONCURRENT_LOGIN_SELECTORS = [
    "button:has-text('Tiếp tục đăng nhập')",
    "span:has-text('Tiếp tục đăng nhập')",
    "text='Tiếp tục đăng nhập'",
    "div:has-text('Tiếp tục đăng nhập')"
]

NHAC_LAI_SELECTORS = [
    "text='Nhắc lại sau'",
    "button:has-text('Nhắc lại sau')",
    "span:has-text('Nhắc lại sau')",
    "div:has-text('Nhắc lại sau')"
]
