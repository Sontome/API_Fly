import fitz
from datetime import datetime, timedelta
import re
import time
import requests
import json
import os
from get_bag_info_pnr_vj import get_bag_info_vj
font_path = "/root/API_Fly/arial.ttf"
font_bold_path = "/root/API_Fly/arialbold.ttf"

NEW_TEXT = "Nơi xuất vé:\nB2BAGTHANVIETAIR, 220-1,2NDFLOOR, SUJIRO489\nBEON-GIL15, SUJI-GU, YONGIN-SI, GYEONGGI-DO, SEOUL\nSố điện thoại :                   +82-10-3546-3396\nEmail:  Hanvietair@gmail.com  "

START_PHRASE = "Công Ty Cổ Phần Hàng Không VietJet"
END_PHRASE = "Tax ID: 0-1055-56100-55-1"

def find_text_coordinates(layout, search_text):
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
        result = get_bag_info_vj(pnr)
        
        return result
    except Exception as e:
        return None

def prase_tieude_hanhly(data):
    tieude = []
    for chieu in data:
        tieude.append(chieu.get("chiều", ""))
    return format_bag_route(tieude)

def merge_bag_info(data):
    result = {}
    for idx, chieu in enumerate(data):
        for p in chieu.get("passengers", []):
            name = p.get("tên")
            bag = p.get("Bag", "     -     ") or "     -     "
            if name not in result:
                result[name] = ["     -     ", "     -     "]
            # bảo đảm idx không vượt quá 1
            if idx < 2:
                result[name][idx] = bag
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

def add_bag_info(bag, layout, page, fs):
    passenger = bag.get("tên")
    baginfo = bag.get("hành lý", "")
    toadopassenger = find_text_coordinates(layout, passenger)
    if not toadopassenger:
        print(f"[WARN] Không tìm được tọa độ cho passenger: {passenger}")
        return
    # optional: tạo khung redact nếu cần
    # toadothanhhanhlydi_khung = fitz.Rect(toadopassenger[0], toadopassenger[1], toadopassenger[0]+30, toadopassenger[1]+10)
    # page.add_redact_annot(toadothanhhanhlydi_khung)
    page.apply_redactions()
    use_font = font_bold_path if os.path.exists(font_bold_path) else font_path
    page.insert_text(
        (toadopassenger[0] + 220, toadopassenger[1] + 15),
        baginfo,
        fontsize=fs * 1.2,
        fontfile=use_font,
        fill=(1, 0, 0),
        render_mode=0
    )

