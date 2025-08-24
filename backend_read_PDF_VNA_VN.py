import fitz
from datetime import datetime, timedelta
import re
import time
NEW_TEXT = "Noi xuat ve:\nB2BAGTHANVIETAIR, 220-1,2NDFLOOR, SUJIRO489\nBEON-GIL15, SUJI-GU, YONGIN-SI, GYEONGGI-DO, SEOUL\nSo dien thoai:  +82-10-3546-3396\nEmail:  Hanvietair@gmail.com\nNgay:  "
 
START_PHRASE = "Nơi xuất vé:"
END_PHRASE = "Ngày:"
def replace_text_between_phrases(pdf_path,
                                  new_text,start_phrase=START_PHRASE, end_phrase=END_PHRASE,
                                 font_size=10):
    outputpath = "output"+pdf_path
    doc = fitz.open(pdf_path)
    page = doc[0]  # chỉ page đầu
    fs = font_size * 0.8

    text = page.get_text()
    #print("===== TEXT PAGE 1 =====")
    #print(text)

    # ===== LẤY NGÀY SAU "Ngày:" =====
    date_found = None
    if "Ngày:" in text:
        start_idx = text.find("Ngày:") + len("Ngày:")
        raw_date = text[start_idx:start_idx+10].strip()
        #print(f"[DEBUG] Ngày gốc sau 'Ngày:': {raw_date}")
        try:
            dt = datetime.strptime(raw_date, "%d%b%Y")
            date_found = dt.strftime("%d/%m/%Y")
            #print(f"[DEBUG] Ngày chuẩn hóa: {date_found}")
        except:
            #print("[DEBUG] Không parse được ngày, giữ nguyên")
            date_found = raw_date
    if date_found:
        new_text_lines = new_text.split("\n")
        for i, line in enumerate(new_text_lines):
            if line.strip().startswith("Ngay:"):
                new_text_lines[i] = f"Ngay: {date_found}"
        new_text = "\n".join(new_text_lines)

    # ===== LẤY GIỜ & NGÀY BAY =====
    found_time = None
    found_date = None

    for line in text.splitlines():
        if re.fullmatch(r"\d{2}:\d{2}", line.strip()):
            found_time = line.strip()
            #print(f"[DEBUG] Giờ bay tìm thấy: {found_time}")
            break

    date_pattern = re.compile(r"\b\d{2}[A-Za-z]{3}\d{4}\b")
    date_matches = date_pattern.findall(text)
    #print(f"[DEBUG] Danh sách date matches: {date_matches}")
    if len(date_matches) >= 2:
        try:
            d = datetime.strptime(date_matches[1], "%d%b%Y")
            found_date = d.strftime("%d/%m/%Y")
            #print(f"[DEBUG] Ngày bay tìm thấy: {found_date}")
        except:
            print("[DEBUG] Không parse được ngày bay")

    if found_time and found_date:
        try:
            flight_dt = datetime.strptime(f"{found_date} {found_time}", "%d/%m/%Y %H:%M")
            checkin_dt = flight_dt - timedelta(hours=4)
            periodt = "(Sang)" if checkin_dt.hour < 12 else "(Chieu)"
            note_str = f"Luu y: Quy khach vui long den san bay truoc {checkin_dt.strftime('%d/%m/%Y %H:%M')} {periodt} de lam thu tuc len may bay."
            #print(f"[DEBUG] Giờ check-in: {note_str}")
        except Exception as e:
            print("[DEBUG] Lỗi parse giờ/ngày:", e)

    # ===== XỬ LÝ GIỜ (thêm sáng/chiều) =====
    for idx, line in enumerate(text.splitlines()):
        if ":" in line:
            time_part = line.strip()
            try:
                t = datetime.strptime(time_part, "%H:%M")
                period = "(Sang)" if t.hour < 12 else "(Chieu)"
                time_part_new = f"{time_part} {period}"
                #print(f"[DEBUG] Đổi giờ: '{time_part}' → '{time_part_new}'")
            except:
                continue
            search_rects = page.search_for(time_part)
            for rect in search_rects:
                page.add_redact_annot(rect)
                page.apply_redactions()
                page.insert_text(
                    (rect.x0, rect.y0 + 5),
                    time_part_new,
                    fontsize=fs,
                    fill=(250/255, 0, 0),
                    render_mode=0
                )

    # ===== AUTO ĐỔI DẠNG NGÀY =====
    matches = set(date_pattern.findall(text))
    for match in matches:
        try:
            d = datetime.strptime(match, "%d%b%Y")
            new_date = d.strftime("%d/%m/%Y")
            #print(f"[DEBUG] Đổi ngày: '{match}' → '{new_date}'")
            search_rects = page.search_for(match)
            for rect in search_rects:
                page.add_redact_annot(rect)
                page.apply_redactions()
                page.insert_text(
                    (rect.x0, rect.y0 + 5),
                    new_date,
                    fontsize=fs,
                    fill=(0, 0, 0),
                    render_mode=0
                )
        except:
            continue

    # ===== ĐỔI MÀU HÀNH LÝ =====
    hl_pattern = re.compile(r"Hành lý: [12]PC")
    matches = set(hl_pattern.findall(text))
    for match in matches:
        #print(f"[DEBUG] Đổi màu đỏ: '{match}'")
        search_rects = page.search_for(match)
        for rect in search_rects:
            page.add_redact_annot(rect)
            page.apply_redactions()
            page.insert_text(
                (rect.x0, rect.y0 + 5),
                match,
                fontsize=fs,
                fill=(250/255, 0, 0),
                render_mode=0
            )

    # ===== THÊM NOTE KHI THẤY DÒNG OK/RQ =====
    note_text = "(1) OK = Đã xác nhận , RQ/SA = Chưa xác nhận chỗ"
    search_rects = page.search_for(note_text)
    for rect in search_rects:
        #print("[DEBUG] Thêm ghi chú cho dòng OK/RQ")
        page.insert_text(
            (rect.x0, rect.y1 + 20),
            note_str,
            fontsize=fs*1.4,
            fill=(1, 0, 0),
            render_mode=0
        )

    # ===== REPLACE TEXT CHÍNH =====
    blocks = page.get_text("blocks")
    for block in blocks:
        block_text = block[4]
        if start_phrase in block_text and end_phrase in block_text:
            #print("[DEBUG] Thay block chính")
            x0, y0, x1, y1 = block[:4]
            rect = fitz.Rect(x0, y0, x1, y1)
            page.add_redact_annot(rect)
            page.apply_redactions()

            adj_x = x0 + 15
            adj_y = y0 + 15
            for i, line in enumerate(new_text.split("\n")):
                if ":" in line:
                    bold_part, normal_part = line.split(":", 1)
                    bold_part += ": "
                    page.insert_text(
                        (adj_x, adj_y + i * (fs + 2)),
                        bold_part,
                        fontsize=fs,
                        fill=(0/255, 61/255, 77/255),
                        render_mode=0.5
                    )
                    text_width = fitz.get_text_length(bold_part, fontsize=fs)
                    page.insert_text(
                        (adj_x + text_width + 3, adj_y + i * (fs + 2)),
                        normal_part.strip(),
                        fontsize=fs,
                        fill=(0, 0, 0),
                        render_mode=0
                    )
                else:
                    page.insert_text(
                        (adj_x, adj_y + i * (fs + 2)),
                        line,
                        fontsize=fs,
                        fill=(0, 0, 0),
                        render_mode=0
                    )

    # ===== GẮN LINK MỚI =====
    rect = fitz.Rect(000, 000, 600, 200)  # (x1, y1, x2, y2)
    page.insert_link({
        "kind": fitz.LINK_URI,
        "from": rect,
        "uri": "https://www.facebook.com/HanVietAirCom",
        "border": [0, 0, 1]
    })

    # ===== LƯU TRỰC TIẾP =====
    doc.save(outputpath)
    #print(f"[DEBUG] Đã lưu file ra: {outputpath}")
    doc.close()
    time.sleep(0.5)
    extract_first_page(outputpath)
    

def extract_first_page(input_pdf):
    """Lấy page 1 của PDF và lưu ra file mới, giữ nguyên hyperlink."""
    doc = fitz.open(input_pdf)
    new_doc = fitz.open()

    # Page 0 là trang 1
    new_doc.insert_pdf(doc, from_page=0, to_page=0, links=True)
    doc.close()
    new_doc.save(input_pdf)
    
    new_doc.close()
    
    #print(f"✅ Đã xuất page 1 ra: {input_pdf}")



 
def reformat_VNA_VN(input_pdf,new_text=NEW_TEXT):
    if new_text=="":
        new_text=NEW_TEXT
    replace_text_between_phrases(
    input_pdf,
    
    new_text
)
# Ví dụ dùng

# ===== TEST =====


#extract_first_page("output.pdf")