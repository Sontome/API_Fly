import requests
import json
import httpx
from datetime import datetime
import os
import math
CONFIG_GIA_FILE = "config_gia.json"
import subprocess
import urllib.parse
global token
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
def url_encode(text):
    if text.endswith("="):
        encoded = urllib.parse.quote(text[:-1])
        return encoded + "="
    else:
        return urllib.parse.quote(text)
def get_company(bear,retry=False):
    global token
    url = "https://agentapi.vietjetair.com/api/v13/Booking/getlistcompanies"
    headers = {
        "accept": "application/json, text/plain, */*",
        "accept-language": "vi-VN,vi;q=0.9,en-US;q=0.8,en;q=0.7",
        "authorization": f"Bearer {bear}",
        "content-type": "application/json",
        "languagecode": "vi",
        "platform": "3",
        "priority": "u=1, i",
        "sec-ch-ua": '"Google Chrome";v="137", "Chromium";v="137", "Not/A)Brand";v="24"',
        "sec-ch-ua-mobile": "?0",
        "sec-ch-ua-platform": '"Windows"',
        "sec-fetch-dest": "empty",
        "sec-fetch-mode": "cors",
        "sec-fetch-site": "same-site"
    }
    
    response = requests.get(url, headers=headers)
    if response.status_code == 401:


        print("🔐 Token hết hạn, chạy lại getcokivj.py để lấy token mới...")
        try:
            subprocess.run(["python", "getcokivj.py"], check=True)
            if not retry:
                # 🧠 Gọi lại chính nó sau khi có token mới
                new_token = get_app_access_token_from_state()
                token = new_token
                data =  get_company(new_token,retry=True)
                return data 
                
                
        except Exception as e:
            print("❌ Lỗi khi chạy getcokivj.py:", e)
        return None        

    if response.status_code == 200:
        
        return response.json()
    else:
        print(f"Lỗi , status code: {response.status_code}")
        print(response.text)
        return None
async def get_vietjet_flight_options( departure_place, 
    return_place,  departure_date, 
    adult_count, child_count,infant_count, company,auth_token, return_date= "", retry=False):
    global token
    
    
    
    url = (
        f"https://agentapi.vietjetair.com/api/v13/Booking/findtraveloptions?"
        f"cityPair={departure_place}-{return_place}"
        f"&departurePlace={departure_place}"
        f"&departurePlaceName=Seoul"
        f"&returnPlace={return_place}"
        f"&returnPlaceName=Ha%20Noi"
        f"&departure={departure_date}"
        f"&return={return_date}"
        f"&currency=KRW"
        f"&company={company}"
        f"&adultCount={adult_count}"
        f"&childCount={child_count}"
        f"&infantCount={infant_count}"
        f"&promoCode="
        f"&greaterNumberOfStops=0"
    )

    headers = {
        "accept": "application/json, text/plain, */*",
        "authorization": f"Bearer {auth_token}",
        "content-type": "application/json",
        "languagecode": "vi",
        "platform": "3",
        "referer": "https://agents2.vietjetair.com/",
    }
    #print(url)
    try:
        async with httpx.AsyncClient(timeout=40) as client:
            response = await client.get(url, headers=headers)
            data = response.json()

            if data.get("resultcode") == 401:
                print("🔐 Token hết hạn, chạy lại getcokivj.py để lấy token mới...")
                try:
                    subprocess.run(["python", "getcokivj.py"], check=True)
                    if not retry:
                        new_token = get_app_access_token_from_state()
                        token = new_token
                        return await get_vietjet_flight_options(
                            departure_place, return_place, departure_date,
                            adult_count, child_count, infant_count,
                            new_token, return_date, retry=True
                        )
                except Exception as e:
                    print("❌ Lỗi khi chạy getcokivj.py:", e)
                return None

            if response.status_code == 200 and data.get("resultcode") == 1:
                print("✅ Lấy dữ liệu chuyến bay thành công!")
                return data
            else:
                print("❌ Có lỗi xảy ra :", response.status_code, response.text)
                return None

    except Exception as e:
        print("💥 Lỗi khi gọi API async:", e)
        return None
