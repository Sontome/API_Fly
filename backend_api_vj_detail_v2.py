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
                "Airport Security": 0,
                "Airport Security CHD": 0,
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
                "Airport Security": 0,
                "Airport Security CHD": 0,
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
def convert_price(data):
    # Hàm tính toán cho từng chiều
    def calc_detail(flight_data):
        fares = flight_data.get("fares", 0)
        feetaxs = flight_data.get("feetaxs", {})
        services = flight_data.get("services", {})

        # Người lớn
        adult_base = fares
        adult_fuel = services.get("Management Fee ITL", 0) + services.get("Fuel Surcharge", 0)
        adult_tax = feetaxs.get("Admin Fee ITL", 0) + feetaxs.get("Airport Tax ITL", 0) + feetaxs.get("Airport Security", 0)
        adult_total = adult_base + adult_fuel + adult_tax

        # Trẻ em
        child_base = fares
        child_fuel = services.get("Management Fee ITL", 0) + services.get("Fuel Surcharge", 0)
        child_tax = feetaxs.get("Admin Fee ITL", 0) + feetaxs.get("Airport Tax ChidITL", 0)+ feetaxs.get("Airport Security CHD", 0)
        child_total = child_base + child_fuel + child_tax

        # Trẻ sơ sinh
        infant_base = 0
        infant_fuel = 0
        infant_tax = feetaxs.get("INFANT CHARGE ITL", 0)
        infant_total = infant_base + infant_fuel + infant_tax

        return {
            "người lớn": {
                "giá_vé": adult_total,
                "giá_vé_gốc": adult_base,
                "phí_nhiên_liệu": adult_fuel,
                "thuế_phí_công_cộng": adult_tax
            },
            "trẻ em": {
                "giá_vé": child_total,
                "giá_vé_gốc": child_base,
                "phí_nhiên_liệu": child_fuel,
                "thuế_phí_công_cộng": child_tax
            },
            "trẻ sơ sinh": {
                "giá_vé": infant_total,
                "giá_vé_gốc": infant_base,
                "phí_nhiên_liệu": infant_fuel,
                "thuế_phí_công_cộng": infant_tax
            }
        }

    # Khởi tạo kết quả
    detail = {
        "người lớn": {
            "giá_vé": 0,
            "giá_vé_gốc": 0,
            "phí_nhiên_liệu": 0,
            "thuế_phí_công_cộng": 0
        },
        "trẻ em": {
            "giá_vé": 0,
            "giá_vé_gốc": 0,
            "phí_nhiên_liệu": 0,
            "thuế_phí_công_cộng": 0
        },
        "trẻ sơ sinh": {
            "giá_vé": 0,
            "giá_vé_gốc": 0,
            "phí_nhiên_liệu": 0,
            "thuế_phí_công_cộng": 0
        }
    }

    # Nếu có departure
    if "departure" in data:
        dep_detail = calc_detail(data["departure"])
        for k in detail:
            for subk in detail[k]:
                detail[k][subk] += dep_detail[k][subk]

    # Nếu có arrival
    if "arrival" in data:
        arr_detail = calc_detail(data["arrival"])
        for k in detail:
            for subk in detail[k]:
                detail[k][subk] += arr_detail[k][subk]

    return {"detail": detail}
async def api_vj_detail_v2(booking_key, adult_count=1, child_count=0, infant_count=0,booking_key_arrival = None):
    global token

    token = get_app_access_token_from_state()
    com = get_company(token)
    
    #print(company)
    token = get_app_access_token_from_state()
    result_data = get_tax(token,booking_key,adult_count, child_count, infant_count,booking_key_arrival)
    result = convert_price(result_data)
    if not result:
        return {
                    "status_code": 	200,
                    "trang": "1",
                    "tổng_trang": "1",
                    "session_key": "",
                    "body": [],
                    "message" : "Không lấy được phí"
                }

    else :
        return {
                    "status_code": 	200,
                    "trang": "1",
                    "tổng_trang": "1",
                    "session_key": "",
                    "body": [result]
                    
                }    