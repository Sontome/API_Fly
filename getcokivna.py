from playwright.sync_api import sync_playwright
import os
import json
import time

STATE_FILE = "statevna.json"

def export_full_state(context, page, path):
    """Lưu đầy đủ cookies + localStorage"""
    cookies = context.cookies()
    local_storage = page.evaluate("() => JSON.stringify(localStorage)")
    session_storage = page.evaluate("() => JSON.stringify(sessionStorage)")

    state = {
        "cookies": cookies,
        "localStorage": json.loads(local_storage),
        "sessionStorage": json.loads(session_storage)
    }

    with open(path, "w", encoding="utf-8") as f:
        json.dump(state, f, indent=2, ensure_ascii=False)
    
    print(f"💾 Đã lưu đầy đủ cookies + storage vào {path}!")

def login_and_save(page, context):
    print("🔐 Đăng nhập...")
    page.goto("https://wholesale.powercallair.com/tm/tmLogin.lts")

    page.fill('input[name="user_agt_Code"]', "5253")
    page.fill('input[name="user_id"]', "HANVIETAIR")
    page.fill('input[name="user_password"]', "Ha@112233")
    page.click('button[style="padding: 30px 14px 30px;background: #f66b17;color:white;font-size:15px"]')

    page.wait_for_load_state("networkidle")
    print("✅ Đăng nhập thành công:", page.url)
    time.sleep(5)
    export_full_state(context, page, STATE_FILE)

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)

    context = browser.new_context()
    page = context.new_page()
    page.goto("https://wholesale.powercallair.com/b2bIndex.lts")
    page.wait_for_load_state("networkidle")

    if "/tmLogin" in page.url:
        print("⚠️ Session hết hạn hoặc chưa login, login lại...")
        login_and_save(page, context)
    else:
        export_full_state(context, page, STATE_FILE)
    
    print("🎯 Đang ở:", page.url)
    
