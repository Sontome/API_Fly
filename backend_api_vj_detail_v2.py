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



def lamtron(so):
        return math.ceil(so / 100) * 100
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
    url = "https://agentapi.vietjetair.com/api/v14/Booking/getlistcompanies"
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
    url = "https://agentapi.vietjetair.com/api/v14/Booking/quotationwithoutpassenger"
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
def get_ancillary_options(bearer_token, booking_key, booking_key_return=None):
    url = "https://agentapi.vietjetair.com/api/v14/Booking/ancillaryOptions"

    params = {
        "bookingKey": booking_key,
        "bookingKeyReturn": booking_key_return,
        "languageCode": "vi"
    }

    headers = {
        "accept": "application/json, text/plain, */*",
        "accept-language": "vi-VN,vi;q=0.9,en-US;q=0.8,en;q=0.7",
        "authorization": f"Bearer {bearer_token}",
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

    try:
        result = {
            "chiều_đi":{
                "HANH_LY_DELUXE": 0,
                "HANH_LY_ECO": 0,
                "HANH_LY": 0,
                "KEY_HANH_LY":""
            },
            "chiều_về":{
                "HANH_LY_DELUXE": 0,
                "HANH_LY_ECO": 0,
                "HANH_LY": 0,
                "KEY_HANH_LY":""

            }
        }
        response = requests.get(url, headers=headers, params=params)
        data = response.json()
        
        data= data.get("data", [])
        
        baggage_item = next((item for item in data if item.get("code") == "Baggage"), None)
        
        if baggage_item:
            ancillaries_departure = baggage_item.get("ancillariesDeparture", [])
            ancillaries_return = baggage_item.get("ancillariesReturn", [])
            
        if ancillaries_departure:
            
            hành_lý_ECO_chiều_đi = next((item for item in ancillaries_departure if item.get("originalName") == "Bag 20kgs"), None)
            
            giá_hành_lý_eco_chiều_đi = hành_lý_ECO_chiều_đi.get("totalAmount",0)
            result["chiều_đi"]["HANH_LY_ECO"]= giá_hành_lý_eco_chiều_đi
            result["chiều_đi"]["HANH_LY"]= giá_hành_lý_eco_chiều_đi
        if ancillaries_return:
            hành_lý_ECO_chiều_về = next((item for item in ancillaries_return if item.get("originalName") == "Bag 20kgs"), None)
            giá_hành_lý_eco_chiều_về = hành_lý_ECO_chiều_về.get("totalAmount",0)
            
            result["chiều_về"]["HANH_LY_ECO"]= (giá_hành_lý_eco_chiều_về)
            result["chiều_về"]["HANH_LY"]= (giá_hành_lý_eco_chiều_về)
        defaultWithFare_item = next((item for item in data if item.get("code") == "DefaultWithFare"), None)  
        default_ancillaries_departure=[]
        default_ancillaries_return=[]
        if defaultWithFare_item :
            
            default_ancillaries_departure = defaultWithFare_item.get("ancillariesDeparture", [])
            default_ancillaries_return = defaultWithFare_item.get("ancillariesReturn", [])
        if default_ancillaries_departure:
            hành_lý_deluxe_chiều_đi = next((item for item in default_ancillaries_departure if item.get("originalName") == "Deluxe 20kgs"), [])
            giá_hành_lý_deluxe_chiều_đi = hành_lý_deluxe_chiều_đi.get("totalAmount",0)
            result["chiều_đi"]["HANH_LY"]= (giá_hành_lý_deluxe_chiều_đi)
            result["chiều_đi"]["HANH_LY_DELUXE"]= (giá_hành_lý_deluxe_chiều_đi)
        if default_ancillaries_return:
            hành_lý_deluxe_chiều_về = next((item for item in default_ancillaries_return if item.get("originalName") == "Deluxe 20kgs"), [])
            giá_hành_lý_deluxe_chiều_về = hành_lý_deluxe_chiều_về.get("totalAmount",0)
            result["chiều_về"]["HANH_LY_DELUXE"]= (giá_hành_lý_deluxe_chiều_về)
            result["chiều_về"]["HANH_LY"]= (giá_hành_lý_deluxe_chiều_về)
        return result
    except Exception as e:
        print (e)
        return {}

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
                "giá_vé": lamtron(adult_total),
                "giá_vé_gốc": lamtron(adult_base),
                "phí_nhiên_liệu": lamtron(adult_fuel),
                "thuế_phí_công_cộng": lamtron(adult_tax)
            },
            "trẻ em": {
                "giá_vé": lamtron(child_total),
                "giá_vé_gốc": lamtron(child_base),
                "phí_nhiên_liệu": lamtron(child_fuel),
                "thuế_phí_công_cộng": lamtron(child_tax)
            },
            "trẻ sơ sinh": {
                "giá_vé": lamtron(infant_total),
                "giá_vé_gốc": lamtron(infant_base),
                "phí_nhiên_liệu": lamtron(infant_fuel),
                "thuế_phí_công_cộng": lamtron(infant_tax)
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
async def api_vj_detail_v2(booking_key, adult_count=1, child_count=0, infant_count=0):
    global token

    token = get_app_access_token_from_state()
    
    
    #print(company)
    token = get_app_access_token_from_state()
    result_data = get_tax(token,booking_key,adult_count, child_count, infant_count)
    
    
    result = convert_price(result_data)
    giá_hành_lý = get_ancillary_options(token,booking_key)
    if giá_hành_lý:
        #print(giá_hành_lý)
        result["detail"]["người lớn"]["giá_vé"] +=lamtron(giá_hành_lý["chiều_đi"]["HANH_LY"])
        result["detail"]["người lớn"]["giá_vé_gốc"] +=giá_hành_lý["chiều_đi"]["HANH_LY"]
        result["detail"]["trẻ em"]["giá_vé"] +=lamtron(giá_hành_lý["chiều_đi"]["HANH_LY"])
        result["detail"]["trẻ em"]["giá_vé_gốc"] +=giá_hành_lý["chiều_đi"]["HANH_LY"]
        if child_count == 0:
           result["detail"]["trẻ em"]["giá_vé"] = 0
           result["detail"]["trẻ em"]["giá_vé_gốc"] = 0
           result["detail"]["trẻ em"]["phí_nhiên_liệu"] = 0
           result["detail"]["trẻ em"]["thuế_phí_công_cộng"] = 0
        
    else :
        
        return {
                    "status_code": 	200,
                    "trang": "1",
                    "tổng_trang": "1",
                    "session_key": "",
                    "body": [],
                    "message" : "Không lấy được giá hành lý"
                }
    
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
async def api_vj_detail_rt_v2(booking_key,booking_key_arrival, adult_count=1, child_count=0, infant_count=0):
    global token

    token = get_app_access_token_from_state()
    
    
    #print(company)
    token = get_app_access_token_from_state()
    result_data = get_tax(token,booking_key,adult_count, child_count, infant_count,booking_key_arrival)
    
    
    result = convert_price(result_data)
    giá_hành_lý = get_ancillary_options(token,booking_key,booking_key_arrival)
    if giá_hành_lý:
        #print(giá_hành_lý)
        result["detail"]["người lớn"]["giá_vé"] +=lamtron(giá_hành_lý["chiều_đi"]["HANH_LY"])
        result["detail"]["người lớn"]["giá_vé_gốc"] +=giá_hành_lý["chiều_đi"]["HANH_LY"]
        result["detail"]["trẻ em"]["giá_vé"] +=lamtron(giá_hành_lý["chiều_đi"]["HANH_LY"])
        result["detail"]["trẻ em"]["giá_vé_gốc"] +=giá_hành_lý["chiều_đi"]["HANH_LY"]
        result["detail"]["người lớn"]["giá_vé"] +=lamtron(giá_hành_lý["chiều_về"]["HANH_LY"])
        result["detail"]["người lớn"]["giá_vé_gốc"] +=giá_hành_lý["chiều_về"]["HANH_LY"]
        result["detail"]["trẻ em"]["giá_vé"] +=lamtron(giá_hành_lý["chiều_về"]["HANH_LY"])
        result["detail"]["trẻ em"]["giá_vé_gốc"] +=giá_hành_lý["chiều_về"]["HANH_LY"]
        if child_count == 0:
           result["detail"]["trẻ em"]["giá_vé"] = 0
           result["detail"]["trẻ em"]["giá_vé_gốc"] = 0
           result["detail"]["trẻ em"]["phí_nhiên_liệu"] = 0
           result["detail"]["trẻ em"]["thuế_phí_công_cộng"] = 0
        
    else :
        
        return {
                    "status_code": 	200,
                    "trang": "1",
                    "tổng_trang": "1",
                    "session_key": "",
                    "body": [],
                    "message" : "Không lấy được giá hành lý"
                }
    
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
