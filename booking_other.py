
import os
import httpx
from playwright.sync_api import TimeoutError,sync_playwright
from backend_supabase_kakao import add_kakao_pnr

# =========================
# CONFIG
# =========================






STATE_FILE = "statevna.json"
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "7843918695:AAGnIVDjJV52Citq0mn8zOQ0_Wr0MmD45qA")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "-1002520783135")

def send_mess_sync_safe(message: str) -> bool:
    """
    Gửi Telegram trực tiếp từ booking_other.
    Chỉ trả True khi Telegram trả status 200 và trường `ok=true`.
    """
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": message,
        "parse_mode": "HTML"
    }

    try:
        with httpx.Client(timeout=20.0) as client:
            res = client.post(url, json=payload)

        if res.status_code != 200:
            print(f"❌ Lỗi gửi Telegram HTTP {res.status_code}: {res.text}")
            return False

        try:
            body = res.json()
        except Exception:
            print(f"❌ Telegram trả dữ liệu không phải JSON: {res.text}")
            return False

        if not body.get("ok", False):
            print(f"❌ Telegram API không ok: {body}")
            return False

        return True
    except Exception as e:
        print(f"💥 Exception khi gửi Telegram: {e}")
        return False

# =========================
# ROUTE
# =========================
def fill_route(page, from_code, to_code):
    print(f"📍 Route: {from_code} -> {to_code}")

    korea_airport_codes = {
        "ICN", "PUS", "GMP", "CJU", "CJJ", "TAE", "KWJ",
        "MWX", "RSU", "USN", "KPO", "YNY", "WJU", "HIN"
    }

    # Nếu nơi đi không thuộc Hàn Quốc, chuyển qua chế độ overseas.
    if from_code not in korea_airport_codes:
        page.check("#areasoto")

        # nơi đi chọn bằng popup city picker
        select_destination_city(
            page,
            from_code,
            trigger_selector="#dep0_text",
            value_selector="#dep0"
        )

        # nơi đến chọn bằng select thường
        page.select_option("#arr0", value=to_code)
    else:
        # nơi đi
        page.select_option("#dep0", value=from_code)

        # nơi đến
        select_destination_city(page, to_code)

    print("✅ Hoàn tất route")

def select_destination_city(page, city_code, trigger_selector="#arr0_text", value_selector="#arr0"):
    print(f"🎯 Chọn điểm: {city_code}")

    page.click(trigger_selector)

    popup_input = page.locator("#strAirCity")
    popup_input.wait_for(state="visible", timeout=5000)

    popup_input.fill("")
    popup_input.fill(city_code)

    page.wait_for_timeout(300)
    popup_input.press("Enter")

    # selector chuẩn: airport code đầu tiên phải là HAN
    result = page.locator(
        f"a[onclick^=\"setAirCity('{city_code}'\"]"
    ).first

    result.wait_for(state="visible", timeout=5000)
    result.click()

    page.wait_for_function(
        f"document.querySelector('{value_selector}').value === '{city_code}'"
    )

    print("✅ Đã chọn điểm")
def fill_depart_date(page, date_text , date_text_dep1 = ""):
    """
    date_text format: YYYY/MM/DD
    ví dụ: 2026/05/21
    """

    print(f"📅 Chọn ngày đi: {date_text}")

    date_input = page.locator("#depdate0_value")

    date_input.wait_for(state="visible", timeout=5000)

    # clear rồi nhập
    date_input.fill("")
    date_input.fill(date_text)

    # trigger change / blur cho web cổ
    #date_input.press("Tab")

    # xác nhận đã set xong
    page.wait_for_function(
        "(el,val)=>el.value===val",
        arg=[date_input.element_handle(), date_text]
    )
    print("✅ Đã nhập ngày đi")
    if date_text_dep1 :
        print(f"📅 Chọn ngày về: {date_text_dep1}")

        date_input = page.locator("#depdate1_value")

        date_input.wait_for(state="visible", timeout=5000)

        # clear rồi nhập
        date_input.fill("")
        date_input.fill(date_text_dep1)

        # trigger change / blur cho web cổ
        #date_input.press("Tab")
        print("✅ Đã nhập ngày về")
    else :
        page.click("#check_OW")
        print("✅ Đã tích OW")
