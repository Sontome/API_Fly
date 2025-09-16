import json
import httpx
from datetime import datetime
import subprocess

vjkrw = "state.json"
vjvnd = "statevnd.json"
vjkrwpy = "getcokivj.py"
vjvndpy = "getcokivjvnd.py"


def get_app_access_token_from_state(file_path=vjkrw):
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)
    except FileNotFoundError:
        print(f"⚠️ Không tìm thấy file {file_path}")
        return None

    origins = data.get("origins", [])
    for origin in origins:
        local_storage = origin.get("localStorage", [])
        for item in local_storage:
            if item.get("name") == "app_access_token":
                return item.get("value")
    return None


def get_company(token: str, file_path=vjkrwpy):
    url = "https://agentapi.vietjetair.com/api/v13/Booking/getlistcompanies"
    headers = {
        "accept": "application/json, text/plain, */*",
        "authorization": f"Bearer {token}",
        "content-type": "application/json",
        "languagecode": "vi",
        "platform": "3"
    }

    with httpx.Client(timeout=10) as client:
        resp = client.get(url, headers=headers)

    if resp.status_code == 401:
        print("🔐 Token hết hạn. Chạy lại script cookie...")
        try:
            subprocess.run(["python", file_path])
        except Exception as e:
            print("❌ Lỗi khi reload cookie:", e)
        return None

    if resp.status_code == 200:
        return resp.json()
    else:
        print(f"Lỗi khi lấy công ty - status: {resp.status_code}")
        print(resp.text)
        return None


def get_vietjet_pnr(token, PNR):
    base_url = "https://agentapi.vietjetair.com/api/v13/EditBooking/getreservationdetailbylocator"
    params = {"locator": PNR}

    headers = {
        'accept': 'application/json, text/plain, */*',
        'authorization': f"Bearer {token}",
        'content-type': 'application/json',
        'languagecode': 'vi',
        'platform': '3'
    }

    with httpx.Client(timeout=10) as client:
        response = client.get(base_url, headers=headers, params=params)

    if response.status_code == 200:
        result = response.json()
        if result["resultcode"] == 1:
            if result["data"]["paymentstatus"]  == True:

                return result["data"]["key"]
            else :
                return ("VJ")
        else:
            return None
    else:
        print(f"Lỗi khi gọi API check PNR: {response.status_code}")
        print(response.text)
        return None


def sendmail(token, reservationKey):
    base_url = "https://agentapi.vietjetair.com/api/v13/EditBooking/sendmailitinerary"
    payload  = {
        "reservationKey": reservationKey,
        "additionalMail": "HANVIETAIR.SERVICE@GMAIL.COM",
        "languagecode" : "vi"

    
    
    }

    headers = {
        'accept': 'application/json, text/plain, */*',
        'authorization': f"Bearer {token}",
        'content-type': 'application/json',
        'languagecode': 'vi',
        'platform': '3'
    }

    with httpx.Client(timeout=10) as client:
        response = client.post(base_url, headers=headers, json=payload)
      
    if response.status_code == 200:
        result = response.json()
        if result["resultcode"] == 1:
            return result["message"]
        else:
            return None
    else:
        print(f"Lỗi khi gọi API gửi mail: {response.status_code}")
        print(response.text)
        return None





def sendmail_vj(pnr):
    token = get_app_access_token_from_state()
    company_info = get_company(token)

    token = get_app_access_token_from_state()
    reservationKey = get_vietjet_pnr(token, pnr)

    if reservationKey:
        if reservationKey =="VJ":
            return ("VJ")

        print("krw")
        result = sendmail(token, reservationKey)
        print(result)
        
    else:
        token = get_app_access_token_from_state(vjvnd)
        company_info = get_company(token, vjvndpy)
        token = get_app_access_token_from_state(vjvnd)
        reservationKey = get_vietjet_pnr(token, pnr)
        if reservationKey:
            if reservationKey =="VJ":
                return ("VJ")
            print("vnd")
            result = sendmail(token, reservationKey)
            print(result)
            
        else:
            return None

    #print(result)
    return ("VJ")


