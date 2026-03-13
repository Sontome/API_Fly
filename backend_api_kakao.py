import hmac
import hashlib
import secrets
import requests
import os
from datetime import datetime, timezone
from typing import Dict, Any
from dotenv import load_dotenv

# Load biến môi trường từ .env
load_dotenv()

API_KEY = os.getenv("API_KEY_SOLAPI")
API_SECRET = os.getenv("API_SECRET_KAKAO")
PF_ID = os.getenv("PF_ID")
VNA = os.getenv("IMAGE_VNA")
VJ = os.getenv("IMAGE_VJ")
DELAY = os.getenv("IMAGE_DELAY")

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

    auth_header = create_auth_header(API_KEY, API_SECRET)

    image_map = {
        "DELAY": DELAY,
        "VJ": VJ,
        "VNA": VNA
    }
    airline_map = {
        "VJ": "Vietjet Air",
        "VNA": "Vietnam Airlines",
        "QH": "Bamboo Airways"
    }
    
    airline_name = airline_map.get(hang, hang)
    variables_map = {
        "DELAY": {
            "#{Airlines_name}": airline_name,
            "#{pnr}": pnr,
            "#{trip_details}": trip,
            "#{old_time}": oldtime,
            "#{new_time}": newtime,
            "#{Delay_reason}": reason,
            "#{url}": f"{hang}/{pnr}"
        },
        "VJ": {
            "#{pnr}": pnr,
            "#{reservation_time}": time,
            "#{trip_details}": trip
        },
        "VNA": {
            "#{pnr}": pnr,
            "#{reservation_time}": time,
            "#{trip_details}": trip
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
    print(response.text)

    response.raise_for_status()
    return response.json()
if __name__ == "__main__":
    result = send_bms_image(
        to_number="084764301092",
        pnr= "ABCEDD",
        time= "30h12p",
        type=VJ,
        trip=(
            
            "ICN-HAN 06:25 ngày 24/04\n"
            "HAN-ICN 23:15 ngày 26/04"
        )
    )

    print(result)
