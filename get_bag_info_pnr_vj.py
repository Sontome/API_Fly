import json
import httpx
from datetime import datetime
import asyncio
import subprocess
vjkrw ="state.json"
vjvnd ="statevnd.json"
vjkrwpy ="getcokivj.py"
vjvndpy ="getcokivjvnd.py"
# ✅ Lấy token từ state.json
async def get_app_access_token_from_state(file_path=vjkrw):
    def read_file():
        with open(file_path, "r", encoding="utf-8") as f:
            return json.load(f)

    data = await asyncio.to_thread(read_file)
    # Đọc xong mới return
    origins = data.get("origins", [])
    for origin in origins:
        local_storage = origin.get("localStorage", [])
        for item in local_storage:
            if item.get("name") == "app_access_token":
                return item.get("value")
    return None

# ✅ Lấy danh sách công ty từ API VJ
async def get_company(token: str,file_path=vjkrwpy):
    url = "https://agentapi.vietjetair.com/api/v13/Booking/getlistcompanies"
    headers = {
        "accept": "application/json, text/plain, */*",
        "authorization": f"Bearer {token}",
        "content-type": "application/json",
        "languagecode": "vi",
        "platform": "3"
    }

    async with httpx.AsyncClient() as client:
        resp = await client.get(url, headers=headers)

    if resp.status_code == 401:
        print("🔐 Token hết hạn. Đại ca cần chạy lại `getcokivj.py` để làm mới token.")
        try:
            subprocess.run(["python", file_path])
        except:
            print ("lỗi khi reload cookie")
        return None

    if resp.status_code == 200:
        return resp.json()
    else:
        print(f"Lỗi khi lấy công ty - status: {resp.status_code}")
        print(resp.text)
        return None
async def get_vietjet_pnr(token, PNR ):
    base_url = "https://agentapi.vietjetair.com/api/v13/EditBooking/getreservationdetailbylocator"
    
    params = {
        "locator" : PNR
    }
    

    headers = {
        'accept': 'application/json, text/plain, */*',
        'authorization': f"Bearer {token}",
        'content-type': 'application/json',
        'languagecode': 'vi',
        'platform': '3'
    }

    async with httpx.AsyncClient() as client:
        response = await client.get(base_url, headers=headers, params=params)

    if response.status_code == 200:
        result = response.json()
        
        if result["resultcode"] == 1 :

            return result["data"]["key"]
        else :
            return None
    else:
        print(f"Lỗi khi gọi API check PNR: {response.status_code}")
        print(response.text)
        return None
async def get_vietjet_bag(token, reservationKey ):
    base_url = "https://agentapi.vietjetair.com/api/v13/EditBooking/getRevervationPassengerCharges"
    
    params = {
        "reservationKey" : reservationKey
    }
    

    headers = {
        'accept': 'application/json, text/plain, */*',
        'authorization': f"Bearer {token}",
        'content-type': 'application/json',
        'languagecode': 'vi',
        'platform': '3'
    }

    async with httpx.AsyncClient() as client:
        response = await client.get(base_url, headers=headers, params=params)

    if response.status_code == 200:
        result = response.json()
        
        if result["resultcode"] == 1 :

            return result["data"]
        else :
            return None
    else:
        print(f"Lỗi khi gọi API check PNR: {response.status_code}")
        print(response.text)
        return None
def format_vj_data(data):
    result = []
    for item in data:
        chieu = f"{item['departureAirport']}-{item['arrivalAirport']}"
        passenger_list = []
        for p in item['passengers']:
            ten = f"{p['passengerLastName']}, {p['passengerFirstName']}"
            bag_info = None
            for charge in p.get('charges', []):
                if 'Bag' in charge['chargeDescription']:
                    bag_info = charge['chargeDescription'].split('Bag')[-1].strip()
                    break
                if 'Deluxe ' in charge['chargeDescription']:
                    bag_info = charge['chargeDescription'].split('Deluxe')[-1].strip()
                    break
            passenger_list.append({
                "tên": ten,
                "Bag": bag_info
            })
        result.append({
            "chiều": chieu,
            "passengers": passenger_list
        })
    return result

async def get_bag_info_vj(pnr):

    token = await get_app_access_token_from_state()
    

    company_info = await get_company(token)
    
    token = await get_app_access_token_from_state()
    reservationKey = await get_vietjet_pnr(token,pnr)
    if reservationKey:
        print("krw")
        bagfile = await get_vietjet_bag(token,reservationKey)
        result = format_vj_data(bagfile)
    else :
        token = await get_app_access_token_from_state(vjvnd)
        company_info = await get_company(token,vjvndpy)
        token = await get_app_access_token_from_state(vjvnd)
        reservationKey = await get_vietjet_pnr(token,pnr)
        if reservationKey:
            print("vnd")
            bagfile = await get_vietjet_bag(token,reservationKey)
            result = format_vj_data(bagfile)
        else :
            
            return None
    print(result)
    return result








