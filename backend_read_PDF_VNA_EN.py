import fitz
from datetime import datetime, timedelta
import re
import time
import os
import shutil
FILES_DIR = "/var/www/files"
FONT_ARIAL = "/usr/share/fonts/truetype/msttcorefonts/Arial.ttf"
NEW_TEXT = "Issuing office:\nB2BAGTHANVIETAIR, 220-1,2NDFLOOR, SUJIRO489\nBEON-GIL15, SUJI-GU, YONGIN-SI, GYEONGGI-DO, SEOUL\nPhone:  +82-10-3546-3396\nEmail:  Hanvietair@gmail.com"
 
START_PHRASE = "Issuing office:"
END_PHRASE = "Date:"
def replace_text_between_phrases(pdf_path,output_path,
                                  new_text,start_phrase=START_PHRASE, end_phrase=END_PHRASE,
                                 font_size=10,type=0):
    new_text = new_text + "\nDate:  "
    doc = fitz.open(pdf_path)
    # ===== THAY "Tổngtiền:" THÀNH "IT FARE" TRÊN TẤT CẢ CÁC TRANG =====
    if type == 1:
        for page_number in range(len(doc)):
            page = doc[page_number]
            tongtien_matches = page.search_for("Tổng tiền:")
            if not tongtien_matches:
                continue
            for rect in tongtien_matches:
                # Tính vị trí mới (lệch phải 180px)
                new_x = rect.x0 + 195
                new_y = rect.y0 +5

                # Tạo vùng cần xóa ở vị trí mới (kích thước tương tự chữ gốc)
                new_rect = fitz.Rect(new_x, rect.y0, new_x + (rect.x1 - rect.x0+80), rect.y1)
                page.add_redact_annot(new_rect)
                page.apply_redactions()

                # Chèn chữ IT FARE vào đúng vị trí mới
                page.insert_text(
                    (new_x, new_y + 5),
                    "IT FARE    ",
                    fontsize=font_size,
                    fontfile=FONT_ARIAL,
                    fontname="arial",
                    fill=(0, 0, 0),
                    render_mode=0
                )  
                print(f"✅ Đã thay 'Tổngtiền:' → 'IT FARE' ở trang {page_number + 1}")                              
    page = doc[0]  # chỉ page đầu
    fs = font_size * 0.8

    text = page.get_text()
    #print("===== TEXT PAGE 1 =====")
    #print(text)

    # ===== LẤY NGÀY SAU "Ngày:" =====
    date_found = None
    if "Date:" in text:
        start_idx = text.find("Date:") + len("Date:")
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
            if line.strip().startswith("Date:"):
                new_text_lines[i] = f"Date: {date_found}"
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
            checkin_dt = flight_dt - timedelta(hours=3)
            periodt = "(AM)" if checkin_dt.hour < 12 else "(PM)"
            note_str = f"Note: Please arrive at the airport before {checkin_dt.strftime('%d/%m/%Y %H:%M')} {periodt} to check in."
            #print(f"[DEBUG] Giờ check-in: {note_str}")
        except Exception as e:
            print("[DEBUG] Lỗi parse giờ/ngày:", e)

    # ===== XỬ LÝ GIỜ (thêm sáng/chiều) =====
    idxmatch = 0  # đếm số time_part hợp lệ đã xử lý
    for line in text.splitlines():
        if ":" in line:
            time_part = line.strip()
            try:
                t = datetime.strptime(time_part, "%H:%M")
                hour = t.hour

                if 0 <= hour <= 6:
                    periodt = "(Early Morning)"
                elif 6 < hour <= 11:
                    periodt = "(Morning)"
                elif 11 < hour <= 13:
                    periodt = "(Noon)"
                elif 13 < hour <= 18:
                    periodt = "(Afternoon)"
                else:
                    periodt = "(Night)"
                time_part_new = f"{time_part} {periodt}"
            except:
                continue

            # tìm và sửa text trên PDF
            search_rects = page.search_for(time_part)
            for rect in search_rects:
                page.add_redact_annot(rect)
                page.apply_redactions()
                page.insert_text(
                    (rect.x0, rect.y0 + 5),
                    time_part_new,
                    fontsize=fs,
                    fontfile=FONT_ARIAL,
                    fontname="arial",
                    fill=(0, 0, 0),
                    render_mode=0
                )

                # chỉ xử lý thêm dòng "ra sân bay đêm hôm trước" nếu là line chẵn (2,4,6,...)
                # và có ngày tương ứng trong date_matches
                if idxmatch % 2 == 0 and periodt == "(Early Morning)" and date_matches:
                    try:
                        print(idxmatch)
                        d_str = date_matches[idxmatch+1]

                        flight_date = datetime.strptime(d_str, "%d%b%Y")
                        pre_night = flight_date - timedelta(days=1)
                        ddmm = pre_night.strftime("%d/%m")

                        page.insert_text(
                            (rect.x0-5, rect.y0 + 30),
                            f"(Ra sân bay\n đêm {ddmm})",
                            fontsize=fs,
                            fontfile=FONT_ARIAL,
                            fontname="arial",
                            fill=(1, 0, 0),
                            render_mode=0
                        )
                    except Exception as e:
                        print(f"[DEBUG] Lỗi khi thêm dòng ra sân bay: {e}")

            idxmatch += 1  # tăng sau khi xử lý 1 time_part

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
    is_infant = "(INF)" in text
    hl_pattern = re.compile(r"Baggage: [12]PC")
    matches = set(hl_pattern.findall(text))
    for match in matches:
        search_rects = page.search_for(match)
        for rect in search_rects:
            if "1PC" in match:
                addon = " (10kg)" if is_infant else " (23kg)"
            elif "2PC" in match:
                addon = " (10kg+10kg)" if is_infant else " (23kg+23kg)"
            else:
                addon = ""

            # Tính vị trí x để dịch sang phải
            addon_x = rect.x1 + 0  # dịch sang phải 10pt
            addon_y = rect.y0 + 9   # cùng line

            page.insert_text(
                (addon_x, addon_y),
                addon,
                fontsize=fs*1.2,
                fill=(1, 0, 0),
                render_mode=0
            )

    # ===== THÊM NOTE KHI THẤY DÒNG OK/RQ =====
    note_text = "(1)OK = confirmed , RQ/SA = Waitlisted"
    search_rects = page.search_for(note_text)
    if type==0:
        for rect in search_rects:
            # Xóa tất cả dòng phía dưới (về mặt hiển thị)
            rect_del = fitz.Rect(rect.x0, rect.y0+10, page.rect.x1, page.rect.y1)
            page.add_redact_annot(rect_del)
            page.apply_redactions()
            # Thêm note_str
            page.insert_text(
                (rect.x0, rect.y1 + 20),
                #note_str,
                "",
                fontsize=fs*1.7,
                fill=(1, 0, 0),
                render_mode=0
            )


    # ===== REPLACE TEXT CHÍNH =====
    blocks = page.get_text("blocks")
    for block in blocks:
        block_text = block[4]
        if "Booking ref" in block_text:
            # In ra để debug
            print("[DEBUG] Found block:", block_text)
            
            # Regex bắt Mã đặt chỗ và Số vé
            match = re.search(r"Booking ref:\s*([A-Z0-9]+).*?Ticket number:\s*([0-9 ]+)", block_text, re.S)
            if match:
                ma_pnr = match.group(1).strip()
                so_ve = match.group(2).strip()
                pnrpax = f"{ma_pnr}-{so_ve}"
                print(f"✅ PNR = {pnrpax}")
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
                        fontfile=FONT_ARIAL,
                        fontname= "arial",
                        fill=(0/255, 61/255, 77/255),
                        render_mode=0.5
                    )
                    text_width = fitz.get_text_length(bold_part, fontsize=fs)
                    page.insert_text(
                        (adj_x + 45 + 3, adj_y + i * (fs + 2)),
                        normal_part.strip(),
                        fontsize=fs,
                        fontfile=FONT_ARIAL,
                        fontname= "arial",
                        fill=(0, 0, 0),
                        render_mode=0
                    )
                else:
                    page.insert_text(
                        (adj_x, adj_y + i * (fs + 2)),
                        line,
                        fontsize=fs,
                        fontfile=FONT_ARIAL,
                        fontname= "arial",
                        fill=(0, 0, 0),
                        render_mode=0
                    )

    # ===== GẮN LINK MỚI =====
   

    # ===== LƯU TRỰC TIẾP =====
    doc.save(output_path)
    #print(f"[DEBUG] Đã lưu file ra: {outputpath}")
    doc.close()
    time.sleep(0.5)
    print(output_path)
    extract_first_page(output_path,pnrpax,type=type)
    

