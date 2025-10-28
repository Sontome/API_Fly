import asyncio
import time
import random
import string
import json
import httpx
import re
from utils_telegram import send_mess
from datetime import datetime,timedelta
from createNewSession import createNewSession
from itertools import zip_longest
EMAIL_RE = re.compile(r'([A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,})', re.I)

# ================== SESSION HANDLER ==================
SESSIONS = {}
SESSION_TTL = 600  # 15 phút
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
def build_an_command(dep, arr, depdate, deptime, arrdate=None, arrtime=None):
    """
    Build lệnh AN cho Vietnam Airlines (1A format)
    Ví dụ:
    build_an_command("ICN", "HAN", "20FEB", "1035", "21FEB", "1040")
    => ANVN20FEBICNHAN1035*21FEB1040
    """
    cmd = f"ANVN{depdate}{dep}{arr}{deptime}"
    if arrdate and arrtime:
        cmd += f"*{arrdate}{arrtime}"
    return cmd
def parse_vn_flights(text):
    lines = text.splitlines()
    data = {"chiều_đi": {}, "chiều_về": {}}
    pattern_main = re.compile(r'^\s*(\d{1,2})\s+VN\s+(\d+)')
    pattern_hang = re.compile(r'\b([A-Z])\d\b')
    pattern_hang_cho = re.compile(r'\b([A-Z])L\b')

    # Thứ tự ưu tiên thực tế
    hang_order = ['Y', 'B', 'M', 'S', 'H', 'K', 'L', 'Q', 'N', 'R', 'T']

    buffer = {}

    # Gộp các dòng phụ
    for i, line in enumerate(lines):
        m = pattern_main.match(line)
        if m:
            num = int(m.group(1))
            flight_no = m.group(2)
            buffer[num] = line.strip()
            if i + 1 < len(lines):
                nxt = lines[i + 1]
                if re.match(r'^\s{2,}\S+', nxt):
                    buffer[num] += " " + nxt.strip()

    # Parse flight 1 và 11
    for num, key in [(1, "chiều_đi"), (11, "chiều_về")]:
        if num in buffer:
            line = buffer[num]
            match = pattern_main.match(line)
            if not match:
                continue
            so_may_bay = match.group(2)
            list_hang = list(set(pattern_hang.findall(line)))
            list_hang_cho = list(set(pattern_hang_cho.findall(line)))

            # Sort theo thứ tự ưu tiên
            list_hang = [h for h in hang_order if h in list_hang]
            list_hang_cho = [h for h in hang_order if h in list_hang_cho]

            data[key] = {
                "số_máy_bay": so_may_bay,
                "list_hạng": list_hang,
                "list_hạng_chờ": list_hang_cho
            }

    return data
def build_ss_command(flights,list_cmd, dep, arr, depdate, so_nguoi, arrdate=None):
    # Lấy chiều đi
    chieu_di = flights.get("chiều_đi", {})
    so_may_bay_di = chieu_di.get("số_máy_bay", "")
    list_hang_di = chieu_di.get("list_hạng", [])
    hang_di = list_hang_di[-1] if list_hang_di else ""  # hạng cuối cùng

    # Build lệnh đi
    cmd = f"SSVN{so_may_bay_di}{hang_di}{depdate}{dep}{arr}PE{so_nguoi}"

    # Nếu có chiều về + arrdate thì nối thêm
    chieu_ve = flights.get("chiều_về", {})
    if arrdate and chieu_ve:
        so_may_bay_ve = chieu_ve.get("số_máy_bay", "")
        list_hang_ve = chieu_ve.get("list_hạng", [])
        hang_ve = list_hang_ve[-1] if list_hang_ve else ""
        cmd += f"*SSVN{so_may_bay_ve}{hang_ve}{arrdate}{arr}{dep}PE{so_nguoi}"
    list_cmd.append(cmd)
    return list_cmd



