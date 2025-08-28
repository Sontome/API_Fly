import fitz
from datetime import datetime
import re

def checkdate_VJ(pdf_path):
    doc = fitz.open(pdf_path)
    page = doc[0]
    text = page.get_text()

    # regex dạng Oct 20, 2025
    pattern = r"\b[A-Za-z]{3}\s\d{1,2},\s\d{4}\b"
    matches = re.findall(pattern, text)

    converted_dates = []
    for date_str in matches:
        try:
            # parse sang datetime
            dt = datetime.strptime(date_str, "%b %d, %Y")
            # format lại sang ddmmyyyy (không dấu /)
            converted_dates.append(dt.strftime("%Y%m%d"))
        except ValueError:
            pass

    doc.close()
    # Nối thành 1 chuỗi cách nhau bằng dấu -
    return "-".join(converted_dates)

# Ví dụ chạy
