import requests
import json
import re
import xml.etree.ElementTree as ET
import subprocess
import asyncio
from utils_telegram import send_mess
file_path = "login1A.py"

def createNewSession(
    session_log_file="session_log.json",
    cookie_file="cookie1a.json"
):
    try:
        # ===== Load LOG_PARENT_JSESSIONID & ENC từ sessionlog.json =====
        with open(session_log_file, "r", encoding="utf-8") as f:
            session_data = json.load(f)

        LOG_PARENT_JSESSIONID = session_data.get("ID")
        ENC_PARENT = session_data.get("EncryptionKey")

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
        url_create = f"https://tc345.resdesktop.altea.amadeus.com/app_ard/apf/do/home.taskmgr/UMCreateSessionKey;jsessionid={LOG_PARENT_JSESSIONID}"
        headers = {
            "accept": "*/*",
            "content-type": "application/x-www-form-urlencoded; charset=UTF-8",
            "x-requested-with": "XMLHttpRequest",
            "referer": "https://tc345.resdesktop.altea.amadeus.com/app_ard/apf/init/login?SITE=AVNPAIDL&LANGUAGE=GB&MARKETS=ARDW_PROD_WBP&ACTION=clpLogin",
        }
        data = {
            "flowExKey": "e14s1",
            "initialAction": "newCrypticSession",
            "recordLocator": "[object PointerEvent]",
            "ctiAcknowledge": "false",
            "LOG_PARENT_JSESSIONID": LOG_PARENT_JSESSIONID,
            "waiAria": "false",
            "SITE": "AVNPAIDL",
            "LANGUAGE": "GB",
            "aria.target": "body",
            "aria.panelId": "3"
        }

        resp = session.post(url_create, headers=headers, data=data)
        if resp.status_code != 200:
            #print(resp.status_code)
            return {"status": "ERROR", "message": "Tạo session key thất bại", "code": resp.status_code}
        print(resp.text[:1])
        
        # ===== Lấy ENC mới =====
        match = re.search(r'<!\[CDATA\[(.*?)\]\]>', resp.text, re.S)
        if not match:
            return {"status": "ERROR", "message": "Không tìm thấy CDATA trong phản hồi createSessionKey"}
        json_text = match.group(1).strip()
        enc_match = re.search(r'"ENC":"([A-F0-9]+)"', json_text)
        
        if not enc_match:
            return {"status": "ERROR", "message": "Không tìm thấy ENC trong CDATA"}
        ENC = enc_match.group(1) # cắt 9 ký tự cuối như code cũ
        
        print("lay enc tong")
        # ===== Login new session =====
        url_login = "https://tc345.resdesktop.altea.amadeus.com/app_ard/apf/do/loginNewSession.UM/login"
        headers = {
            "accept": "*/*",
            "accept-language": "en-US,en;q=0.9",
            "content-type": "application/x-www-form-urlencoded; charset=UTF-8",
            "priority": "u=1, i",
            "sec-ch-ua": '"Chromium";v="139", "Not;A=Brand";v="99"',
            "sec-ch-ua-mobile": "?0",
            "sec-ch-ua-platform": '"Windows"',
            "sec-fetch-dest": "empty",
            "sec-fetch-mode": "cors",
            "sec-fetch-site": "same-origin",
            "x-requested-with": "XMLHttpRequest",
            "referer": "https://tc345.resdesktop.altea.amadeus.com/app_ard/apf/init/login?SITE=AVNPAIDL&LANGUAGE=GB&MARKETS=ARDW_PROD_WBP&ACTION=clpLogin",
        }
        payload = {
            
            "LANGUAGE": "GB",
            "SITE": "AVNPAIDL",
            "MARKETS": "ARDW_PROD_WBP",
            "initialAction": "newCrypticSession",
            "waiAria": "false",
            "LOG_PARENT_JSESSIONID": LOG_PARENT_JSESSIONID,
            "recordLocator": "[object PointerEvent]", 
            "ctiAcknowledge": "false",
            "aria.target": "body.main.s1",
            "aria.sprefix": "s1",
            "ENC": ENC, # rút gọn
            "ENCT": "1",
            "aria.panelId": "1"
        }

        resp_login = session.post(url_login, headers=headers, data=payload)
        if resp_login.status_code != 200:
            #print(resp_login.text)
            return {"status": "ERROR", "message": "Login new session thất bại", "code": resp_login.status_code}
        print("tạo ss con ") 
        # ===== Tìm cryptic session data =====
        pattern = re.compile(
            r'<templates-init[^>]*moduleId="cryptic"[^>]*><!\[CDATA\[(.*?)\]\]></templates-init>',
            re.DOTALL
        )
        match_cryptic = pattern.search(resp_login.text)
        if match_cryptic == None:
            msg = "🔐 Token hết hạn. cần chạy lại `login1A.py` để làm mới token."
        
            print(msg)
        
            try:
                asyncio.run(send_mess(msg))
            except Exception as e:
                print(f"Lỗi gửi telegram: {e}")
        
            return None
        cryptic_data = None
        if match_cryptic:
            cdata_content = match_cryptic.group(1)
            try:
                cryptic_data = json.loads(cdata_content)
                jSessionId = cryptic_data["model"]["jSessionId"]
                officeId = cryptic_data["model"]["officeId"]
                language = cryptic_data["model"]["language"]
                defaultActivePluginType = cryptic_data["model"]["defaultActivePluginType"]
                dcxid = cryptic_data["model"]["dcxid"]
                siteCode = cryptic_data["model"]["siteCode"]
                octx = cryptic_data["model"]["octx"]
                organization = cryptic_data["model"]["organization"]
                result = {
                    "status": "OK",
                    "ENC": ENC,
                    "officeId":officeId,
                    "jSessionId": jSessionId,
                    "language": language,
                    "defaultActivePluginType": defaultActivePluginType,
                    "dcxid": dcxid,
                    "siteCode": siteCode,
                    "octx": octx,
                    "organization": organization

                }
                #print(cryptic_data)
                with open("crypticjsession.json", "w", encoding="utf-8") as f:
                    json.dump(result, f, indent=2, ensure_ascii=False)
                
            
            except:
                cryptic_data = None
                return None
        return result

    except Exception as e:
        return {"status": "ERROR", "message": str(e)}


if __name__ == "__main__":
     result = createNewSession()

     #print(result)






