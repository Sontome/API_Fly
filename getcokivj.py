from playwright.sync_api import sync_playwright
import os
import time
STATE_FILE = "state.json"

def login_and_save(page, context):
    print("🔐 Đăng nhập...")
    page.goto("https://agents2.vietjetair.com/login")

    page.fill('input[name="username"]', "KR000242A47CY4")
    
    page.fill('input[name="password"]', "Bkdfasdv@203414")
    page.click('button[class="mat-focus-indicator button_login font_16 font_button full-width mat-raised-button mat-button-base"]')
    time.sleep(10)
    page.wait_for_load_state("networkidle")
    print("✅ Đăng nhập thành công:", page.url)

    # Lưu cả cookies + localStorage
    context.storage_state(path=STATE_FILE)
    print("💾 Đã lưu state!")

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)

    if os.path.exists(STATE_FILE):
        print("🍪 Tìm thấy state.json, tạo context từ state...")
        context = browser.new_context(storage_state=STATE_FILE)
    else:
        context = browser.new_context()

    page = context.new_page()

        # Lấy localStorage/sessionStorage (có thể chứa token)
    #local_storage = page.evaluate("window.localStorage.getItem('Authorization')")
    #session_storage = page.evaluate("window.sessionStorage.getItem('Authorization')")
    

    login_and_save(page, context)
   
   

    
   