def build_nm_command(hanhkhach, list_cmd):
    """
    Thêm các dòng lệnh hành khách vào list_cmd chính.
    - hanhkhach: list các dòng dạng 'NM1PHAM/THI NGA MS(ADT)'
    - list_cmd: list chứa các lệnh chính
    """
    if not isinstance(hanhkhach, list):
        raise ValueError("hanhkhach phải là list")
    if not isinstance(list_cmd, list):
        raise ValueError("list_cmd phải là list")

    for line in hanhkhach:
        line = line.strip()
        if line:  # tránh append dòng trống
            list_cmd.append("NM1"+line.upper())  # chuẩn hóa in hoa cho đúng format 1A
    list_cmd.append("AP HCMC 01035463396")
    
    return list_cmd
def build_pricing_command(hanhkhach, list_cmd, doituong):
    """
    Build lệnh pricing theo đối tượng hành khách.
    - hanhkhach: list chứa tên hoặc dòng hành khách
    - list_cmd: list chứa các lệnh chính
    - doituong: ADT | STU | VFR
    """
    has_infant = 0
    cmd = ""

    # Đảm bảo kiểu dữ liệu
    if not isinstance(hanhkhach, list):
        raise ValueError("hanhkhach phải là list")
    if not isinstance(list_cmd, list):
        raise ValueError("list_cmd phải là list")

    # Xử lý từng đối tượng
    doituong = doituong.upper().strip()

    if doituong == "ADT":
        cmd = "FXB"

    elif doituong == "STU":
        cmd = "FXB/RSTU,U"

    elif doituong == "VFR":
        parts = []
        has_chd = False
        has_infant = 0

        for idx, pax in enumerate(hanhkhach, start=1):
            pax_upper = pax.upper()

            # Check INF
            if "INF" in pax_upper:
                has_infant = 1
                

            # Check CHD
            if "CHD" in pax_upper:
                has_chd = True
                parts.append(f"PAX/P{idx}/RVFR-CH,U")
            else:
                parts.append(f"PAX/P{idx}/RVFR,U")

        if parts:
            cmd = "FXB/" + "//".join(parts)
        else:
            # không có pax nào => fallback chung
            cmd = "FXB/PAX/RVFR,U"

        

    # Thêm dòng chính FXB vào list
    if cmd:
        list_cmd.append(cmd)
    # Nếu có INF thì thêm dòng FXP riêng
    if has_infant and doituong=="VFR":
        list_cmd.append("FXP/INF/RVFR-INF,U")
    return list_cmd, has_infant
