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
        print(result)
        if result["resultcode"] == 1 :
            print(result["data"])
            return result["data"]
        else :
            return None
    else:
        print(f"Lỗi khi gọi API check PNR: {response.status_code}")
        print(response.text)
        return None
def format_flight_data(data):
    passengers = data.get("passengers", [])
    
    hanthanhtoan = data.get("datePayLater", "")
    paymentstatus = data.get("paymentstatus", "")
    tongbillgiagoc = data.get("totalamount", "")
    currency = data.get("currency", "").get("code", "")
    pnr = data.get("locator", "")
    listthongtinchuyenbay = data.get("journeys", [])
   
    
    result = {}
    i = 1  # đặt ngoài vòng for
    passenger_list = []
    for p in passengers:
        passenger_list.append({
            "lastName": p.get("lastName", ""),
            "firstName": p.get("firstName", ""),
            "phonenumber": p.get("phonenumber", ""),
            "email": p.get("email", "")
        })
    for a in listthongtinchuyenbay:
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

    res = {
        "pnr": pnr,
        "status": "OK",
        "hang": "VJ",
        "tongbillgiagoc": tongbillgiagoc,
        "currency" : currency,
        "paymentstatus": paymentstatus,
        
        "hanthanhtoan": hanthanhtoan,
        "chieudi": result.get("1"),
        "chieuve": result.get("2",{}),
        "passengers": passenger_list
    }

    return res

async def checkpnr_vj(pnr):

    token = await get_app_access_token_from_state()
    

    company_info = await get_company(token)
    
    token = await get_app_access_token_from_state()
    res = await get_vietjet_pnr(token,pnr)
    if res:
        result = format_flight_data(res)
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
    print(result)
    return result



if __name__ == "__main__":


    async def main():
        a = await checkpnr_vj(
            "4FM22V"
        )
        print(a)

    asyncio.run(main())









