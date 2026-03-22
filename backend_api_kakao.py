import hmac
import hashlib
import secrets
import requests
import time
import os
from datetime import datetime, timezone
from typing import Dict, Any
from dotenv import load_dotenv
from utils_telegram import send_mess
# from backend_supabase_kakao import get_kakanoti_by_pnr
# Load biến môi trường từ .env
load_dotenv()
import asyncio
import re
API_KEY = os.getenv("API_KEY_SOLAPI")
API_SECRET = os.getenv("API_SECRET_KAKAO")
PF_ID = os.getenv("PF_ID")
VNA = os.getenv("IMAGE_VNA")
VJ = os.getenv("IMAGE_VJ")
DELAY = os.getenv("IMAGE_DELAY")
BF24H = os.getenv("IMAGE_BF24H")
BLACKLIST_PARTIAL = [
    
    "764301092"
    
]


def normalize_phone_number(to_number: str) -> str:
    # ====================
    # 🧹 CLEAN INPUT
    # ====================
    to_number = to_number.strip()

    # giữ lại số và dấu +
    to_number = re.sub(r"[^\d+]", "", to_number)

    # chỉ giữ + ở đầu (nếu có)
    if "+" in to_number:
        to_number = "+" + to_number.replace("+", "")

    # ====================
    # 🇰🇷 HÀN QUỐC
    # ====================
    if to_number.startswith("+82"):
        to_number = "0" + to_number[3:]

    if to_number.startswith("82"):
        to_number = "0" + to_number[2:]

    if to_number.startswith("01"):
        if len(to_number) != 11:
            print("⚠️ SĐT Hàn không đúng độ dài:", to_number)
        return to_number

    # ====================
    # 🇻🇳 VIỆT NAM
    # ====================
    if to_number.startswith("+84"):
        number = to_number[3:]
        if len(number) != 9:
            print("⚠️ SĐT VN không đúng độ dài:", to_number)
        return "+84" + number

    if to_number.startswith("84"):
        number = to_number[2:]
        if len(number) != 9:
            print("⚠️ SĐT VN không đúng độ dài:", to_number)
        return "+84" + number

    if to_number.startswith("0"):
        number = to_number[1:]
        if len(number) != 9:
            print("⚠️ SĐT VN không đúng độ dài:", to_number)
        return "+84" + number

    # ====================
    # 🤡 ĐOÁN THIẾU
    # ====================
    if to_number.isdigit():
        if len(to_number) == 9:
            return "+84" + to_number
        elif len(to_number) == 10 and to_number.startswith("1"):
            return "0" + to_number

    print("❌ Không nhận diện được số:", to_number)
    return to_number
def generate_signature(api_secret: str, date_time: str, salt: str) -> str:
    """HMAC-SHA256 signature"""
    data = date_time + salt
    signature = hmac.new(
        api_secret.encode(),
        data.encode(),
        hashlib.sha256
    ).hexdigest()
    return signature


def create_auth_header(api_key: str, api_secret: str) -> str:
    """Authorization header"""
    date_time = datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z')
    salt = secrets.token_hex(16)
    signature = generate_signature(api_secret, date_time, salt)

    return f"HMAC-SHA256 apiKey={api_key}, date={date_time}, salt={salt}, signature={signature}"


