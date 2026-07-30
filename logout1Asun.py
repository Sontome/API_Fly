import requests
import json
import re
import xml.etree.ElementTree as ET
import subprocess

def logout1A(
    session_log_file="session_log_sun.json",
    cookie_file="cookie1a_sun.json"
):
    try:
        # ===== Load LOG_PARENT_JSESSIONID & ENC từ sessionlog.json =====
        with open(session_log_file, "r", encoding="utf-8") as f:
            session_data = json.load(f)

        

        # ===== Load cookie =====
        with open(cookie_file, "r", encoding="utf-8") as f:
            cookies_raw = json.load(f)
        if isinstance(cookies_raw, list):
            cookies = {c["name"]: c["value"] for c in cookies_raw}
        else:
            cookies = cookies_raw

        session = requests.Session()
        session.cookies.update(cookies)

        # ===== Tạo session key =====
        url = "https://tc110.resdesktop.altea.amadeus.com/app_ard/apf/init/login"
        params = {
            "SITE": "A9GPAIDL",
            "LANGUAGE": "GB",
            "MARKETS": "ARDW_PROD_WBP",
            "event": "LOGIN_LOGOUT"
        }

        headers = {
            "accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7",
            "accept-language": "en-US,en;q=0.9",
            "priority": "u=0, i",
            "sec-ch-ua": "\"Chromium\";v=\"139\", \"Not;A=Brand\";v=\"99\"",
            "sec-ch-ua-mobile": "?0",
            "sec-ch-ua-platform": "\"Windows\"",
            "sec-fetch-dest": "document",
            "sec-fetch-mode": "navigate",
            "sec-fetch-site": "same-origin",
            "sec-fetch-user": "?1",
            "upgrade-insecure-requests": "1",
            "referer": "https://tc110.resdesktop.altea.amadeus.com/app_ard/apf/init/login?SITE=A9GPAIDL&LANGUAGE=GB&MARKETS=ARDW_PROD_WBP&ACTION=clpLogin"
            

        }

        
        resp = session.get(url, headers=headers, params=params)

        print("👉 Status:", resp.status_code)
        print("👉 URL:", resp.url)
        print("👉 Response:")
        print(resp.text[:1000])  # in thử 1000 ký tự đầu để tránh dài vl

    except :
        print("lỗi không xác định")

logout1A()