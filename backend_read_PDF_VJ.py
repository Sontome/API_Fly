import fitz
from datetime import datetime, timedelta
import re
import time
import requests
import json
import os
from get_bag_info_pnr_vj import get_bag_info_vj
FONT_ARIAL = "/usr/share/fonts/truetype/msttcorefonts/Arial.ttf"
NEW_TEXT = "Nơi xuất vé:\nB2BAGTHANVIETAIR, 220-1,2NDFLOOR, SUJIRO489\nBEON-GIL15, SUJI-GU, YONGIN-SI, GYEONGGI-DO, SEOUL\nSo dien thoai :                   +82-10-3546-3396\nEmail:  Hanvietair@gmail.com  "

START_PHRASE = "Công Ty Cổ Phần Hàng Không VietJet"
END_PHRASE = "Tax ID: 0-1055-56100-55-1"
def find_text_coordinates(layout, search_text):
    """
    Tìm tọa độ (x0, y0) của text trong layout PDF.
    Nếu tìm thấy 2 kết quả trở lên thì trả về kết quả thứ 2.
    Nếu chỉ có 1 hoặc không có thì trả kết quả phù hợp.
    """
    pattern = re.escape(search_text)
    coords_list = []

    for block in layout.get("blocks", []):
        for line in block.get("lines", []):
            line_text = " ".join(span["text"] for span in line["spans"]).strip()
            if re.search(pattern, line_text):
                x0, y0, _, _ = line["bbox"]
                coords_list.append([x0, y0])

    if len(coords_list) >= 2:
        return coords_list[1]
    elif coords_list:
        return coords_list[0]
    else:
        return None
def check_bag_vj(pnr):
    try:
        url = "https://thuhongtour.com/get_bag_vj"
        params = {
            "pnr": pnr
        }
        headers = {
            "accept": "application/json"
        }
        
        response = requests.get(url, params=params, headers=headers)
    
    
        return response.text
    except Exception:
        return None
def prase_tieude_hanhly(data):
    tieude = []
    for chieu in data:
        tieude.append(chieu["chiều"])
    format_bag_route(tieude)
    return format_bag_route(tieude)
def merge_bag_info(data):
    result = {}

    for idx, chieu in enumerate(data):
        for p in chieu["passengers"]:
            name = p["tên"]
            bag = p.get("Bag", "     -     ") or "     -     "  # nếu None hoặc "" thì để --
            if name not in result:
                result[name] = ["     -     ", "     -     "]  # mặc định 2 chiều đều rỗng
            result[name][idx] = bag  # gán theo thứ tự chiều đi / chiều về

    return [
        {"tên": name, "hành lý": "           ".join(bags)}
        for name, bags in result.items()
    ]
def format_bag_route(routes):
    if not routes:
        return "Hành lý"
    if len(routes) == 1:
        return f"Hành lý    {routes[0]}"
    return f"Hành lý    {routes[0]}  |  {routes[1]}"

def add_bag_info(bag,layout,page,fs):
    passenger = bag["tên"]
    baginfo = bag["hành lý"]
    toadopassenger = find_text_coordinates(layout, passenger)
    
    toadothanhhanhlydi_khung = fitz.Rect(toadopassenger[0], toadopassenger[1], toadopassenger[0]+30,toadopassenger[1]+10)
    #page.add_redact_annot(toadothanhhanhly_khung)
    page.apply_redactions()
    page.insert_text(
        (toadopassenger[0]+220, toadopassenger[1]+15),
        baginfo,
        
        fontsize=fs*1.2,
        # fontfile=FONT_ARIAL_BOLD if os.path.exists(FONT_ARIAL_BOLD) else FONT_ARIAL,
        # fontname="arialbold" if os.path.exists(FONT_ARIAL_BOLD) else "arial",
        fill=(1, 0, 0),
        render_mode=0
    )