async def giu_ve_live_cmd(hanhkhach, dep, arr, depdate, deptime, arrdate=None, arrtime=None, doituong="VFR"):
    cmd_AN = build_an_command(dep, arr, depdate, deptime, arrdate, arrtime)
    print("Lệnh AN:", cmd_AN)

    try:
        async with httpx.AsyncClient(http2=False, timeout=60) as client:
            # Lấy session trước
            ssid, res = await send_command(client, "IG", "giuvelive")
            print(res)

            # Gửi lệnh AN
            ssid, resAN = await send_command(client, cmd_AN, "giuvelive")
            print(res)

            text = resAN.json()["model"]["output"]["crypticResponse"]["response"]
            print("Text AN:", text)

            result = parse_vn_flights(text)
            list_cmd = []
            so_nguoi = len(hanhkhach)

            # Build các command kế tiếp
            list_cmd = build_ss_command(result, list_cmd, dep, arr, depdate, so_nguoi, arrdate)
            print("Build SS done ✅")

            list_cmd = build_nm_command(hanhkhach, list_cmd)
            print("Build NM done ✅")

            list_cmd, has_infant = build_pricing_command(hanhkhach, list_cmd, doituong)
            print("Build pricing done ✅")

            # --- Gửi từng command trong list_cmd ---
            responses = []
            for idx, cmd in enumerate(list_cmd):
                print(f"👉 Gửi lệnh {idx+1}/{len(list_cmd)}: {cmd}")
                try:
                    ssid, res = await send_command(client, cmd, "giuvelive")
                    responses.append({
                        "cmd": cmd,
                        "response": res.json()["model"]["output"]["crypticResponse"]["response"]
                    })
                except Exception as e:
                    print(f"⚠️ Lỗi khi gửi {cmd}: {e}")
                    responses.append({"cmd": cmd, "response": "error"})

            # --- Nếu có INFANT ---
            if has_infant:
                print("Check list giá vé INF")
                try:
                    cmd_inf = get_cheapest_fxt_command(list_inf)
                    print(cmd_inf)
                    ssid, res = await send_command(client, cmd_inf, "giuvelive")
                    responses.append({
                        "cmd": cmd_inf,
                        "response": res.json()["model"]["output"]["crypticResponse"]["response"]
                    })
                    print("Xử lý yêu cầu chọn chuyến của INF ✅")
                except Exception as e:
                    print("Không có yêu cầu chọn chuyến của INF:", e)

            # --- Gửi chuỗi lệnh chốt vé ---
            for cmd in ["APE-hanvietair.service@gmail.com","APE-hanvietair.service@gmail.com/p1","APE-HANVIETAIR247@gmail.com/p1","APM-+82 1035463396","APM-+82 1035463396/p1","APM-+82 1021511790/p1","APN-E+HANVIETAIR.SERVICE@GMAIL.COM/VI/p1","APN-M+821035463396/VI/P1","TK OK", "RF HVA", "ER", "IG"]:
                print(f"✈️ Gửi {cmd}")
                ssid, res = await send_command(client, cmd, "giuvelive")
                responses.append({
                    "cmd": cmd,
                    "response": res.json()["model"]["output"]["crypticResponse"]["response"]
                })

            # --- Kiểm tra phản hồi IG cuối ---
            resend_text = responses[-1]["response"]
            print("📩 Kết quả IG cuối:", resend_text)

            # Regex tìm chuỗi dạng IGNORED - FMMOQR
            match = re.search(r"IGNORED\s*-\s*([A-Z0-9]{6})", resend_text)
            if match:
                pnr = match.group(1)
                print(f"✅ Giữ vé thành công! PNR: {pnr}")
                await send_mess(f"✅ Giữ vé VNA thành công! PNR: {pnr}")
                return {
                    "status": "OK",
                    "pnr": pnr,
                    "responses": responses
                }
            else:
                print("❌ Không tìm thấy PNR trong phản hồi IG.")
                return {
                    "status": "Error",
                    "responses": responses
                }

    except Exception as e:
        print("💥 Lỗi trong giu_ve_live_cmd:", e)
        await send_mess("lỗi api 1A")
        
        return {
            "status": "Error",
            "responses": str(e)
        }
MONTH_MAP = {
    "JAN": "01", "FEB": "02", "MAR": "03", "APR": "04",
    "MAY": "05", "JUN": "06", "JUL": "07", "AUG": "08",
    "SEP": "09", "OCT": "10", "NOV": "11", "DEC": "12"
}
def get_cheapest_fxt_command(data):
    """
    Hàm nhận vào object JSON (output từ 1A),
    tìm dòng giá vé thấp nhất và trả về lệnh FXT tương ứng.
    """
    try:
        text = data["model"]["output"]["crypticResponse"]["response"]
    except KeyError:
        return None  # data không đúng format

    # Regex bắt dòng kiểu:
    # 01 TKAP4KRE+* * IN       * P1,4       *     40300  *      *Y
    pattern = r"(\d{2})\s+\S+\*.*?\*\s+IN\s+\*\s+(P[\d,]+)\s+\*\s+(\d+)"
    matches = re.findall(pattern, text)

    fares = []
    for stt, pax, price in matches:
        fares.append((int(price), stt, pax))

    if not fares:
        return None

    # Sắp xếp giá tăng dần, lấy dòng rẻ nhất
    fares.sort(key=lambda x: x[0])
    _, stt, pax = fares[0]

    return f"FXT{stt}/{pax}"
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
def formatsove(text: str):
    # Lấy nội dung trong dấu ngoặc
    inside_parentheses = re.findall(r'\(([^)]*)\)', text)

    # Đếm số lần xuất hiện của ADT, CHD, INF
    count_ADT = sum(1 for s in inside_parentheses if 'ADT' in s)
    count_CHD = sum(1 for s in inside_parentheses if 'CHD' in s)
    count_INF = sum(1 for s in inside_parentheses if 'INF' in s)
    count_VFR = sum(1 for s in inside_parentheses if 'VFR' in s)
    count_STU = sum(1 for s in inside_parentheses if 'STU' in s)
    return ( count_ADT + count_CHD + count_INF + count_VFR +count_STU)
    
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
    print("cryp")
    if cryp["status"]=="ERROR":
        # print(cryp)
        return ssid, cryp
    
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
    print("send command")
     # với httpx async client phải await
    res= resp
    try:
        js = res.json()    # nếu resp là sync object
        # check nếu là lỗi từ API 1A
        if (
            isinstance(js, dict)
            and "model" in js
            and "output" in js["model"]
            and "crypticError" in js["model"]["output"]
        ):
            err = js["model"]["output"]["crypticError"]
            if "errorNumber" in err and err["errorNumber"] == 99000:
                await send_mess("lỗi api 1A")
    except Exception:
        print("Không parse được JSON:", await res.text())
    return ssid, resp


