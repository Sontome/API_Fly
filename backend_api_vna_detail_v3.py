import aiohttp
import json
import asyncio
from datetime import datetime,timedelta
import os
from collections import OrderedDict
import pytz
from backend_api_vna_v3 import PowerCallClient
airport_timezone_map = {
    # Việt Nam
    "SGN": "Asia/Ho_Chi_Minh",
    "HAN": "Asia/Ho_Chi_Minh",
    "DAD": "Asia/Ho_Chi_Minh",
    "CXR": "Asia/Ho_Chi_Minh",
    "PQC": "Asia/Ho_Chi_Minh",
    "VII": "Asia/Ho_Chi_Minh",
    "HUI": "Asia/Ho_Chi_Minh",
    "VCA": "Asia/Ho_Chi_Minh",

    # Hàn Quốc
    "ICN": "Asia/Seoul",
    "PUS": "Asia/Seoul",
    "CJU": "Asia/Seoul"
}
# ====== ⚙️ CONFIG ====== #

COOKIE_FILE = "statevna.json"

def extract_flight_code(s):
    parts = s.split("/")
    return parts[0] + parts[2]  # "VN" + "0417"
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
def calculate_landing_time(time_departure: str, duration_minutes: int, departure_airport: str, arrival_airport: str) -> str:
    # Múi giờ theo sân bay
    tz_depart = pytz.timezone(airport_timezone_map.get(departure_airport.upper(), "UTC"))
    tz_arrive = pytz.timezone(airport_timezone_map.get(arrival_airport.upper(), "UTC"))

    # Giờ cất cánh theo local time sân bay đi
    departure_time_naive = datetime.strptime(time_departure, "%H:%M")
    # Gán ngày fake tạm để xử lý, ví dụ ngày hôm nay
    departure_time = tz_depart.localize(datetime.now().replace(hour=departure_time_naive.hour, minute=departure_time_naive.minute, second=0, microsecond=0))

    # Tính giờ UTC rồi cộng thời gian bay
    arrival_time_utc = departure_time.astimezone(pytz.utc) + timedelta(minutes=duration_minutes)

    # Convert ngược lại giờ local sân bay đến
    arrival_time_local = arrival_time_utc.astimezone(tz_arrive)

    return arrival_time_local.strftime("%H:%M")
def convert_hhmm_to_minutes(hhmm: str) -> int:
    hours = int(hhmm[:2])
    minutes = int(hhmm[2:])
    return hours * 60 + minutes
def create_session_powercall():
    print(datetime.now().strftime("%Y%m%d_%H"))
    return datetime.now().strftime("%Y%m%d_%H")
def parse_gia_ve_tre_em(fare):
    CF = list(map(int, str(fare[0]["CF"]).split("/")))
    SF = list(map(int, str(fare[0]["SF"]).split("/")))
    IF = list(map(int, str(fare[0]["IF"]).split("/")))
    childfee= int((CF[0]))
    childtax = int(fare[0]["CHTX"])
    childfuel = int(fare[0]["CHFU"])
    adtfuel = int(fare[0]["ADFU"])
    adttax = int(fare[0]["TAX"])
    adtfee = int(SF[0])
    inffee= int((IF[0]))
    inftax = int(fare[0]["INTX"])
    inffuel = int(fare[0]["INFU"])

    
    adt = f"{adtfee}/{adttax}/{adtfuel}"
    chd = f"{childfee}/{childtax}/{childfuel}"
    inf = f"{inffee}/{inftax}/{inffuel}"
    #print([adt,chd,inf])
    return [adt,chd,inf]
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
    #print(data)
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


async def get_vna_flight_options( payload):
        
    async with PowerCallClient() as pc:
    
        
        result = await pc.getdetail(payload=payload)
    

    
    

        
        

        


        
        
        #print(result)
        kq= await doc_va_loc_ve_re_nhat(result)
        print(kq)
        return kq

# ====== 🧪 HÀM API CHÍNH ====== #

