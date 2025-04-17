import requests
import json
import httpx
from datetime import datetime

# ✅ Format lại thời gian
def format_time(time_str):
    try:
        dt = datetime.strptime(time_str, "%Y-%m-%d %H:%M")
        return dt.strftime("%H:%M ngày %d/%m")
    except Exception as e:
        print("❌ Format lỗi vcl:", e)
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

# ✅ Gọi API async lấy flight options
async def get_vietjet_flight_options(city_pair, departure_place, departure_place_name,
    return_place, return_place_name, departure_date, return_date,
    adult_count, child_count, auth_token):

    url = "https://agentapi.vietjetair.com/api/v13/Booking/findtraveloptions"
    params = {
        "cityPair": city_pair,
        "departurePlace": departure_place,
        "departurePlaceName": departure_place_name,
        "returnPlace": return_place,
        "returnPlaceName": return_place_name,
        "departure": departure_date,
        "return": return_date,
        "currency": "KRW",
        "company": "hA0syYxT72sdFED0bwazxR9VKaikKVx9ZXNNIbOMpLg=",
        "adultCount": adult_count,
        "childCount": child_count,
        "infantCount": "0",
        "promoCode": "",
        "greaterNumberOfStops": "0"
    }
    headers = {
        "accept": "application/json, text/plain, */*",
        "authorization": f"Bearer {auth_token}",
        "content-type": "application/json",
        "languagecode": "vi",
        "platform": "3",
        "referer": "https://agents2.vietjetair.com/",
    }
    try:
        async with httpx.AsyncClient(timeout=30) as client:
            response = await client.get(url, headers=headers, params=params)
            if response.status_code == 200:
                print("✅ Lấy dữ liệu chuyến bay thành công!")
                return response.json()
            else:
                print("❌ Có lỗi xảy ra vcl:", response.status_code, response.text)
                return None
    except Exception as e:
        print("💥 Lỗi khi gọi API async:", e)
        return None

def extract_flight(data, list_key):
    try:
        list_chuyen = data.get("data", {}).get(list_key, [])
        eco_min, deluxe_min = None, None

        def make_flight_info(flight_info, fare):
            return {
                "Flight": flight_info.get("Number"),
                "From": flight_info.get("departureAirport", {}).get("Code"),
                "To": flight_info.get("arrivalAirport", {}).get("Code"),
                "ETD": flight_info.get("ETDLocal"),
                "ETA": flight_info.get("ETALocal"),
                "BookingKey": fare.get("BookingKey"),
                "FareCost": fare.get("FareCost"),
                "Currency": fare.get("currency", {}).get("code"),
                "SeatsAvailable": fare.get("SeatsAvailable"),
                "Type": fare.get("Description")
            }

        for chuyen in list_chuyen:
            segments = chuyen.get("segmentOptions", [])
            if not segments:
                continue
            flight_info = segments[0].get("flight", {})
            for fare in chuyen.get("fareOption", []):
                if fare.get("Description") == "Eco":
                    if eco_min is None or fare.get("FareCost") < eco_min["FareCost"]:
                        eco_min = make_flight_info(flight_info, fare)
                elif fare.get("Description") == "Deluxe":
                    if deluxe_min is None or fare.get("FareCost") < deluxe_min["FareCost"]:
                        deluxe_min = make_flight_info(flight_info, fare)

        if eco_min and deluxe_min:
            return [eco_min if deluxe_min["FareCost"] - eco_min["FareCost"] >= 40000 else deluxe_min]
        return [eco_min] if eco_min else [deluxe_min] if deluxe_min else []
    except Exception as e:
        print("❌ Lỗi xử lý dữ liệu flight:", e)
        return []

def get_tax(authorization, booking_key):
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
        "numberOfAdults": 1,
        "numberOfChilds": 0,
        "numberOfInfants": 0
    }
    try:
        res = requests.post(url, headers=headers, json=payload)
        res.raise_for_status()
        return res.json()
    except requests.RequestException as e:
        print("❌ Lỗi khi gọi API thuế:", e)
        return None

def save_all_results(sochieu, vechieudi, giave_chieu_di, vechieuve=None, giave_chieu_ve=None):
    if sochieu == "1":
        return {"ve_chieu_di": vechieudi, "gia_ve_chieu_di": giave_chieu_di}
    return {
        "ve_chieu_di": vechieudi,
        "gia_ve_chieu_di": giave_chieu_di,
        "ve_chieu_ve": vechieuve,
        "gia_ve_chieu_ve": giave_chieu_ve
    }

def thongtinve(data, sochieu):
    try:
        text = ""
        if str(sochieu) == "2":
            chieudi = data["ve_chieu_di"][0]
            chieuve = data["ve_chieu_ve"][0]
            text += f"VJ ✈️ {chieudi['From']}->{chieudi['To']} lúc {format_time(chieudi['ETD'])} - {chieudi['Type']} {chieudi['FareCost']}\n"
            text += f"VJ ✈️ {chieuve['From']}->{chieuve['To']} lúc {format_time(chieuve['ETD'])} - {chieuve['Type']} {chieuve['FareCost']}\n"
            text += f"💰 Giá tổng: {data['gia_ve_chieu_di']['data']['totalamountdeparture']} + {data['gia_ve_chieu_ve']['data']['totalamountdeparture']}"
        else:
            chieudi = data["ve_chieu_di"][0]
            text += f"VJ ✈️ {chieudi['From']}->{chieudi['To']} lúc {format_time(chieudi['ETD'])} - {chieudi['Type']} {chieudi['FareCost']}\n"
            text += f"💰 Giá tổng: {data['gia_ve_chieu_di']['data']['totalamountdeparture']}"
        return text
    except Exception as e:
        return f"❌ Lỗi show info: {e}"

async def api_vj(city_pair, departure_place, departure_place_name, return_place, return_place_name, 
                 departure_date, return_date, adult_count, child_count, sochieu):
    token = get_app_access_token_from_state()
    result_data = await get_vietjet_flight_options(
        city_pair, departure_place, departure_place_name,
        return_place, return_place_name,
        departure_date, return_date,
        adult_count, child_count, token
    )

    if not result_data:
        return "❌ Không tải được danh sách chuyến bay"

    vechieudi = extract_flight(result_data, "list_Travel_Options_Departure")
    if not vechieudi:
        return "❌ Không có chuyến đi nào hợp lệ"

    giave_chieu_di = get_tax(token, vechieudi[0]['BookingKey'])

    if str(sochieu) == "2":
        vechieuve = extract_flight(result_data, "list_Travel_Options_Arrival")
        if not vechieuve:
            return "❌ Không có chuyến về nào hợp lệ"
        giave_chieu_ve = get_tax(token, vechieuve[0]['BookingKey'])
        result = save_all_results(sochieu, vechieudi, giave_chieu_di, vechieuve, giave_chieu_ve)
    else:
        result = save_all_results(sochieu, vechieudi, giave_chieu_di)

    return thongtinve(result, sochieu)
