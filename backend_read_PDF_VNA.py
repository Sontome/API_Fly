import fitz
from datetime import datetime, timedelta
import re
import time


START_PHRASE_KR = "발행점소:"
START_PHRASE_VN = "Nơi xuất vé:"
START_PHRASE_EN = "Issuing office:"

def check_ngon_ngu (pdf_path):
    doc = fitz.open(pdf_path)
    page = doc[0]
    text = page.get_text()
    #print("===== TEXT PAGE 1 =====")
    #print(text)

    # ===== LẤY NGÀY SAU "Ngày:" =====
    
    if START_PHRASE_KR in text:
        return("KR")
    if START_PHRASE_VN in text:
        return("VN")
    if START_PHRASE_EN in text:
        return("EN")
    return("VN")
