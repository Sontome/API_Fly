import asyncio
import time
import random
import string
import json
import httpx
import re
from datetime import datetime,timedelta
from createNewSession import createNewSession
from itertools import zip_longest
EMAIL_RE = re.compile(r'([A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,})', re.I)

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
def deduplicate_lines(raw_text):
    # Cắt thành từng dòng, loại bỏ khoảng trắng dư
    lines = [line.strip() for line in raw_text.splitlines() if line.strip()]

    # Lọc trùng, giữ nguyên thứ tự xuất hiện đầu tiên
    seen = set()
    unique_lines = []
    for line in lines:
        if line not in seen:
            seen.add(line)
            unique_lines.append(line)

    return "\n".join(unique_lines)

def convert_date(date_str):
    # Ví dụ: "14NOV" => "14/11"
    day = date_str[:2]
    month = MONTH_MAP.get(date_str[2:].upper(), "??")
    return f"{day}/{month}"

def _to_utc(base_hhmm: str, tz_offset: int, day_offset: int = 0) -> datetime:
    """Chuyển HHMM local -> 'UTC giả lập' bằng cách TRỪ tz_offset và cộng day_offset nếu cần."""
    dt = datetime(2000, 1, 1, int(base_hhmm[:2]), int(base_hhmm[2:]))
    return dt - timedelta(hours=tz_offset) + timedelta(days=day_offset)


def parse_flights(data):
    flights = []
    for item in data:
        line = item.get("info", "").strip()
        if not line:
            continue

        parts = line.split()

        flight_code = parts[0] + parts[1]  # VD: VN417
        fare_class = parts[2]              # VD: R
        date_str = parts[3]                # VD: 20AUG

        # Xử lý năm, nếu tháng bay < tháng hiện tại => năm sau
        month_now = datetime.now().month
        month_flight = datetime.strptime(date_str, "%d%b").month
        year = datetime.now().year + (1 if month_flight < month_now else 0)
        date_fmt = datetime.strptime(f"{date_str}{year}", "%d%b%Y").strftime("%d/%m/%Y")

        origin = parts[5][:3]  # VD: ICN
        dest = parts[5][3:]    # VD: HAN

        if "FLWN" in line:
            dep_time = "Đã Bay"
            arr_time = ""
        else:
            dep_time = parts[7][:2] + ":" + parts[7][2:]
            arr_time = parts[8][:2] + ":" + parts[8][2:] if len(parts) > 8 else ""

        flights.append({
            "số_máy_bay": flight_code,
            "ngày_đi": date_fmt,
            "nơi_đi": origin,
            "nơi_đến": dest,
            "giờ_đi": dep_time,
            "giờ_đến": arr_time,
            "loại_vé": fare_class
        })

    return flights
def formatsove(text):
    # Cắt từng dòng + bỏ dòng trống
    lines = [l.strip() for l in text.split("\n") if l.strip()]

    tickets = []
    seen = set()

    for line in lines:
        if any(key in line for key in ["FA PAX", "FA INF", "FA CHD"]):
            parts = line.split()
            if len(parts) >= 4:
                ticket_number = parts[3].split("/")[0]
                if ticket_number not in seen:
                    seen.add(ticket_number)
                    tickets.append(ticket_number)

    return tickets