def replace_text_between_phrases(pdf_path, output_path,
                                  new_text, start_phrase=START_PHRASE, end_phrase=END_PHRASE,
                                  font_size=10):

    doc = fitz.open(pdf_path)
    page = doc[0]  # chỉ page đầu
    fs = font_size * 0.8
    text = page.get_text()
    #print(text)
    pnrformat = r"\b[A-Z0-9]{6}\b"

    layout = page.get_text("dict")
    baglist = None
    for block in layout["blocks"]:
        for line in block.get("lines", []):
            line_text = " ".join(span["text"] for span in line["spans"]).strip()
            if re.search(pnrformat, line_text  )and len(line_text.replace(" ", "")) == 6:
                
                pnr = line_text.strip()
                print(pnr)
                baglist = get_bag_info_vj(pnr)
                print(baglist)
                
                
                if baglist:
                    tieude= prase_tieude_hanhly(baglist)
                    # ===== khung số cân hành lý =====  
                        
                    toadothanhhanhlydi = find_text_coordinates(layout, "Tên hành khách")
                    print(toadothanhhanhlydi)
                    toadothanhhanhlydi_khung = fitz.Rect(toadothanhhanhlydi[0], toadothanhhanhlydi[1], toadothanhhanhlydi[0]+30,toadothanhhanhlydi[1]+10)
                    #page.add_redact_annot(toadothanhhanhly_khung)
                    page.apply_redactions()
                    page.insert_text(
                        (toadothanhhanhlydi[0]+170, toadothanhhanhlydi[1]+8),
                        tieude,
                        # fontfile=FONT_ARIAL,
                        # fontname = "arial",
                        fontsize=fs*1.2,
                        fill=(1, 1, 1),
                        render_mode=0
                    )
                    bags= merge_bag_info(baglist)
                    print(bags)
                    for bag in bags:
                        add_bag_info(bag,layout,page,fs)
                    print(tieude)
                    break
    print("chạy xong hành lý")

    
    

    # ===== LẤY GIỜ BAY =====
    found_time = None
    found_date = None
    for line in text.splitlines():
        match = re.match(r"(\d{2}:\d{2})\s*-\s*.*", line.strip())
        #print(match)
        if match:
            time_part = match.group(1)
            found_time = time_part
            break
    for line in text.splitlines():
        match = re.match(r"(\d{2}:\d{2})\s*-\s*.*", line.strip())
        
        if match:
            #print(match)
            time_part = match.group(1)
            full_part = match.group(0)
            #print(full_part)
            try:
                t = datetime.strptime(time_part, "%H:%M")
                hour = t.hour
                if 0 <= hour <= 6:
                    period = "(Rang sang)"
                elif 6 < hour <= 11:
                    period = "(Sang)"
                elif 11 < hour <= 13:
                    period = "(Trua)"
                elif 13 < hour <= 18:
                    period = "(Chieu)"
                else:
                    period = "(Dem)"
                
                time_new = f"{full_part} {period}"
                #print(f"[DEBUG] Giờ bay: {full_part} → {time_new}")
            except:
                time_new = time_part
                period = ""
            
            # Chèn text trực tiếp vào PDF
            search_rects = page.search_for(full_part)
            #print(search_rects)
            if search_rects:
                # Gộp tất cả rect lại thành 1 bounding box bao phủ hết
                x0 = min(r.x0 for r in search_rects)
                y0 = min(r.y0 for r in search_rects)
                x1 = max(r.x1 for r in search_rects)
                y1 = max(r.y1 for r in search_rects)
                full_rect = fitz.Rect(x0, y0, x1, y1)
                #print("Full rect:", full_rect)
            
                rect_del = fitz.Rect(full_rect.x0, full_rect.y0, full_rect.x1, full_rect.y0+10)
                page.add_redact_annot(rect_del)
                page.apply_redactions()
                page.insert_text(
                    (full_rect.x0, full_rect.y0+11),
                    time_new,
                    # fontfile=FONT_ARIAL,
                    # fontname = "arial",
                    fontsize=fs*1.1,
                    fill=(0, 0, 0),
                    render_mode=0
                )
                #print(time_new)
                # Lưu lại để dùng tính checkin
           

    # ===== LẤY NGÀY BAY ===== dạng "Aug 28, 2025"
    date_pattern = re.compile(r"\b[A-Za-z]{3}\s\d{1,2},\s\d{4}\b")
    date_matches = date_pattern.findall(text)
    if date_matches:
        try:
            d = datetime.strptime(date_matches[0], "%b %d, %Y")
            found_date = d.strftime("%d/%m/%Y")
            #print(f"[DEBUG] Ngày bay tìm thấy: {found_date}")
        except Exception as e:
            print(f"[DEBUG] Không parse được ngày bay: {e}")

    # ===== TÍNH GIỜ CHECKIN =====
    if found_time and found_date:
        try:
            flight_dt = datetime.strptime(f"{found_date} {found_time}", "%d/%m/%Y %H:%M")
            checkin_dt = flight_dt - timedelta(hours=3)
            periodt = "(Sang)" if checkin_dt.hour < 12 else "(Chieu)"
            note_str = f"Luu y: Quy khach vui long den san bay truoc {checkin_dt.strftime('%d/%m/%Y %H:%M')} {periodt} de lam thu tuc\n len may bay."
            #print(f"[DEBUG] Giờ check-in: {note_str}")
        except Exception as e:
            print("[DEBUG] Lỗi parse giờ/ngày:", e)

    # ===== AUTO ĐỔI DẠNG NGÀY TRONG PDF =====
    matches = set(date_pattern.findall(text))
    for match in matches:
        try:
            d = datetime.strptime(match, "%b %d, %Y")
            new_date = d.strftime("%d/%m/%Y")
            #print(f"[DEBUG] Đổi ngày: '{match}' → '{new_date}'")
            search_rects = page.search_for(match)
            for rect in search_rects:
                page.add_redact_annot(rect)
                page.apply_redactions()
                page.insert_text(
                    (rect.x0, rect.y0 + 11),
                    new_date,
                    fontsize=fs*1.2,
                    fill=(0, 0, 0),
                    render_mode=0
                )
        except:
            continue

    # ===== THÊM NOTE SAU DÒNG "Đăng ký ngay!" =====
    note_text = "Bạn có đang bỏ lỡ q"
    search_rects = page.search_for(note_text)
    for rect in search_rects:
        # Xóa tất cả dòng phía dưới (về mặt hiển thị)
        rect_del = fitz.Rect(rect.x0, rect.y0, page.rect.x1, page.rect.y1)
        page.add_redact_annot(rect_del)
        page.apply_redactions()
        # Thêm note_str
        page.insert_text(
            (rect.x0, rect.y1 + 5),
            #note_str,
            "",
            fontsize=fs*1.7,
            fill=(1, 0, 0),
            render_mode=0
        )

       
    # ===== Xóa banner Hành trình Du lịch" =====
    hanhtrinhdulich_text = "Hành trình Du lịch"
    hanhtrinhdulich_rects = page.search_for(hanhtrinhdulich_text)
    rect_hanhtrinhdulich_del = fitz.Rect(hanhtrinhdulich_rects[0].x0, hanhtrinhdulich_rects[0].y0, hanhtrinhdulich_rects[0].x1+600, hanhtrinhdulich_rects[0].y1+30)
    page.add_redact_annot(rect_hanhtrinhdulich_del)
    page.apply_redactions()
    adj_x = hanhtrinhdulich_rects[0].x0
    adj_y = hanhtrinhdulich_rects[0].y0 +3 # căn từ dưới note_str
    #arial_font = fitz.Font(fontfile=FONT_ARIAL)

    for i, line in enumerate(new_text.split("\n")):
        if ":" in line:
            bold_part, normal_part = line.split(":", 1)
            bold_part += ":"

            # In phần bold
            page.insert_text(
                (adj_x, adj_y + i * (fs * 1.4)),
                bold_part,
                fontsize=fs * 1.2,
                fontfile=FONT_ARIAL,
                
                fontname= "arial",
                fill=(0/255, 61/255, 77/255),
                render_mode=2
            )

            # Tính chiều rộng đúng với font Arial
            #text_width = arial_font.text_length(bold_part, fontsize=fs * 1.2)

            # In phần normal, cách ra 5pt
            page.insert_text(
                (adj_x + 80, adj_y + i * (fs * 1.4)),
                normal_part.strip(),
                fontsize=fs * 1.2,
                fontfile=FONT_ARIAL,
                # fontname= "arial",
                fill=(0, 0, 0),
                render_mode=0
            )
        else:
            page.insert_text(
                (adj_x, adj_y + i * (fs * 1.4)),
                line,
                fontsize=fs * 1.2,
                fontfile=FONT_ARIAL,
                # fontname= "arial",
                fill=(0, 0, 0),
                render_mode=0
            )

    # ===== GẮN LINK =====
    
    # ===== LƯU FILE =====
    doc.save(output_path)
    doc.close()
    time.sleep(0.5)
    extract_first_page(output_path)
    

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



 
def reformat_VJ(input_pdf,output_path,new_text=NEW_TEXT):
    if new_text=="":
        new_text=NEW_TEXT
    replace_text_between_phrases(
    input_pdf,
    output_path,
    new_text
)
# Ví dụ dùng

# ===== TEST =====

#reformat_VJ("input.pdf","output.pdf")



#extract_first_page("output.pdf")














