import requests
import json
import time  # 👈 Thêm thư viện time
from datetime import datetime
# Định nghĩa các hàm
def format_time(time_str):
    try:
        dt = datetime.strptime(time_str, "%Y-%m-%d %H:%M")
        return dt.strftime("%H:%M ngày %d/%m")
    except Exception as e:
        print("❌ Format lỗi vcl:", e)
        return time_str
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
    #print("📡 Status code:", response.status_code)

    if response.status_code == 200:
        print("✅ Lấy dữ liệu chuyến bay thành công!")
        return response.json()
    else:
        print("❌ Có lỗi xảy ra vcl:", response.text)
        return None

def doc_va_loc_ve_re_nhat(data):
    try:

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
        print("✅ Check vé rẻ nhất")
        #print(ket_qua)
        return ket_qua

        

    except Exception as e:
        print("❌ Lỗi xử lý file:", e)
        return None
def doc_va_loc_ve_re_nhat_chieu_ve(data):
    try:
        

        list_chuyen = data.get("data", {}).get("list_Travel_Options_Arrival", [])
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
        print("✅ Check vé rẻ nhất chiều về")
        return ket_qua
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

        

        print("✅ Đã lấy giá chốt")
        return data
    except requests.RequestException as e:
        print("❌ Lỗi khi gọi API:", e)
        return None
def gettax_chieu_ve(authorization: str, bookingKey: str):
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

        with open("tax_vj_chieu_ve.json", "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=4)

        print("✅ Đã lưu kết quả vào file tax_chieu_ve.json")
        return data
    except requests.RequestException as e:
        print("❌ Lỗi khi gọi API:", e)
        return None

def get_booking_keys(data):
    try:
        
       

        booking_keys = []
        for chuyen in data:
            key = chuyen.get("BookingKey")
            if key:
                booking_keys.append(key)

        return booking_keys
    except Exception as e:
        print("❌ Lỗi đọc file:", e)
        return []
def print_flight_info(data):
    try:
        # Đọc dữ liệu từ file result.json
        

        # Duyệt qua các chuyến bay trong dữ liệu
        for flight in data:
            # Lấy các giá trị cần thiết từ từng chuyến bay
            from_airport = flight.get("From", "N/A")
            to_airport = flight.get("To", "N/A")
            etd = flight.get("ETD", "N/A")
            flight_type = flight.get("Type", "N/A")
            fare_cost = flight.get("FareCost", "N/A")
            
            # In ra thông tin chuyến bay
            print(f"Hãng: VIETJET - Chặng bay: {from_airport}-{to_airport} ? chiều ( {flight_type} : {fare_cost})")
            print(f"{from_airport}-{to_airport} {format_time(etd)}")
            
           
            print()

    except Exception as e:
        print("❌ Lỗi khi xử lý file:", e)
def read_tax_from_file(data):
    try:
        

        totalamountdeparture = data.get("data", {}).get("totalamountdeparture")
        if totalamountdeparture is not None:
            #print(f"💸 Giá Chốt: {totalamountdeparture}")
            pass
        else:
            print(f"❌ Không tìm thấy trường totalamountdeparture trong {filename}.")
        return totalamountdeparture
    except Exception as e:
        print(f"❌ Lỗi đọc file {filename}:", e)
        return None
# Gọi hàm
def save_all_results(sochieu,vechieudi, giave_chieu_di, vechieuve=None ,giave_chieu_ve=None, filename="full_result.json"):
    data = {
        "ve_chieu_di": vechieudi,
        "ve_chieu_ve": vechieuve,
        "gia_ve_chieu_di": giave_chieu_di,
        "gia_ve_chieu_ve": giave_chieu_ve
    }
    if sochieu=="1":
        data = {
            "ve_chieu_di": vechieudi,
            
            "gia_ve_chieu_di": giave_chieu_di
        }
    
    try:
        with open(filename, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=4)
        print(f"✅ Lưu file '{filename}'")
        #print(data)
        return data
    except Exception as e:
        print("❌ Lỗi lưu file vcl:", e)
token = get_app_access_token_from_state()
def api_vj(city_pair, departure_place, departure_place_name, return_place, return_place_name, 
         departure_date, return_date, adult_count, child_count,sochieu):
    # Lấy token
    loi= ""
    
    # Lấy flight options
   
    danhsachchuyen=get_vietjet_flight_options(
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
    if danhsachchuyen ==None :
        print("báo lỗi khong tai duoc")
        loi += "báo lỗi khong tai duoc\n"
    # Lọc vé phù hợp
    vechieudi = doc_va_loc_ve_re_nhat(danhsachchuyen)
    if vechieudi ==None :
        print("báo lỗi het chuyen")
        loi += "báo lỗi het chuyen\n"
         # >>result_chieu_di.json
     # >>result_chieu_ve.json
    # Lấy booking key và tính thuế
    booking_key = vechieudi[0]['BookingKey'] # Lấy BookingKey đầu tiên
    giave_chieu_di = gettax(token, booking_key)
    if str(sochieu) =="2":
        
        vechieuve = doc_va_loc_ve_re_nhat_chieu_ve(danhsachchuyen) 
        if vechieuve ==None :
            print("báo lỗi het chuyen ve")
            loi += "báo lỗi het chuyen ve\n"
        booking_key = vechieuve[0]['BookingKey']
        giave_chieu_ve = gettax(token, booking_key)
        result = save_all_results(sochieu,vechieudi,  giave_chieu_di,vechieuve, giave_chieu_ve)
        return result 
    #booking_key_chieu_ve = get_booking_keys_from_file("result_chieu_ve.json")[0]  # Lấy BookingKey đầu tiên
    #gettax_chieu_ve(token, booking_key_chieu_ve)

    else:
    # In thông tin chuyến bay (giả sử bạn có hàm này)
        result = save_all_results(sochieu,vechieudi,  giave_chieu_di)
        return result 
    

    
# Chạy hàm test với các tham số đầu vào tùy ý
api_vj(
    city_pair="HAN-PUS",
    departure_place="",
    departure_place_name="",
    return_place="",
    return_place_name="",
    departure_date="2025-05-01",
    return_date="2025-05-01",
    adult_count="1",
    child_count="0",
    sochieu = "2"
)