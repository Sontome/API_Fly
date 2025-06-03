import aiohttp
import json
import asyncio
from datetime import datetime
import os
from collections import OrderedDict

# ====== ⚙️ CONFIG ====== #

COOKIE_FILE = "statevna.json"


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

def parse_gia_ve(raw_str):
    parts = list(map(int, raw_str.split("/")))
    gia_goc = parts[0]
    tong_thue_phi = parts[1]
    phi_nhien_lieu = parts[2]

    return {
        "giá_vé": str(gia_goc + tong_thue_phi),
        "giá_vé_gốc": str(gia_goc),
        "phí_nhiên_liệu": str(phi_nhien_lieu),
        "thuế_phí_công_cộng": str(tong_thue_phi - phi_nhien_lieu)
    }
# ====== 🔧 LOAD CONFIG ====== #




# ====== 🔍 LỌC VÉ ====== #
async def doc_va_loc_ve_re_nhat(data):
    print(data)
    trang = str(data.get("PAGE", "1"))
    tong_trang = str(data.get("TOTALPAGE", "1"))
    fares = data.get("FARES", [])
    session_key = str(data.get("SessionKey", "0"))
    def loc_fare_vn(fare): return fare.get("CA") == "VN"  and (fare.get("OC") != "KE")
    
    
    fares_thang = list(filter(loc_fare_vn, fares))
    
    if not fares_thang:
        
        print("❌ Không có vé phù hợp điều kiện VN + VFR")
        return {
        "status_code": 200,
        "trang": trang,
        "tổng_trang": tong_trang,
        "session_key" : session_key,
        "body" : "null"
        }
        
    return {
        "status_code": 200,
        "trang": trang,
        "tổng_trang": tong_trang,
        "session_key" : session_key,
        "body" :fares_thang
    }


async def get_vna_flight_options( session_key,dep0, arr0, depdate0,activedVia,activedIDT,filterTimeSlideMin0,filterTimeSlideMax0,filterTimeSlideMin1,filterTimeSlideMax1,page,adt,chd,inf,sochieu,depdate1=""):
        
    with open(COOKIE_FILE, "r", encoding="utf-8") as f:
        raw_cookies = json.load(f)["cookies"]
    cookies = {c["name"]: c["value"] for c in raw_cookies}
    

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
        
        'activedVia': activedVia,
        'activedStatus': 'OK,HL',
        'activedIDT': activedIDT,
        'minAirFareView': '1',
        'maxAirFareView': '2000000',
        'page': page,
        
        'sort': 'priceAsc',
        'interval01Val': '1000',
        'interval02Val': '',
        'filterTimeSlideMin0': filterTimeSlideMin0,
        'filterTimeSlideMax0': filterTimeSlideMax0,
        'filterTimeSlideMin1': filterTimeSlideMin1,
        'filterTimeSlideMax1': filterTimeSlideMax1,
        'trip':sochieu,
        'dayInd': 'N',
        'strDateSearch': depdate0[:6],
        'daySeq': '0',
        'dep0': dep0,
        'dep1': "",
        'arr0': arr0,
        'arr1': "",
        'depdate0': depdate0,
        'depdate1': depdate1,
        'retdate': depdate1,
        'comp': 'Y',
        'adt': adt,
        'chd': chd,
        'inf': inf,
        'car': 'YY',
        'idt': 'ALL',
        'isBfm': 'Y',
        'CBFare': 'YY',
        'miniFares': 'Y',
        'sessionKey': session_key
    }
    if sochieu=="RT":
        form_data.update({
            "activedAirport": f"{dep0}-{arr0}-{arr0}-{dep0}",
            'activedCLSS2': 'M,E,S,H,R,L,U,I,Z,W,J,K,T,B,A,N,Q,Y,V',
            "dep1": arr0,
            "depdate1": depdate1,
            "interval02Val": "1000",
            "retdate": depdate1
           
        })
    

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
        
        

        


        
        
    #print(result)
    kq= await doc_va_loc_ve_re_nhat(result)
    
    return kq

# ====== 🧪 HÀM API CHÍNH ====== #

