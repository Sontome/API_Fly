import requests
import json
import httpx
from datetime import datetime
import os
import math
CONFIG_GIA_FILE = "config_gia.json"

# 🔧 Giá mặc định
DEFAULT_CONFIG_GIA = {
    "HANH_LY_DELUXE": 2000,
    "HANH_LY_ECO": 40000,
    "PHI_XUAT_VE_2_CHIEU": 15000,
    "PHI_XUAT_VE_1CH_DELUXE": 40000,
    "PHI_XUAT_VE_1CH_ECO": 32000,
    "HANH_LY_ECO_KM": 0, 
    "KM_END_DATE": "2025-05-26 00:00"  
}

# 📦 Load cấu hình giá
def load_config_gia():
    if os.path.exists(CONFIG_GIA_FILE):
        try:
            with open(CONFIG_GIA_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                config_loaded = {
                    "PHI_XUAT_VE_2_CHIEU": int(data.get("PHI_XUAT_VE_2_CHIEU", DEFAULT_CONFIG_GIA["PHI_XUAT_VE_2_CHIEU"])),
                    "HANH_LY_DELUXE": int(data.get("HANH_LY_DELUXE", DEFAULT_CONFIG_GIA["HANH_LY_DELUXE"])),
                    "HANH_LY_ECO": int(data.get("HANH_LY_ECO", DEFAULT_CONFIG_GIA["HANH_LY_ECO"])),
                    "PHI_XUAT_VE_1CH_DELUXE": int(data.get("PHI_XUAT_VE_1CH_DELUXE", DEFAULT_CONFIG_GIA["PHI_XUAT_VE_1CH_DELUXE"])),
                    "PHI_XUAT_VE_1CH_ECO": int(data.get("PHI_XUAT_VE_1CH_ECO", DEFAULT_CONFIG_GIA["PHI_XUAT_VE_1CH_ECO"])),
                    "HANH_LY_ECO_KM" : int(data.get("HANH_LY_ECO_KM", DEFAULT_CONFIG_GIA["HANH_LY_ECO_KM"])),
                    "KM_END_DATE" : str(data.get("KM_END_DATE", DEFAULT_CONFIG_GIA["KM_END_DATE"]))
                }

                # 🖨️ In ra log
                print("📥 Đã load cấu hình giá từ file:")
                

               
                return config_loaded
        except Exception as e:
            print("❌ Lỗi khi đọc config_gia.json:", e)

    print("⚠️ Không tìm thấy hoặc lỗi file config_gia.json, dùng mặc định:")
    
    

    
    return DEFAULT_CONFIG_GIA.copy()
config_gia = load_config_gia()
# ✅ Format lại thời gian
def price_add(chieudi: dict, chieuve: dict | None, config_gia: dict) -> int:
    tong = 0

    def get_hanh_ly_price(flight: dict) -> int:
        loai = flight["Type"].lower()
        if loai == "eco":
            try:
                etd = datetime.strptime(flight["ETD"], "%Y-%m-%d %H:%M")
                km_end = datetime.strptime(config_gia["KM_END_DATE"], "%Y-%m-%d %H:%M")
                if etd < km_end:
                    print("km")
                    return config_gia["HANH_LY_ECO_KM"]
                    
            except:
                pass
            print("ko km")
            return config_gia["HANH_LY_ECO"]
        elif loai == "deluxe":
            return config_gia["HANH_LY_DELUXE"]
        return 0

    # 👕 Hành lý chiều đi
    tong += get_hanh_ly_price(chieudi)

    if chieuve:
        # 🎒 Hành lý chiều về
        tong += get_hanh_ly_price(chieuve)

        # 🧾 Phí xuất vé 2 chiều
        tong += config_gia["PHI_XUAT_VE_2_CHIEU"]
    else:
        # 🧾 Phí xuất vé 1 chiều (theo loại vé đi)
        loai = chieudi["Type"].lower()
        if loai == "eco":
            tong += config_gia["PHI_XUAT_VE_1CH_ECO"]
        elif loai == "deluxe":
            tong += config_gia["PHI_XUAT_VE_1CH_DELUXE"]

    return tong
def format_time(time_str):
    try:
        dt = datetime.strptime(time_str, "%Y-%m-%d %H:%M")
        return dt.strftime("%H:%M ngày %d/%m")
    except Exception as e:
        print("❌ Format lỗi vcl:", e)
        return time_str

# ✅ Lấy token từ state.json
def get_app_access_token_from_state(file_path="state.json"):
    with open(file_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    origins = data.get("origins", [])
    for origin in origins:
        local_storage = origin.get("localStorage", [])
        for item in local_storage:
            if item.get("name") == "app_access_token":
                return item.get("value")
    return None

# ✅ Gọi API async lấy flight options
async def get_vietjet_flight_options(city_pair, departure_place, departure_place_name,
    return_place, return_place_name, departure_date, return_date,
    adult_count, child_count, auth_token):

    url = "https://agentapi.vietjetair.com/api/v13/Booking/findtraveloptions"
    params = {
        "cityPair": city_pair,
        "departurePlace": departure_place,
        "departurePlaceName": departure_place_name,
        "returnPlace": return_place,
        "returnPlaceName": return_place_name,
        "departure": departure_date,
        "return": return_date,
        "currency": "KRW",
        #"company": "hA0syYxT72sdFED0bwazxXXZXgHIbmt%C6%92Ppgjd1l4dCU=",
        "adultCount": adult_count,
        "childCount": child_count,
        "infantCount": "0",
        "promoCode": "",
        "greaterNumberOfStops": "0"
    }
    headers = {
        "accept": "application/json, text/plain, */*",
        "authorization": f"Bearer {auth_token}",
        "content-type": "application/json",
        "languagecode": "vi",
        "platform": "3",
        "referer": "https://agents2.vietjetair.com/",
    }
    try:
        async with httpx.AsyncClient(timeout=30) as client:
            response = await client.get(url, headers=headers, params=params)
            if response.status_code == 200:
                print("✅ Lấy dữ liệu chuyến bay thành công!")
                print(response.text)
                return response.json()
            else:
                print("❌ Có lỗi xảy ra :", response.status_code, response.text)
                return None
    except Exception as e:
        print("💥 Lỗi khi gọi API async:", e)
        return None

def extract_flight(data, list_key, config):
    try:
        list_chuyen = data.get("data", {}).get(list_key, [])
        eco_min, deluxe_min = None, None

        def make_flight_info(flight_info, fare):
            return {
                "Flight": flight_info.get("Number"),
                "From": flight_info.get("departureAirport", {}).get("Code"),
                "To": flight_info.get("arrivalAirport", {}).get("Code"),
                "ETD": flight_info.get("ETDLocal"),
                "ETA": flight_info.get("ETALocal"),
                "BookingKey": fare.get("BookingKey"),
                "FareCost": fare.get("FareCost"),
                "Currency": fare.get("currency", {}).get("code"),
                "SeatsAvailable": fare.get("SeatsAvailable"),
                "Type": fare.get("Description")
            }

        

        for chuyen in list_chuyen:
            segments = chuyen.get("segmentOptions", [])
            if not segments:
                continue
            flight_info = segments[0].get("flight", {})
            for fare in chuyen.get("fareOption", []):
                if fare.get("Description") == "Eco":
                    if eco_min is None or fare.get("FareCost") < eco_min["FareCost"]:
                        eco_min = make_flight_info(flight_info, fare)
                elif fare.get("Description") == "Deluxe":
                    if deluxe_min is None or fare.get("FareCost") < deluxe_min["FareCost"]:
                        deluxe_min = make_flight_info(flight_info, fare)

        if eco_min and deluxe_min:
            
            etd = datetime.strptime(eco_min["ETD"], "%Y-%m-%d %H:%M")
            
            km_end = datetime.strptime(config["KM_END_DATE"], "%Y-%m-%d %H:%M")
             
            
            hanh_ly_eco = config["HANH_LY_ECO_KM"] if etd and etd < km_end else config["HANH_LY_ECO"]
            chenhlech = deluxe_min["FareCost"] - eco_min["FareCost"]
            return [eco_min if chenhlech >= hanh_ly_eco else deluxe_min]

        return [eco_min] if eco_min else [deluxe_min] if deluxe_min else []

    except Exception as e:
        print("❌ Lỗi xử lý dữ liệu flight:", e)
        return []

def get_tax(authorization, booking_key):
    url = "https://agentapi.vietjetair.com/api/v13/Booking/quotationwithoutpassenger"
    headers = {
        "accept": "application/json, text/plain, */*",
        "authorization": f"Bearer {authorization}",
        "content-type": "application/json",
        "languagecode": "vi",
        "platform": "3"
    }
    payload = {
        "journeys": [{"index": 1, "bookingKey": booking_key}],
        "numberOfAdults": 1,
        "numberOfChilds": 0,
        "numberOfInfants": 0
    }
    try:
        res = requests.post(url, headers=headers, json=payload)
        res.raise_for_status()
        return res.json()
    except requests.RequestException as e:
        print("❌ Lỗi khi gọi API thuế:", e)
        return None

def save_all_results(sochieu, vechieudi, giave_chieu_di, vechieuve=None, giave_chieu_ve=None):
    if sochieu == "1":
        return {"ve_chieu_di": vechieudi, "gia_ve_chieu_di": giave_chieu_di}
    return {
        "ve_chieu_di": vechieudi,
        "gia_ve_chieu_di": giave_chieu_di,
        "ve_chieu_ve": vechieuve,
        "gia_ve_chieu_ve": giave_chieu_ve
    }
def to_price(number: float) -> str:
    number = math.ceil(number / 100) * 100
    so_ngan = number / 1000
    return f"{so_ngan:,.3f}w".replace(",", ".")

def thongtinve(data, sochieu,name):
    try:
        text = ""
        if str(sochieu) == "2":
            chieudi = data["ve_chieu_di"][0]
            chieuve = data["ve_chieu_ve"][0]
            text += f"👤Tên Khách:  {name}\n\n"
            text += f"Hãng: VIETJET - Chặng bay: {chieudi['From']}-{chieudi['To']} Khứ Hồi ( {chieudi['Type']}:{to_price(data['gia_ve_chieu_di']['data']['totalamountdeparture'])}-{chieuve['Type']}:{to_price(data['gia_ve_chieu_ve']['data']['totalamountdeparture'])} )\n\n"
            text += f"{chieudi['From']}-{chieudi['To']} {format_time(chieudi['ETD'])}\n"
            text += f"{chieuve['From']}-{chieuve['To']} {format_time(chieuve['ETD'])}\n"
            text += f"Vietjet 7kg xách tay, 20kg ký gửi, giá vé = {to_price(data['gia_ve_chieu_di']['data']['totalamountdeparture']+data['gia_ve_chieu_ve']['data']['totalamountdeparture']+price_add(chieudi, chieuve, config_gia))}"
        else:
            chieudi = data["ve_chieu_di"][0]
            text += f"👤Tên Khách:  {name}\n\n"
            text += f"Hãng: VIETJET - Chặng bay: {chieudi['From']}-{chieudi['To']} 1 Chiều ( {chieudi['Type']}:{to_price(data['gia_ve_chieu_di']['data']['totalamountdeparture'])} )\n\n"
            text += f"{chieudi['From']}-{chieudi['To']} {format_time(chieudi['ETD'])}\n"
            
            text += f"Vietjet 7kg xách tay, 20kg ký gửi, giá vé = {to_price(data['gia_ve_chieu_di']['data']['totalamountdeparture']+price_add(chieudi, None, config_gia))}"
        return text
    except Exception as e:
        return f"❌ Lỗi show info: {e}"

async def api_vj(name,city_pair, departure_place, departure_place_name, return_place, return_place_name, 
                 departure_date, return_date,adult_count=1, child_count=0, sochieu=2):
    token = get_app_access_token_from_state()
    result_data = await get_vietjet_flight_options(
        city_pair, departure_place, departure_place_name,
        return_place, return_place_name,
        departure_date, return_date,
        adult_count, child_count, token
    )

    if not result_data:
        return "❌ Không tải được danh sách chuyến bay"

    vechieudi = extract_flight(result_data, "list_Travel_Options_Departure", config_gia)
    if not vechieudi:
        return f"👤Tên Khách:  {name}\n\n❌ Không có chuyến đi nào hợp lệ"


    giave_chieu_di = get_tax(token, vechieudi[0]['BookingKey'])

    if str(sochieu) == "2":
        vechieuve = extract_flight(result_data, "list_Travel_Options_Arrival", config_gia)
        if not vechieuve:
            return "❌ Không có chuyến về nào hợp lệ"
        giave_chieu_ve = get_tax(token, vechieuve[0]['BookingKey'])
        result = save_all_results(sochieu, vechieudi, giave_chieu_di, vechieuve, giave_chieu_ve)
    else:
        result = save_all_results(sochieu, vechieudi, giave_chieu_di)

    return thongtinve(result, sochieu,name)
