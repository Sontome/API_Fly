import asyncio
import time
import random
import string
import json
import httpx
import re
from datetime import datetime,timedelta

from createNewSessionSUN import createNewSession




SESSIONS = {}
SESSION_TTL = 600  # 15 phút
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
url = "https://tc110.resdesktop.altea.amadeus.com/cryptic/apfplus/modules/cryptic/cryptic?SITE=A9GPAIDL&LANGUAGE=GB&OCTX=ARDW_PROD_WBP"
urlclose = "https://tc110.resdesktop.altea.amadeus.com/app_ard/apf/do/loginNewSession.taskmgr/UMCloseSessionKey;jsessionid="
headers = {
    "accept": "*/*",
    "accept-language": "en-US,en;q=0.9",
    "content-type": "application/x-www-form-urlencoded; charset=UTF-8",
    "referer": "https://tc110.resdesktop.altea.amadeus.com/app_ard/apf/init/login?SITE=A9GPAIDL&LANGUAGE=GB&MARKETS=ARDW_PROD_WBP&ACTION=clpLogin",
}

with open("cookie1a_sun.json", "r", encoding="utf-8") as f:
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
    # print(cryp)
    if cryp["status"]=="ERROR":
        print(cryp)
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
    # print(res)
    try:
        js = res.json()    # nếu resp là sync object
        # check nếu là lỗi từ API 1A
        
    except Exception:
        print("Không parse được JSON:", await res.text())
    return ssid, resp
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
    pattern = r"(\d{2})\s+\S+\s+\*\s+IN\s+\*\s+(P\d+(?:,\d+)*)\s+\*\s+(\d+)"
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

async def beginRepricePNR_SUN(pnr:str):
    try:
        async with httpx.AsyncClient(http2=False) as client:
            ssid, res = await send_command(client, "IG", str(pnr))
            print("clear code")
            ssid, res = await send_command(client, "RT" + str(pnr), str(pnr))

            print("✅ Response RT ... ")
            data = res.json()
            
            # print(data)

            rt_respone_raw = data["model"]["output"]["crypticResponse"]["response"]
            # nếu có page 2 thì gọi thêm MD đúng 1 lần
            if ")>" in rt_respone_raw:
                print("co trang 2")
        
                ssid, res_md = await send_command(client, "MD", str(pnr))
        
                data_md = res_md.json()
        
                rt_respone_raw += "\n" + data_md["model"]["output"]["crypticResponse"]["response"]
            rt_respone = parse_pnr(rt_respone_raw,pnr)
            ssid, pricegocres = await send_command(client, "TQT", str(pnr))
            
            print("✅ Response gia goc ... ")
            pricegoc_data = pricegocres.json()
            pricegoc = pricegoc_data["model"]["output"]["crypticResponse"]["response"]
            
            ssid, res = await send_command(client, "IG", str(pnr))

            print("✅ Response IG ... ")
            listhanhly= parse_segments(pricegoc)
            rt_respone["listhanhly"] = listhanhly
            # print(listhanhly)
            # ✅ Cập nhật doituong theo passenger_type từ listhanhly
            if listhanhly:
                rt_respone["doituong"] = listhanhly[0].get("passenger_type", "ADT")
            ssid, res = await send_close(client, str(pnr))
            print("close Session")
            

            #print (respone)
            
            
        return rt_respone
    except Exception as e:
        print("🚨 Lỗi khi chạy:", e)
        
        return {"error": str(e)}
