import fitz
import re
def check_payment(pdf_path):
    doc = fitz.open(pdf_path)
    page = doc[0]  # chỉ page đầu

    # Lấy toàn bộ text dạng block
    blocks = page.get_text("blocks")
    #print("===== BLOCKS TRONG TRANG =====")
    name =None
    if len(blocks) > 3:
        text_block3 = blocks[3][4]  # phần text ở vị trí index 4
        #print("Text gốc block 3:", text_block3)

        # Bỏ "Tên:" và các ký tự đặc biệt (ví dụ dấu phẩy)
        cleaned = text_block3.replace("Tên:", "").strip()
        name = re.sub(r"[^\w\s]", "", cleaned)  # chỉ giữ chữ + số + khoảng trắng
        #print("Text đã lọc:", name)
    else:
        print("Không tìm thấy block 3")

    # ===== THÊM NOTE SAU DÒNG "Đăng ký ngay!" =====
    note_text = "Vui lòng thanh toán trước"
    search_rects = page.search_for(note_text)
    if search_rects:
        doc.close()
        return {
            "paymentstatus" : "False",
            "name" :name
        }

    doc.close()
    return {
            "paymentstatus" : "True",
            "name" :name
        }

# Test
#print(check_payment("input.pdf"))