def fill_passenger_count(page, adt, chd, inf):
    print(f"👥 Chọn số khách - ADT:{adt}, CHD:{chd}, INF:{inf}")

    page.select_option("#adt_value", value=str(adt))
    page.select_option("#chd_value", value=str(chd))
    page.select_option("#inf_value", value=str(inf))

    page.wait_for_function(
        """([adt, chd, inf]) => {
            return document.querySelector('#adt_value')?.value === adt
                && document.querySelector('#chd_value')?.value === chd
                && document.querySelector('#inf_value')?.value === inf;
        }""",
        arg=[str(adt), str(chd), str(inf)]
    )
    print("✅ Đã chọn số khách")
def submit_search(page):
    print("🚀 Bấm tìm chuyến bay...")

    btn = page.locator("a[onclick=\"goSkdFare('L');\"]")

    btn.wait_for(state="visible", timeout=5000)

    btn.click()

    # chờ web load kết quả
    

    print("✅ Đã submit tìm chuyến") 
    wait_loading_finish(page)  
def wait_loading_finish(page):
    print("⏳ Chờ loading xong...")

    # đợi network trước
    page.wait_for_load_state("networkidle")

    # đợi mấy popup/banner/loading hay gặp biến mất
    selectors = [
        ".loading",
        ".layerPop",
        ".banner",
        ".dimmed",
        ".overlay",
        ".ui-widget-overlay"
    ]

    for css in selectors:
        try:
            page.locator(css).wait_for(state="hidden", timeout=2000)
        except:
            pass

    print("✅ Hết loading")

def select_airline(page, airline_code="KE"):
    print(f"✈️ Chọn hãng bay: {airline_code}")
    #wait_loading_finish(page)
    # mở tab filter hãng bay
    filter_box = page.locator("#carFilter")
    filter_box.wait_for(state="visible", timeout=5000)
    filter_box.click()

    # đợi checkbox hãng hiện ra
    checkbox = page.locator(
        f'#carFilter input[type="checkbox"][value="{airline_code}"]'
    )

    checkbox.wait_for(state="visible", timeout=5000)

    # nếu chưa tick thì tick
    if not checkbox.is_checked():
        checkbox.check(force=True)
    page.wait_for_load_state("networkidle")
    print("✅ Đã chọn hãng bay") 
def select_fare(page, fare_id:str):
    wait_loading_finish(page) 
    print(f"🎯 Chọn fare ID: {fare_id}")

    page.evaluate(f"faresSelect('{fare_id}')")

    page.wait_for_load_state("networkidle")

    print("✅ Đã chọn fare")
def reserve_selected_fare(page, fareindex: str,adt=1,chd=0,inf=0):
    wait_loading_finish(page)

    print(f"🛒 Tiến hành đặt chỗ fare index: {fareindex}")

    # đợi function tồn tại
    page.wait_for_function(
        "typeof reserveFare === 'function'"
    )

    # đợi nút reserve xuất hiện
    reserve_btn = page.locator('a[href^="javascript:reserveFare"]')
    reserve_btn.first.wait_for(state="visible", timeout=10000)

    # nghỉ nhẹ cho DOM ổn định
    page.wait_for_timeout(500)

    # chạy script
    current_url = page.url
    page.evaluate(
        """
        ({idx, adt, chd, inf}) => {
            reserveFare(idx, '0', 9, adt, chd, inf, '', '');
        }
        """,
        {
            "idx": fareindex,
            "adt": adt,
            "chd": chd,
            "inf": inf
        }
    )

    # reserveFare xử lý async, cần đợi điều hướng thật sự diễn ra.
    try:
        page.wait_for_function(
            "(oldUrl) => window.location.href !== oldUrl",
            arg=current_url,
            timeout=20000
        )
        page.wait_for_load_state("domcontentloaded")
        page.wait_for_load_state("networkidle")
    except TimeoutError:
        # Fallback: có thể web không đổi URL nhưng form khách đã render.
        page.locator("#paxLastNameEn1").wait_for(state="visible", timeout=15000)

    wait_loading_finish(page) 
    print("✅ Đã chạy reserveFare")
