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
        return f"{ngay_str[6:8]}/{ngay_str[4:6]}/{ngay_str[:4]}"
    else:
        
        return None

def create_session_powercall():
    print(datetime.now().strftime("%Y%m%d_%H"))
    return datetime.now().strftime("%Y%m%d_%H")

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



# ====== 🔍 LỌC VÉ ====== #
async def doc_va_loc_ve_re_nhat(data):
    fares = data.get("FARES", [])
    print(fares)
    def loc_fare_vn(fare): return fare.get("CA") == "VN"  and (fare.get("OC") != "KE")
    
    
    fares_thang = list(filter(loc_fare_vn, fares))
    
    if not fares_thang:
        
        print("❌ Không có vé phù hợp điều kiện VN + VFR")
        return {
        "status_code": 200,
        "body" : "null"
        }
        
    return {
        "status_code": 200,
        "body" :fares_thang
    }


async def get_vna_flight_options( dep0, arr0, depdate0):
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
        'activedCLSS2': '',
        'activedAirport': f"{dep0}-{arr0}",
        
        'activedVia': '0',
        'activedStatus': 'OK,HL',
        'activedIDT': 'ADT,VFR',
        'minAirFareView': '10000',
        'maxAirFareView': '1500000',
        'page': '1',
        'sort': 'priceAsc',
        'interval01Val': '1000',
        'interval02Val': '',
        'filterTimeSlideMin0': '5',
        'filterTimeSlideMax0': '2355',
        'filterTimeSlideMin1': '5',
        'filterTimeSlideMax1': '2345',
        'trip':"OW",
        'dayInd': 'N',
        'strDateSearch': depdate0[:6],
        'daySeq': '0',
        'dep0': dep0,
        'dep1': "",
        'arr0': arr0,
        'arr1': "",
        'depdate0': depdate0,
        'depdate1': "",
        'retdate': "",
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

    

    connector = aiohttp.TCPConnector(ssl=False)
    async def warm_up_session(session):
        url = "https://wholesale.powercallair.com/booking/findSkdFareGroup.lts"
        try:
            async with session.get(url) as resp:
                print("🔥 Warm-up done, status:", resp.status)
        except Exception as e:
            print("Warm-up lỗi:", e)
    async def call_vna_api(session,form_data):
        url = "https://wholesale.powercallair.com/booking/findSkdFareGroup.lts?viewType=xml"
        try:
            async with session.post(url, headers=headers, data=form_data) as response:
                text = await response.text()
                print(text[:100])
                if response.status != 200:
                    print("❌ Status:", response.status)
                    return "HTTP_ERROR", text
                if not await is_json_response(text):
                    print("❗Không phải JSON, có thể là HTML")
                    return "INVALID_RESPONSE", text
                data = json.loads(text)
                if isinstance(data, dict) and data.get("resultCode") == "-9999":
                    print("❌ JSON báo lỗi resultCode -9999")
                    return "ERROR_RESULT", data
                return "OK", json.loads(text)
        except Exception as e:
            print("💥 Lỗi gọi API:", e)
            return "EXCEPTION", str(e)
    
    async with aiohttp.ClientSession(cookies=cookies, connector=connector) as session:
        await warm_up_session(session)
        for attempt in range(2):
            status, result = await call_vna_api(session, form_data)
            print(f"🎯 Gọi API lần {attempt+1} =>", status)
            if status == "OK":
                break
        
        fares = result.get("FARES", [])
        
        def loc_fare_vn(fare): return fare.get("CA") == "VN" 
        
    
        
        
        fares_thang = list(filter(loc_fare_vn, fares))
       
        form_data.update({
            "activedVia": "1"



        })
        if not fares_thang  :
            print("gọi api lần 3 do ko có bay thẳng")
            status, result = await call_vna_api(session,form_data)

        


        
        
    #print(result)
    kq= await doc_va_loc_ve_re_nhat(result)
    
    return kq

# ====== 🧪 HÀM API CHÍNH ====== #

async def api_vna_v2(dep0, arr0, depdate0):
    
    
    
    print(f"From {dep0} to {arr0} | Ngày đi: {format_date(depdate0)} ")

    data = await get_vna_flight_options(
        dep0=dep0, arr0=arr0,
        depdate0=format_date(depdate0)
    )
    result = []
    #print(data)
    for item in data["body"]:
        flight_info = {
            "hãng":"VNA",
            "nơi_đi": item["SK"][0]["DA"],
            "nơi_đến": item["SK"][0]["AA"],
            "giờ_cất_cánh": (str(item["SK"][0]["DT"])),
            "ngày_cất_cánh": (item["SK"][0]["DD"]),
            "thời_gian_bay": item["SK"][0]["TT"],
            "thời_gian_chờ": item["SK"][0]["HTX"],
            "giờ_hạ_cánh": (str(item["SK"][0]["AT"])),
            "ngày_hạ_cánh": (item["SK"][0]["AD"]),
            "hành_lý_vna": item["P"],
            "giá_vé": item["MA"],
            "số_điểm_dừng": item["SK"][0]["VA"],
            "điểm_dừng_1": item["SK"][0].get("VA1", ""),
            "điểm_dừng_2": item["SK"][0].get("VA2", "")
            

        }
        result.append(flight_info)
    data["body"] = result
    print(data)
    
    
    return data