# ================== BUSINESS LOGIC ==================
async def process_row(client: httpx.AsyncClient, row, ssid):
    """Xử lý 1 row combo (dùng lại ssid từ checkve1A)"""
    results = []

    for seg in row:
        # print(f"👉 [Task] Đang check {seg}")
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
            print("clearcode")
            ssid, res = await send_command(client, "RT"+str(code),ssid)
            
            # if str(res["code"])=="403":
            #     return (str(res))
            
            data = res.json()
            
            # print(data)

            # segments = data["model"]["output"]["crypticResponse"]["response"]
            # if segments =="INVALID RECORD LOCATOR\n>":
            #     return {
            #         "status": "Không phải VNA"
            #     }
            # print(segments)
            # loop_count=0
            # while ")>" in segments and loop_count < 3:
            #     loop_count += 1
            #     ssid, res_md = await send_command(client, "md", ssid)
            #     data_md = json.loads(res_md.text)
            #     segments_md = data_md["model"]["output"]["crypticResponse"]["response"]
            #     segments += segments_md  # gộp thêm
                

            #     segments = deduplicate_lines(segments)
            # with open("test.json", "w", encoding="utf-8") as f:
            #      f.write(segments)
            ssid, res = await send_command(client, "IG", ssid)
            #result = parse_booking(segments)
            result = data
        # with open("ketqua.json", "w", encoding="utf-8") as f:
        #     json.dump(result, f, ensure_ascii=False, indent=2)

            
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
            
            if str(res["code"])=="403":
                return (str(res))
            data = json.loads(res.text)


            segments = data["model"]["output"]["crypticResponse"]["response"]
            if segments =="INVALID RECORD LOCATOR\n>":
                return {
                    "status": "Không phải VNA"
                }
            #print(segments)
            
            
            ssid, res = await send_command(client, "IG", ssid)
            
            result =(formatsove(segments))
        

            
        print(f"⏱️ Tổng thời gian chạy: {time.time() - start_time:.2f} giây")
        return result
    except Exception as e:
        print (" lỗi :" +str(e))
        return None
async def code1a(code,ssid):
    
    segments=None
    try:
        async with httpx.AsyncClient(http2=False) as client:
            # chỉ gọi send_command lần đầu ở đây
            
            ssid, res = await send_command(client, str(code),ssid)
            print(res.json())
            respone = res.json()
            
            
            
            
            
            
            
            
        return respone
    except Exception as e:
        await send_mess("lỗi api 1A")
        return {"error": str(e)}


