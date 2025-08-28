import fitz
import re
from datetime import datetime

def checkdate_VNA(pdf_path):
    doc = fitz.open(pdf_path)
    page = doc[0]
    text = page.get_text()

    # regex ngày dạng 15Aug2025
    date_pattern = r"\b\d{2}[A-Za-z]{3}\d{4}\b"
    dates = re.findall(date_pattern, text)
    dates = [d for i, d in enumerate(dates) if i % 2 == 1]

    # regex giờ dạng Thời gian bay: 04:50 -> chỉ lấy 04:50
    patterns = [
        r"Thời gian bay:\s*(\d{2}:\d{2})",
        r"비행시간:\s*(\d{2}:\d{2})",
        r"Duration:\s*(\d{2}:\d{2})"
    ]

    times = []
    for p in patterns:
        times = re.findall(p, text)
        if times:  # nếu tìm thấy thì dừng
            break

    doc.close()

    # lọc và đổi định dạng ngày sang yyyy/mm/dd
    filtered_dates = []
    for date_str, time_str in zip(dates, times):
        t = datetime.strptime(time_str, "%H:%M")
        if t >= datetime.strptime("01:30", "%H:%M"):
            formatted_date = datetime.strptime(date_str, "%d%b%Y").strftime("%Y%m%d")
            filtered_dates.append(formatted_date)

    # nối thành 1 chuỗi
    return "-".join(filtered_dates)

# Ví dụ chạy
