from playwright.sync_api import sync_playwright, TimeoutError
import re, json, xml.etree.ElementTree as ET
import threading, time
from queue import Queue
import os
from dotenv import load_dotenv
load_dotenv()

USERNAME = os.getenv("USERNAME_1A")
PASSWORD = os.getenv("PASSWORD_1A")

LOGOUT_SIGNAL = "/tmp/logout1a"
STATE_FILE = "/root/API_Fly/state_1a.json"

unlock_queue = Queue()


def unlock_worker():
    while True:
        unlock_queue.put("check_unlock")
        time.sleep(5)


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
    except Exception as e:
        print("Parse session lỗi:", e)
        return None


def save_last_crash_time():
    with open(STATE_FILE, "w") as f:
        json.dump({"last_crash": time.time()}, f)


def get_last_crash_time():
    if not os.path.exists(STATE_FILE):
        return None
    try:
        with open(STATE_FILE) as f:
            return json.load(f).get("last_crash")
    except:
        return None


def wait_if_recent_crash():
    last = get_last_crash_time()
    if not last:
        return
    elapsed = time.time() - last
    wait_time = 300  # 5 phút
    if elapsed < wait_time:
        remaining = int(wait_time - elapsed)
        print(f"⏳ Crash gần đây, đợi {remaining}s để Amadeus reset session...")
        time.sleep(remaining)


def try_logout_old_session(p):
    print("🔄 Thử logout session cũ...")
    browser = p.chromium.launch(headless=True)
    page = browser.new_page()

    cookie_file = "cookie1a.json"
    if os.path.exists(cookie_file):
        try:
            with open(cookie_file) as f:
                cookies = json.load(f)
            page.context.add_cookies(cookies)
        except:
            pass

    try:
        page.goto(
            "https://tc345.resdesktop.altea.amadeus.com/app_ard/apf/init/login?SITE=AVNPAIDL&LANGUAGE=GB&MARKETS=ARDW_PROD_WBP&ACTION=clpLogin",
            timeout=30000
        )
        time.sleep(3)

        try:
            page.wait_for_selector(
                "#eusermanagement_logout_logo_logout_id",
                timeout=5000
            )
            page.click("#eusermanagement_logout_logo_logout_id")
            time.sleep(2)
            try:
                page.wait_for_selector("#uicAlertBox_ok", timeout=5000)
                page.click("#uicAlertBox_ok")
            except:
                pass
            print("✅ Logout session cũ OK")
            time.sleep(3)
        except:
            print("ℹ️ Không có session cũ cần logout")

    except Exception as e:
        print(f"⚠️ Logout session cũ lỗi: {e}")
    finally:
        browser.close()

    if os.path.exists(cookie_file):
        os.remove(cookie_file)


def do_logout(page, browser):
    if not os.path.exists(LOGOUT_SIGNAL):
        return False

    print("⚠️ Nhận yêu cầu logout")
    try:
        os.remove(LOGOUT_SIGNAL)
        page.wait_for_selector(
            "#eusermanagement_logout_logo_logout_id", timeout=10000
        )
        page.click("#eusermanagement_logout_logo_logout_id")
        print("✅ Đã click Logout")
        page.wait_for_selector("#uicAlertBox_ok", state="visible", timeout=10000)
        page.click("#uicAlertBox_ok")
        print("✅ Đã xác nhận Sign out")
        time.sleep(5)
        browser.close()
        return True
    except Exception as e:
        print("❌ Logout lỗi:", e)
        try:
            browser.close()
        except:
            pass
        return True


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
    except TimeoutError:
        print("[❌] Không bắt được createSessionKey")
        page.screenshot(path="/root/API_Fly/login1a_timeout.png")
        save_last_crash_time()
        return None, browser

    jsession_data = getIDvsENC(body)
    if not jsession_data:
        save_last_crash_time()
        return None, browser

    with open("session_log.json", "w", encoding="utf-8") as f:
        json.dump(jsession_data, f, indent=2, ensure_ascii=False)

    cookies = page.context.cookies()
    with open("cookie1a.json", "w", encoding="utf-8") as f:
        json.dump(cookies, f, indent=2, ensure_ascii=False)

    # Xóa crash time khi login thành công
    if os.path.exists(STATE_FILE):
        os.remove(STATE_FILE)

    print("[✅] Login thành công:", jsession_data)
    return {"page": page, "browser": browser}, browser


if __name__ == "__main__":
    # Xóa logout signal cũ khi khởi động
    if os.path.exists(LOGOUT_SIGNAL):
        os.remove(LOGOUT_SIGNAL)
        print("🗑️ Xóa logout signal cũ")

    with sync_playwright() as p:

        # Bước 1: đợi nếu crash gần đây
        wait_if_recent_crash()

        # Bước 2: logout session cũ trước khi login mới
        try_logout_old_session(p)
        time.sleep(5)

        # Bước 3: login mới
        result, browser = login(p)

        if not result:
            browser.close()
            exit(1)

        page = result["page"]

        threading.Thread(target=unlock_worker, daemon=True).start()
        print("🚀 Browser giữ sống")

        try:
            while True:
                if do_logout(page, browser):
                    break

                if not unlock_queue.empty():
                    msg = unlock_queue.get()
                    if msg == "check_unlock":
                        try:
                            page.wait_for_selector(
                                "#uicAlertBox_ok", state="visible", timeout=1000
                            )
                            page.click("#uicAlertBox_ok")
                            print("Đóng alert")
                        except TimeoutError:
                            pass

                        try:
                            page.wait_for_selector(
                                "#eusermanagement_logout_lock_PASSWORD_id_input",
                                timeout=1000,
                            )
                            page.fill(
                                "#eusermanagement_logout_lock_PASSWORD_id_input",
                                PASSWORD
                            )
                            page.click("#eusermanagement_logout_lock_save_id")
                            print("Unlock OK")
                        except TimeoutError:
                            pass

                time.sleep(1)

        finally:
            if os.path.exists(LOGOUT_SIGNAL) is False:
                save_last_crash_time()
            try:
                browser.close()
            except:
                pass
