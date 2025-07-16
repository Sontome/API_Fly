import json
import httpx
from datetime import datetime
import asyncio

# ✅ Lấy token từ state.json
async def get_app_access_token_from_state(file_path="state.json"):
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
async def get_company(token: str):
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
        return None

    if resp.status_code == 200:
        return resp.json()
    else:
        print(f"Lỗi khi lấy công ty - status: {resp.status_code}")
        print(resp.text)
        return None

# ✅ Format lại dữ liệu chuyến bay
def format_flight_data(raw_data):
    formatted_flights = []
    
    for flight in raw_data:
        departure_date = flight['departureDate']
        date_obj = datetime.strptime(departure_date, '%Y-%m-%d')
        formatted_date = date_obj.strftime('%d/%m/%Y')
        
        fare_charges = flight['fareOption']['fareCharges'][0]
        base_amount = fare_charges['currencyAmounts'][0]['baseAmount']
        
        fare_class_code = flight['fareOption']['fareClass']['code']
        fare_type = fare_class_code.split('_')[1] if '_' in fare_class_code else fare_class_code
        
        formatted_flight = {
            "ngày": formatted_date,
            "giá_vé_gốc": int(base_amount),
            "loại_vé": fare_type
        }
        
        formatted_flights.append(formatted_flight)
    
    return formatted_flights

# ✅ Gọi API lấy vé VJ
async def get_vietjet_flights(token, company, departure, arrival, departure_date, return_date=None,
                              currency="KRW", adult_count=1, child_count=0,
                              cabin_class="Y", infant_count=0):
    base_url = "https://agentapi.vietjetair.com/api/v13/Booking/lowFareOptions"
    
    params = {
        'cityPair': f"{departure}-{arrival}",
        'departure': departure_date,
        'currency': currency,
        'adultCount': adult_count,
        'childCount': child_count,
        'cabinClass': cabin_class,
        'infantCount': infant_count,
        'company': company
    }
    if return_date:
        params["Return"] = return_date

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
        return response.json()
    else:
        print(f"Lỗi khi gọi API lowFare: {response.status_code}")
        print(response.text)
        return None

# ✅ Hàm chính để lấy vé rẻ nhất
async def lay_danh_sach_ve_re_nhat(departure, arrival, sochieu, departure_date, return_date=None):
    if sochieu == "OW":
        return_date = None

    res = {
        "status_code": "200",
        "message": "",
        "body": {
            "chiều_đi": [],
            "chiều_về": []
        }
    }

    token = await get_app_access_token_from_state()
    if not token:
        res["status_code"] = "401"
        res["message"] = "Không lấy được token"
        return res

    company_info = await get_company(token)
    if not company_info:
        res["status_code"] = "403"
        res["message"] = "Không lấy được danh sách công ty"
        return res

    company = company_info['data'][1]['company']['key']

    flight_result = await get_vietjet_flights(token, company, departure, arrival, departure_date, return_date)

    if flight_result:
        res["message"] = flight_result.get("message", "")
        if flight_result.get("resultcode") == 1:
            datachieudi = flight_result.get("data", {}).get("departure", [])
            datachieuve = flight_result.get("data", {}).get("arrival", [])
            res["body"]["chiều_đi"] = format_flight_data(datachieudi)
            res["body"]["chiều_về"] = format_flight_data(datachieuve)
        else:
            res["resultcode"] = flight_result.get("resultcode", "")
    else:
        res["message"] = "Lỗi không lấy được danh sách"

    return res