async def repricePNR_SUN(pnr, type, rt_respone=None):
    try:
        async with httpx.AsyncClient(http2=False) as client:
            ssid, res = await send_command(client, "IG", pnr)
            print("clear code")
            ssid, res = await send_command(client, "RT" + str(pnr), pnr)
            print("✅ Response RT ... ")
            data = res.json()

            rt_respone_raw = data["model"]["output"]["crypticResponse"]["response"]
            rt_respone = parse_pnr(rt_respone_raw, pnr)

            if type == "VFR":
                # ── Phân loại passengers theo loaikhach (index 1-based) ──
                adt_indices = []
                chd_indices = []
                has_inf = False

                for i, pax in enumerate(rt_respone.get("passengers", []), start=1):
                    loai = pax.get("loaikhach", "ADT").upper()
                    if loai == "CHD":
                        chd_indices.append(str(i))
                    else:
                        adt_indices.append(str(i))
                    if pax.get("inf"):
                        has_inf = True

                # ── Build FXP command ──
                parts = []
                if adt_indices:
                    parts.append(f"PAX/RVFR,U555555/P{','.join(adt_indices)}")
                if chd_indices:
                    parts.append(f"PAX/RVFR-CH,U555555/P{','.join(chd_indices)}")

                commandreprice = "FXP/" + "//".join(parts)
                print(f"🧾 FXP command: {commandreprice}")

            else:
                commandreprice = "FXB"

            ssid, pricegocres = await send_command(client, commandreprice, pnr)
            print("✅ Response FXP/FXB ... ")
            pricegoc = pricegocres.json()
            giareprice = pricegoc["model"]["output"]["crypticResponse"]["response"]

            # Kiểm tra KRW
            if "KRW" not in giareprice:
                print("⚠️ Không có KRW, bỏ qua")
                ssid, res = await send_command(client, "IG", pnr)
                ssid, res = await send_close(client, pnr)
                print("close Session")
                return {"status": "ERROR", "reason": "KRW not found", "response": giareprice}

            # ── Xử lý INF nếu có ──
            if type == "VFR" and has_inf:
                ssid, list_inf_raw = await send_command(client, "FXP/INF/RVFR-IN,U", pnr)
                list_inf = list_inf_raw.json()
                print("📦 Xử lý INF reprice")
                try:
                    cmd_inf = get_cheapest_fxt_command(list_inf)
                    print(f"🎫 FXT INF command: {cmd_inf}")
                    if cmd_inf:
                        ssid, res = await send_command(client, cmd_inf, pnr)
                        print("✅ Xử lý yêu cầu chọn chuyến của inf")
                    else:
                        print("⚠️ Không tìm được FXT command cho INF")
                except Exception as e:
                    print(f"⚠️ Không có yêu cầu chọn chuyến của inf: {e}")

            ssid, res = await send_command(client, "RFHVA", pnr)
            print("✅ Response RFHVA ... ")

            ssid, res = await send_command(client, "ET", pnr)
            print("✅ Response ET ... ")

            ssid, res = await send_command(client, "IG", pnr)
            ssid, res = await send_close(client, pnr)
            print("close Session")

        return {"status": "OK"}

    except Exception as e:
        print("🚨 Lỗi khi chạy:", e)
        return {"error": str(e)}
async def autoRepricePNR_SUN(pnr: str):
    try:
        # Bước 1: beginRepricePNR_SUN
        print(f"🔍 Begin reprice PNR: {pnr}")
        begin_result = await beginRepricePNR_SUN(pnr)

        if "error" in begin_result:
            print(f"❌ beginRepricePNR_SUN lỗi: {begin_result['error']}")
            return {"status": "ERROR", "reason": "beginRepricePNR_SUN failed", "detail": begin_result}

        # Bước 2: Kiểm tra loaive của tất cả chặng
        chang_list = begin_result.get("chang", [])
        if not chang_list:
            return {"status": "ERROR", "reason": "Không có chặng bay"}

        excluded_classes = {"S", "G", "A", "X"}
        all_valid_class = all(
            seg.get("loaive", "") not in excluded_classes
            for seg in chang_list
        )

        # Bước 3: Kiểm tra departure chặng 1
        dep_chang1 = chang_list[0].get("departure", "")
        valid_departure = dep_chang1 in ("ICN", "PUS")

        print(f"✅ loaive hợp lệ: {all_valid_class}, departure chặng 1: {dep_chang1}")

        if not all_valid_class or not valid_departure:
            return {
                "status": "SKIP",
                "reason": "Không đủ điều kiện reprice",
                "all_valid_class": all_valid_class,
                "departure_chang1": dep_chang1
            }

        # Bước 4: Chạy repricePNR_SUN
        print(f"🚀 Đủ điều kiện, tiến hành reprice VFR cho PNR: {pnr}")
        reprice_result = await repricePNR_SUN(pnr, "VFR")

        return {
            "status": reprice_result.get("status", "ERROR"),
            "pnr": pnr,
            "reprice_result": reprice_result
        }

    except Exception as e:
        print(f"🚨 autoRepricePNR_SUN lỗi: {e}")
        return {"status": "ERROR", "reason": str(e)}