def formatPNR(text):
    # Cắt từng dòng + bỏ dòng trống
    lines = [l.strip() for l in text.split("\n") if l.strip()]

    data = {
        "pnr": "",
        "passengers": [],
        "flights": [],
        "email": "",
        "phone": "",
        "tickets": []
    }

    current_passenger_index = -1
    all_tickets = set()  # gom vé ở đây

    for line in lines:
        # Lấy PNR
        if line.startswith("RP/") and line.split()[-1]:
            data["pnr"] = line.split()[-1]

        # Lấy tên hành khách
        elif line[0].isdigit() and "." in line and ")" in line and "VN" not in line:
            current_passenger_index += 1
            data["passengers"].append({"name": line.split(".", 1)[1].strip()})

        # Lấy flight info
        elif line[0].isdigit() and " VN" in line:
            data["flights"].append({"info": line.split(" ", 1)[1].strip()})

        # Lấy email
        elif " APE " in line and not data["email"]:
            data["email"] = line.split("APE", 1)[1].strip()

        # Lấy phone
        elif " APM " in line and not data["phone"]:
            data["phone"] = line.split("APM", 1)[1].strip()

        # Lấy ticket FA PAX
        elif "FA PAX" in line:
            ticket_number = line.split()[3].split("/")[0]
            all_tickets.add(ticket_number)

    # Lọc flight
    data["flights"] = [
        f for f in data["flights"]
        if f["info"].startswith("VN") and not f["info"].startswith("VN SSR")
        and not f["info"].startswith("SSR")
    ]

    # Convert set vé -> list (bỏ trùng + giữ thứ tự thêm)
    data["tickets"] = list(dict.fromkeys(all_tickets))
    data["flights"] = parse_flights(data["flights"] )
    return data
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
        print(cryp)
        return ssid, cryp["code"]
    
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
            ssid, res = await send_command(client, "IG", ssid)
            ssid, res = await send_command(client, "RT"+str(code),ssid)
            
            if str(res)=="403":
                return (str(res))
            data = json.loads(res.text)


            segments = data["model"]["output"]["crypticResponse"]["response"]
            if segments =="INVALID RECORD LOCATOR\n>":
                return {
                    "status": "Không phải VNA"
                }
            print(segments)
            loop_count=0
            while ")>" in segments and loop_count < 3:
                loop_count += 1
                ssid, res_md = await send_command(client, "md", ssid)
                data_md = json.loads(res_md.text)
                segments_md = data_md["model"]["output"]["crypticResponse"]["response"]
                segments += segments_md  # gộp thêm
                

                segments = deduplicate_lines(segments)
            with open("test.json", "w", encoding="utf-8") as f:
                 f.write(segments)
            ssid, res = await send_command(client, "IG", ssid)
            #result = parse_booking(segments)
            result =formatPNR(segments)
        with open("ketqua.json", "w", encoding="utf-8") as f:
            json.dump(result, f, ensure_ascii=False, indent=2)

            
        print(f"⏱️ Tổng thời gian chạy: {time.time() - start_time:.2f} giây")
        return result
    except Exception as e:
        print (" lỗi :" +str(e))
        return None
async def checksomatveVNA(code,ssid=None):
    start_time = time.time()
    segments=None
    try:
        async with httpx.AsyncClient(http2=False) as client:
            # chỉ gọi send_command lần đầu ở đây
            ssid, res = await send_command(client, "IG", ssid)
            ssid, res = await send_command(client, "RT"+str(code),ssid)
            
            if str(res)=="403":
                return (str(res))
            data = json.loads(res.text)


            segments = data["model"]["output"]["crypticResponse"]["response"]
            if segments =="INVALID RECORD LOCATOR\n>":
                return {
                    "status": "Không phải VNA"
                }
            #print(segments)
            loop_count=0
            while ")>" in segments and loop_count < 3:
                loop_count += 1
                ssid, res_md = await send_command(client, "md", ssid)
                data_md = json.loads(res_md.text)
                segments_md = data_md["model"]["output"]["crypticResponse"]["response"]
                segments += segments_md  # gộp thêm
                

                segments = deduplicate_lines(segments)
            with open("test.json", "w", encoding="utf-8") as f:
                 f.write(segments)
            ssid, res = await send_command(client, "IG", ssid)
            #result = parse_booking(segments)
            result =len(formatsove(segments))
        with open("ketqua.json", "w", encoding="utf-8") as f:
            json.dump(result, f, ensure_ascii=False, indent=2)

            
        print(f"⏱️ Tổng thời gian chạy: {time.time() - start_time:.2f} giây")
        return result
    except Exception as e:
        print (" lỗi :" +str(e))
        return None

# if __name__ == "__main__":
#     print(asyncio.run(checksomatveVNA("DMSOVU","Check")))

