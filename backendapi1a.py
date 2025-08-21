import asyncio
import time
import random
import string
import json
import httpx
import re
from datetime import datetime,timedelta
from createNewSession import createNewSession

# ================== SESSION HANDLER ==================
SESSIONS = {}
SESSION_TTL = 900  # 15 phút
# Map sân bay sang UTC offset
# Map sân bay sang UTC offset
AIRPORT_TZ = {
    "HAN": 7,
    "SGN": 7,
    "DAD": 7,
    "ICN": 9,
    "PUS": 9,
    "CXR": 7,
    "PQC": 7,
    # nếu cần thì bổ sung thêm
}
MONTH_MAP = {
    "JAN": "01", "FEB": "02", "MAR": "03", "APR": "04",
    "MAY": "05", "JUN": "06", "JUL": "07", "AUG": "08",
    "SEP": "09", "OCT": "10", "NOV": "11", "DEC": "12"
}

def convert_date(date_str):
    # Ví dụ: "14NOV" => "14/11"
    day = date_str[:2]
    month = MONTH_MAP.get(date_str[2:].upper(), "??")
    return f"{day}/{month}"
def parse_booking(text):
    lines = text.splitlines()
    pax_list = []
    flight_lines = []
    ape_list = []
    fa_list = []

    # Regex bắt pax
    pax_pattern = re.compile(r"(\d+)\.([A-Z]+)/([A-Z\s]+?\([A-Z]+\))")
    # Regex bắt flight
    flight_pattern = re.compile(r"\s*\d+\s+VN\s+\d+")
    # Regex bắt APE
    ape_pattern = re.compile(r"APE\s+(.+)", re.IGNORECASE)
    # Regex bắt FA
    fa_pattern = re.compile(r"FA\sPAX\s+(\d+-\d+)", re.IGNORECASE)

    for i, line in enumerate(lines):
        # PAX
        pax_match = pax_pattern.findall(line)
        if pax_match:
            for _, ln, fn in pax_match:
                pax_list.append({"lastName": ln.strip(), "firstName": fn.strip()})
            # lấy chuyến bay sau dòng tên
            if i + 1 < len(lines) and flight_pattern.search(lines[i+1]):
                flight_lines.append(lines[i+1].strip())
            if i + 2 < len(lines) and flight_pattern.search(lines[i+2]):
                flight_lines.append(lines[i+2].strip())

        # APE
        ape_match = ape_pattern.search(line)
        if ape_match:
            ape_list.append(ape_match.group(1).strip())

        # FA
        fa_match = fa_pattern.search(line)
        if fa_match:
            fa_list.append(fa_match.group(1).strip())

    result = {
        "pax": pax_list,
        "flights": flight_lines,
        "APE": ape_list,
        "FA": fa_list,
        "paymentstatus": bool(fa_list)  # True nếu có vé, False nếu không
    }
    return result
def _to_utc(base_hhmm: str, tz_offset: int, day_offset: int = 0) -> datetime:
    """Chuyển HHMM local -> 'UTC giả lập' bằng cách TRỪ tz_offset và cộng day_offset nếu cần."""
    dt = datetime(2000, 1, 1, int(base_hhmm[:2]), int(base_hhmm[2:]))
    return dt - timedelta(hours=tz_offset) + timedelta(days=day_offset)

def parse_flight(flight_str: str) -> dict:
    # Ví dụ chuỗi:
    # "3  VN 415 R 14NOV 5 ICNHAN HK2  1805 2055  14NOV  E  VN/DE62IL"
    parts = flight_str.split()

    flight_no   = parts[2]          # 415
    fare_class  = parts[3]          # R / L ...
    dep_date    = parts[4]          # 14NOV
    city_pair   = parts[6]          # ICNHAN
    dep_time    = parts[8]          # 1805
    arr_time    = parts[9]          # 2055
    # Một số dòng có cột ngày đến ngay sau giờ đến:
    arr_date    = parts[10] if len(parts) > 10 and re.fullmatch(r"\d{2}[A-Z]{3}", parts[10]) else dep_date

    dep_airport = city_pair[:3]
    arr_airport = city_pair[3:]

    dep_tz = AIRPORT_TZ.get(dep_airport, 0)
    arr_tz = AIRPORT_TZ.get(arr_airport, 0)

    # Day offset dựa vào token ngày đến so với ngày đi (PNR chặng ngắn thường chỉ 0 hoặc 1 ngày)
    day_offset = 0 if arr_date == dep_date else 1

    dep_utc = _to_utc(dep_time, dep_tz, 0)
    arr_utc = _to_utc(arr_time, arr_tz, day_offset)

    # Nếu vẫn nhỏ hơn (đi tuyến dài/qua mốc) thì cộng thêm 1 ngày nữa cho chắc
    if arr_utc < dep_utc:
        arr_utc += timedelta(days=1)

    duration = arr_utc - dep_utc
    dur_minutes = duration.days * 24 * 60 + duration.seconds // 60
    dur_h = dur_minutes // 60
    dur_m = dur_minutes % 60

    return {
        "sohieumaybay": flight_no,
        "loaive": fare_class,
        "ngaycatcanh": convert_date(dep_date),
        "departure": dep_airport,
        "arrival": arr_airport,
        "giocatcanh": f"{dep_time[:2]}:{dep_time[2:]}",
        "giohacanh": f"{arr_time[:2]}:{arr_time[2:]}",
        "thoigianbay": f"{dur_h}h{dur_m:02d}m"
    }
