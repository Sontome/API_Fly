from playwright.sync_api import sync_playwright, TimeoutError
import json
import xml.etree.ElementTree as ET
import threading
import time
import os
from queue import Queue
from dotenv import load_dotenv

load_dotenv()

USERNAME = os.getenv("SUN_1A_USERNAME")
PASSWORD = os.getenv("SUN_1A_PASSWORD")

LOGOUT_SIGNAL = "/tmp/logout1asun"
STATE_FILE = "/root/API_Fly/state_sun1a.json"  # lưu trạng thái giữa các lần chạy

unlock_queue = Queue()


def unlock_worker():
    while True:
        unlock_queue.put("check_unlock")
        time.sleep(5)


def getIDvsENC(xml_data):
    try:
        root = ET.fromstring(xml_data)
        framework_json = root.find("framework").text.strip()
        framework = json.loads(framework_json)
        session_id = framework["session"]["id"]
        data_json = root.find("data").text.strip()
        data = json.loads(data_json)
        encryption_key = data["model"]["output"]["encryptionKey"]
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
    """Nếu crash gần đây < 5 phút thì đợi cho Amadeus reset"""
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
    """Mở browser, vào Amadeus và logout session cũ nếu còn"""
    print("🔄 Thử logout session cũ...")
    browser = p.chromium.launch(headless=True)
    page = browser.new_page()

    # Inject cookie cũ nếu còn
    cookie_file = "/root/API_Fly/cookie1a_sun.json"
    if os.path.exists(cookie_file):
        try:
            with open(cookie_file) as f:
                cookies = json.load(f)
            page.context.add_cookies(cookies)
        except:
            pass

    try:
        page.goto(
            "https://tc110.resdesktop.altea.com/app_ard/apf/init/login",
            timeout=30000
        )
        time.sleep(3)

        # Thử click logout nếu đang có session
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

    # Xóa cookie cũ
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


def login(p):
    browser = p.chromium.launch(headless=True)
    page = browser.new_page()

    def target_response(res):
        return "createSessionKey" in res.url

    url = "https://www.accounts.amadeus.com/LoginService/authorizeAngular?service=ARD_9G-DC&client_id=1ASIXARD9GDC&LANGUAGE=GB&redirect_uri=https%3A%2F%2Ftc110.resdesktop.altea.amadeus.com%2Fapp_ard%2Fapf%2Finit%2Flogin%3FSITE%3DA9GPAIDL%26LANGUAGE%3DGB%26MARKETS%3DARDW_PROD_WBP%26ACTION%3DclpLogin#/login"

    page.goto(url)
    page.wait_for_selector("#userAliasInput")
    page.fill("#userAliasInput", USERNAME)
    page.click('button[type="submit"]')
    page.wait_for_selector("#passwordInput")
    page.fill("#passwordInput", PASSWORD)
    page.click('button[type="submit"]')

    try:
        page.wait_for_selector("#privateDataDiscOkButton", timeout=5000)
        page.click("#privateDataDiscOkButton")
    except:
        pass

    try:
        res = page.wait_for_event("response", timeout=60000, predicate=target_response)
        body = res.text()
    except TimeoutError:
        print("❌ Không bắt được createSessionKey")
        page.screenshot(path="/root/API_Fly/login_timeout.png")
        save_last_crash_time()  # ← lưu thời điểm fail
        return None, browser

    session = getIDvsENC(body)
    if not session:
        save_last_crash_time()
        return None, browser

    with open("session_log_sun.json", "w") as f:
        json.dump(session, f, indent=2)
    with open("/root/API_Fly/cookie1a_sun.json", "w") as f:
        json.dump(page.context.cookies(), f, indent=2)

    # Xóa crash time khi login thành công
    if os.path.exists(STATE_FILE):
        os.remove(STATE_FILE)

    print("✅ Login OK", session)
    return {"page": page, "browser": browser}, browser


if __name__ == "__main__":

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
            # Lưu crash time nếu thoát không phải do logout signal
            if os.path.exists(LOGOUT_SIGNAL) is False:
                save_last_crash_time()
            try:
                browser.close()
            except:
                pass