def get_tax(authorization, booking_key, adult_count, child_count, infant_count,booking_key_arrival=None): 
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
        "numberOfAdults": adult_count,
        "numberOfChilds": child_count,
        "numberOfInfants": infant_count
    }
    result = {
        "arrival":{},
        "departure":{}

    }
    if booking_key_arrival :
        payload["journeys"] = [{"index": 1, "bookingKey": booking_key},{"index": 2 ,"bookingKey": booking_key_arrival}]
    try:
        res = requests.post(url, headers=headers, json=payload)
        res_json = res.json()

        if res_json.get("resultcode") != 1:
            print("⚠️ Gọi lại get_tax lần 2...")
            res = requests.post(url, headers=headers, json=payload)
            res_json = res.json()

        result["departure"] = (extract_tax(res_json,"departure"))
        if booking_key_arrival :
            result["arrival"] = (extract_tax(res_json,"arrival"))
        return result
    except requests.RequestException as e:
        print("❌ Lỗi khi gọi API thuế:", e)
        return None
def extract_tax(tax,departure):
    """
    Hàm xử lý dữ liệu thuế từ API VietJet
    Trả về:
    - giá_vé_gốc (int)
    - thuế_phí_công_cộng (int)
    - phí_nhiên_liệu (int)
    """
    try:
        data = tax.get("data", {})
        departure = data.get(departure, {})

        # Giá vé gốc
        fares = departure.get("fares", {})
        total_fares = fares.get("charges", [{}])[0].get("totalbaseamount", 0)
        count_fares = fares.get("charges", [{}])[0].get("count", 1)  # Lấy count của phần tử đầu tiên
        gia_ve_goc = total_fares / count_fares if count_fares else 0

        # Thuế phí công cộng
        try:
            feetaxs = departure.get("feetaxs", {})
            charges = feetaxs.get("charges", [])

            result = {
                "Admin Fee ITL": 0,
                "Airport Tax ITL": 0,
                "Airport Tax ChidITL": 0,
                "INFANT CHARGE ITL": 0
            }

            for item in charges:
                name = item.get("groupname", "")
                total_amount = item.get("totalamount", 0)
                count = item.get("count", 1)
                amount_per_ticket = total_amount / count if count else 0

                if name in result:
                    result[name] = round(amount_per_ticket)

            thue_phi_cong_cong =  result

        except Exception as e:
            print("❌ Lỗi khi xử lý feetaxs:", e)
            thue_phi_cong_cong = {
                "Admin Fee ITL": 0,
                "Airport Tax ITL": 0,
                "Airport Tax ChidITL": 0,
                "INFANT CHARGE ITL": 0
            }
        

        # Phí nhiên liệu
        try:
            services = departure.get("services", {})
            charges = services.get("charges", [])

            result = {
                "Management Fee ITL": 0,
                "Fuel Surcharge": 0
              
            }

            for item in charges:
                name = item.get("groupname", "")
                total_amount = item.get("totalamount", 0)
                count = item.get("count", 1)
                amount_per_ticket = total_amount / count if count else 0

                if name in result:
                    result[name] = round(amount_per_ticket)

            phi_nhien_lieu =  result

        except Exception as e:
            print("❌ Lỗi khi xử lý services:", e)
            phi_nhien_lieu = {
                "Management Fee ITL": 0,
                "Fuel Surcharge": 0
            }





        

        return {
            "fares": round(gia_ve_goc),
            "feetaxs": (thue_phi_cong_cong),
            "services": (phi_nhien_lieu)
        }

    except Exception as e:
        print("❌ Lỗi khi xử lý dữ liệu thuế:", e)
        return {
            "giá_vé_gốc": 0,
            "thuế_phí_công_cộng": 0,
            "phí_nhiên_liệu": 0
        }
