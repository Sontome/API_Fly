import fitz
import re
from datetime import datetime

def check_payment(pdf_path):
    doc = fitz.open(pdf_path)
    page = doc[0]

    # Extract tên khách (nếu có)
    name = None
    blocks = page.get_text("blocks")
    if len(blocks) > 3:
        text_block3 = blocks[3][4]
        cleaned = text_block3.replace("Tên:", "").strip()
        name = re.sub(r"[^\w\s]", "", cleaned)

    # ===== Check thanh toán trước =====
    note_text = "Vui lòng thanh toán trước"
    search_rects = page.search_for(note_text)
    paymentstatus = "False" if search_rects else "True"

    # Nếu chưa thanh toán → return luôn, trips rỗng
    if paymentstatus == "False":
        doc.close()
        return {
            "paymentstatus": paymentstatus,
            "name": name,
            
            "result": {f"{k}{i}": "" for i in range(1,5) for k in ["trip","day","time"]}
        }

    # ===== Đã thanh toán thì mới parse =====
    date_pattern = re.compile(r"\b[A-Z][a-z]{2}\s+\d{1,2},\s+\d{4}\b")
    trip_pattern = re.compile(r"\b\d{2}:\d{2}\s*-\s*[A-Za-zÀ-ỹ\s]+\b")

    days, tripinfo = [], []

    for b in blocks:
        text_in_block = b[4]

        matches_date = date_pattern.findall(text_in_block)
        if matches_date:
            days.extend(matches_date)

        matches_trip = trip_pattern.findall(text_in_block)
        if matches_trip:
            tripinfo.extend([m.strip() for m in matches_trip])

    # Convert ngày sang dd/mm/yyyy
    converted_days = []
    for d in days:
        try:
            dt = datetime.strptime(d, "%b %d, %Y")
            converted_days.append(dt.strftime("%d/%m/%Y"))
        except Exception:
            converted_days.append(d)

    # Parse tripinfo
    trips = []
    for t in tripinfo:
        try:
            time_part, place_part = t.split("-", 1)
            time_part = time_part.strip()
            place_part = place_part.replace("Terminal", "").strip()
            trips.append({"time": time_part, "place": place_part})
        except Exception:
            continue

    # Ghép trip → day → time
    result = {}
    trip_count = min(len(trips) // 2, len(converted_days))
    for i in range(trip_count):
        from_place = trips[2*i]["place"]
        to_place = trips[2*i+1]["place"]
        date = converted_days[i] if i < len(converted_days) else ""
        time = trips[2*i]["time"]

        trip_no = i + 1
        result[f"trip{trip_no}"] = f"{from_place}-{to_place}"
        result[f"day{trip_no}"] = date
        result[f"time{trip_no}"] = time

    # Bổ sung đủ trip1..trip4
    for j in range(1, 5):
        result.setdefault(f"trip{j}", "")
        result.setdefault(f"day{j}", "")
        result.setdefault(f"time{j}", "")

    doc.close()
    return {
        "paymentstatus": paymentstatus,
        "name": name,
        
        "result": result
    }

# Test
#print(check_payment("input1.pdf"))
