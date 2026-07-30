from camoufox.sync_api import Camoufox
from playwright.sync_api import TimeoutError
import json
import xml.etree.ElementTree as ET
import threading
import time
import os
import random
from queue import Queue
from dotenv import load_dotenv

load_dotenv()

USERNAME = os.getenv("SUN_1A_USERNAME")
PASSWORD = os.getenv("SUN_1A_PASSWORD")

LOGOUT_SIGNAL = "/tmp/logout1asun"

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


def human_type(page, selector, text):
    """Type như người thật: click, hover, delay ngẫu nhiên giữa các ký tự"""
    locator = page.locator(selector)
    locator.hover()
    time.sleep(random.uniform(0.2, 0.5))
    locator.click()
    time.sleep(random.uniform(0.1, 0.3))
    for char in text:
        page.keyboard.type(char, delay=random.randint(80, 180))
        # Thỉnh thoảng dừng lâu hơn như người thật
        if random.random() < 0.1:
            time.sleep(random.uniform(0.2, 0.5))


def human_click(page, selector):
    """Click với mouse move tự nhiên"""
    locator = page.locator(selector)
    box = locator.bounding_box()
    if box:
        # Move đến gần button trước
        page.mouse.move(
            box["x"] + box["width"] / 2 + random.randint(-5, 5),
            box["y"] + box["height"] / 2 + random.randint(-5, 5),
        )
        time.sleep(random.uniform(0.1, 0.3))
    locator.click()


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


def login():
    with Camoufox(
        headless=True,
        os="windows",  # giả lập Windows OS fingerprint
        geoip=True,
    ) as browser:

        page = browser.new_page()

        def target_response(res):
            return "createSessionKey" in res.url

        url = "https://www.accounts.amadeus.com/LoginService/authorizeAngular?service=ARD_9G-DC&client_id=1ASIXARD9GDC&LANGUAGE=GB&redirect_uri=https%3A%2F%2Ftc110.resdesktop.altea.com%2Fapp_ard%2Fapf%2Finit%2Flogin"

        page.goto(url)
        time.sleep(random.uniform(1.0, 2.0))  # đợi page load tự nhiên

        page.wait_for_selector("#userAliasInput")
        time.sleep(random.uniform(0.5, 1.0))

        human_type(page, "#userAliasInput", USERNAME)
        time.sleep(random.uniform(0.5, 1.0))

        human_click(page, 'button[type="submit"]')
        time.sleep(random.uniform(1.5, 2.5))

        page.wait_for_selector("#passwordInput")
        time.sleep(random.uniform(0.5, 1.0))

        human_type(page, "#passwordInput", PASSWORD)
        time.sleep(random.uniform(0.5, 1.0))

        human_click(page, 'button[type="submit"]')
        time.sleep(random.uniform(1.5, 2.5))

        try:
            page.wait_for_selector("#privateDataDiscOkButton", timeout=5000)
            human_click(page, "#privateDataDiscOkButton")
        except:
            pass

        try:
            res = page.wait_for_event(
                "response", timeout=60000, predicate=target_response
            )
            body = res.text()
        except TimeoutError:
            print("❌ Không bắt được createSessionKey")
            page.screenshot(path="/root/API_Fly/login_timeout.png")
            return None, browser

        session = getIDvsENC(body)
        if not session:
            return None, browser

        with open("session_log_sun.json", "w") as f:
            json.dump(session, f, indent=2)

        with open("cookie1a_sun.json", "w") as f:
            json.dump(page.context.cookies(), f, indent=2)

        print("✅ Login OK", session)

        return {"page": page, "browser": browser}, browser


if __name__ == "__main__":

    result, browser = login()

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
                            "#eusermanagement_logout_lock_PASSWORD_id_input", PASSWORD
                        )
                        page.click("#eusermanagement_logout_lock_save_id")
                        print("Unlock OK")
                    except TimeoutError:
                        pass

            time.sleep(1)

    finally:
        try:
            browser.close()
        except:
            pass