def replace_text_between_phrases(pdf_path, output_path,
                                 new_text, start_phrase=START_PHRASE, end_phrase=END_PHRASE,
                                 font_size=10):

    doc = fitz.open(pdf_path)
    page = doc[0]
    fs = font_size * 0.8
    text = page.get_text()
    pnrformat = r"\b[A-Z0-9]{6}\b"

    layout = page.get_text("dict")
    baglist = None
    for block in layout.get("blocks", []):
        for line in block.get("lines", []):
            line_text = " ".join(span["text"] for span in line["spans"]).strip()
            if re.search(pnrformat, line_text) and len(line_text.replace(" ", "")) == 6:
                pnr = line_text.strip()
                print("[DEBUG] PNR:", pnr)
                baglist = check_bag_vj(pnr)
                print("[DEBUG] raw baglist:", baglist)
                if isinstance(baglist, str):
                    try:
                        baglist = json.loads(baglist)
                    except Exception as e:
                        print("[DEBUG] JSON load error:", e)
                        baglist = None
                if baglist:
                    tieude = prase_tieude_hanhly(baglist)
                    toadothanhhanhlydi = find_text_coordinates(layout, "Tên hành khách")
                    print("[DEBUG] toado ten hanh khach:", toadothanhhanhlydi)
                    if toadothanhhanhlydi:
                        page.apply_redactions()
                        page.insert_text(
                            (toadothanhhanhlydi[0] + 170, toadothanhhanhlydi[1] + 8),
                            tieude,
                            fontsize=fs * 1.2,
                            fontfile=font_path if os.path.exists(font_path) else None,
                            fill=(1, 1, 1),
                            render_mode=0
                        )
                    bags = merge_bag_info(baglist)
                    for bag in bags:
                        add_bag_info(bag, layout, page, fs)
                    break

    # ===== LẤY GIỜ BAY =====
    found_time = None
    found_date = None
    for line in text.splitlines():
        match = re.match(r"(\d{2}:\d{2})\s*-\s*.*", line.strip())
        if match:
            time_part = match.group(1)
            found_time = time_part
            break

    for line in text.splitlines():
        match = re.match(r"(\d{2}:\d{2})\s*-\s*.*", line.strip())
        if match:
            time_part = match.group(1)
            full_part = match.group(0)
            try:
                t = datetime.strptime(time_part, "%H:%M")
                hour = t.hour
                if 0 <= hour <= 6:
                    period = "(Rạng sáng)"
                elif 6 < hour <= 11:
                    period = "(Sáng)"
                elif 11 < hour <= 13:
                    period = "(Trưa)"
                elif 13 < hour <= 18:
                    period = "(Chiều)"
                else:
                    period = "(Đêm)"
                time_new = f"{full_part} {period}"
            except:
                time_new = time_part
            search_rects = page.search_for(full_part)
            if search_rects:
                x0 = min(r.x0 for r in search_rects)
                y0 = min(r.y0 for r in search_rects)
                x1 = max(r.x1 for r in search_rects)
                y1 = max(r.y1 for r in search_rects)
                full_rect = fitz.Rect(x0, y0, x1, y1)
                rect_del = fitz.Rect(full_rect.x0, full_rect.y0, full_rect.x1, full_rect.y0+10)
                page.add_redact_annot(rect_del)
                page.apply_redactions()
                page.insert_text(
                    (full_rect.x0, full_rect.y0 + 11),
                    time_new,
                    fontsize=fs * 1.1,
                    fontfile=font_path if os.path.exists(font_path) else None,
                    fill=(0, 0, 0),
                    render_mode=0
                )

    # ===== LẤY NGÀY BAY ===== dạng "Aug 28, 2025"
    date_pattern = re.compile(r"\b[A-Za-z]{3}\s\d{1,2},\s\d{4}\b")
    matches = set(date_pattern.findall(text))
    for match in matches:
        try:
            d = datetime.strptime(match, "%b %d, %Y")
            new_date = d.strftime("%d/%m/%Y")
            search_rects = page.search_for(match)
            for rect in search_rects:
                page.add_redact_annot(rect)
                page.apply_redactions()
                page.insert_text(
                    (rect.x0, rect.y0 + 11),
                    new_date,
                    fontsize=fs * 1.2,
                    fontfile=font_path if os.path.exists(font_path) else None,
                    fill=(0, 0, 0),
                    render_mode=0
                )
        except:
            continue

    # ===== THÊM NOTE SAU DÒNG "Đăng ký ngay!" =====
    note_text = "Bạn có đang bỏ lỡ q"
    search_rects = page.search_for(note_text)
    if search_rects:
        for rect in search_rects:
            rect_del = fitz.Rect(rect.x0, rect.y0, page.rect.x1, page.rect.y1)
            page.add_redact_annot(rect_del)
            page.apply_redactions()
            page.insert_text(
                (rect.x0, rect.y1 + 5),
                "",
                fontsize=fs * 1.7,
                fill=(1, 0, 0),
                render_mode=0
            )

    # ===== Xóa banner Hành trình Du lịch" =====
    hanhtrinhdulich_text = "Hành trình Du lịch"
    hanhtrinhdulich_rects = page.search_for(hanhtrinhdulich_text)
    if hanhtrinhdulich_rects:
        rect_hanhtrinhdulich_del = fitz.Rect(
            hanhtrinhdulich_rects[0].x0,
            hanhtrinhdulich_rects[0].y0,
            hanhtrinhdulich_rects[0].x1 + 600,
            hanhtrinhdulich_rects[0].y1 + 30
        )
        page.add_redact_annot(rect_hanhtrinhdulich_del)
        page.apply_redactions()
        adj_x = hanhtrinhdulich_rects[0].x0
        adj_y = hanhtrinhdulich_rects[0].y0 + 3

        # in block NEW_TEXT
        for i, line in enumerate(new_text.split("\n")):
            y_pos = adj_y + i * (fs * 1.4)
            if ":" in line:
                bold_part, normal_part = line.split(":", 1)
                bold_part += ":"
                page.insert_text(
                    (adj_x, y_pos),
                    bold_part,
                    fontsize=fs * 1.2,
                    fontfile=font_bold_path if os.path.exists(font_bold_path) else (font_path if os.path.exists(font_path) else None),
                    fill=(0/255, 61/255, 77/255),
                    render_mode=2
                )
                # đơn giản: đặt normal text cách 30pt — ổn với hầu hết trường hợp
                page.insert_text(
                    (adj_x + 30 + 5, y_pos),
                    normal_part.strip(),
                    fontsize=fs * 1.2,
                    fontfile=font_path if os.path.exists(font_path) else None,
                    fill=(0, 0, 0),
                    render_mode=0
                )
            else:
                page.insert_text(
                    (adj_x, y_pos),
                    line,
                    fontsize=fs * 1.2,
                    fontfile=font_path if os.path.exists(font_path) else None,
                    fill=(0, 0, 0),
                    render_mode=0
                )

    # ===== LƯU FILE =====
    doc.save(output_path)
    doc.close()
    time.sleep(0.5)
    extract_first_page(output_path)

def extract_first_page(input_pdf):
    doc = fitz.open(input_pdf)
    new_doc = fitz.open()
    new_doc.insert_pdf(doc, from_page=0, to_page=0, links=True)
    doc.close()
    new_doc.save(input_pdf)
    new_doc.close()

def reformat_VJ(input_pdf, output_path, new_text=NEW_TEXT):
    if new_text == "":
        new_text = NEW_TEXT
    replace_text_between_phrases(input_pdf, output_path, new_text)