def extract_flight(data, list_key, config,phi_chieu_di):
    chieu = "chiều đi"
    if list_key == "list_Travel_Options_Arrival": 
        chieu = "chiều về"
    try:
        
        list_chuyen = data.get("data", {}).get(list_key, [])
        with open("test.json", "w", encoding="utf-8") as f:
            json.dump(list_chuyen, f, ensure_ascii=False, indent=4)
        eco, deluxe = None, None

        def make_flight_info(flight_info, fare,stt,phi_chieu_di,chieu):
            thoi_gian_0 = flight_info.get("ETDLocal")
            thoi_gian_1 = flight_info.get("ETALocal")
            ngay0, gio0 = thoi_gian_0.split(" ")
            ngay1, gio1 = thoi_gian_1.split(" ")
            
            return {
                chieu :{
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
                    "giá_vé": 0,
                    "giá_vé_gốc": fare.get("FareCost"),
                    "phí_nhiên_liệu": math.floor(phi_chieu_di.get("services").get("Management Fee ITL")+ phi_chieu_di.get("services").get("Fuel Surcharge") ),
                    "thuế_phí_công_cộng": math.floor(phi_chieu_di.get("feetaxs").get("Admin Fee ITL")+ phi_chieu_di.get("feetaxs").get("Airport Tax ITL")),
                    "số_ghế_còn": str(fare.get("SeatsAvailable")),
                    "hành_lý_vna": "None"
                }
            }
        
        data = []
        stt = 1
        for chuyen in list_chuyen:
            if chuyen['fareOption']:
                segments = chuyen.get("segmentOptions", [])
                if not segments:
                    continue
                flight_info = segments[0].get("flight", {})
                for fare in chuyen.get("fareOption", []):
                    if fare.get("Description") == "Eco":
                        
                        eco = make_flight_info(flight_info, fare,stt,phi_chieu_di,chieu)
                    elif fare.get("Description") == "Deluxe":
                        
                        deluxe = make_flight_info(flight_info, fare,stt,phi_chieu_di,chieu)

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
                if ve[chieu]["loại_vé"] == "ECO":
                    ve["thông_tin_chung"]["giá_vé_gốc"] += hanh_ly_eco
                else:
                    ve["thông_tin_chung"]["giá_vé_gốc"] += config["HANH_LY_DELUXE"]
                ve["thông_tin_chung"]["giá_vé"] += ve["thông_tin_chung"]["giá_vé_gốc"]+ve["thông_tin_chung"]["phí_nhiên_liệu"]+ve["thông_tin_chung"]["thuế_phí_công_cộng"]
                ve["thông_tin_chung"]["giá_vé"]=str(math.floor(ve["thông_tin_chung"]["giá_vé"]))
                ve["thông_tin_chung"]["giá_vé_gốc"]=str(math.floor(ve["thông_tin_chung"]["giá_vé_gốc"]))
                ve["thông_tin_chung"]["phí_nhiên_liệu"]=str(ve["thông_tin_chung"]["phí_nhiên_liệu"])
                ve["thông_tin_chung"]["thuế_phí_công_cộng"]=str(ve["thông_tin_chung"]["thuế_phí_công_cộng"])
                data.append(ve)
                stt += 1     


        return data

    except Exception as e:
        print("❌ Lỗi xử lý dữ liệu flight:", e)
        return []
