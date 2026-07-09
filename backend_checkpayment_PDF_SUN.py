import re
import fitz
from datetime import datetime

def check_payment_sun(pdf_path):
    # mapping sân bay (KEY uppercase substrings) -> IATA
    # dùng chung với VNA vì cách hiển thị tên sân bay giống nhau
    airports_map_raw = {
        "SEOUL INCHEON INTERNATION": "ICN",
        "BUSAN GIMHAE INTL": "PUS",
        "DAEGU INTL": "TAE",
        "HANOI NOI BAI INTL": "HAN",
        "HO CHI MINH CITY TAN SON NHAT": "SGN",
        "DA NANG INTERNATIONAL": "DAD",
        "HAI PHONG CAT BI INTL": "HPH",
        "CAN THO INTL": "VCA",
        "NHA TRANG CAM RANH": "CXR",
        "DA LAT LIEN KHUONG": "DLI",
        "DONG HOI INTL": "VDH",
        "BUON MA THUOT BUON MA THUOT": "BMV",
        "VINH VINH/VN": "VII",
        "QUY NHON PHU CAT": "UIH",
        "THANH HOA THO XUAN": "THD",
        "PHU QUOC INTL": "PQC",
        "PLEIKU PLEIKU": "PXU",
        "HUE PHU BAI INTL": "HUI",
        "QUANG NAM CHU LAI": "VCL",
        "CA MAU CA MAU": "CAH",
        "DIEN BIEN DIEN BIEN PHU": "DIN",
        "RACH GIA RACH GIA": "VKG",
        "TUY HOA TUY HOA": "TBB",
        "VAN DON INTL": "VDO",
        "TAIPEI TAOYUAN INTL": "TPE"
    }
    airports_map = {k.upper(): v for k, v in airports_map_raw.items()}

    doc = fitz.open(pdf_path)

    # ====== TÌM SỐ VÉ (dạng 809 2451473800 / 809-2451473800 / 8092451473800) ======
    full_text = ""
    for p in doc:
        full_text += p.get_text().upper() + "\n"

    ticket_match = re.search(r"\bSỐ VÉ\s*:?\s*(\d{3}[-\s]?\d{10})\b", full_text)
    if not ticket_match:
        ticket_match = re.search(r"\b\d{3}[-\s]?\d{10}\b", full_text)

    sove = ""
    if ticket_match:
        sove = re.sub(r"[-\s]", "", ticket_match.group(1) if ticket_match.lastindex else ticket_match.group(0))

    page = doc[0]
    raw_blocks = page.get_text("blocks")

    blocks = []
    for i, b in enumerate(raw_blocks):
        raw_text = b[4]
        lines = [ln.strip() for ln in raw_text.splitlines() if ln.strip()]
        blocks.append({
            "idx": i,
            "raw": raw_text,
            "lines": lines,
            "upper": raw_text.upper()
        })

    # tìm các block "departure" (phải có số hiệu chuyến bay dạng 9G411 + giờ)
    departure_indices = []
    for i, blk in enumerate(blocks):
        # flight number Sun PhuQuoc: digit + letter + digits, vd 9G411, 9G410
        has_flight_no = re.search(r"\b\d[A-Z]\d{2,4}\b", blk["upper"])
        has_time = re.search(r"\b\d{2}:\d{2}\b", blk["upper"])
        if has_flight_no and has_time:
            departure_indices.append(i)

    def find_airports_near(block_index, max_window=5):
        matches = []
        start = max(0, block_index - max_window)
        end = min(len(blocks) - 1, block_index + max_window)
        for bi in range(start, end + 1):
            blk = blocks[bi]
            for li, line in enumerate(blk["lines"]):
                uline = line.upper()
                for ap_name, code in airports_map.items():
                    if ap_name in uline:
                        matches.append((bi, li, code))
                        break

        matches_sorted = sorted(matches, key=lambda x: (x[0], x[1]))

        seen = set()
        codes_ordered = []
        for bi, li, code in matches_sorted:
            if code not in seen:
                codes_ordered.append(code)
                seen.add(code)
            if len(codes_ordered) >= 2:
                break

        return codes_ordered

    result = {
        "trip1": "", "day1": "", "time1": "",
        "trip2": "", "day2": "", "time2": "",
        "trip3": "", "day3": "", "time3": "",
        "trip4": "", "day4": "", "time4": ""
    }

    for idx, dep_idx in enumerate(departure_indices):
        if idx >= 4:
            break
        blk = blocks[dep_idx]

        t_m = re.search(r"\b(\d{2}:\d{2})\b", blk["upper"])
        time_str = t_m.group(1) if t_m else ""

        d_m = re.search(r"\b(\d{1,2}[A-Z]{3}\d{4})\b", blk["upper"])
        if d_m:
            day_raw = d_m.group(1)
            try:
                day_dt = datetime.strptime(day_raw.title(), "%d%b%Y")
                day_str = day_dt.strftime("%d/%m/%Y")
            except Exception:
                day_str = day_raw
        else:
            day_str = ""

        codes = find_airports_near(dep_idx, max_window=5)
        trip_code = ""
        if len(codes) >= 2:
            trip_code = f"{codes[0]}-{codes[1]}"

        result[f"trip{idx+1}"] = trip_code
        result[f"day{idx+1}"] = day_str
        result[f"time{idx+1}"] = time_str

    doc.close()
    return {
        "paymentstatus": "True",
        "sove": sove,
        "result": result
    }

# ví dụ chạy
# print(check_payment_sun("input_sun.pdf"))
