import aiohttp
import json
import asyncio
from datetime import datetime
import os

# ====== ⚙️ CONFIG ====== #
CONFIG_GIA_FILE = "config_gia_vna.json"
COOKIE_FILE = "statevna.json"
DEFAULT_CONFIG_GIA = {
    "PHI_XUAT_VE_1CH": 30000,
    "PHI_XUAT_VE_2CH": 10000
}

# ====== 🧠 UTIL ====== #
async def is_json_response(text):
    try:
        json.loads(text)
        return True
    except ValueError:
        return False

def format_time(time_int):
    time_str = str(time_int).zfill(4)
    return f"{time_str[:2]}:{time_str[2:]}"

def to_price(price):
    rounded = round(price / 100) * 100
    str_price = f"{rounded:,}".replace(",", ".")
    return f"{str_price}w"

def format_date(ngay_str):
    if "-" in ngay_str and len(ngay_str) == 10:
        return ngay_str.replace("-", "")
    elif len(ngay_str) == 8:
        return f"{ngay_str[6:8]}/{ngay_str[4:6]}"
    else:
        
        return None

def create_session_powercall():
    return datetime.now().strftime("%Y%m%d_%H%M%S")

# ====== 🔧 LOAD CONFIG ====== #
def load_config_gia():
    if os.path.exists(CONFIG_GIA_FILE):
        try:
            with open(CONFIG_GIA_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                config = {
                    "PHI_XUAT_VE_1CH": int(data.get("PHI_XUAT_VE_1CH", DEFAULT_CONFIG_GIA["PHI_XUAT_VE_1CH"])),
                    "PHI_XUAT_VE_2CH": int(data.get("PHI_XUAT_VE_2CH", DEFAULT_CONFIG_GIA["PHI_XUAT_VE_2CH"]))
                }
                print("📥 Đã load config:")
                for k, v in config.items():
                    print(f"  - {k}: {v:,}đ")
                return config
        except Exception as e:
            print("❌ Lỗi đọc file config:", e)

    print("⚠️ Dùng config mặc định:")
    for k, v in DEFAULT_CONFIG_GIA.items():
        print(f"  - {k}: {v:,}đ")
    return DEFAULT_CONFIG_GIA.copy()

config_gia = load_config_gia()

# ====== 💰 XỬ LÝ GIÁ ====== #
def price_add(sochieu, config_gia: dict) -> int:
    return config_gia["PHI_XUAT_VE_2CH"] if str(sochieu) == "2" else config_gia["PHI_XUAT_VE_1CH"]

# ====== 🔍 LỌC VÉ ====== #
async def doc_va_loc_ve_re_nhat(data, session, headers, form_data):
    fares = data.get("FARES", [])
    def loc_fare_vn(fare): return fare.get("IT") == "VFR" and fare.get("CA") == "VN" and fare.get("VA") == "0"
    def loc_fare_vn_noituyen(fare): return fare.get("IT") == "VFR" and fare.get("CA") == "VN" and fare.get("VA") == "1"
    def loc_fare_vn_1pc(fare): return fare.get("IT") == "ADT" and fare.get("CA") == "VN" and fare.get("VA") == "0"
    def loc_fare_vn_1pc_noituyen(fare): return fare.get("IT") == "ADT" and fare.get("CA") == "VN" and fare.get("VA") == "1"
    fares_nt = list(filter(loc_fare_vn_noituyen, fares))
    fares_thang = list(filter(loc_fare_vn, fares))
    fares_thang_1pc = list(filter(loc_fare_vn_1pc, fares))
    fares_nt_1pc = list(filter(loc_fare_vn_1pc_noituyen, fares))
    if not fares_thang:
        if not fares_nt:
            if not fares_thang_1pc:
                if not fares_nt_1pc:
                    print("❌ Không có vé phù hợp điều kiện VN + VFR")
                    return None
                return min(fares_nt_1pc, key=lambda f: int(f.get("MA", 999999999)))
            return min(fares_thang_1pc, key=lambda f: int(f.get("MA", 999999999)))
        
        return min(fares_nt, key=lambda f: int(f.get("MA", 999999999)))
    return min(fares_thang, key=lambda f: int(f.get("MA", 999999999)))

# ====== 📄 IN THÔNG TIN VÉ ====== #
def thong_tin_ve(data, sochieu, name):
    if not data:
        return "❌ Không có dữ liệu vé!"

    hang = "Vietnam Airlines"
    chang_bay = data.get("AP", "??-??")
    kieubay = "Bay Thẳng" if data.get("VA") == "0" else "Nối Tuyến"
    chieu_text = "1 Chiều" if str(sochieu) == "1" else "Khứ hồi"
    if data.get('IT')=='ADT':
        hanhly= "12kg xách tay, 23kg ký gửi, giá vé ="
    else:
        hanhly= "12kg xách tay, 46kg ký gửi, giá vé ="
    thongtin_chang = ""
    for s in data.get("SK", []):
        ga_di = s.get("DA", "??")
        ga_den = s.get("AA", "??")
        gio_di = format_time(s.get("DT", 0))
        ngay_di = format_date(str(s.get("DD", "")))
        ga_noi = s.get("VA1", "??")
        if ga_noi != "??":
            thongtin_chang += f"\n {ga_di}-{ga_noi}-{ga_den} {gio_di} ngày {ngay_di}"
        else:
            thongtin_chang += f"\n {ga_di}-{ga_den} {gio_di} ngày {ngay_di}"

    gia_ve = int(data.get("MA", 0)) + price_add(sochieu, config_gia)
    gia_str = to_price(gia_ve)
    return f"""👤 Tên Khách: {name}
Hãng: {hang} - Chặng bay: {chang_bay} | {chieu_text} ({kieubay})  
{thongtin_chang}
{hang} {hanhly} {gia_str}
"""

# ====== 🚀 CALL API POWERCALL ====== #
async def get_vna_flight_options(trip, dep0, arr0, depdate0, depdate1, retdate, sochieu, activedVia="0"):
    with open(COOKIE_FILE, "r", encoding="utf-8") as f:
        raw_cookies = json.load(f)["cookies"]
    cookies = {c["name"]: c["value"] for c in raw_cookies}
    session_key = create_session_powercall()

    headers = {
        "accept": "application/json, text/javascript, */*; q=0.01",
        "accept-language": "vi-VN,vi;q=0.9,en-US;q=0.8,en;q=0.7",
        "content-type": "application/x-www-form-urlencoded; charset=UTF-8",
        "x-requested-with": "XMLHttpRequest",
        "Referer": "https://wholesale.powercallair.com/booking/findSkdFareGroup.lts?mode=v3"
    }

    form_data = {
        'mode': 'v3',
        'activedCar': 'VN',
        'activedCLSS1': 'M,E,S,H,R,L,U,I,Z,W,J,K,T,B,A,N,Q,Y,V',
        'activedCLSS2': 'M,E,S,H,R,L,U,I,Z,W,J,K,T,B,A,N,Q,Y,V',
        'activedAirport': f"{dep0}-{arr0}-{arr0}-{dep0}",
        
        'activedVia': '0',
        'activedStatus': 'OK,HL',
        'activedIDT': 'ADT,VFR',
        'minAirFareView': '10000',
        'maxAirFareView': '1500000',
        'page': '1',
        'sort': 'priceAsc',
        'interval01Val': '1000',
        'interval02Val': '1000',
        'filterTimeSlideMin0': '5',
        'filterTimeSlideMax0': '2355',
        'filterTimeSlideMin1': '5',
        'filterTimeSlideMax1': '2345',
        'trip': trip,
        'dayInd': 'N',
        'strDateSearch': depdate0[:6],
        'daySeq': '0',
        'dep0': dep0,
        'dep1': arr0,
        'arr0': arr0,
        'arr1': dep0,
        'depdate0': depdate0,
        'depdate1': depdate1,
        'retdate': retdate,
        'comp': 'Y',
        'adt': '1',
        'chd': '0',
        'inf': '0',
        'car': 'YY',
        'idt': 'ALL',
        'isBfm': 'Y',
        'CBFare': 'YY',
        'miniFares': 'Y',
        'sessionKey': session_key
    }

    if str(sochieu) == "1":
        form_data.update({
            "activedAirport": f"{dep0}-{arr0}",
            "trip": "OW",
            "dep1": "",
            "depdate1": "",
            "interval02Val": "",
            "retdate": "",
            "activedCLSS2": ""
        })

    connector = aiohttp.TCPConnector(ssl=False)

    async def call_vna_api(session,form_data):
        async with session.post(
            "https://wholesale.powercallair.com/booking/findSkdFareGroup.lts?viewType=xml",
            headers=headers, data=form_data
        ) as response:
            
            text = await response.text()
            #print(text)
            if response.status != 200:
                print("❌ Lỗi gọi API:", response.status)
                return None, None
            if not await is_json_response(text):
                print("khong phải json")
                return "INVALID_COOKIE", text
            try:
                print(" json")
                result=json.loads(text)
                return "OK", result
            except json.JSONDecodeError:
                print("khong decode json được")
                return "INVALID_JSON", text
    
    async with aiohttp.ClientSession(cookies=cookies, connector=connector) as session:
        status, result = await call_vna_api(session,form_data)
        print("gọi api lần 1")
        status, result = await call_vna_api(session,form_data)
        print("gọi api lần 2")
        fares = result.get("FARES", [])
        def loc_fare_vn(fare): return fare.get("IT") == "VFR" and fare.get("CA") == "VN" and fare.get("VA") == "0"
        
        def loc_fare_vn_1pc(fare): return fare.get("IT") == "ADT" and fare.get("CA") == "VN" and fare.get("VA") == "0"
        
        
        fares_thang = list(filter(loc_fare_vn, fares))
        fares_thang_1pc = list(filter(loc_fare_vn_1pc, fares))
        form_data.update({
            "activedVia": "1"



        })
        if not fares_thang and not fares_thang_1pc :
            print("gọi api lần 3 do ko có bay thẳng")
            status, result = await call_vna_api(session,form_data)

        


        #print(result)
        
    if status == "OK":
        print("lưu vào test.json")
        with open("test.json", "w", encoding="utf-8") as f:
            json.dump(result, f, ensure_ascii=False, indent=4)

    return await doc_va_loc_ve_re_nhat(result, session, headers, form_data)

# ====== 🧪 HÀM API CHÍNH ====== #
async def api_vna(dep0, arr0, depdate0, depdate1="", name="khách lẻ", sochieu="1"):
    trip = "RT" if sochieu == "2" else "OW"
    if sochieu == "1": depdate1 = ""
    print(f"🛫 Tìm vé cho: {name} | Số chiều: {sochieu}")
    print(f"From {dep0} to {arr0} | Ngày đi: {depdate0} | Ngày về: {depdate1 if depdate1 else '⛔ Không có'}")

    result = await get_vna_flight_options(
        trip=trip, dep0=dep0, arr0=arr0,
        depdate0=format_date(depdate0),
        depdate1=format_date(depdate1),
        retdate=format_date(depdate1),
        sochieu=sochieu
    )
    print(result)
    return thong_tin_ve(result, sochieu, name)