async def api_vj_v2(departure_place, return_place, departure_date ,return_date, adult_count=1, child_count=0, infant_count=0, sochieu=1):
    global token

    token = get_app_access_token_from_state()
    com = get_company(token)
    company = url_encode(com['data'][1]['company']['key'])
    #print(company)
    token = get_app_access_token_from_state()
    result_data = await get_vietjet_flight_options(
        departure_place,
        return_place,
        departure_date,
        adult_count, child_count, infant_count,company, token,return_date
    )

    if not result_data:
        return "❌ Không tải được danh sách chuyến bay"

    phi_chieu_di = None
    
    try:
        list_departure = result_data.get("data", {}).get("list_Travel_Options_Departure", [])
        
        if list_departure :
            print("lấy được list chiều đi")
            
            if list_departure[0]["fareOption"]:
                try : 
                    booking_key_chieu_di = list_departure[0]["fareOption"][0].get("BookingKey")
                    print("có booking key")
                    
                except :
                    print ( "không có booking key ,lấy TravelOptionKey ")
                    return "❌ hết vé chiều đi"
            else : 
                traveloptionkey = list_departure[0]["TravelOptionKey"]
                print("có traveloptionkey > hết vé chiều đi")
                return {
                    "status_code": 	200,
                    "trang": "1",
                    "tổng_trang": "1",
                    "session_key": "",
                    "body": [],
                    "message" : "Hết vé chiều đi"
                }
                    
            

            if booking_key_chieu_di:
                phi_chieu_di = get_tax(token, booking_key_chieu_di, adult_count, child_count, infant_count)
            else:
                
                print("⚠️ có traveloptionkey , ko có booking key hết vé chiều đi")
                return {
                    "status_code": 	200,
                    "trang": "1",
                    "tổng_trang": "1",
                    "session_key": "",
                    "body": [],
                    "message" : "Hết vé chiều đi"
                }
        else:
            
            print("⚠️ Không có dữ liệu chuyến bay chiều đi")
            return {
                "status_code": 	200,
                "trang": "1",
                "tổng_trang": "1",
                "session_key": "",
                "body": [],
                "message" : "Hết vé chiều đi"
            }
    except Exception as e:
        print("❌ ", e)
        return {
            "status_code": 401,
            "trang": "1",
            "tổng_trang": "1",
            "session_key": "",
            "body": [],
            "message" : "Lỗi khi xử lý lấy booking key hoặc tax:"
        }

    vechieudi = extract_flight(result_data, "list_Travel_Options_Departure", config_gia, phi_chieu_di["departure"])
    
    if not vechieudi:
        return {
            "status_code": 200,
            "trang": "1",
            "tổng_trang": "1",
            "session_key": "",
            "body": [],
            "message" : "Hết vé chiều đi"
        }
    print ('tạo list vé chiều đi xong')
    ket_qua =vechieudi
    ket_qua.sort(key=lambda x: int(x["thông_tin_chung"]["giá_vé"]))
    result = {
        "status_code": 200,
        "trang": "1",
        "tổng_trang": "1",
        "session_key": "",
        "body": ket_qua
    }

    return result
