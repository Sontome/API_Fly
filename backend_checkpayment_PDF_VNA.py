import re
import fitz
from datetime import datetime

def check_payment_vna(pdf_path):
    # mapping sân bay (KEY uppercase substrings) -> IATA
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
        "VAN DON INTL": "VDO"
    }
    # đảm bảo keys uppercase (bảo hiểm)
    airports_map = {k.upper(): v for k, v in airports_map_raw.items()}

    doc = fitz.open(pdf_path)
    # ====== 🔥 TÌM SỐ VÉ 738 ======
    full_text = ""
    for p in doc:
        full_text += p.get_text().upper() + "\n"

    # match 738-xxxxxxxxxx | 738 xxxxxxxxxx | 738xxxxxxxxxx
    ticket_match = re.search(r"\b738[-\s]?\d{10}\b", full_text)
    sove = ticket_match.group(0) if ticket_match else ""
    page = doc[0]
    raw_blocks = page.get_text("blocks")  # list of tuples

    # chuẩn hoá block structure: index, raw_text, lines, upper_text
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

    # tìm các block "departure" (phải có flight number + time)
    departure_indices = []
    for i, blk in enumerate(blocks):
        # flight number pattern: 1-3 letters + digits (cơ bản)
        has_flight_no = re.search(r"\b[A-Z]{1,3}\d{1,4}\b", blk["upper"])
        has_time = re.search(r"\b\d{2}:\d{2}\b", blk["upper"])
        if has_flight_no and has_time:
            departure_indices.append(i)

    def find_airports_near(block_index, max_window=5):
        """
        Trả về list các IATA codes tìm được (theo order xuất hiện trên trang),
        up to 2 codes. Ta scan window xung quanh block_index, collect (block_idx, line_idx, code),
        rồi sort theo block_idx,line_idx để đảm bảo order top->bottom.
        """
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
                        break  # next line

        # sort theo vị trí trên trang (block index asc, line index asc)
        matches_sorted = sorted(matches, key=lambda x: (x[0], x[1]))

        # dedupe giữ lần xuất hiện đầu tiên
        seen = set()
        codes_ordered = []
        for bi, li, code in matches_sorted:
            if code not in seen:
                codes_ordered.append(code)
                seen.add(code)
            if len(codes_ordered) >= 2:
                break

        return codes_ordered

    # tạo result slots
    result = {
        "trip1": "", "day1": "", "time1": "",
        "trip2": "", "day2": "", "time2": "",
        "trip3": "", "day3": "", "time3": "",
        "trip4": "", "day4": "", "time4": ""
    }

    # duyệt từng departure block, lấy time/day và tìm airport pair gần nhất
    for idx, dep_idx in enumerate(departure_indices):
        if idx >= 4:
            break  # chỉ lấy tối đa 4 chuyến
        blk = blocks[dep_idx]
        # time hh:mm (first match)
        t_m = re.search(r"\b(\d{2}:\d{2})\b", blk["upper"])
        time_str = t_m.group(1) if t_m else ""

        # day (ví dụ 12Feb2026) - block upper, chuyển .title() để parse
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

        # tìm airports gần block này (theo vị trí trang)
        codes = find_airports_near(dep_idx, max_window=5)
        trip_code = ""
        if len(codes) >= 2:
            # đảm bảo origin là cái đứng trước destination trên trang
            trip_code = f"{codes[0]}-{codes[1]}"
        else:
            trip_code = ""  # nếu không đủ 2 code thì để rỗng

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
#print(check_payment_vna("input.pdf"))

