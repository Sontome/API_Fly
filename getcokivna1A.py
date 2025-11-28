from playwright.sync_api import sync_playwright
import json
import time

STATE_FILE = "statevna1A.json"

def export_full_state(context, page, path):
    """Lưu cookies + localStorage thôi, bỏ sessionStorage cho đỡ lỗi"""
    cookies = context.cookies()
    local_storage = {}
    try:
        local_storage = json.loads(page.evaluate("() => JSON.stringify(localStorage)"))
    except Exception as e:
        print("⚠️ Không thể đọc localStorage:", e)

    state = {
        "cookies": cookies,
        "localStorage": local_storage
    }

    with open(path, "w", encoding="utf-8") as f:
        json.dump(state, f, indent=2, ensure_ascii=False)
    
    print(f"💾 Đã lưu cookies + localStorage vào {path}!")

def login_and_save(page, context):
    print("🔐 Đang login...")
    page.goto("https://www.accounts.amadeus.com/LoginService/authorizeAngular?service=ARD_VN_DC&client_id=1ASIXARDVNDC&LANGUAGE=GB&redirect_uri=https%3A%2F%2Ftc345.resdesktop.altea.amadeus.com%2Fapp_ard%2Fapf%2Finit%2Flogin%3FSITE%3DAVNPAIDL%26LANGUAGE%3DGB%26MARKETS%3DARDW_PROD_WBP%26ACTION%3DclpLogin#/login")

    page.fill('input[id="userAliasInput"]', "SEL28AA8")
    page.press('input[id="userAliasInput"]', "Enter")
    time.sleep(1)

    page.fill('input[id="passwordInput"]', "Bkdfasdv@2034141")
    page.press('input[id="passwordInput"]', "Enter")
    time.sleep(3)

    try:
        page.click('button[id="privateDataDiscOkButton"]')
    except:
        pass

    # Đợi redirect về domain tc345
    print("⏳ Đang đợi redirect sang domain chính...")
    for _ in range(20):
        if "tc345.resdesktop.altea.amadeus.com" in page.url:
            print("✅ Đã vào tc345, tiến hành lưu state")
            export_full_state(context, page, STATE_FILE)
            return
        time.sleep(1)

    print("❌ Login thất bại hoặc chưa redirect về đúng domain:", page.url)

with sync_playwright() as p:
    browser = p.chromium.launch(headless=False)

    # Dùng storage_state nếu có
    try:
        context = browser.new_context(storage_state=STATE_FILE)
    except:
        print("⚠️ File state không tồn tại hoặc lỗi, tạo context mới")
        context = browser.new_context()

    page = context.new_page()
    page.goto("https://tc345.resdesktop.altea.amadeus.com/app_ard/apf/init/login?SITE=AVNPAIDL&LANGUAGE=GB&MARKETS=ARDW_PROD_WBP&ACTION=clpLogin")
    page.wait_for_load_state("load")
    time.sleep(2)

    if "login" in page.url or "accounts.amadeus.com" in page.url:
        print("⚠️ Cookie hết hạn hoặc chưa login")
        login_and_save(page, context)
    else:
        print("✅ Dùng lại cookie thành công!")