async def sendemail1a(code, ssid):
    try:
        async with httpx.AsyncClient(http2=False) as client:
            print("⚡ Gọi send_command lần 1...")
            ssid, res = await send_command(client, "RT" + str(code), ssid)

            # check text "NO MATCH FOR RECORD LOCATOR"
            if "NO MATCH FOR RECORD LOCATOR" in res.text:
                print("⛔ Không tìm thấy PNR:", code)
                return "None"

            print("✅ Response lần 1:", res.text)
            respone = res.json()
            

            print("⚡ Gọi send_command lần 2...")
            ssid, res = await send_command(client, "ITR-EML-HANVIETAIR.SERVICE@GMAIL.COM/LP VI", ssid)
            print("✅ Response lần 2:", res.text)
            respone = res.json()
            

        return respone

    except Exception as e:
        print("🚨 Lỗi khi chạy:", e)
        await send_mess("lỗi api 1A")
        return {"error": str(e)}
# if __name__ == "__main__":
#     print(asyncio.run(checksomatveVNA("EN4IGQ","Check")))



async def repricePNR(pnr, doituong):
    try:
        async with httpx.AsyncClient(http2=False) as client:
            ssid, res = await send_command(client, "IG", "reprice")
            print("clear code")
            ssid, res = await send_command(client, "RT" + str(pnr), "reprice")

            print("✅ Response RT ... ")
            ssid, namelist = await send_command(client, "RTN", "reprice")

            print("✅ Response RTN ... ")
            ssid, pricegocres = await send_command(client, "TQT", "reprice")
            
            print("✅ Response gia goc ... ")
            pricegoc_data = pricegocres.json()
            pricegoc = pricegoc_data["model"]["output"]["crypticResponse"]["response"]
            # Build lệnh 
            namelist_data = namelist.json()
            resp_text = namelist_data["model"]["output"]["crypticResponse"]["response"]
            lines = [x.strip() for x in resp_text.split("\n") if re.match(r"^\d+\.", x.strip())]
            # ✅ Regex bắt tất cả dạng: "1.TEN/...(...)" kể cả dính nhau
            pattern = r"(\d+)\.([A-Z/\s]+(?:MR|MS|MISS|MSTR)?\([^)]*\))"
            matches = re.findall(pattern, resp_text, flags=re.DOTALL)
            has_infant = "(INF/" in resp_text
            pax_cmd_parts = []
            
            for pax_num, pax_info in matches:
                pax_info = pax_info.strip()
                pax_doituong = doituong.upper()
            
               
            
                pax_type_suffix = ""
                if "(CHD/" in pax_info:
                    pax_type_suffix = "-CH"
                    if pax_doituong == "STU":
                        pax_doituong = "VFR"
                elif "(ADT)" in pax_info:
                    pax_type_suffix = ""
            
                pax_cmd = f"/PAX/P{pax_num}/R{pax_doituong}{pax_type_suffix},U"
                pax_cmd_parts.append(pax_cmd)
                
            # Nếu có trẻ sơ sinh → gọi lệnh riêng trước
            ssid, res = await send_command(client, "tte/all", "reprice")
            list_inf = ""
            print("✅ Xóa TST all... ")
            if has_infant and doituong.upper() != "ADT":
                pax_doituong_inf = doituong.upper()
                if pax_doituong_inf== "STU":
                    pax_doituong_inf = "VFR"
                pax_cmd_inf = f"FXP/INF/RVFR-INF,U"
                print("👶 Có trẻ sơ sinh → gọi FXP/INF trước")
                
                ssid, list_inf_raw = await send_command(client, pax_cmd_inf, "reprice")
                list_inf = list_inf_raw.json()
                print(pax_cmd_inf)
                try:

                    cmd_inf = get_cheapest_fxt_command(list_inf)
                    print(cmd_inf)
                    ssid, res = await send_command(client, cmd_inf, "reprice")
                    print("Xử lý yêu cầu chọn chuyến của inf")
                except:
                    print("Không có yêu cầu chọn chuyến của inf")
            

            # Gộp các phần thành lệnh hoàn chỉnh
            if doituong.upper() != "ADT":
                final_cmd = "FXB" + "/".join(pax_cmd_parts)
            else:
                final_cmd = "FXB"
            if doituong.upper() == "STU":
                final_cmd = "FXB/PAX/RSTU,U"

            print(f"⚙️ Lệnh final: {final_cmd}")

            ssid, res = await send_command(client, final_cmd, "reprice")
            print("✅ Response lenh reprice ... ")

            ssid, pricemoires = await send_command(client, "TQT", "reprice")

            print("✅ Response gia moi ... ")
            pricemoi_data = pricemoires.json()
            pricemoi = pricemoi_data["model"]["output"]["crypticResponse"]["response"]
            
            ssid, res = await send_command(client, "rfson hva", "reprice")

            print("✅ Response rfson ... ")
            ssid, res = await send_command(client, "ET", "reprice")

            print("✅ Response ET ... ")
            respone = res.json()
            respone["pricegoc"] = pricegoc
            respone["pricemoi"] = pricemoi
            respone["list_inf"] = list_inf
            ssid, res = await send_command(client, "IG", "reprice")

            #print (respone)
            
            
        return respone

    except Exception as e:
        print("🚨 Lỗi khi chạy:", e)
        await send_mess("lỗi api 1A")
        return {"error": str(e)}


