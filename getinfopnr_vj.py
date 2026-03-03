import json
import httpx
from datetime import datetime
import asyncio
import subprocess
from backend_api_vj_v2 import get_ancillary_options,get_tax
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
        #print(result)
        if result["resultcode"] == 1 :
            #print(result["data"])
            return result["data"]
        else :
            return None
    else:
        print(f"Lỗi khi gọi API check PNR: {response.status_code}")
        print(response.text)
        return None
async def get_visa_vj(token, key , keyhanhkhach):
    base_url = "https://agentapi.vietjetair.com/api/v14/EditBooking/passenger/getDetailByReservationKey"
    
    params = {
        "reservationKey" : key,
        "passengerKey" : keyhanhkhach

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
        #print(result)
        if result["resultcode"] == 1 :
            #print(result["data"])
            return result["data"]
        else :
            return None
    else:
        print(f"Lỗi khi gọi API check PNR: {response.status_code}")
        print(response.text)
        return None
# ===== Tạo nội dung Kakao message =====
def build_kakao_message(chieudi, chieuve):
    lines = []

    for seg in [chieudi, chieuve]:
        if seg and seg.get("departure") and seg.get("arrival"):
            route = f"{seg.get('departure','')}-{seg.get('arrival','')}"
            time = seg.get("giocatcanh","")
            full_date = seg.get("ngaycatcanh","")

            short_date = ""
            if full_date:
                parts = full_date.split("/")
                if len(parts) >= 2:
                    short_date = f"{parts[0]}/{parts[1]}"

            lines.append(f"{route} {time} ngày {short_date}")

    return "\n".join(lines)

     
def tinh_gia_nguoi_lon(data):
    ket_qua = 0

    allowed = {"Admin Fee ITL", "Airport Tax ITL","Airport Security", "Fuel Surcharge", "Management Fee ITL"}

    for chieu in data:
        chieu_index = chieu["index"]
        nguoi_lon = None   # chỉ lấy 1 thằng

        for pax in chieu["passengers"]:
            charges = pax["charges"]

            # check người lớn: có Airport Tax ITL
            is_adt = any(c["chargeDescription"] == "Airport Tax ITL" for c in charges)

            if is_adt:
                tong_base = sum(
                    c["baseAmount"]
                    for c in charges
                    if c["chargeDescription"] in allowed
                )

                

                ket_qua += tong_base
                break   # gặp 1 thằng người lớn rồi thì té luôn

        

    return ket_qua
async def get_price_goc( key ):
    token = await get_app_access_token_from_state()
    base_url = "https://agentapi.vietjetair.com/api/v14/EditBooking/getRevervationPassengerCharges"
    
    params = {
        "reservationKey" : key

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
        #print(result)
        if result["resultcode"] == 1 :
            #print(result["data"])
            return result["data"]
        else :
            return None
    else:
        print(f"Lỗi khi gọi API check PNR: {response.status_code}")
        print(response.text)
        return None
async def format_flight_data(data):
    token = await get_app_access_token_from_state()
    passengers = data.get("passengers", [])
    chargeForPassengers = data.get("chargeForPassengers", [])
    key = data.get("key", "")
    hanthanhtoan = data.get("datePayLater", "")
    paymentstatus = data.get("paymentstatus", "")
    tongbillgiagoc = data.get("totalamount", "")
    currency = data.get("currency", "").get("code", "")
    pnr = data.get("locator", "")
    listthongtinchuyenbay = data.get("journeys", [])
    giagocthuephi= await get_price_goc(key)
    giagocthuephi = tinh_gia_nguoi_lon(giagocthuephi)
    #print(giagocthuephi)
    result = {}
    bk_key={"1":"","2":""}
    i = 1  # đặt ngoài vòng for
    passenger_list = []
    for p in passengers:
        keyhanhkhach =  p.get("key", "")
        if keyhanhkhach:
            passportNumberdata = await checkvisa_vj(key,keyhanhkhach)
            passportNumber = passportNumberdata[0]
            quoctich = passportNumberdata[1]
        passenger_list.append({
            "lastName": p.get("lastName", ""),
            "firstName": p.get("firstName", ""),
            "phonenumber": p.get("phonenumber", ""),
            "email": p.get("email", ""),
            "child" : p.get("child", ""),
            "infant" : p.get("infant", ""),
            "gender" : p.get("gender", ""),
            "keyhanhkhach" : p.get("key", ""),
            "passportNumber" : passportNumber,
            "quoctich" : quoctich
        })
    for a in listthongtinchuyenbay:
        bk_key[str(i)]= a.get("bookingkey", "")
        raw_loaive = a.get("fareClassDes", "")
        if raw_loaive == "Deluxe1":
            loaive = "DELUXE"
        elif raw_loaive == "Eco1":
            loaive = "ECO"
        else:
            loaive = raw_loaive
        segments = a.get("segments", [{}])
        etd_full = segments[0].get("ETDLocal", "")
        eta_full = segments[0].get("ETALocal", "")
        try:
            etd_parts = etd_full.strip().split(" ")
            ngaycatcanh_raw = etd_parts[0] if len(etd_parts) > 0 else ""
            giocatcanh = etd_parts[1] if len(etd_parts) > 1 else ""

            # 👉 Convert "2025-08-20" => "20/08/2025"
            ngaycatcanh = ""
            if ngaycatcanh_raw:
                dt = datetime.strptime(ngaycatcanh_raw, "%Y-%m-%d")
                ngaycatcanh = dt.strftime("%d/%m/%Y")
            eta_parts = eta_full.strip().split(" ")
            ngayhacanh_raw = eta_parts[0] if len(eta_parts) > 0 else ""
            giohacanh = eta_parts[1] if len(eta_parts) > 1 else ""

            # 👉 Convert "2025-08-20" => "20/08/2025"
            ngayhacanh = ""
            if ngayhacanh_raw:
                dt = datetime.strptime(ngayhacanh_raw, "%Y-%m-%d")
                ngayhacanh = dt.strftime("%d/%m/%Y")
        except:
            giocatcanh = ""
            ngaycatcanh = ""
            giohacanh = ""
            ngayhacanh = ""
        result[str(i)] = {
            "departure": segments[0].get("departureAirport", {}).get("Code", ""),
            "departurename": segments[0].get("departureAirport", {}).get("Name", ""),
            "arrival": segments[0].get("arrivalAirport", {}).get("Code", ""),
            "arrivalname": segments[0].get("arrivalAirport", {}).get("Name", ""),
            "loaive": loaive,
            "giocatcanh": giocatcanh,
            "ngaycatcanh": ngaycatcanh,
            "giohacanh": giohacanh,
            "ngayhacanh": ngayhacanh,
            "thoigianbay": segments[0].get("Duration", ""),
            "sohieumaybay": segments[0].get("Number", "")
        }
        i += 1
    giahanhly = get_ancillary_options(token,bk_key["1"],bk_key["2"])
    #print(giahanhly)

    giacoban = chargeForPassengers[0].get("charges")[0].get("amountfare")
    if result["1"].get("loaive") == "ECO":
        giacoban += (giahanhly["chiều_đi"]["HANH_LY_ECO"])
    else :
        giacoban += (giahanhly["chiều_đi"]["HANH_LY_DELUXE"])
    
    if bk_key["2"]:
        giacoban += chargeForPassengers[1].get("charges")[0].get("amountfare")
        if result["2"].get("loaive") == "ECO":
            giacoban += (giahanhly["chiều_về"]["HANH_LY_ECO"])
        else :
            giacoban += (giahanhly["chiều_về"]["HANH_LY_DELUXE"])
    giacoban +=giagocthuephi
    giacoban -= 100
    giacoban = (int(giacoban) // 100) * 100
    #print(giacoban)
    listchieu = []
    
    i = 1
    while True:
        seg = result.get(str(i))
        if not seg:
            break
        listchieu.append(seg)
        i += 1
    
    # lọc bỏ segment nào có loaive = ""
    listchieu = [s for s in listchieu if s.get("loaive", "") != ""]
    
    # gán lại chieudi - chieuve sau khi lọc
    chieudi = listchieu[0] if len(listchieu) >= 1 else {}
    chieuve = listchieu[1] if len(listchieu) >= 2 else {}
    kakaomess = build_kakao_message(chieudi, chieuve)   
    res = {
        "pnr": pnr,
        "status": "OK",
        "hang": "VJ",
        "tongbillgiagoc": tongbillgiagoc,
        "currency" : currency,
        "paymentstatus": paymentstatus,
        "key": key,
        "hanthanhtoan": hanthanhtoan,
        "chieudi": chieudi,
        "chieuve": chieuve,
        "passengers": passenger_list,
        "giacoban": giacoban,
        "kakaomess" :kakaomess
    }

    return res

async def checkpnr_vj(pnr):

    token = await get_app_access_token_from_state()
    

    company_info = await get_company(token)
    
    token = await get_app_access_token_from_state()
    res = await get_vietjet_pnr(token,pnr)
    if res:

        result =await format_flight_data(res)
       
    else :
        token = await get_app_access_token_from_state(vjvnd)
        company_info = await get_company(token,vjvndpy)
        token = await get_app_access_token_from_state(vjvnd)
        res = await get_vietjet_pnr(token,pnr)
        if res:
            result = format_flight_data(res)
        else :
            print(res)
            return None
    #print(result)
    return result
def format_getDetailByReservationKey(data):
    passportNumber = data.get("passportNumber", "")
    isoCode= data.get("nationCountry", "")
    if isoCode == "KOR" :
        quoctich= "KR"
    else : 
        quoctich= "VN"
    return [passportNumber,quoctich]
async def checkvisa_vj(key,keyhanhkhach):
    token = await get_app_access_token_from_state()
    res = await get_visa_vj(token,key,keyhanhkhach)
    if res:
        result = format_getDetailByReservationKey(res)
    else : 
        return None

    return result

if __name__ == "__main__":


    async def main():
        a = await checkpnr_vj(
            "V7C9EY"
        )
        print(a)

    asyncio.run(main())