async def api_vna_v2(dep0, arr0, depdate0,activedVia,activedIDT,filterTimeSlideMin0,filterTimeSlideMax0,filterTimeSlideMin1,filterTimeSlideMax1,page,adt,chd,inf,sochieu,session_key):
    
    if session_key==None:
        session_key = create_session_powercall()
    if session_key=="":
        session_key = create_session_powercall()
    print(f"From {dep0} to {arr0} | Ngày đi: {format_date(depdate0)} ")

    data = await get_vna_flight_options(session_key=session_key,
        dep0=dep0, arr0=arr0,
        depdate0=format_date(depdate0),
        activedVia=activedVia,
        activedIDT=activedIDT,
        filterTimeSlideMin0=filterTimeSlideMin0,
        filterTimeSlideMax0=filterTimeSlideMax0,
        filterTimeSlideMin1=filterTimeSlideMin1,
        filterTimeSlideMax1=filterTimeSlideMax1,        
        page=page,
        adt=adt,
        chd=chd,
        inf=inf,
        sochieu=sochieu
    )
    if data["body"]=="null":
        return data
    result = []
    #print(data)
    for item in data["body"]:
        flight_info = { 
            "chiều_đi":{
            
                "hãng":"VNA",
                "id": item["I"],
                "nơi_đi": item["SK"][0]["DA"],
                "nơi_đến": item["SK"][0]["AA"],
                "giờ_cất_cánh": format_time(int(item["SK"][0]["DT"])),
                "ngày_cất_cánh": format_date(str(item["SK"][0]["DD"])),
                "thời_gian_bay": str(item["SK"][0]["TT"]),
                "thời_gian_chờ": format_time(int(item["SK"][0].get("HTX") or 0)),
                "giờ_hạ_cánh": format_time(int(item["SK"][0]["AT"])),
                "ngày_hạ_cánh": format_date(str(item["SK"][0]["AD"])),
                
                
                "số_điểm_dừng": str(item["SK"][0]["VA"]),
                "điểm_dừng_1": item["SK"][0].get("VA1", ""),
                "điểm_dừng_2": item["SK"][0].get("VA2", ""),
                
                "loại_vé": item["CS"][:1]
                
            },
            "thông_tin_chung":{
                **parse_gia_ve(str(item["FA"][0]["FD"])),
                "số_ghế_còn":  str(item["FA"][0]["AV"]),
                "hành_lý_vna": item["IT"]


            }
            
            
        }
        result.append(flight_info)
    data["body"] = result
   
    print(data)
    
    
    return data
async def api_vna_rt_v2(dep0, arr0, depdate0,activedVia,activedIDT,filterTimeSlideMin0,filterTimeSlideMax0,filterTimeSlideMin1,filterTimeSlideMax1,page,adt,chd,inf,sochieu,depdate1,session_key):
    
    if session_key==None:
        session_key = create_session_powercall()
    if session_key=="":
        session_key = create_session_powercall()
    print(f"From {dep0} to {arr0}-khứ hồi | Ngày đi: {format_date(depdate0)} ")

    data = await get_vna_flight_options(session_key=session_key,
        dep0=dep0, arr0=arr0,
        depdate0=format_date(depdate0),
        depdate1=format_date(depdate1),
        activedVia=activedVia,
        activedIDT=activedIDT,
        filterTimeSlideMin0=filterTimeSlideMin0,
        filterTimeSlideMax0=filterTimeSlideMax0,
        filterTimeSlideMin1=filterTimeSlideMin1,
        filterTimeSlideMax1=filterTimeSlideMax1,
        page=page,
        adt=adt,
        chd=chd,
        inf=inf,
        sochieu=sochieu
    )

    result = []
    if data["body"]=="null":
        return data
    print(data)
    for item in data["body"]:
        flight_info = { 
            "chiều_đi":{
            
                "hãng":"VNA",
                "id": item["I"],
                "nơi_đi": item["SK"][0]["DA"],
                "nơi_đến": item["SK"][0]["AA"],
                "giờ_cất_cánh": format_time(int(item["SK"][0]["DT"])),
                "ngày_cất_cánh": format_date(str(item["SK"][0]["DD"])),
                "thời_gian_bay": str(item["SK"][0]["TT"]),
                "thời_gian_chờ": format_time(int(item["SK"][0].get("HTX") or 0)),
                "giờ_hạ_cánh": format_time(int(item["SK"][0]["AT"])),
                "ngày_hạ_cánh": format_date(str(item["SK"][0]["AD"])),
                
               
                "số_điểm_dừng": str(item["SK"][0]["VA"]),
                "điểm_dừng_1": item["SK"][0].get("VA1", ""),
                "điểm_dừng_2": item["SK"][0].get("VA2", ""),
                
                "loại_vé": item["CS"][:1]
                
            },
            "chiều_về":{
            
                "hãng":"VNA",
                "id": item["I"],
                "nơi_đi": item["SK"][1]["DA"],
                "nơi_đến": item["SK"][1]["AA"],
                "giờ_cất_cánh": format_time(int(item["SK"][1]["DT"])),
                "ngày_cất_cánh": format_date(str(item["SK"][1]["DD"])),
                "thời_gian_bay": str(item["SK"][1]["TT"]),
                "thời_gian_chờ": format_time(int(item["SK"][1].get("HTX") or 0)),
                "giờ_hạ_cánh": format_time(int(item["SK"][1]["AT"])),
                "ngày_hạ_cánh": format_date(str(item["SK"][1]["AD"])),
                
                
                "số_điểm_dừng": str(item["SK"][1]["VA"]),
                "điểm_dừng_1": item["SK"][1].get("VA1", ""),
                "điểm_dừng_2": item["SK"][1].get("VA2", ""),
                
                "loại_vé": item["CS"][3:4]
                
            },
            "thông_tin_chung":{
                **parse_gia_ve(str(item["FA"][0]["FD"])),
                "số_ghế_còn":  str(item["FA"][0]["AV"]),
                "hành_lý_vna": item["IT"]

            }
            
            
        }
        result.append(flight_info)
    data["body"] = result
    
    print(data)
    
    
    return data