def extract_first_page(input_pdf, prnpax, type=0):
    """Lấy page 1 hoặc full PDF tùy theo type, giữ nguyên hyperlink."""
    doc = fitz.open(input_pdf)
    new_doc = fitz.open()

    if type == 0:
        # Page 0 là trang 1
        new_doc.insert_pdf(doc, from_page=0, to_page=0, links=True)
    else:
        # Lấy toàn bộ các trang
        new_doc.insert_pdf(doc, from_page=0, to_page=len(doc)-1, links=True)

    doc.close()
    new_doc.save(input_pdf)
    new_doc.close()

    print(f"{prnpax}.pdf")
    try:
        os.makedirs(FILES_DIR, exist_ok=True)
        dest_filename = f"{prnpax}.pdf"
        dest_path = os.path.join(FILES_DIR, dest_filename)
        shutil.copy2(input_pdf, dest_path)
        print(f"✅ Đã copy {input_pdf} sang {dest_path}")
    except Exception as e:
        print(f"❌ Lỗi khi copy file: {e}")



 
def reformat_VNA_EN(input_pdf,output_path,new_text=NEW_TEXT):
    if new_text=="":
        new_text=NEW_TEXT
    replace_text_between_phrases(
    input_pdf,
    output_path,
    new_text,
    type=type
)
# Ví dụ dùng

# ===== TEST =====
#reformat_VNA_EN("input.pdf","output.pdf")



#extract_first_page("output.pdf")