def parse_segments(text):
    pattern = re.compile(
        r"^\s*\d+\s+[A-Z ]?\s*([A-Z]{3})\s+\w+\s+\d+\s+\w\s+\d{2}[A-Z]{3}\s+\d{4}\s+OK\s+([A-Z0-9]+)",
        re.MULTILINE
    )

    segments = []

    for airport, fare_basis in pattern.findall(text):
        segments.append({
            "airport": airport,
            "fare_basis": fare_basis,
            "passenger_type": "VFR" if fare_basis.endswith("0KE") else "ADT"
        })

    return segments
def parse_pnr(text,pnr):
    text=text.replace("*", " ")
    data = {"pnr": pnr,"chang": [], "passengers": [], "paymentstatus": False,"tongbillgiagoc":0,"doituong":"ADT","giavegoc":0}

    # ======== CHECK THANH TOÁN ========
    data["status"] = "OK"
    data["paymentstatus"] = "FA PAX" in text

    # ======== BẮT HÀNH KHÁCH ========
    passenger_pattern = re.compile(
        r"(\d+)\.([A-Z]+)\/([A-Z\s]+?)"       # số thứ tự + họ + tên
        r"(?:\(([A-Z]+(?:\/\d{2}[A-Z]{3}\d{2})?)\))?"  # loại hành khách + ngày sinh nếu có
        r"(?:\((INF[A-Z0-9\/\s]+)\))?"          # INF nếu có
        r"(?=\s+\d+\.|\n|$)"
    )

    for match in passenger_pattern.finditer(text):
        last = match.group(2)
        first = match.group(3).strip()
        type_ = match.group(4) or ""  # ADT, CHD, MSTR
        bd = None
        inf_raw = match.group(5)
        if '/' in type_:
            type_part, bd_raw = type_.split('/', 1)
            type_ = type_part
            try:
                bd = datetime.strptime(bd_raw, "%d%b%y").strftime("%d/%m/%Y")
            except ValueError:
                bd = None 
        passenger = {
            "lastName": last,
            "firstName": first,
            "loaikhach": type_,
            "ngaysinh": bd
        }

        if inf_raw:
            inf_raw = inf_raw.replace("INF", "", 1).strip()
            if "/" in inf_raw:
                inf_last, inf_first = inf_raw.split("/", 1)
                passenger["inf"] = {
                    "lastName": inf_last.strip(),
                    "firstName": inf_first.strip()
                }

        data["passengers"].append(passenger)

    # ======== BẮT CHẶNG BAY ========
    flight_pattern = re.compile(
        r"^\s*\d+\s+"
        r"9G\s+(\d+)\s+"
        r"([A-Z])\s+"
        r"(\d{2}[A-Z]{3})\s+"
        r"(\d)\s+"
        r"([A-Z]{3})([A-Z]{3})\s+"
        r"([A-Z]{2}\d+)\s+"
        r"(\d+)\s+"
        r"(\d{4})\s+"
        r"(\d{4})",
        re.MULTILINE
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
        so_hieu = f"9G{f.group(1)}"
        loai_ve = f.group(2)
        ngay_cat_raw = f.group(3)
        dep = f.group(5)
        arr = f.group(6)
        status = f.group(7)
        gio_cat = f.group(9)
        gio_ha = f.group(10)
        ngay_ha_raw = f.group(3)

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
    # ======== BUILD KAKAO MESSAGE ========
    lines = []

    for seg in data.get("chang", []):
        dep = seg.get("departure", "")
        arr = seg.get("arrival", "")
        time = seg.get("giocatcanh", "")
        full_date = seg.get("ngaycatcanh", "")

        short_date = ""
        if full_date:
            parts = full_date.split("/")
            if len(parts) >= 2:
                short_date = f"{parts[0]}/{parts[1]}"

        if dep and arr:
            lines.append(f"{dep}-{arr} {time} ngày {short_date}")

    data["kakaomess"] = "\n".join(lines)
    return data

# print(asyncio.run(beginRepricePNR_SUN("FYLNP3"))    )    
# print(asyncio.run(repricePNR_SUN("FYLNP3","VFR")))
