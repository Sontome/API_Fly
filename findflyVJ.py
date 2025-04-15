import requests
import json
import time  # 👈 Thêm thư viện time

# Định nghĩa các hàm

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

def get_vietjet_flight_options(city_pair, departure_place, departure_place_name, return_place, return_place_name,
                                departure_date, return_date, adult_count, child_count, auth_token):
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
        "accept-language": "en-US,en;q=0.9",
        "authorization": f"Bearer {auth_token}",
        "content-type": "application/json",
        "languagecode": "vi",
        "platform": "3",
        "priority": "u=1, i",
        "sec-ch-ua": "\"Not:A-Brand\";v=\"24\", \"Chromium\";v=\"134\"",
        "sec-ch-ua-mobile": "?0",
        "sec-ch-ua-platform": "\"Windows\"",
        "sec-fetch-dest": "empty",
        "sec-fetch-mode": "cors",
        "sec-fetch-site": "same-site",
        "referer": "https://agents2.vietjetair.com/",
    }

    response = requests.get(url, headers=headers, params=params)
    print("📡 Status code:", response.status_code)

    if response.status_code == 200:
        with open("flyresult.json", "w", encoding="utf-8") as f:
            json.dump(response.json(), f, ensure_ascii=False, indent=4)
        print("✅ Lưu file `flyresult.json` ngon lành cành đào!")
    else:
        print("❌ Có lỗi xảy ra vcl:", response.text)

def doc_va_loc_ve_re_nhat(file_path):
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)

        list_chuyen = data.get("data", {}).get("list_Travel_Options_Departure", [])
        eco_min = None
        deluxe_min = None

        def tao_thong_tin_flight(flight_info, fare):
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
            segment = chuyen.get("segmentOptions", [])
            if not segment:
                continue
            flight_info = segment[0].get("flight", {})
            for fare in chuyen.get("fareOption", []):
                fare_type = fare.get("Description")
                fare_cost = fare.get("FareCost")
                if fare_type == "Eco":
                    if eco_min is None or fare_cost < eco_min["FareCost"]:
                        eco_min = tao_thong_tin_flight(flight_info, fare)
                elif fare_type == "Deluxe":
                    if deluxe_min is None or fare_cost < deluxe_min["FareCost"]:
                        deluxe_min = tao_thong_tin_flight(flight_info, fare)

        ket_qua = []
        if eco_min and deluxe_min:
            chenh_lech = deluxe_min["FareCost"] - eco_min["FareCost"]
            if chenh_lech >= 40000:
                ket_qua.append(eco_min)
            else:
                ket_qua.append(deluxe_min)
        elif eco_min:
            ket_qua.append(eco_min)
        elif deluxe_min:
            ket_qua.append(deluxe_min)

        with open("result.json", "w", encoding="utf-8") as f:
            json.dump(ket_qua, f, ensure_ascii=False, indent=4)

        print("✅ Đã lưu vé phù hợp nhất (theo chênh lệch giá) vào file result.json đại ca ơi!")

    except Exception as e:
        print("❌ Lỗi xử lý file:", e)

def gettax(authorization: str, bookingKey: str):
    url = "https://agentapi.vietjetair.com/api/v13/Booking/quotationwithoutpassenger"
    headers = {
        "accept": "application/json, text/plain, */*",
        "authorization": f"Bearer {authorization}",
        "content-type": "application/json",
        "languagecode": "vi",
        "platform": "3"
    }
    payload = {
        "journeys": [
            {
                "index": 1,
                "bookingKey": bookingKey
            }
        ],
        "numberOfAdults": 1,
        "numberOfChilds": 0,
        "numberOfInfants": 0
    }

    try:
        res = requests.post(url, headers=headers, json=payload)
        res.raise_for_status()
        data = res.json()

        with open("tax.json", "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=4)

        print("✅ Đã lưu kết quả vào file tax.json")
        return data
    except requests.RequestException as e:
        print("❌ Lỗi khi gọi API:", e)
        return None

def get_booking_keys_from_file(file_path: str):
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)

        booking_keys = []
        for chuyen in data:
            key = chuyen.get("BookingKey")
            if key:
                booking_keys.append(key)

        return booking_keys
    except Exception as e:
        print("❌ Lỗi đọc file:", e)
        return []
def print_flight_info():
    try:
        # Đọc dữ liệu từ file result.json
        with open("result.json", "r", encoding="utf-8") as f:
            data = json.load(f)

        # Duyệt qua các chuyến bay trong dữ liệu
        for flight in data:
            # Lấy các giá trị cần thiết từ từng chuyến bay
            from_airport = flight.get("From", "N/A")
            to_airport = flight.get("To", "N/A")
            etd = flight.get("ETD", "N/A")
            flight_type = flight.get("Type", "N/A")
            fare_cost = flight.get("FareCost", "N/A")
            
            # In ra thông tin chuyến bay
            print(f"✈️ Flight from {from_airport} to {to_airport}")
            print(f"   - ETD: {etd}")
            print(f"   - Type: {flight_type}")
            print(f"   - FareCost: {fare_cost} KRW")
            print()

    except Exception as e:
        print("❌ Lỗi khi xử lý file:", e)
def read_tax_from_file():
    try:
        with open("tax.json", "r", encoding="utf-8") as f:
            data = json.load(f)
        
        totalamountdeparture = data.get("data", {}).get("totalamountdeparture")
        if totalamountdeparture is not None:
            print(f"💸 Giá Chốt: {totalamountdeparture}")
        else:
            print("❌ Không tìm thấy trường totalamountdeparture trong tax.json.")
        return data
    except Exception as e:
        print("❌ Lỗi đọc file tax.json:", e)
        return None
# Gọi hàm
print_flight_info()
def test(city_pair, departure_place, departure_place_name, return_place, return_place_name, 
         departure_date, return_date, adult_count, child_count):
    # Lấy token
    token = get_app_access_token_from_state()
    
    # Lấy flight options
    get_vietjet_flight_options(
        city_pair=city_pair,
        departure_place=departure_place,
        departure_place_name=departure_place_name,
        return_place=return_place,
        return_place_name=return_place_name,
        departure_date=departure_date,
        return_date=return_date,
        adult_count=adult_count,
        child_count=child_count,
        auth_token=token
    )
    
    # Lọc vé phù hợp
    doc_va_loc_ve_re_nhat("flyresult.json")
    
    # Lấy booking key và tính thuế
    booking_key = get_booking_keys_from_file("result.json")[0]  # Lấy BookingKey đầu tiên
    gettax(token, booking_key)
    
    # In thông tin chuyến bay (giả sử bạn có hàm này)
    print_flight_info()
    read_tax_from_file()
# Chạy hàm test với các tham số đầu vào tùy ý
test(
    city_pair="HAN-ICN",
    departure_place="HAN",
    departure_place_name="Ho Chi Minh",
    return_place="ICN",
    return_place_name="Ha Noi",
    departure_date="2025-05-01",
    return_date="2025-05-05",
    adult_count="1",
    child_count="0"
)