def fill_customer(page, customers):
    """
    customers: list[dict]
    Mỗi khách gồm: type, gender, firstname, lastname
    Ví dụ:
    [
        {"type": "ADT", "gender": "M", "firstname": "AN", "lastname": "NGUYEN" ,"birthday" :"20000130"},
        {"type": "CHD", "gender": "F", "firstname": "BINH", "lastname": "TRAN","birthday" :"20000130"}
    ]
    """
    print(f"🧾 Bắt đầu điền thông tin {len(customers)} khách")

    for idx, customer in enumerate(customers, start=1):
        raw_gender = str(customer.get("gender", "NAM")).strip().upper()
        gender_map = {
            "NAM": "M",
            "MALE": "M",
            "M": "M",
            "NU": "F",
            "NỮ": "F",
            "FEMALE": "F",
            "F": "F"
        }
        gender = gender_map.get(raw_gender, "M")

        first_name = str(customer.get("firstname", "")).strip().upper()
        last_name = str(customer.get("lastname", "")).strip().upper()
        pax_type = str(customer.get("type", "")).strip().upper()
        birthday = str(customer.get("birthday", "")).strip()
        print(
            f"👤 Khách {idx} - TYPE:{pax_type or 'N/A'}, "
            f"GENDER:{gender}, LAST:{last_name}, FIRST:{first_name}"
        )

        gender_selector = f"#paxGenderRadio{gender}{idx}"
        last_name_selector = f"#paxLastNameEn{idx}"
        first_name_selector = f"#paxFirstNameEn{idx}"
        birth_gender_selector = f"#paxBirth{idx}"

        page.locator(gender_selector).wait_for(state="visible", timeout=10000)
        page.evaluate("""
            (selector) => {
                const el = document.querySelector(selector);
                if (el) el.click();
            }
            """, gender_selector)

        # page.wait_for_function(
        #     "(selector, val) => document.querySelector(selector)?.value === val",
        #     arg=[hidden_gender_selector, gender]
        # )
        print("đã tích chọn gender")
        page.click(last_name_selector)
        # page.keyboard.press("Control+A")
        # page.keyboard.press("Backspace")
        page.type(last_name_selector, last_name, delay=1)

        page.click(first_name_selector)
        # page.keyboard.press("Control+A")
        # page.keyboard.press("Backspace")
        page.type(first_name_selector, first_name, delay=1)
        page.click(birth_gender_selector)
        # page.keyboard.press("Control+A")
        # page.keyboard.press("Backspace")
        page.type(birth_gender_selector, birthday, delay=1)

    print("✅ Đã điền xong thông tin khách")
