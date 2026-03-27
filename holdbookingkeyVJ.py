import requests
import json
from utils_telegram import send_mess
from datetime import datetime
import os
import math
import asyncio
import subprocess
import urllib.parse
global token
from backend_supabase_kakao import add_kakao_pnr
# 🔧 Giá mặc định



def get_full_name(data):
    for group in ["nguoilon", "treem", "embe"]:
        if data.get(group):
            p = data[group][0]
            full_name = f"{p['Họ']} {p['Tên']}"
            return full_name.replace(",", "").strip()
    return None
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
    url = "https://agentapi.vietjetair.com/api/v14/Booking/ancillaryOptions"
    if booking_key_return:
        params = {
            "bookingKey": booking_key,
            "bookingKeyReturn": booking_key_return,
            "languageCode": "vi"
        }
    else : 
        params = {
            "bookingKey": booking_key,
            
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
            "key_hành_lý_chiều_đi" :"",
            "key_hành_lý_chiều_về" :"",
            "loai_hành_lý_chiều_về" :"",
            "loai_hành_lý_chiều_đi" :"",
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
            result["loai_hành_lý_chiều_đi"]= "ECO"
        if ancillaries_return:
            hành_lý_ECO_chiều_về = next((item for item in ancillaries_return if item.get("originalName") == "Bag 20kgs"), None)
            giá_hành_lý_eco_chiều_về = hành_lý_ECO_chiều_về.get("purchaseKey","")
            
            
            result["key_hành_lý_chiều_về"]= giá_hành_lý_eco_chiều_về
            result["loai_hành_lý_chiều_về"]= "ECO"
        defaultWithFare_item = next((item for item in data if item.get("code") == "DefaultWithFare"), None)  
        default_ancillaries_departure=[]
        default_ancillaries_return=[]
        if defaultWithFare_item :
            
            default_ancillaries_departure = defaultWithFare_item.get("ancillariesDeparture", [])
            default_ancillaries_return = defaultWithFare_item.get("ancillariesReturn", [])
        if default_ancillaries_departure:
            hành_lý_deluxe_chiều_đi = next((item for item in default_ancillaries_departure if item.get("originalName") == "Bag 20kgs"), [])
            giá_hành_lý_deluxe_chiều_đi = hành_lý_deluxe_chiều_đi.get("purchaseKey","")
            result["key_hành_lý_chiều_đi"]= giá_hành_lý_deluxe_chiều_đi
            result["loai_hành_lý_chiều_đi"]= "DELUXE"
            
        if default_ancillaries_return:
            hành_lý_deluxe_chiều_về = next((item for item in default_ancillaries_return if item.get("originalName") == "Bag 20kgs"), [])
            giá_hành_lý_deluxe_chiều_về = hành_lý_deluxe_chiều_về.get("purchaseKey","")
            
            result["key_hành_lý_chiều_về"]= giá_hành_lý_deluxe_chiều_về
            result["loai_hành_lý_chiều_về"]= "DELUXE"
        print (result)
        return result
    except Exception as e:
        print (e)
        return {}
def get_payment_methods(token,bookingkey_departure, bookingkey_arrival=None):
    url = "https://agentapi.vietjetair.com/api/v13/Booking/paymentMethods"
    
    # Params truyền qua URL
    if bookingkey_arrival:
        params = {
            "bookingkeydeparture": bookingkey_departure,
            "bookingkeyarrival": bookingkey_arrival
        }
    else:
        params = {
            "bookingkeydeparture": bookingkey_departure
            
        }

    headers = {
        "accept": "application/json, text/plain, */*",
        "authorization": f"Bearer {token}",
        "content-type": "application/json",
        "languagecode": "vi",
        "platform": "3",
        "priority": "u=1, i",
        "referer": "https://agents2.vietjetair.com/"
    }

    try:
        response = requests.get(url, headers=headers, params=params)
        response.raise_for_status()
        
        data = response.json()
        data0  = data.get("data",[])
        paykey = data0[0].get("key","")

        
        return paykey
    except requests.exceptions.RequestException as err:
        print (response)
        print("❌ Không lấy được get_payment_methods", err)
        print("Status:", response.status_code if 'response' in locals() else "Unknown")
      
        return None  
def create_booking(payload_dict, bearer_token):
    url = "https://agentapi.vietjetair.com/api/v14/Booking/createbooking"

    headers = {
        "accept": "application/json, text/plain, */*",
        "authorization": f"Bearer {bearer_token}",
        "content-type": "application/json",
        "languagecode": "vi",
        "platform": "3",
        "referer": "https://agents2.vietjetair.com/"
    }

    try:
        res = requests.post(url, headers=headers, json=payload_dict)
        res.raise_for_status()
        
        return res.json()
    except Exception as e:
        print("❌ Lỗi create booking:", e)
        if res is not None:
            print("Status:", res.status_code)
            print("Response text:", res.text[:1000])  # in 1000 ký tự đầu
        return None  


def build_passenger_embe(embe_list, passengers):
    embe_index = 0

    for i, passenger in enumerate(passengers):
        if passenger["fareApplicability"]["adult"] and embe_index < len(embe_list):
            embe = embe_list[embe_index]
            gioitinh = embe["Giới_tính"].strip().lower()
            gender = "Male" if gioitinh == "nam" else "Female"

            infant_data = {
                "index": embe_index + 1,
                "passengerSuffix": f" {embe_index + 1}",
                "reservationProfile": {
                    "lastName": embe["Họ"].upper(),
                    "firstName": embe["Tên"].upper(),
                    "gender": gender,
                    "passport": {
                        "number": embe["Hộ_chiếu"]
                    }
                }
            }

            passenger["infants"] = [infant_data]
            embe_index += 1
    return passengers
def build_passenger_data(passenger_list,soluong,iso,exten,phone,email,start_index=1, is_child=False, is_infant=False):
    passengers = []
    index = start_index
   

    for p in passenger_list:
        gioitinh = p["Giới_tính"].strip().lower()
        title = "Mr" if gioitinh == "nam" else "Mrs"
        if is_child or is_infant:
            title = None  # sửa lại null → None (Python chuẩn)
        gender = "Male" if gioitinh == "nam" else "Female"

        quoctich = p["Quốc_tịch"].strip().upper()
        nation_code = "VNM" if quoctich == "VN" else "KOR"
        nation_name = "Vietnam" if quoctich == "VN" else "South Korea"

        sendmail_flag = True if index == 1 else False
        Suffix= index
        if is_child : 
            Suffix= index-soluong
        passenger = {
            "index": index,
            "sendmail": sendmail_flag,
            "passengerSuffix": f" {Suffix}" ,
            "fareApplicability": {
                "child": is_child,
                "adult": not is_child and not is_infant
            },
            "reservationProfile": {
                "lastName": p["Họ"],
                "firstName": p["Tên"],
                "title": title,
                "gender": gender,
                "address": {
                    "location": {
                        "country": {
                            "code": nation_code,
                            "name": nation_name
                        }
                    }
                } if index == 1 else {"location": {}},
                
                "personalContactInformation" :{},
                "passport": {
                    "number": p["Hộ_chiếu"]
                },
                "loyaltyProgram": {}
            }
        }
        if index == 1 and is_child==False:
            passenger["reservationProfile"]["nationCountry"]={
                "code": nation_code,
                "name": nation_name
            }
            passenger["reservationProfile"]["personalContactInformation"] = {
                "number": phone,
                "mobileIsoCode": iso,
                "mobileNumber": phone,
                "extension": exten,
                "isoCode": iso,
                
                "email": email
            }

        passengers.append(passenger)
        index += 1

    return passengers, index


def build_journeys(passengers_count, bookingkey, bookingkeychieuve=None):
    journeys = [{
        "index": 1,
        "passengerJourneyDetails": [
            {"passenger": {"index": i + 1}, "bookingKey": bookingkey}
            for i in range(passengers_count)
        ]
    }]
    if bookingkeychieuve:
        journeys.append({
            "index": 2,
            "passengerJourneyDetails": [
                {"passenger": {"index": i + 1}, "bookingKey": bookingkeychieuve}
                for i in range(passengers_count)
            ]
        })
    return journeys

def build_ancillary(passengers_count, keyhanhly=None, keyhanhlychieuve=None):
    ancillary = []
    if keyhanhly:
        ancillary = [
            {
                "purchaseKey": keyhanhly,
                "passenger": { "index": i + 1 },
                "journey": { "index": 1 }
            }
            for i in range(passengers_count)
        ]
    if keyhanhlychieuve:
        ancillary += [
            {
                "purchaseKey": keyhanhlychieuve,
                "passenger": { "index": i + 1 },
                "journey": { "index": 2 }
            }
            for i in range(passengers_count)
        ]
    return ancillary

def build_payload_all(passenger_data, bookingkey, keyhanhly, keypaylate,sanbaydi,iso,exten,phone,email, bookingkeychieuve=None, keyhanhlychieuve=None):
    all_passengers = []
    index = 1
    soluong = len(passenger_data.get("nguoilon", [])) 
    soluongembe = len(passenger_data.get("embe", [])) 
    nguoilon, index = build_passenger_data(passenger_data.get("nguoilon", []),soluong,iso,exten,phone,email,start_index=index, is_child=False)
    all_passengers += nguoilon
    treem, index = build_passenger_data(passenger_data.get("treem", []),soluong,iso,exten,phone,email,start_index=index, is_child=True)
    all_passengers += treem
    if soluongembe:
        all_passengers= build_passenger_embe(passenger_data.get("embe", []),all_passengers)
    
    total_passengers = len(all_passengers)
    journeys = build_journeys(total_passengers, bookingkey, bookingkeychieuve)
    ancillaries = build_ancillary(total_passengers, keyhanhly, keyhanhlychieuve)
    #print(ancillaries)
    #print(journeys)
    #print(all_passengers)
    payload = {
        "languagecode": "vi",
        "bookingInformation": {
            "contactInformation": {
                "isoCode": "KR",
                "extension": "82",
                "phoneNumber": "1085092507",
                "name": "KOR HANVIET AIR",
                "email": "hanvietair.service@gmail.com"
            }
        },
        "departureAirportCode": sanbaydi,
        "passengers": all_passengers,
        "journeys": journeys,
        "seatSelections": [],
        "ancillaryPurchases": ancillaries,
        "paymentTransactions": [
            {
                "allPassengers": True,
                "paymentMethod": {
                    "key": keypaylate,
                    "identifier": "PL"
                },
                "currencyAmounts": [
                    {
                        "totalAmount": 0,
                        "exchangeRate": 1,
                        "currency": { "code": "KRW" }
                    }
                ]
            }
        ]
    }
    return payload

def booking(passenger_data,bookingkey,sochieu,sanbaydi,iso="VN",exten="82",phone="1035463396",email="hanvietair247@gmail.com" ,bookingkeychieuve=None,phonekakao="",emailkakao=""):
    token = get_app_access_token_from_state()
    get_company(token)
    token = get_app_access_token_from_state()
    if sochieu =="RT":
        keyhanhly = get_ancillary_options(token,bookingkey,bookingkeychieuve)
        
    else :
        keyhanhly = get_ancillary_options(token,bookingkey)
    if keyhanhly["loai_hành_lý_chiều_đi"] == "ECO":
        keyhanhlychieudi = keyhanhly["key_hành_lý_chiều_đi"]
    else :
        keyhanhlychieudi = None
    if keyhanhly["loai_hành_lý_chiều_về"] == "ECO":    
        keyhanhlychieuve = keyhanhly["key_hành_lý_chiều_về"]
    else:
        keyhanhlychieuve = None
        
    keypaylate = get_payment_methods(token,bookingkey,bookingkeychieuve)
    print(keyhanhly)
    #print(keypaylate)
    payload = build_payload_all(passenger_data, bookingkey, keyhanhlychieudi, keypaylate,sanbaydi,iso,exten,phone,email, bookingkeychieuve, keyhanhlychieuve)
    #print(payload)
    result = create_booking(payload,token)
    #print(result)
    mess = result["message"]
    
    
    try:
        mã_giữ_vé = result["data"]["locator"]
        hạn_thanh_toán = result["data"]["datePayLater"]
        print(mã_giữ_vé)
        print(hạn_thanh_toán)
        try :
            tenkakao = get_full_name(passenger_data)
            add_kakao_pnr(phone=phonekakao,name=tenkakao,pnr=mã_giữ_vé,email=emailkakao)
        except Exception as e:
            print("❌ Lỗi add_kakao_pnr:", e)
        mess = "Giữ vé VJ thành công! PNR: " + mã_giữ_vé
        try:
            asyncio.run(send_mess(mess))
        except :
            pass
        return {
            "mã_giữ_vé" : mã_giữ_vé,
            "hạn_thanh_toán" : hạn_thanh_toán,
            "mess" : mess
        }
    except :
        print(mess)
        return {
            "mã_giữ_vé" : "",
            "hạn_thanh_toán" : "",
            "mess" : mess
        }
    


ds_khach = {
    "nguoilon": [
        {"Họ": "Nguyen", "Tên": "An", "Hộ_chiếu": "123123123123", "Giới_tính": "nam", "Quốc_tịch": "VN"},
        {"Họ": "Nguyen", "Tên": "An", "Hộ_chiếu": "123123123124", "Giới_tính": "nam", "Quốc_tịch": "VN"}
    ],
    "treem": [
        {"Họ": "Nguyen", "Tên": "An", "Hộ_chiếu": "123123123125", "Giới_tính": "nam", "Quốc_tịch": "VN"}
        
    ],
    "embe": [
        {"Họ": "Nguyen", "Tên": "An", "Hộ_chiếu": "123123123125", "Giới_tính": "nam", "Quốc_tịch": "VN"}
    ]
}

