async def api_vna_detail_v3(payload):
    
    
    
    data = await get_vna_flight_options(
        payload=payload                                
    )
    if data["body"]=="null":
        return data
    result = []
    print(data)
    for item in data["body"]:
        detail = parse_gia_ve_tre_em(item["FARE"])
        chiều_đi={
                    
                        "hãng":"VNA",
                        "id": item["I"],
                        "nơi_đi": item["SK"][0]["DA"],
                        "nơi_đến": item["SK"][0]["AA"],
                        "giờ_cất_cánh": format_time(int(item["SK"][0]["DT"])),
                        "ngày_cất_cánh": format_date(str(item["SK"][0]["DD"])),
                        "thời_gian_bay": str(item["SK"][0]["TT"]),
                        "thời_gian_chờ": str(item["SK"][0].get("HTX") or 0),
                        "giờ_hạ_cánh": format_time(int(item["SK"][0]["AT"])),
                        "ngày_hạ_cánh": format_date(str(item["SK"][0]["AD"])),
                        "số_hiệu_máy_bay": item["SK"][0]["SG"][0]["RC"],
                        "số_hiệu_máy_bay_1": "",
                        "số_hiệu_máy_bay_2": "",
                    
                        "số_điểm_dừng": str(item["SK"][0]["VA"]),
                        "điểm_dừng_1": item["SK"][0].get("VA1", ""),
                        "điểm_dừng_2": item["SK"][0].get("VA2", ""),
                       
                        
                        "loại_vé": item["CS"][:1]
                        
                    }
                
        giờ_hạ_cánh_1_đi = ""
        giờ_cất_cánh_1_đi = ""
        giờ_hạ_cánh_2_đi = ""
        giờ_cất_cánh_2_đi = ""
        print(chiều_đi)
        số_hiệu_máy_bay_đi = extract_flight_code(chiều_đi["số_hiệu_máy_bay"])
        số_hiệu_máy_bay_1_đi = ""
        số_hiệu_máy_bay_2_đi = ""
        if chiều_đi["số_điểm_dừng"] == "1": 
            máy_bay_1_đi= item["SK"][0]["SG"][1]["RC"]
            số_hiệu_máy_bay_1_đi = extract_flight_code(máy_bay_1_đi)
            giờ_bay_chặng_1 = item["SKD"][0]["SEG"][0].get("TT","")
            thời_gian_bay = convert_hhmm_to_minutes(giờ_bay_chặng_1)
            #print(thời_gian_bay)
            giờ_hạ_cánh_1_đi = calculate_landing_time(chiều_đi["giờ_cất_cánh"],thời_gian_bay,chiều_đi["nơi_đi"],chiều_đi["điểm_dừng_1"])
            print(giờ_hạ_cánh_1_đi)
            print((chiều_đi["thời_gian_chờ"]))
            giờ_cất_cánh_1_đi = calculate_landing_time(giờ_hạ_cánh_1_đi,convert_hhmm_to_minutes(chiều_đi["thời_gian_chờ"]),chiều_đi["điểm_dừng_1"],chiều_đi["điểm_dừng_1"])
            print(giờ_cất_cánh_1_đi)
        if chiều_đi["số_điểm_dừng"] == "2": 
            máy_bay_1_đi= item["SK"][0]["SG"][1]["RC"]
            số_hiệu_máy_bay_1_đi = extract_flight_code(máy_bay_1_đi)
            máy_bay_2_đi= item["SK"][0]["SG"][2]["RC"]
            số_hiệu_máy_bay_2_đi = extract_flight_code(máy_bay_2_đi)
            giờ_bay_chặng_1 = item["SKD"][0]["SEG"][0].get("TT","")
            thời_gian_bay = convert_hhmm_to_minutes(giờ_bay_chặng_1)
            #print(thời_gian_bay)
            giờ_hạ_cánh_1_đi = calculate_landing_time(chiều_đi["giờ_cất_cánh"],thời_gian_bay,chiều_đi["nơi_đi"],chiều_đi["điểm_dừng_1"])
            #print(giờ_hạ_cánh_1_đi)
            #print((chiều_đi["thời_gian_chờ"]))
            giờ_cất_cánh_1_đi = calculate_landing_time(giờ_hạ_cánh_1_đi,convert_hhmm_to_minutes(chiều_đi["thời_gian_chờ"]),chiều_đi["điểm_dừng_1"],chiều_đi["điểm_dừng_1"])
            
            giờ_bay_chặng_2 = item["SKD"][0]["SEG"][1].get("TT","")
            thời_gian_bay = convert_hhmm_to_minutes(giờ_bay_chặng_2)
        

            
            giờ_hạ_cánh_2_đi = calculate_landing_time(giờ_cất_cánh_1_đi,thời_gian_bay,chiều_đi["điểm_dừng_1"],chiều_đi["điểm_dừng_2"])
            giờ_cất_cánh_2_đi = calculate_landing_time(giờ_hạ_cánh_2_đi,chiều_đi["thời_gian_chờ"],chiều_đi["điểm_dừng_2"],chiều_đi["điểm_dừng_2"])
                        
        flight_info = { 
            
            "detail":{
                "người lớn":parse_gia_ve(detail[0]),
                "trẻ em":parse_gia_ve(detail[1]),
                "trẻ sơ sinh":parse_gia_ve(detail[2]),
                "số_ghế_còn":  str(item["FA"][0]["AV"]),
                "hành_lý_vna": item["IT"]

            },
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
                
                "số_hiệu_máy_bay": số_hiệu_máy_bay_đi,
                "số_hiệu_máy_bay_1": số_hiệu_máy_bay_1_đi,
                "số_hiệu_máy_bay_2": số_hiệu_máy_bay_2_đi,
                "số_điểm_dừng": str(item["SK"][0]["VA"]),
                "điểm_dừng_1": item["SK"][0].get("VA1", ""),
                "điểm_dừng_2": item["SK"][0].get("VA2", ""),
                "giờ_hạ_cánh_1" : giờ_hạ_cánh_1_đi,
                "giờ_cất_cánh_1" : giờ_cất_cánh_1_đi,
                "giờ_hạ_cánh_2" : giờ_hạ_cánh_2_đi,
                "giờ_cất_cánh_2" : giờ_cất_cánh_2_đi,                
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
    
    #print(data)
    
    
    return data
async def api_vna_detail_rt_v3(payload):
    
    
    data = await get_vna_flight_options(
        payload=payload 
    )

    result = []
    if data["body"]=="null":
        return data
    #print(data)
    for item in data["body"]:
        detail = parse_gia_ve_tre_em(item["FARE"])
        chiều_đi={
            
                "hãng":"VNA",
                "id": item["I"],
                "nơi_đi": item["SK"][0]["DA"],
                "nơi_đến": item["SK"][0]["AA"],
                "giờ_cất_cánh": format_time(int(item["SK"][0]["DT"])),
                "ngày_cất_cánh": format_date(str(item["SK"][0]["DD"])),
                "thời_gian_bay": str(item["SK"][0]["TT"]),
                "thời_gian_chờ": str(item["SK"][0].get("HTX") or 0),
                "giờ_hạ_cánh": format_time(int(item["SK"][0]["AT"])),
                "ngày_hạ_cánh": format_date(str(item["SK"][0]["AD"])),
                
                "số_hiệu_máy_bay": item["SK"][0]["SG"][0]["RC"],
                "số_hiệu_máy_bay_1": "",
                "số_hiệu_máy_bay_2": "",
                "số_điểm_dừng": str(item["SK"][0]["VA"]),
                "điểm_dừng_1": item["SK"][0].get("VA1", ""),
                "điểm_dừng_2": item["SK"][0].get("VA2", ""),
                "giờ_hạ_cánh_1" : "",
                "giờ_cất_cánh_1" : "",
                "giờ_hạ_cánh_2" : "",
                "giờ_cất_cánh_2" : "",
                
                "loại_vé": item["CS"][:1]
                
            }
        chiều_về={
            
                "hãng":"VNA",
                "id": item["I"],
                "nơi_đi": item["SK"][1]["DA"],
                "nơi_đến": item["SK"][1]["AA"],
                "giờ_cất_cánh": format_time(int(item["SK"][1]["DT"])),
                "ngày_cất_cánh": format_date(str(item["SK"][1]["DD"])),
                "thời_gian_bay": str(item["SK"][1]["TT"]),
                "thời_gian_chờ": (item["SK"][1].get("HTX") or 0),
                "giờ_hạ_cánh": format_time(int(item["SK"][1]["AT"])),
                "ngày_hạ_cánh": format_date(str(item["SK"][1]["AD"])),
                
                "số_hiệu_máy_bay": item["SK"][1]["SG"][0]["RC"],
                "số_hiệu_máy_bay_1": "",
                "số_hiệu_máy_bay_2": "",
                "số_điểm_dừng": str(item["SK"][1]["VA"]),
                "điểm_dừng_1": item["SK"][1].get("VA1", ""),
                "điểm_dừng_2": item["SK"][1].get("VA2", ""),
                
                "loại_vé": item["CS"][3:4]
                
            }
        giờ_hạ_cánh_1_đi = ""
        giờ_cất_cánh_1_đi = ""
        giờ_hạ_cánh_2_đi = ""
        giờ_cất_cánh_2_đi = ""
        giờ_hạ_cánh_1_về = ""
        giờ_cất_cánh_1_về = ""
        giờ_hạ_cánh_2_về = ""
        giờ_cất_cánh_2_về = ""
        #print(chiều_về)
        số_hiệu_máy_bay_đi = extract_flight_code(item["SK"][0]["SG"][0]["RC"])
        số_hiệu_máy_bay_1_đi = ""
        số_hiệu_máy_bay_2_đi = ""
        số_hiệu_máy_bay_về = extract_flight_code(item["SK"][1]["SG"][0]["RC"])
        số_hiệu_máy_bay_1_về = ""
        số_hiệu_máy_bay_2_về = ""
        
        if chiều_đi["số_điểm_dừng"] == "1": 
            
            số_hiệu_máy_bay_1_đi = extract_flight_code(item["SK"][0]["SG"][1]["RC"])
            giờ_bay_chặng_1 = item["SKD"][0]["SEG"][0].get("TT","")
            thời_gian_bay = convert_hhmm_to_minutes(giờ_bay_chặng_1)
            #print(thời_gian_bay)
            giờ_hạ_cánh_1_đi = calculate_landing_time(chiều_đi["giờ_cất_cánh"],thời_gian_bay,chiều_đi["nơi_đi"],chiều_đi["điểm_dừng_1"])
            #print(giờ_hạ_cánh_1_đi)
            #print((chiều_đi["thời_gian_chờ"]))
            giờ_cất_cánh_1_đi = calculate_landing_time(giờ_hạ_cánh_1_đi,convert_hhmm_to_minutes(chiều_đi["thời_gian_chờ"]),chiều_đi["điểm_dừng_1"],chiều_đi["điểm_dừng_1"])
        if chiều_đi["số_điểm_dừng"] == "2": 
            số_hiệu_máy_bay_1_đi = extract_flight_code(item["SK"][0]["SG"][1]["RC"])
            số_hiệu_máy_bay_2_đi = extract_flight_code(item["SK"][0]["SG"][2]["RC"])
            giờ_bay_chặng_1 = item["SKD"][0]["SEG"][0].get("TT","")
            thời_gian_bay = convert_hhmm_to_minutes(giờ_bay_chặng_1)
            #print(thời_gian_bay)
            giờ_hạ_cánh_1_đi = calculate_landing_time(chiều_đi["giờ_cất_cánh"],thời_gian_bay,chiều_đi["nơi_đi"],chiều_đi["điểm_dừng_1"])
            #print(giờ_hạ_cánh_1_đi)
            #print((chiều_đi["thời_gian_chờ"]))
            giờ_cất_cánh_1_đi = calculate_landing_time(giờ_hạ_cánh_1_đi,convert_hhmm_to_minutes(chiều_đi["thời_gian_chờ"]),chiều_đi["điểm_dừng_1"],chiều_đi["điểm_dừng_1"])
            
            giờ_bay_chặng_2 = item["SKD"][0]["SEG"][1].get("TT","")
            thời_gian_bay = convert_hhmm_to_minutes(giờ_bay_chặng_2)
        

            
            giờ_hạ_cánh_2_đi = calculate_landing_time(giờ_cất_cánh_1_đi,thời_gian_bay,chiều_đi["điểm_dừng_1"],chiều_đi["điểm_dừng_2"])
            giờ_cất_cánh_2_đi = calculate_landing_time(giờ_hạ_cánh_2_đi,chiều_đi["thời_gian_chờ"],chiều_đi["điểm_dừng_2"],chiều_đi["điểm_dừng_2"])
        
        if chiều_về["số_điểm_dừng"] == "1": 
            số_hiệu_máy_bay_1_về = extract_flight_code(item["SK"][1]["SG"][1]["RC"])
            số_hiệu_máy_bay_2_về = extract_flight_code(item["SK"][1]["SG"][2]["RC"])
            giờ_bay_chặng_1 = item["SKD"][1]["SEG"][0].get("TT","")
            thời_gian_bay = convert_hhmm_to_minutes(giờ_bay_chặng_1)
            #print(thời_gian_bay)
            giờ_hạ_cánh_1_về = calculate_landing_time(chiều_về["giờ_cất_cánh"],thời_gian_bay,chiều_về["nơi_đi"],chiều_về["điểm_dừng_1"])
            
            print(chiều_về["giờ_cất_cánh"],thời_gian_bay,chiều_về["nơi_đi"],chiều_về["điểm_dừng_1"])
            print(giờ_hạ_cánh_1_về)
            giờ_cất_cánh_1_về = calculate_landing_time(giờ_hạ_cánh_1_về,convert_hhmm_to_minutes(chiều_về["thời_gian_chờ"]),chiều_về["điểm_dừng_1"],chiều_về["điểm_dừng_1"])
            print(giờ_hạ_cánh_1_về,convert_hhmm_to_minutes(chiều_về["thời_gian_chờ"]),chiều_về["điểm_dừng_1"],chiều_về["điểm_dừng_1"])
        if chiều_về["số_điểm_dừng"] == "2": 
            giờ_bay_chặng_1 = item["SKD"][1]["SEG"][0].get("TT","")
            thời_gian_bay = convert_hhmm_to_minutes(giờ_bay_chặng_1)
            #print(thời_gian_bay)
            giờ_hạ_cánh_1_về = calculate_landing_time(chiều_về["giờ_cất_cánh"],thời_gian_bay,chiều_về["nơi_đi"],chiều_về["điểm_dừng_1"])
            #print(giờ_hạ_cánh_1_đi)
            #print((chiều_đi["thời_gian_chờ"]))
            giờ_cất_cánh_1_về = calculate_landing_time(giờ_hạ_cánh_1_về,convert_hhmm_to_minutes(chiều_về["thời_gian_chờ"]),chiều_về["điểm_dừng_1"],chiều_về["điểm_dừng_1"])
            
            giờ_bay_chặng_2 = item["SKD"][1]["SEG"][1].get("TT","")
            thời_gian_bay = convert_hhmm_to_minutes(giờ_bay_chặng_2)
        

            
            giờ_hạ_cánh_2_về = calculate_landing_time(giờ_cất_cánh_1_về,thời_gian_bay,chiều_về["điểm_dừng_1"],chiều_về["điểm_dừng_2"])
            giờ_cất_cánh_2_về = calculate_landing_time(giờ_hạ_cánh_2_về,chiều_về["thời_gian_chờ"],chiều_về["điểm_dừng_2"],chiều_về["điểm_dừng_2"])


        flight_info = { 
            
            "detail":{
                "người lớn":parse_gia_ve(detail[0]),
                "trẻ em":parse_gia_ve(detail[1]),
                "trẻ sơ sinh":parse_gia_ve(detail[2]),
                "số_ghế_còn":  str(item["FA"][0]["AV"]),
                "hành_lý_vna": item["IT"]

            },
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
                "số_hiệu_máy_bay": số_hiệu_máy_bay_đi,
                "số_hiệu_máy_bay_1": số_hiệu_máy_bay_1_đi,
                "số_hiệu_máy_bay_2": số_hiệu_máy_bay_2_đi,
               
                "số_điểm_dừng": str(item["SK"][0]["VA"]),
                "điểm_dừng_1": item["SK"][0].get("VA1", ""),
                "điểm_dừng_2": item["SK"][0].get("VA2", ""),
                "giờ_hạ_cánh_1" : giờ_hạ_cánh_1_đi,
                "giờ_cất_cánh_1" : giờ_cất_cánh_1_đi,
                "giờ_hạ_cánh_2" : giờ_hạ_cánh_2_đi,
                "giờ_cất_cánh_2" : giờ_cất_cánh_2_đi,
                
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
                "số_hiệu_máy_bay": số_hiệu_máy_bay_về,
                "số_hiệu_máy_bay_1": số_hiệu_máy_bay_1_về,
                "số_hiệu_máy_bay_2": số_hiệu_máy_bay_2_về,
                
                
                "số_điểm_dừng": str(item["SK"][1]["VA"]),
                "điểm_dừng_1": item["SK"][1].get("VA1", ""),
                "điểm_dừng_2": item["SK"][1].get("VA2", ""),
                "giờ_hạ_cánh_1" : giờ_hạ_cánh_1_về,
                "giờ_cất_cánh_1" : giờ_cất_cánh_1_về,
                "giờ_hạ_cánh_2" : giờ_hạ_cánh_2_về,
                "giờ_cất_cánh_2" : giờ_cất_cánh_2_về,
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
    
    #print(data)
    
    
    return data