async def beginRepricePNR(pnr):
    try:
        async with httpx.AsyncClient(http2=False) as client:
            ssid, res = await send_command(client, "IG", "beginreprice")
            print("clear code")
            ssid, res = await send_command(client, "RT" + str(pnr), "beginreprice")

            print("✅ Response RT ... ")
           
            ssid, pricegocres = await send_command(client, "TQT", "beginreprice")
            
            print("✅ Response gia goc ... ")
            pricegoc_data = pricegocres.json()
            pricegoc = pricegoc_data["model"]["output"]["crypticResponse"]["response"]
            
            ssid, res = await send_command(client, "IG", "beginreprice")

            print("✅ Response IG ... ")
            respone = res.json()
            respone["pricegoc"] = pricegoc
            
            

            #print (respone)
            
            
        return respone

    except Exception as e:
        print("🚨 Lỗi khi chạy:", e)
        await send_mess("lỗi api 1A")
        return {"error": str(e)}


def parse_pnr(text,pnr):
    data = {"pnr": pnr,"chang": [], "passengers": [], "paymentstatus": False,"tongbillgiagoc":0,"doituong":"ADT"}

    # ======== CHECK THANH TOÁN ========
    data["status"] = "OK"
    data["paymentstatus"] = "FA PAX" in text

    # ======== BẮT HÀNH KHÁCH ========
    passenger_pattern = re.compile(r"(\d+)\.([A-Z]+)\/([A-Z\s]+?)(?:\((\w+)\))?(?=\s+\d+\.|\n|$)")
    for match in passenger_pattern.finditer(text):
        last, first, type_ = match.group(2), match.group(3).strip(), match.group(4) or ""
        data["passengers"].append({
            "lastName": last,
            "firstName": first,
            "loaikhach": type_
        })

    # ======== BẮT CHẶNG BAY ========
    flight_pattern = re.compile(
        r"VN\s*(\d+)\s+([A-Z])\s+(\d{2}[A-Z]{3})\s+\d+\s+([A-Z]{3})([A-Z]{3})\s+([A-Z]{2}\d+)\s+(\d{4})\s+(\d{4})\s+(\d{2}[A-Z]{3})"
    )
    chang_so = 1
    current_year = datetime.now().year
    current_month = datetime.now().month

    def convert_date(datestr):
        """Chuyển '03DEC' → datetime object"""
        day = int(datestr[:2])
        month_str = datestr[2:].upper()
        month_map = {
            "JAN": 1, "FEB": 2, "MAR": 3, "APR": 4,
            "MAY": 5, "JUN": 6, "JUL": 7, "AUG": 8,
            "SEP": 9, "OCT": 10, "NOV": 11, "DEC": 12
        }
        month = month_map.get(month_str, 1)
        year = current_year if month >= current_month else current_year + 1
        return datetime(year, month, day)

    # ======== MAP MÚI GIỜ ========
    timezone_offset = {
        # 🇻🇳 Việt Nam (UTC+7)
        "SGN": 7, "HAN": 7, "DAD": 7, "CXR": 7, "PQC": 7, "VII": 7,
        "VCA": 7, "HPH": 7, "THD": 7, "UIH": 7, "HUI": 7, "VCL": 7,
        "BMV": 7, "DIN": 7, "DLI": 7, "PXU": 7, "VCS": 7, "CAH": 7,
        "TBB": 7, "VDH": 7, "VKG": 7,

        # 🇰🇷 Hàn Quốc (UTC+9)
        "ICN": 9, "GMP": 9, "PUS": 9, "CJU": 9, "TAE": 9, "KWJ": 9,
        "USN": 9, "RSU": 9, "KPO": 9, "WJU": 9, "YNY": 9, "CHF": 9, "HIN": 9,
    }

    for f in flight_pattern.finditer(text):
        so_hieu = f"VN{f.group(1)}"
        loai_ve = f.group(2)
        ngay_cat_raw = f.group(3)
        dep = f.group(4)
        arr = f.group(5)
        status = f.group(6)
        gio_cat = f.group(7)
        gio_ha = f.group(8)
        ngay_ha_raw = f.group(9)

        ngay_cat = convert_date(ngay_cat_raw)
        ngay_ha = convert_date(ngay_ha_raw)

        try:
            # Parse giờ
            t1 = datetime.strptime(gio_cat, "%H%M")
            t2 = datetime.strptime(gio_ha, "%H%M")

            # Nếu giờ hạ < giờ cất → sang ngày hôm sau
            # if t2 < t1:
            #     ngay_ha += timedelta(days=1)

            # Ghép lại thành datetime full
            dep_dt = datetime.combine(ngay_cat.date(), t1.time())
            arr_dt = datetime.combine(ngay_ha.date(), t2.time())

            # Cộng/trừ theo chênh lệch múi giờ
            dep_offset = timezone_offset.get(dep.upper(), 0)
            arr_offset = timezone_offset.get(arr.upper(), 0)
            delta_tz = (arr_offset - dep_offset)

            # Thời gian bay thực tế
            diff = arr_dt - dep_dt - timedelta(hours=delta_tz)
            hours = diff.seconds // 3600
            minutes = (diff.seconds // 60) % 60
            flight_time = f"{hours:02}:{minutes:02}"

        except Exception as e:
            flight_time = ""

        data["chang"].append({
            "sochang": chang_so,
            "departure": dep,
            "departurename": map_airport_name(dep),
            "arrival": arr,
            "arrivalname": map_airport_name(arr),
            "loaive": loai_ve,
            "status": status,
            "giocatcanh": f"{gio_cat[:2]}:{gio_cat[2:]}",
            "ngaycatcanh": ngay_cat.strftime("%d/%m/%Y"),
            "giohacanh": f"{gio_ha[:2]}:{gio_ha[2:]}",
            "ngayhacanh": ngay_ha.strftime("%d/%m/%Y"),
            "thoigianbay": flight_time,
            "sohieumaybay": so_hieu
        })
        chang_so += 1

    return data


# ===============================
# 📍 Map mã sân bay -> tên
# ===============================
def map_airport_name(code: str) -> str:
    mapping = {
        # 🇻🇳 VIỆT NAM
        "SGN": "Ho Chi Minh",
        "HAN": "Ha Noi",
        "DAD": "Da Nang",
        "CXR": "Nha Trang",
        "PQC": "Phu Quoc",
        "VII": "Vinh",
        "VCA": "Can Tho",
        "HPH": "Hai Phong",
        "THD": "Thanh Hoa",
        "UIH": "Quy Nhon",
        "HUI": "Hue",
        "VCL": "Chu Lai",
        "BMV": "Buon Ma Thuot",
        "DIN": "Dien Bien Phu",
        "DLI": "Da Lat",
        "PXU": "Pleiku",
        "VCS": "Con Dao",
        "CAH": "Ca Mau",
        "TBB": "Tuy Hoa",
        "VDH": "Dong Hoi",
        "VKG": "Rach Gia",

        # 🇰🇷 HÀN QUỐC
        "ICN": "Seoul",
        "GMP": "Seoul",
        "PUS": "Busan",
        "CJU": "Jeju",
        "TAE": "Daegu",
        "KWJ": "Gwangju",
        "USN": "Ulsan",
        "RSU": "Yeosu",
        "KPO": "Pohang",
        "WJU": "Wonju",
        "YNY": "Yangyang",
        "CHF": "Chuncheon",
        "HIN": "Jinju",
    }

    # fallback: nếu không tìm thấy
    return mapping.get(code.upper(), f"Unknown ({code.upper()})")
def parse_price(text):
    result = {
        "total": 0,
        "priceperone": False,
        "doituong":"ADT",
        "tqtnumber":"0"
    }
    if "KRH" in text:
        result["doituong"] = "STU"
    elif "KRE" in text:
        result["doituong"] = "VFR"
    # ======== CASE 1: Có GRAND TOTAL KRW ========
    grand_total_match = re.search(r"\nGRAND TOTAL KRW\s+([\d,]+)", text)
    if grand_total_match:
        total = grand_total_match.group(1).replace(",", "")
        result["total"] = int(total)
        result["priceperone"] = True
        return result

    # ======== CASE 2: Không có GRAND TOTAL ========
    price_matches = re.findall(r"KRW\s+([\d,]+)\s+BT\/", text)
    if price_matches:
        total_sum = sum(int(p.replace(",", "")) for p in price_matches)
        result["total"] = total_sum
        result["priceperone"] = False
        # ======== Lấy số đầu tiên của dòng thứ 2 ========
        lines = text.strip().splitlines()
        if len(lines) >= 2:
            match_num = re.match(r"\s*(\d+)", lines[1])
            if match_num:
                result["tqtnumber"] = str(match_num.group(1))

    return result
async def checkmatvechoVNA(code,ssid=None):
    
    segments=None
    try:
        async with httpx.AsyncClient(http2=False) as client:
            # chỉ gọi send_command lần đầu ở đây
            ssid, res = await send_command(client, "IG", ssid)
            print("clearcode")
            ssid, res = await send_command(client, "RT"+str(code),ssid)
            
            # if str(res["code"])=="403":
            #     return (str(res))
            
            data = res.json()
            
            # print(data)

            rt_respone_raw = data["model"]["output"]["crypticResponse"]["response"]
            rt_respone = parse_pnr(rt_respone_raw,code)
            

                
                
            try:
                ssid, res = await send_command(client, "TQT", ssid)
            
                
                data = res.json()
                tqt_reponse=data["model"]["output"]["crypticResponse"]["response"]
                tqt = parse_price(tqt_reponse)
                print(tqt["tqtnumber"])
                
                rt_respone["doituong"] = tqt["doituong"]
                if tqt["priceperone"]==True:

                    rt_respone["tongbillgiagoc"] = int(tqt["total"])*len(rt_respone["passengers"])
                else :
                    ssid, res_fare_raw = await send_command(client, "TQT/T"+tqt["tqtnumber"], ssid)
                    res_fare = res_fare_raw.json()["model"]["output"]["crypticResponse"]["response"]
                    vfr_fare = re.search(r"KRE", res_fare)
                    stu_fare = re.search(r"KRH", res_fare)
                    
                    rt_respone["tongbillgiagoc"] = int(tqt["total"])
                    if vfr_fare :
                        rt_respone["doituong"] = "VFR"
                    if stu_fare :
                        rt_respone["doituong"] = "STU"

            except:
                pass

            ssid, res = await send_command(client, "IG", ssid)
            print("clearcode")
        
        return (rt_respone)
    except Exception as e:
        print (" lỗi :" +str(e))
        await send_mess("lỗi api 1A")
        return None
if __name__ == "__main__":
    b="DLOEQY"
    b="D8D4LD"
    a = asyncio.run(checkmatvechoVNA(b,"checkmatvecho"))
    print(a)




