def formatPNR(data):
    result = {
        "pnr": None,
        "status": "OK",
        "hang" : "VNA",
        "tongbillgiagoc": None,
        "currency": "KRW",
        "paymentstatus": bool(data.get("FA")),  # có FA thì coi như paid
        "hanthanhtoan": None,
        "chieudi": {},
        "chieuve": {},
        "passengers": []  # list hành khách
    }

    # === Lấy PNR từ flights (cuối dòng thường có /PNR)
    if data.get("flights"):
        match_pnr = re.search(r"/([A-Z0-9]{6})$", data["flights"][0])
        if match_pnr:
            result["pnr"] = match_pnr.group(1)

    # Lấy danh sách hành khách
    pax_list = data.get("pax", [])
    ape_list = data.get("APE", [])
    fa_list = data.get("FA", [])

    max_len = max(len(pax_list), len(ape_list), len(fa_list))

    for i in range(max_len):
        passenger = {
            "lastName": pax_list[i]["lastName"] if i < len(pax_list) else None,
            "firstName": pax_list[i]["firstName"] if i < len(pax_list) else None,
            "email": ape_list[i] if i < len(ape_list) else None,
            "sove": None
        }

        # Lấy số vé từ FA
        if i < len(fa_list):
            fa_parts = fa_list[i].split("/")
            if len(fa_parts) > 0:
                passenger["sove"] = fa_parts[0].replace("FA PAX", "").strip()

        result["passengers"].append(passenger)

        # === Chiều đi
        if data.get("flights"):
            if len(data["flights"]) > 0:
                result["chieudi"] = parse_flight(data["flights"][0])
            if len(data["flights"]) > 1:
                result["chieuve"] = parse_flight(data["flights"][1])

    return result

def generate_jsession():
    return ''.join(random.choices(string.ascii_letters + string.digits, k=16))

def create_new_session(jsession_id=None):
    if jsession_id is None:
        jsession_id = generate_jsession()
    a = createNewSession()
    if a ==None:
        SESSIONS[jsession_id] = {
            "cryptic": createNewSession(),
            "created_at": time.time()
        }
        return jsession_id
    SESSIONS[jsession_id] = {
        "cryptic": a,
        "created_at": time.time()
    }
    return jsession_id

def get_session(jsession_id):
    if jsession_id is None:
        return None
    session = SESSIONS.get(jsession_id)
    if not session:
        return None
    if time.time() - session["created_at"] > SESSION_TTL:
        del SESSIONS[jsession_id]
        return None
    return session["cryptic"]

def cleanup_sessions():
    now = time.time()
    expired = [sid for sid, s in SESSIONS.items() if now - s["created_at"] > SESSION_TTL]
    for sid in expired:
        del SESSIONS[sid]
    if expired:
        print(f"🗑 Đã xóa {len(expired)} session hết hạn")

def loadJsession(jsession_id=None):
    session = get_session(jsession_id)
    if session is None:
        ssid = create_new_session(jsession_id)
        #print(ssid)
        session = get_session(ssid)
        return [ssid, session]
    cleanup_sessions()
    return [jsession_id, session]


# ================== HTTPX CLIENT ==================
url = "https://tc345.resdesktop.altea.amadeus.com/cryptic/apfplus/modules/cryptic/cryptic?SITE=AVNPAIDL&LANGUAGE=GB&OCTX=ARDW_PROD_WBP"
urlclose = "https://tc345.resdesktop.altea.amadeus.com/app_ard/apf/do/loginNewSession.taskmgr/UMCloseSessionKey;jsessionid="
headers = {
    "accept": "*/*",
    "accept-language": "en-US,en;q=0.9",
    "content-type": "application/x-www-form-urlencoded; charset=UTF-8",
    "referer": "https://tc345.resdesktop.altea.amadeus.com/app_ard/apf/init/login?SITE=AVNPAIDL&LANGUAGE=GB&MARKETS=ARDW_PROD_WBP&ACTION=clpLogin",
}

with open("cookie1a.json", "r", encoding="utf-8") as f:
    cookies_raw = json.load(f)
COOKIES = {c["name"]: c["value"] for c in cookies_raw} if isinstance(cookies_raw, list) else cookies_raw

async def send_close(client: httpx.AsyncClient, ssid=None):
    ssid, cryp = loadJsession(ssid)
    if cryp==None:
        return ssid, None
    #print(ssid, cryp)
    jSessionId = cryp["jSessionId"]
    
    url = urlclose + jSessionId +"dispatch=close&flowId=apftaskmgr"

    

    
    resp = await client.get(url, headers=headers, cookies=COOKIES,  timeout=30)
    return ssid, resp
