import requests
import json

from datetime import datetime

CONFIG_GIA_FILE = "config_gia.json"
import subprocess
import urllib.parse
global token
# 🔧 Giá mặc định




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
def get_lowfare_options(bearer_token, company,departure,departure_date ,arrival,return_date=None):
    url = "https://agentapi.vietjetair.com/api/v13/Booking/lowFareOptions"

    params = {
        "cityPair": departure +"-"+arrival,
        "departure": departure_date,
        "currency": "KRW",
        "adultCount": "1" ,
        "childCount": "0",
        "infantCount": "0",
        "cabinClass": "Y",
        "Return": return_date,
        "company": company



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
            "chiều_đi":[],
            "chiều_về":[],
            "resultcode" : 0,
            "message" : ""
        }  
        response = requests.get(url, headers=headers, params=params)
        res = response.json()
        data = res.get("data",[])
        datachieudi = data.get("departure",[])
        datachieuve = data.get("arrival",[])
        result["chiều_đi"] = datachieudi
        result["chiều_về"] = datachieuve
        return result
    except Exception as e:
        print (e)
        return result
def lay_danh_sach_ve_re_nhat(departure,departure_date ,sochieu,arrival,return_date=None):
    if sochieu == "OW":
        
        return_date= None
    token = get_app_access_token_from_state()
    company = get_company(token)
    token = get_app_access_token_from_state()
    result = get_lowfare_options(token,company,departure,departure_date,arrival,return_date)
    return result

test = lay_danh_sach_ve_re_nhat("ICN","2025-07-15","OW","HAN")
print(test)
