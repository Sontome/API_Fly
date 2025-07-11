import requests
import json

from datetime import datetime
import os
import math

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
def get_ancillary_options(bearer_token, booking_key, booking_key_return=None):
    url = "https://agentapi.vietjetair.com/api/v13/Booking/ancillaryOptions"

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
            
            giá_hành_lý_eco_chiều_đi = hành_lý_ECO_chiều_đi.get("purchaseKey","")
            
            result["key_hành_lý_chiều_đi"]= giá_hành_lý_eco_chiều_đi
        if ancillaries_return:
            hành_lý_ECO_chiều_về = next((item for item in ancillaries_return if item.get("originalName") == "Bag 20kgs"), None)
            giá_hành_lý_eco_chiều_về = hành_lý_ECO_chiều_về.get("purchaseKey","")
            
            
            result["key_hành_lý_chiều_về"]= giá_hành_lý_eco_chiều_về
        defaultWithFare_item = next((item for item in data if item.get("code") == "DefaultWithFare"), None)  
        default_ancillaries_departure=[]
        default_ancillaries_return=[]
        if defaultWithFare_item :
            
            default_ancillaries_departure = defaultWithFare_item.get("ancillariesDeparture", [])
            default_ancillaries_return = defaultWithFare_item.get("ancillariesReturn", [])
        if default_ancillaries_departure:
            hành_lý_deluxe_chiều_đi = next((item for item in default_ancillaries_departure if item.get("originalName") == "Deluxe 20kgs"), [])
            giá_hành_lý_deluxe_chiều_đi = hành_lý_deluxe_chiều_đi.get("purchaseKey","")
            result["key_hành_lý_chiều_đi"]= giá_hành_lý_deluxe_chiều_đi
            
        if default_ancillaries_return:
            hành_lý_deluxe_chiều_về = next((item for item in default_ancillaries_return if item.get("originalName") == "Deluxe 20kgs"), [])
            giá_hành_lý_deluxe_chiều_về = hành_lý_deluxe_chiều_về.get("purchaseKey","")
            
            result["key_hành_lý_chiều_về"]= giá_hành_lý_deluxe_chiều_về
        return result
    except Exception as e:
        print (e)
        return {}
    
token = get_app_access_token_from_state()
get_company(token)
token = get_app_access_token_from_state()


key0="Mshf45MT70SUbvc9j1n0%C2%A5iEqoDoHXUtXQZLDaPrJfZ255y8b%C6%92zovWUG%C2%A5zE8l3WYMMLhW%C2%A5jCBk%C6%92OlHl3Be82PmMPj5rhwjMEIKY65oOtSwHD31Avwlyj%C2%A5Q8V7sLbQCthw6W4j8U2HlUGfp9sIAbF4JqUqEKT14l7v4AcOOwIkYokywbCqHigOblxeRzaabeyNuARc2CjVcjPSXFC6YLCFsjZ%C2%A5%C2%A5HIl4bTfNH2O%C6%92i%C6%92huGbO28nHOMg%C2%A5RN6%C2%A5QjfxfApDDKNkECHkB56g67gfU7yJu5uw0TKhJCnaGtVkPxBTzPKGLWXozmyIMWo%C2%A5mVtEElcmLAvQ81IxaMUG%C6%92bAobi1JN7n%C6%92IbtmdSArb1oQLruSJ9rVm5UEuoG9y0wOn6aSld%C2%A5F8yWgvw3%C2%A506Z7cr2yVrbpga20K%C2%A5LkfIYqY2agKt1Vpb35Peu96Pox1hW85QdWERcIuN2etaXCBHDtcCcMp5sWQ8NIsfEQYZEP7ehlThb3ledoOSJi8fd5DjHgKZ50AKvKKPjtAY1Py3ug8NfahgCiTZqlYd%C6%92jPgvUpFBRqJiw%C6%92P0="
key1="Mshf45MT70SUbvc9j1n0%C2%A5pItqj6RM9X%C6%92tj1EqDCLxAOISt2WtYEmWPV0WpUUYBrZjkVNS2eAF2knxYE6SGlkc4gCHR7NqNxSwtrC%C6%925YuHDGl7Qv79LP%C6%92Hkdb7zAK%C6%92yptqAkcxC9o%C6%92UoyM28rNgOl%C2%A5t9S6Zkhn0hbkzj017bVyRqmT8I8a7mSd%C6%92ZyGjOvA1Fz50iuNwrQBAOQYHJS%C6%92rE62yNxHXsF78uWMOX0KeU4cRqb0QzMHwJb1SpA40p%C2%A5XUnGfjp%C2%A5Ph3QQZqPUf8ufD1mpdpwj3YUW2iS36qMmy6p%C6%92yuIRd2G8obFM3XJOI5zO%C2%A5pn6ciT80O0V5QALcK%C6%925m1d0a%C2%A5dXr8ruLxThVLbu4Ti%C6%92jTAov1ymLvycdP3QKSw%C2%A5cqIlvtkyKaQjrKzwmvNvElG%C6%92T36vlpGMMVcWpsFXvQtJvkSXjxtXDMA7hpi7GfFDYzimAJ5m3TID4FfQuK6YhEyELMRUld5rIHx40Bsjmep282OzzVNmszuOlY73WmT1vwpYkQqhZO%C2%A5N2e4C50t9AUxfguM3Nb%C6%92HIODhr2IpXPpghY="
test = get_ancillary_options(token,key0,key1)
print(test)