from playwright.sync_api import sync_playwright, TimeoutError
import re, json, xml.etree.ElementTree as ET
import threading, time
from queue import Queue


USERNAME = "SEL28AA8"
PASSWORD = "Bkdfasdv@203414"

unlock_queue = Queue()

def unlock_worker():
    """Thread phụ — chỉ gửi tín hiệu check unlock"""
    while True:
        unlock_queue.put("check_unlock")
        time.sleep(5)  # Mỗi 5s check 1 lần

def getIDvsENC(xml_data):
    try:
        root = ET.fromstring(xml_data)
        framework_json_str = root.find("framework").text.strip()
        framework_data = json.loads(framework_json_str)
        session_id = framework_data["session"]["id"]

        data_json_str = root.find("data").text.strip()
        data_data = json.loads(data_json_str)
        encryption_key = data_data["model"]["output"]["encryptionKey"]

        return {"ID": session_id, "EncryptionKey": encryption_key}
    except:
        return None

def login(p, username=USERNAME, password=PASSWORD):
    browser = p.chromium.launch(headless=True)
    page = browser.new_page()

    def is_target_response(res):
        return "createSessionKey" in res.url and ";jsessionid=" in res.url.lower()

    page.goto("https://tc345.resdesktop.altea.amadeus.com/app_ard/apf/init/login?SITE=AVNPAIDL&LANGUAGE=GB&MARKETS=ARDW_PROD_WBP&ACTION=clpLogin")

    page.wait_for_selector("#userAliasInput")
    page.fill("#userAliasInput", username)
    page.click('button[type="submit"]')

    page.wait_for_selector("#passwordInput")
    page.fill("#passwordInput", password)
    page.click('button[type="submit"]')

    try:
        page.wait_for_selector('#privateDataDiscOkButton', timeout=5000)
        page.click('#privateDataDiscOkButton')
    except:
        pass

    try:
        res = page.wait_for_event("response", timeout=60000, predicate=is_target_response)
        body = res.text()
    except:
        print("[❌] Không bắt được createSessionKey")
        return None, browser

    jsession_data = getIDvsENC(body)
    if jsession_data:
        with open("session_log.json", "w", encoding="utf-8") as f:
            json.dump(jsession_data, f, indent=2, ensure_ascii=False)

        cookies = page.context.cookies()
        with open("cookie1a.json", "w", encoding="utf-8") as f:
            json.dump(cookies, f, indent=2, ensure_ascii=False)

        print("[✅] Login thành công:", jsession_data)
        return {"status": "OK", "session": jsession_data, "page": page, "browser": browser}, browser
    else:
        return None, browser

if __name__ == "__main__":
    with sync_playwright() as p:
        result, browser = login(p)
        if result:
            page = result["page"]
           # Start thread gửi tín hiệu check unlock
            threading.Thread(target=unlock_worker, daemon=True).start()

            print("[*] Giữ browser sống, auto unlock đang chạy...")
            try:
                while True:
                    if not unlock_queue.empty():
                        msg = unlock_queue.get()
                        if msg == "check_unlock":
                            try:
                                page.wait_for_selector(
                                    "#eusermanagement_logout_lock_PASSWORD_id_input",
                                    state="visible",
                                    timeout=2000
                                )
                                print("[⚠] Phát hiện khóa — đang nhập password...")
                                page.fill("#eusermanagement_logout_lock_PASSWORD_id_input", PASSWORD)
                                page.click("#eusermanagement_logout_lock_save_id")
                                print("[✅] Đã unlock!")
                            except TimeoutError:
                                print("keep ss alive")
            except KeyboardInterrupt:
                print("\n[!] Đóng browser")
            
        browser.close()




