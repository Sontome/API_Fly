


from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeoutError
import os
import time
import shutil

STATE_FILE = "statevnd.json"
LOGIN_URL = "https://agents2.vietjetair.com/login"
USERNAME = "AG410513A44ED9"
PASSWORD = "Hlfndma@748282"

# Thời hạn chờ (ms)
SHORT_TIMEOUT = 10_000
LONG_TIMEOUT = 60_000

def remove_state():
    if os.path.exists(STATE_FILE):
        try:
            os.remove(STATE_FILE)
            print("🧹 Đã xóa state.json (clean profile)")
        except Exception as e:
            print("⚠️ Xóa state.json thất bại:", e)

def try_login(page, context):
    """Thử login — trả về True nếu login thành công (detect bằng redirect sau login)."""
    try:
        print("🔐 Vào trang login...")
        page.goto(LOGIN_URL, timeout=LONG_TIMEOUT)
    except PlaywrightTimeoutError:
        print("⚠️ Timeout khi goto. Thử tiếp...")
    except Exception as e:
        print("⚠️ Lỗi khi goto:", e)

    # Thêm fallback: chờ selector xuất hiện (như incognito)
    try:
        page.wait_for_selector('input[name="username"]', timeout=SHORT_TIMEOUT)
    except PlaywrightTimeoutError:
        print("❌ Không thấy input username (timeout).")
        return False

    try:
        print("✍️ Điền thông tin login...")
        page.fill('input[name="username"]', USERNAME, timeout=SHORT_TIMEOUT)
        page.fill('input[name="password"]', PASSWORD, timeout=SHORT_TIMEOUT)
        # click button (dùng click + wait_for_load_state)
        page.click('button[class*="button_login"]', timeout=SHORT_TIMEOUT)
    except PlaywrightTimeoutError:
        print("⚠️ Timeout khi thao tác trên form.")
        return False
    except Exception as e:
        print("⚠️ Lỗi khi fill/click:", e)
        return False

    # Đợi chuyển trang / network idle
    try:
        page.wait_for_load_state("networkidle", timeout=LONG_TIMEOUT)
    except PlaywrightTimeoutError:
        print("⏱️ Chờ networkidle timeout — tiếp tục kiểm tra URL/content...")

    # Kiểm tra xem có phải đã login thành công (ví dụ URL đổi hoặc xuất hiện element đặc trưng)
    current_url = page.url
    print("🔎 URL hiện tại sau login:", current_url)

    # Ở đây dùng heuristic: nếu url không chứa '/login' hoặc xuất hiện element dashboard thì coi như success
    if "/login" not in current_url.lower():
        print("✅ Có vẻ đã login (URL khác /login).")
        return True

    # Thử kiểm tra 1 selector đặc trưng sau login (cần sửa nếu site khác)
    try:
        if page.query_selector("text=Logout") or page.query_selector("text=Đăng xuất"):
            print("✅ Có nút Logout — đã login.")
            return True
    except Exception:
        pass

    print("❌ Chưa login (vẫn ở trang login).")
    return False

with sync_playwright() as p:
    # Tweak arguments để giảm khả năng bị detect
    browser = p.chromium.launch(headless=True,
                                args=[
                                    "--disable-blink-features=AutomationControlled",
                                    "--no-sandbox",
                                    "--disable-dev-shm-usage",
                                    "--disable-infobars",
                                    "--disable-extensions",
                                ])
    # Thử tạo context từ state nếu có
    context = None
    used_state = False

    def make_clean_context():
        ctx = browser.new_context(
            user_agent=("Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36"),
            java_script_enabled=True,
            ignore_https_errors=True,
        )
        # xoá dấu hiệu webdriver
        ctx.add_init_script("() => { Object.defineProperty(navigator, 'webdriver', {get: () => undefined}); }")
        return ctx

    if os.path.exists(STATE_FILE):
        print("🍪 Tìm thấy state.json, thử tạo context từ state...")
        try:
            context = browser.new_context(storage_state=STATE_FILE,
                                          user_agent=("Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                                                      "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36"),
                                          ignore_https_errors=True)
            context.add_init_script("() => { Object.defineProperty(navigator, 'webdriver', {get: () => undefined}); }")
            used_state = True
        except Exception as e:
            print("⚠️ Tạo context từ state thất bại:", e)
            used_state = False

    # Nếu không có state hoặc tạo từ state thất bại thì dùng context sạch (giống incognito)
    if context is None:
        context = make_clean_context()

    page = context.new_page()

    # Thử login với context hiện tại. Nếu thất bại và context từ state, thì xoá state và thử lại với context sạch.
    ok = try_login(page, context)
    if not ok and used_state:
        print("🔁 Thử xoá state.json rồi chạy lại với context sạch (đã detect state gây lỗi).")
        # đóng context cũ
        try:
            context.close()
        except Exception:
            pass
        remove_state()
        context = make_clean_context()
        page = context.new_page()
        ok = try_login(page, context)

    # Nếu vẫn fail, chụp screenshot để debug và lưu HTML
    if not ok:
        try:
            screenshot_path = "debug_fail.png"
            html_path = "debug_fail.html"
            page.screenshot(path=screenshot_path, full_page=True)
            with open(html_path, "w", encoding="utf-8") as f:
                f.write(page.content())
            print(f"📸 Đã lưu screenshot -> {screenshot_path} và HTML -> {html_path} để debug.")
        except Exception as e:
            print("⚠️ Lỗi khi lưu debug artifacts:", e)
        print("💀 Login thất bại. Kiểm tra screenshot/HTML hoặc thử chạy manual (headful) để xem what's going on.")
    else:
        # Lưu state (cookies + localStorage) vào file
        try:
            context.storage_state(path=STATE_FILE)
            print("💾 Đã lưu state vào", STATE_FILE)
        except Exception as e:
            print("⚠️ Lỗi khi lưu state:", e)

    # Giải phóng
    try:
        context.close()
    except Exception:
        pass
    try:
        browser.close()
    except Exception:
        pass

    print("🏁 Xong lượt chạy.")

    
   



