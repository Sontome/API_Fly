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
            return result["data"]["key"]
        else:
            return None
    else:
        print(f"Lỗi khi gọi API check PNR: {response.status_code}")
        print(response.text)
        return None


def get_vietjet_bag(token, reservationKey):
    base_url = "https://agentapi.vietjetair.com/api/v13/EditBooking/getRevervationPassengerCharges"
    params = {"reservationKey": reservationKey}

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
            return result["data"]
        else:
            return None
    else:
        print(f"Lỗi khi gọi API lấy hành lý: {response.status_code}")
        print(response.text)
        return None


def format_vj_data(data):
    result = []
    for item in data:
        chieu = f"{item['departureAirport']}-{item['arrivalAirport']}"
        passenger_list = []
        for p in item['passengers']:
            ten = f"{p['passengerLastName']}, {p['passengerFirstName']}"
            bag_list = []
            for charge in p.get('charges', []):
                desc = charge['chargeDescription']
                if 'Bag' in desc:
                    bag_list.append(desc.split('Bag')[-1].strip())
                elif 'Deluxe' in desc:
                    bag_list.append(desc.split('Deluxe ')[-1].strip())
            bag_info = "+".join(bag_list) if bag_list else None
            passenger_list.append({
                "tên": ten,
                "Bag": bag_info
            })
        result.append({
            "chiều": chieu,
            "passengers": passenger_list
        })
    return result


def get_bag_info_vj(pnr):
    token = get_app_access_token_from_state()
    company_info = get_company(token)

    token = get_app_access_token_from_state()
    reservationKey = get_vietjet_pnr(token, pnr)

    if reservationKey:
        print("krw")
        bagfile = get_vietjet_bag(token, reservationKey)
        result = format_vj_data(bagfile)
    else:
        token = get_app_access_token_from_state(vjvnd)
        company_info = get_company(token, vjvndpy)
        token = get_app_access_token_from_state(vjvnd)
        reservationKey = get_vietjet_pnr(token, pnr)
        if reservationKey:
            print("vnd")
            bagfile = get_vietjet_bag(token, reservationKey)
            result = format_vj_data(bagfile)
        else:
            return None

    #print(result)
    return result



