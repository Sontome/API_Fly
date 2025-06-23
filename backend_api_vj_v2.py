import requests
import json
import httpx
from datetime import datetime
import os
import math
CONFIG_GIA_FILE = "config_gia.json"
import subprocess

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
        print("❌ Format lỗi :", e)
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
async def get_vietjet_flight_options( departure_place, 
    return_place,  departure_date, 
    adult_count, child_count, auth_token, retry=False):

    url = "https://agentapi.vietjetair.com/api/v13/Booking/findtraveloptions"
    params = {
        "cityPair": departure_place+"-"+return_place,
        "departurePlace": departure_place,
        "departurePlaceName": "",
        "returnPlace": return_place,
        "returnPlaceName":"",
        "departure": departure_date,
        "return": "",
        "currency": "KRW",
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
        async with httpx.AsyncClient(timeout=40) as client:
            response = await client.get(url, headers=headers, params=params)
            data = response.json()

            # ✅ Nếu bị 401 bên trong JSON
            if data.get("resultcode") == 401:

                print("🔐 Token hết hạn, chạy lại getcokivj.py để lấy token mới...")
                try:
                    subprocess.run(["python", "getcokivj.py"], check=True)
                    if not retry:
                        # 🧠 Gọi lại chính nó sau khi có token mới
                        new_token = get_app_access_token_from_state()
                        data = await get_vietjet_flight_options(
                             departure_place,
                            return_place, 
                            departure_date, 
                            adult_count, child_count, new_token, retry=True
                        )
                        return data 
                        
                        
                except Exception as e:
                    print("❌ Lỗi khi chạy getcokivj.py:", e)
                return None

            if response.status_code == 200:
                print("✅ Lấy dữ liệu chuyến bay thành công!")
                #print(response.text)
                if retry==True:
                    return data    
                return data
            else:
                print("❌ Có lỗi xảy ra :", response.status_code, response.text)
                return None

    except Exception as e:
        print("💥 Lỗi khi gọi API async:", e)
        return None
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
def extract_flight(data, list_key, config,phi_chieu_di):
    try:
        
        list_chuyen = data.get("data", {}).get(list_key, [])
        with open("test.json", "w", encoding="utf-8") as f:
            json.dump(list_chuyen, f, ensure_ascii=False, indent=4)
        eco, deluxe = None, None

        def make_flight_info(flight_info, fare,stt,phi_chieu_di):
            thoi_gian_0 = flight_info.get("ETDLocal")
            thoi_gian_1 = flight_info.get("ETALocal")
            ngay0, gio0 = thoi_gian_0.split(" ")
            ngay1, gio1 = thoi_gian_1.split(" ")
            
            return {
                "chiều đi" :{
                "hãng": "VJ",
                "id":  str(stt),
                "nơi_đi": flight_info.get("departureAirport", {}).get("Code"),
                "nơi_đến": flight_info.get("arrivalAirport", {}).get("Code"),
                "giờ_cất_cánh": gio0,
                "ngày_cất_cánh": f"{ngay0[8:10]}/{ngay0[5:7]}/{ngay0[:4]}",
                "thời_gian_bay": flight_info.get("Duration"),
                "thời_gian_chờ": "00:00",
                "giờ_hạ_cánh": gio1,
                "ngày_hạ_cánh": f"{ngay1[8:10]}/{ngay1[5:7]}/{ngay1[:4]}",
                "số_điểm_dừng": "0",
                "điểm_dừng_1": "",
                "điểm_dừng_2": "",
                "loại_vé": (fare.get("Description")).upper(),
                
                "BookingKey": fare.get("BookingKey")
                },
                "thông_tin_chung": {
                    "giá_vé": "0",
                    "giá_vé_gốc": fare.get("FareCost"),
                    "phí_nhiên_liệu": phi_chieu_di.get("data").get("departure").get("services").get('totalamount'),
                    "thuế_phí_công_cộng": "0",
                    "số_ghế_còn": str(fare.get("SeatsAvailable")),
                    "hành_lý_vna": "None"
                }
            }
        
        data = []
        stt = 1
        for chuyen in list_chuyen:
            segments = chuyen.get("segmentOptions", [])
            if not segments:
                continue
            flight_info = segments[0].get("flight", {})
            for fare in chuyen.get("fareOption", []):
                if fare.get("Description") == "Eco":
                    
                    eco = make_flight_info(flight_info, fare,stt,phi_chieu_di)
                elif fare.get("Description") == "Deluxe":
                    
                    deluxe = make_flight_info(flight_info, fare,stt,phi_chieu_di)

            if eco and deluxe:
                
                etd = datetime.strptime(flight_info.get("ETDLocal"), "%Y-%m-%d %H:%M")
                
                km_end = datetime.strptime(config["KM_END_DATE"], "%Y-%m-%d %H:%M")
                
                
                hanh_ly_eco = config["HANH_LY_ECO_KM"] if etd and etd < km_end else config["HANH_LY_ECO"]
                chenhlech = deluxe["thông_tin_chung" ]["giá_vé_gốc"] - eco["thông_tin_chung" ]["giá_vé_gốc"]
                if chenhlech >= hanh_ly_eco :
                    
                    ve= eco
                else :
                    ve = deluxe
            elif eco : ve= eco  
            elif deluxe : ve= deluxe 
            if ve["chiều đi"]["loại_vé"] == "ECO":
                ve["thông_tin_chung"]["giá_vé_gốc"] += hanh_ly_eco
            else:
                ve["thông_tin_chung"]["giá_vé_gốc"] += config["HANH_LY_DELUXE"]
            data.append(ve)
            stt += 1     


        return data

    except Exception as e:
        print("❌ Lỗi xử lý dữ liệu flight:", e)
        return []
async def api_vj_v2( departure_place,  return_place, 
                 departure_date,adult_count=1, child_count=0, sochieu=1):
    token = get_app_access_token_from_state()
    result_data = await get_vietjet_flight_options(
        departure_place, 
        return_place, 
        departure_date, 
        adult_count, child_count, token
    )

    if not result_data:
        return "❌ Không tải được danh sách chuyến bay"
    try:
        booking_key_chieu_di = result_data['data']['list_Travel_Options_Departure'][0]["fareOption"][0]["BookingKey"]
        
            
        
        phi_chieu_di = get_tax(token,booking_key_chieu_di)
        print(phi_chieu_di)
    except:
        pass
    vechieudi = extract_flight(result_data, "list_Travel_Options_Departure", config_gia,phi_chieu_di)
    if not vechieudi:
        return f"❌ Không có chuyến đi nào hợp lệ"
    


   

    
    result = vechieudi

    return result