def fill_phone(
    page,
    phone="010-2451-1790",
    from_code="",
    to_code="",
    dep_date="",
    arr_date="",
    customers=None,
    phonekakao=""
):
    print(f"📞 Điền số điện thoại: {phone}")

    parts = str(phone).strip().split("-")
    if len(parts) != 3:
        parts = ["010", "2451", "1790"]

    mid = parts[1]
    last = parts[2]

    page.locator('input[name="revMobile02"]').wait_for(state="visible", timeout=10000)
    page.fill('input[name="revMobile02"]', "")
    page.fill('input[name="revMobile02"]', mid)

    page.locator('input[name="revMobile03"]').wait_for(state="visible", timeout=10000)
    page.fill('input[name="revMobile03"]', "")
    page.fill('input[name="revMobile03"]', last)
    page.fill('input[name="stayPhone"]', "01035463396")
    for checkbox_id in ("#ruleAgree1", "#ruleAgree2", "#ruleAgree3"):
        checkbox = page.locator(checkbox_id)
        checkbox.wait_for(state="visible", timeout=10000)
        if not checkbox.is_checked():
            checkbox.check(force=True)

    finish_btn = page.locator('[onclick="finishPaxInfo();"]').first
    finish_btn.wait_for(state="visible", timeout=10000)
    page.wait_for_load_state("networkidle")
    wait_loading_finish(page)

    # Tránh treo ở Locator.click trên site cũ: dùng handler dialog + trigger JS trực tiếp.
    def _dialog_handler(dialog):
        print(f"📣 Dialog sau khi bấm hoàn tất: {dialog.type} - {dialog.message}")
        dialog.accept()

    page.on("dialog", _dialog_handler)
    try:
        triggered = page.evaluate(
            """
            () => {
                const btn = document.querySelector('[onclick="finishPaxInfo();"]');
                if (btn) {
                    btn.click();
                    return "button-clicked";
                }
                if (typeof finishPaxInfo === "function") {
                    finishPaxInfo();
                    return "function-called";
                }
                return "not-found";
            }
            """
        )
        print(f"ℹ️ Trigger finishPaxInfo: {triggered}")
        if triggered == "not-found":
            raise RuntimeError("Không tìm thấy nút/hàm finishPaxInfo để submit.")

        # cho JS submit/dialog xử lý xong
        page.wait_for_timeout(1200)
    finally:
        page.remove_listener("dialog", _dialog_handler)

    # Sau khi xác nhận, web chuyển sang màn hình đặt vé thành công.
    page.wait_for_load_state("domcontentloaded")
    page.wait_for_load_state("networkidle")

    booking_code = ""
    total_fee = ""
    try:
        booking_code_cell = page.locator(
            "xpath=//tr[.//img[@alt='예약번호']]//td[1]"
        ).first
        booking_code_cell.wait_for(state="visible", timeout=15000)
        booking_code = booking_code_cell.inner_text().strip()

        # total_fee_cell = page.locator(
        #     "xpath=//tr[.//img[@alt='Total fee']]//td[1]"
        # ).first
        # total_fee_cell.wait_for(state="visible", timeout=15000)
        # total_fee = total_fee_cell.inner_text().strip()
    except TimeoutError:
        print("⚠️ Không tìm thấy đủ thông tin mã giữ chỗ / tổng tiền trên trang kết quả.")

    route = f"{from_code}-{to_code}".strip("-")
    date_range = dep_date or ""
    if arr_date:
        date_range = f"{date_range} - {arr_date}" if date_range else arr_date
    route_line = f"{route} {date_range}".strip()

    passenger_lines = []
    for customer in customers or []:
        full_name = f"{str(customer.get('lastname', '')).strip().upper()} {str(customer.get('firstname', '')).strip().upper()}".strip()
        if full_name:
            passenger_lines.append(full_name)

    detail_lines = [line for line in [route_line, *passenger_lines] if line]
    detail_text = "\n".join(detail_lines)

    if booking_code or total_fee:
        if booking_code and phonekakao:
            first_customer_name = ""
            if customers:
                first_customer = customers[0]
                first_customer_name = (
                    f"{str(first_customer.get('lastname', '')).strip().upper()} "
                    f"{str(first_customer.get('firstname', '')).strip().upper()}"
                ).strip()
            try:
                add_kakao_pnr(
                    phone=str(phonekakao).strip(),
                    name=first_customer_name,
                    pnr=booking_code
                )
                print(
                    f"✅ Đã add_kakao_pnr | phone={phonekakao} | name={first_customer_name} | pnr={booking_code}"
                )
            except Exception as e:
                print(f"❌ Lỗi add_kakao_pnr: {e}")

        mess = f"Đã giữ vé {booking_code} thành công"
        if detail_text:
            mess = f"{mess}\n{detail_text}"
        sent_ok = send_mess_sync_safe(mess)
        if sent_ok:
            print(f"📨 Đã gửi thông báo: {mess}")
        else:
            print(f"❌ Gửi Telegram thất bại: {mess}")
    else:
        mess = "Giữ vé thất bại"
        if detail_text:
            mess = f"{mess}\n{detail_text}"
        print("⚠️ Không lấy được dữ liệu mã giữ chỗ / tổng tiền.")
        sent_ok = send_mess_sync_safe(mess)
        if sent_ok:
            print(f"📨 Đã gửi thông báo: {mess}")
        else:
            print(f"❌ Gửi Telegram thất bại: {mess}")
    print("✅ Đã điền phone, tick 3 điều khoản và bấm hoàn tất")