def send_bms_image(
    to_number: str,
    pnr: str,
    time: str="",
    type: str="",
    trip: str="",
    image_link: str="https://hanvietair.com/vi",
    hang: str="",
    reason: str="",
    oldtime: str="",
    newtime: str="",
    sms=True
) -> Dict[str, Any]:
    """Send Kakao BMS IMAGE message"""
    to_number = normalize_phone_number(to_number)
    auth_header = create_auth_header(API_KEY, API_SECRET)
    for blocked in BLACKLIST_PARTIAL:
        if blocked in to_number:
            print(f"🚫 SĐT chứa blacklist ({blocked}), skip: {to_number}")
            return {
                "status": "blocked",
                "reason": "blacklist_partial",
                "to": to_number
            }
    image_map = {
        "DELAY": DELAY,
        "VJ": VJ,
        "VNA": VNA,
        "BF24H": BF24H
    }
    airline_map = {
        "VJ": "Vietjet Air",
        "VNA": "Vietnam Airlines",
        "QH": "Bamboo Airways"
    }
    
    airline_name = airline_map.get(hang, hang)
    variables_map = {
        "DELAY": {
            "#{Airlines_name}":"\n"+ airline_name,
            "#{pnr}": pnr,
            "#{trip_details}":  f"\n{trip}",
            "#{old_time}": oldtime,
            "#{new_time}": newtime,
            "#{delay_reason}": reason,
            "#{url}": f"check/{hang}/{pnr}"
        },
        "VJ": {
            "#{pnr}": pnr,
            "#{Airlines_name}": "\n"+airline_map.get(type, type),
            "#{url}": f"check/{type}/{pnr}"
        },
        "VNA": {
            "#{pnr}": pnr,
            "#{Airlines_name}": "\n"+airline_map.get(type, type),
            "#{url}": f"check/{type}/{pnr}"
        },
        "BF24H": {
            "#{pnr}": pnr,
            "#{Airlines_name}": "\n"+airline_name,
            "#{trip_info}": "\n"+trip,
            "#{url}": f"check/{hang}/{pnr}"
        }
    }

    image_id = image_map.get(type, VNA)
    variables = variables_map.get(type, variables_map["VNA"])

    headers = {
        "Authorization": auth_header,
        "Content-Type": "application/json"
    }

    message_data = {
        "messages": [
            {
                "to": to_number,
                "type": "ATA",
                "country": "82",
                "from": "01035463396",
                "kakaoOptions": {
                    "pfId": PF_ID,
                    "disableSms": sms,
                    "templateId": image_id,
                    "variables": variables
                }
            }
        ]
    }

    # Nếu có image_link thì thêm vào
    

    response = requests.post(
        "https://api.solapi.com/messages/v4/send-many/detail",
        json=message_data,
        headers=headers
    )

    print(response.status_code)
    # print(response.text)
    result = response.json()
    try:
        new_balance = result["groupInfo"]["log"][-1]["newBalance"]
        print(new_balance)
        if new_balance < 5000:
            asyncio.run(send_mess(f"Cảnh báo : số dư solapi sắp hết, vui lòng nạp tiền: {new_balance} w"))
        response.raise_for_status()
    except Exception as e:
        print(f"Lỗi khi lấy số dư solapi: {e}")
    return response.json()
# def kakao_delay(
#     pnr: str,
#     type: str,
#     trip: str,
#     hang: str,
#     reason: str,
#     oldtime: str,
#     newtime: str
# ):
#     """
#     Gửi BMS delay cho tất cả phone theo pnr
#     """

#     data_list = get_kakanoti_by_pnr(pnr)

#     if not data_list:
#         print("⚠️ Không có data để gửi đại ca")
#         return

#     success = 0
#     fail = 0

#     for data in data_list:
#         phone = data.get("phone")

#         if not phone:
#             continue

#         payload = {
#             "to_number": phone,
#             "pnr": pnr,
#             "type": type,
#             "trip": trip,
#             "hang": hang,
#             "reason": reason,
#             "oldtime": oldtime,
#             "newtime": newtime
#         }
#         print(payload)
#         try:
#             send_bms_image(**payload)
#             print(f"✅ Gửi OK -> {phone}")
#             success += 1
#         except Exception as e:
#             print(f"❌ Lỗi gửi {phone}: {e}")
#             fail += 1
#     time.sleep(1)
#     print(f"🔥 Done : success={success}, fail={fail}")
# if __name__ == "__main__":
#     result = kakao_delay(
       
#         pnr= "U9XV2C",
       
#         type="DELAY",
#         hang= "VNA",
#         trip=(
            
#             "ICN-HAN 06:25 ngày 24/04\n"
#             "HAN-ICN 23:15 ngày 26/04"
#         ),
#         reason= "DELAY",
#         oldtime= "10HP",
#         newtime= "11H"
#     )

    # print(result)