async def send_command(client: httpx.AsyncClient, command_str: str, ssid=None):
    ssid, cryp = loadJsession(ssid)
    #print(ssid,cryp["status"])
    if cryp["status"]=="ERROR":
        return ssid, cryp["code"]
    #print(ssid, cryp)
    jSessionId = cryp["jSessionId"]
    contextId = cryp["dcxid"]
    userId = cryp["officeId"]
    organization = cryp["organization"]

    payload = {
        "jSessionId": jSessionId,
        "contextId": contextId,
        "userId": userId,
        "organization": organization,
        "officeId": userId,
        "gds": "AMADEUS",
        "tasks": [
            {
                "type": "CRY",
                "command": {
                    "command": command_str,
                    "prohibitedList": "SITE_JCPCRYPTIC_PROHIBITED_COMMANDS_LIST_1"
                }
            },
            {
                "type": "ACT",
                "actionType": "speedmode.SpeedModeAction",
                "args": {
                    "argsType": "speedmode.SpeedModeActionArgs",
                    "obj": {}
                }
            }
        ]
    }

    data = {"data": json.dumps(payload, separators=(",", ":"))}
    resp = await client.post(url, headers=headers, cookies=COOKIES, data=data, timeout=30)
    return ssid, resp


# ================== BUSINESS LOGIC ==================
async def process_row(client: httpx.AsyncClient, row, ssid):
    """Xử lý 1 row combo (dùng lại ssid từ checkve1A)"""
    results = []

    for seg in row:
        print(f"👉 [Task] Đang check {seg}")
        ssid, res = await send_command(client, seg, ssid)
        #print("KQ seg:", res.text[:50])

        ssid, res = await send_command(client, "fxr/ky/rvfr,u", ssid)
        giachuyenbay = json.loads(res.text)
        giachuyenbay = giachuyenbay["model"]["output"]["crypticResponse"]["response"]
        print("KQ fxr:", giachuyenbay[:200])

        results.append({
            "combo": seg,
            "giachuyenbay": giachuyenbay
        })

        ssid, res = await send_command(client, "XE1,2", ssid)
        
    ssid, res = await send_command(client, "IG", ssid)
    return results



async def checkve1A(code,ssid=None):
    start_time = time.time()
    all_results = []

    async with httpx.AsyncClient(http2=False) as client:
        # chỉ gọi send_command lần đầu ở đây
        ssid, res = await send_command(client, code)
        data = json.loads(res.text)

        segments = data["model"]["output"]["speedmode"]["structuredResponse"]["availabilityResponse"]
        all_segments = []
        for segment in segments:
            j_list = []
            for group in segment["core"]:
                for leg in group:
                    for line in leg["line"]:
                        display = line["display"]

                        if any(item.get("v") == "KE" and item.get("c") == 2 for item in display):
                            continue

                        stt = next(
                            (item["v"].strip() for item in display if item.get("c") == 1 and item.get("v").strip()),
                            None
                        )

                        if stt and any(item.get("v", "").startswith("J") for item in display):
                            j_list.append(f"J{stt}")
            all_segments.append(j_list)

        combos = []
        if len(all_segments) >= 2:
            chieu_di = all_segments[0]
            chieu_ve = all_segments[1]
            for d in chieu_di:
                row = []
                for v in chieu_ve:
                    row.append(f"SS1{d}*{v}")
                combos.append(row)

        print("Tổ hợp:", combos)

        for row in combos:
            res_row = await process_row(client, row, ssid)
            all_results.extend(res_row)

    with open("ketqua.json", "w", encoding="utf-8") as f:
        json.dump(all_results, f, ensure_ascii=False, indent=2)

    print(f"⏱️ Tổng thời gian chạy: {time.time() - start_time:.2f} giây")
    return combos

async def checkPNR(code,ssid=None):
    start_time = time.time()
    segments=None
    try:
        async with httpx.AsyncClient(http2=False) as client:
            # chỉ gọi send_command lần đầu ở đây
            ssid, res = await send_command(client, "RT"+str(code))
            
            if str(res)=="403":
                return (str(res))
            data = json.loads(res.text)


            segments = data["model"]["output"]["crypticResponse"]["response"]
            if segments =="INVALID RECORD LOCATOR\n>":
                return {
                    "status": "Không phải VNA"
                }

            ssid, res = await send_close(client,  ssid)
            result = parse_booking(segments)
            result =formatPNR(result)
        with open("ketqua.json", "w", encoding="utf-8") as f:
            json.dump(result, f, ensure_ascii=False, indent=2)

            
        print(f"⏱️ Tổng thời gian chạy: {time.time() - start_time:.2f} giây")
        return result
    except Exception as e:
        print (" lỗi :" +str(e))
        return None

if __name__ == "__main__":
    print(asyncio.run(checkPNR("FJRPXF")))