# =========================
# MAIN
# =========================
def booking_other(hang,from_code, to_code, dep_date, arr_date="", index="", customer="", phonekakao="", wait_for_manual_close=False):
    type_order = {"ADT": 0, "CHD": 1, "INF": 2}
    normalized_customer = []

    for item in customer or []:
        current = dict(item)
        current_type = str(current.get("type", "ADT")).strip().upper()
        current["type"] = current_type if current_type in type_order else "ADT"
        normalized_customer.append(current)

    type_count = {"ADT": 0, "CHD": 0, "INF": 0}
    for item in normalized_customer:
        type_count[item["type"]] += 1

    sorted_customer = sorted(
        normalized_customer,
        key=lambda x: (type_order.get(x["type"], 99), -type_count.get(x["type"], 0))
    )

    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=True,
            slow_mo=500
        )

        context = browser.new_context(
            storage_state=STATE_FILE
        )

        page = context.new_page()

        # vào thẳng trang search luôn
        page.goto("https://wholesale.powercallair.com/b2bIndex.lts")

        page.wait_for_load_state("networkidle")

        print("✅ Đã login bằng state")

        # chạy tiếp luôn
        fill_route(page, from_code, to_code)
        fill_passenger_count(
            page,
            adt=type_count["ADT"],
            chd=type_count["CHD"],
            inf=type_count["INF"]
        )
        fill_depart_date(page, dep_date, arr_date)
        submit_search(page)
        select_airline(page=page,airline_code=hang)
        #input("enter")
        select_fare(page=page,fare_id=str(index))
        #input("enter")
        reserve_selected_fare(
            page=page,
            fareindex=str(index),
            adt=type_count["ADT"],
            chd=type_count["CHD"],
            inf=type_count["INF"]
        )
        # Ví dụ gọi hàm điền khách sau khi màn hình passenger đã hiển thị:
        fill_customer(page, sorted_customer)
        fill_phone(
            page,
            from_code=from_code,
            to_code=to_code,
            dep_date=dep_date,
            arr_date=arr_date,
            customers=sorted_customer,
            phonekakao=phonekakao
        )
        # chỉ giữ browser mở khi cần debug thủ công
        if wait_for_manual_close:
            input("Nhấn Enter khi muốn tắt browser...")

        browser.close()


# if __name__ == "__main__":
#     booking_other(
#         hang="7C",
#         from_code="ICN",
#         to_code="HAN",
#         dep_date="2026/08/18",
#         arr_date="2026/08/20",
#         index="16",
#         customer=[
#             {"type": "ADT", "gender": "NAM", "firstname": "VAN A", "lastname": "NGUYEN","birthday" :"20000130"}
            
#             # {"type": "CHD", "gender": "NAM", "firstname": "BE C", "lastname": "LE"},
#             # {"type": "INF", "gender": "NU", "firstname": "BABY D", "lastname": "PHAM"},
#             # {"type": "ADT", "gender": "NAM", "firstname": "THI B", "lastname": "TRAN"}
#         ],
#         wait_for_manual_close=True
#     )