async def api_vj_rt_v2(departure_place, return_place, departure_date,return_date, adult_count=1, child_count=0, infant_count=0, sochieu=2):
    global token
    token = get_app_access_token_from_state()
    com = get_company(token)
    company = url_encode(com['data'][1]['company']['key'])
    #print(company)
    token = get_app_access_token_from_state()
    result_data = await get_vietjet_flight_options(
        departure_place,
        return_place,
        departure_date,
        
        adult_count, child_count, infant_count,company, token,return_date
    )

    if not result_data:
        return "❌ Không tải được danh sách chuyến bay"
    
    phi_chieu_di = None
    
    try:
        
        list_departure = result_data.get("data", {}).get("list_Travel_Options_Departure", [])
          
        list_arrival = result_data.get("data", {}).get("list_Travel_Options_Arrival", [])
        
        if list_departure :
            print("lấy được list chiều đi")
            
            if list_departure[0]["fareOption"]:
                try : 
                    booking_key_chieu_di = list_departure[0]["fareOption"][0].get("BookingKey")
                    print("có booking key chiều đi")
                    
                except :
                    print ( "không có booking key chiều đi ")
                    return "❌ hết vé chiều đi"
            else : 
                
                print(" hết vé chiều đi")
                return {
                    "status_code": 200,
                    "trang": "1",
                    "tổng_trang": "1",
                    "session_key": "",
                    "body": [],
                    "message" : "Hết vé chiều đi"
                }
        if list_arrival :
            print("lấy được list chiều về")
            
            if list_arrival[0]["fareOption"]:
                try : 
                    booking_key_chieu_ve = list_arrival[0]["fareOption"][0].get("BookingKey")
                    print("có booking key chiều về")
                    
                except :
                    print ( "không có booking key chiều về ")
                    return "❌ hết vé chiều về"
            else : 
                
                print(" hết vé chiều về")
                return {
                    "status_code": 200,
                    "trang": "1",
                    "tổng_trang": "1",
                    "session_key": "",
                    "body": [],
                    "message" : "Hết vé chiều về"
                }
        
        if booking_key_chieu_ve and booking_key_chieu_di:
            phi_chieu_di = get_tax(token, booking_key_chieu_di, adult_count, child_count, infant_count,booking_key_chieu_ve)
            
            
        
    except Exception as e:
        print("❌ Lỗi khi xử lý lấy booking key hoặc tax:", e)
        return {
                    "status_code": 401,
                    "trang": "1",
                    "tổng_trang": "1",
                    "session_key": "",
                    "body": [],
                    "message" : "Lỗi xử lý lấy booking key hoặc tax"
                }

    vechieudi = extract_flight(result_data, "list_Travel_Options_Departure", config_gia, phi_chieu_di["departure"])
    vechieuve = extract_flight(result_data, "list_Travel_Options_Arrival",  config_gia, phi_chieu_di["arrival"])
    if not vechieudi:
        return {
            "status_code": 200,
            "trang": "1",
            "tổng_trang": "1",
            "session_key": "",
            "body": [],
            "message" : "Hết vé chiều đi"
        }
    if not vechieuve:
        return {
            "status_code": 200,
            "trang": "1",
            "tổng_trang": "1",
            "session_key": "",
            "body": [],
            "message" : "Hết vé chiều ve"
        }
    ket_qua = []

    for chieu_di in vechieudi:
        for chieu_ve in vechieuve:
            # Parse giá trị số từ string
            gia_ve = int(chieu_di["thông_tin_chung"]["giá_vé"]) + int(chieu_ve["thông_tin_chung"]["giá_vé"])
            gia_ve_goc = int(chieu_di["thông_tin_chung"]["giá_vé_gốc"]) + int(chieu_ve["thông_tin_chung"]["giá_vé_gốc"])
            phi_nhien_lieu = int(chieu_di["thông_tin_chung"]["phí_nhiên_liệu"]) + int(chieu_ve["thông_tin_chung"]["phí_nhiên_liệu"])
            thue_phi = int(chieu_di["thông_tin_chung"]["thuế_phí_công_cộng"]) + int(chieu_ve["thông_tin_chung"]["thuế_phí_công_cộng"])
            
            # Số ghế còn lấy số nhỏ hơn
            so_ghe_con = min(int(chieu_di["thông_tin_chung"]["số_ghế_còn"]), int(chieu_ve["thông_tin_chung"]["số_ghế_còn"]))
            
            # Hành lý giữ nguyên "None" như mẫu
            hanh_ly_vna = "None"

            to_hop = {
                "chiều đi": chieu_di["chiều đi"],
                "chiều về": chieu_ve["chiều về"],
                "thông_tin_chung": {
                    "giá_vé": str(gia_ve),
                    "giá_vé_gốc": str(gia_ve_goc),
                    "phí_nhiên_liệu": str(phi_nhien_lieu),
                    "thuế_phí_công_cộng": str(thue_phi),
                    "số_ghế_còn": str(so_ghe_con),
                    "hành_lý_vna": hanh_ly_vna
                }
            }

            ket_qua.append(to_hop)
            ket_qua.sort(key=lambda x: int(x["thông_tin_chung"]["giá_vé"]))
    result = {
        "status_code": 200,
        "trang": "1",
        "tổng_trang": "1",
        "session_key": "",
        "body": ket_qua
    }

    return result