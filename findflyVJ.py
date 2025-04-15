import requests
import json
import time  # 👈 Thêm thư viện time

# Bắt đầu tính giờ
start_time = time.time()

url = "https://agentapi.vietjetair.com/api/v13/Booking/findtraveloptions"

params = {
    "cityPair": "ICN-HAN",
    "departurePlace": "ICN",
    "departurePlaceName": "Seoul",
    "returnPlace": "HAN",
    "returnPlaceName": "Ha Noi",
    "departure": "2025-04-17",
    "return": "2025-04-17",
    "currency": "KRW",
    "company": "hA0syYxT72sdFED0bwazxR9VKaikKVx9ZXNNIbOMpLg=",
    "adultCount": "1",
    "childCount": "0",
    "infantCount": "0",
    "promoCode": "",
    "greaterNumberOfStops": "0"
}

headers = {
    "accept": "application/json, text/plain, */*",
    "accept-language": "en-US,en;q=0.9",
    "authorization": "Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ1bmlxdWVfbmFtZSI6IntcIk5hbWVcIjpcIktSMjQyMDA5QTE4S1hNLUhUdW9pXCIsXCJLZXlcIjpcIlJZZ0p0VWt3Y04wYzBsVHFzVndZwqVzWVpPUkIzNHZKWExnME9RRjgydlM0PVwiLFwiVXNlckxvZ29uTmFtZVwiOlwiS1IyNDIwMDlBMThLWE1cIixcIlRpbWVfTG9naW5cIjpcIjA0LzE1LzIwMjUgMTU6MDU6MDJcIixcIlRpbWVzdGFtcFwiOm51bGx9IiwibmJmIjoxNzQ0NzA0MzAyLCJleHAiOjIwNjAzMjM1MDIsImlhdCI6MTc0NDcwNDMwMiwiaXNzIjoiR0BsYXh5T25lIn0.HMO4aMsOxrbpYJJUBl5hKmVg5GeXNgMUP8sHp-U7m5I",
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

print("Status code:", response.status_code)

if response.status_code == 200:
    with open("flyresult.json", "w", encoding="utf-8") as f:
        json.dump(response.json(), f, ensure_ascii=False, indent=4)
    print("✅ Lưu file `flyresult.json` ngon lành cành đào!")
else:
    print("❌ Có lỗi xảy ra:", response.text)

def doc_va_loc_eco_moi(file_path):
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)

        ket_qua = []
        list_chuyen = data.get("data", {}).get("list_Travel_Options_Departure", [])

        for chuyen in list_chuyen:
            flight_info = chuyen.get("segmentOptions", [])[0].get("flight", {})
            ma_chuyen = flight_info.get("Number")
            gio_di = flight_info.get("ETDLocal")
            gio_den = flight_info.get("ETALocal")
            from_airport = flight_info.get("departureAirport", {}).get("Name")
            to_airport = flight_info.get("arrivalAirport", {}).get("Name")

            for fare in chuyen.get("fareOption", []):
                if fare.get("Description") == "Eco":
                    ket_qua.append({
                        "Flight": ma_chuyen,
                        "From": from_airport,
                        "To": to_airport,
                        "ETD": gio_di,
                        "ETA": gio_den,
                        "BookingKey": fare.get("BookingKey"),
                        "FareCost": fare.get("FareCost"),
                        "Currency": fare.get("currency", {}).get("code"),
                        "SeatsAvailable": fare.get("SeatsAvailable")
                    })

        if ket_qua:
            print("✅ Vé Eco tìm được như sau:")
            for i, kq in enumerate(ket_qua, 1):
                print(f"{i}. 🛫 {kq['From']} ({kq['ETD']}) → 🛬 {kq['To']} ({kq['ETA']})")
                print(f"   ✈️ Flight: {kq['Flight']} | Giá: {kq['FareCost']} {kq['Currency']} | Ghế còn: {kq['SeatsAvailable']}")
                print(f"   🔑 BookingKey: {kq['BookingKey'][:40]}...")
                print()
        else:
            print("❌ Không có vé Eco nào trong file này luôn đại ca ơi.")

    except Exception as e:
        print("❌ Lỗi xử lý file:", e)

# Gọi hàm
doc_va_loc_eco_moi("flyresult.json")

# Tính giờ xong và in kết quả
end_time = time.time()
tong_thoi_gian = round(end_time - start_time, 2)
print(f"⏱️ Tổng thời gian chạy: {tong_thoi_gian} giây")
