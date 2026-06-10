import httpx
import json
import os
import asyncio
from dotenv import load_dotenv
load_dotenv()
# 👉 Thêm token và chat_id vào config, hoặc gán trực tiếp luôn
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "-1002520783135")
TELEGRAM_CHAT_ID_CHECKIN = os.getenv("TELEGRAM_CHAT_ID", "-1005182212364")

async def send_mess(message: str) -> bool:
    

    try:
        url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
        payload = {
            "chat_id": TELEGRAM_CHAT_ID,
            "text": message,
            "parse_mode": "HTML"  # Cho phép format đẹp
        }
        async with httpx.AsyncClient() as client:
            res = await client.post(url, json=payload)
            if res.status_code != 200:
                print(f"❌ Lỗi gửi tin nhắn: {res.text}")
                return False
            return True
    except Exception as e:
        print(f"💥 Lỗi gửi message Telegram: {e}")
        return False
async def send_mess_checkin(message: str) -> bool:
    

    try:
        url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
        payload = {
            "chat_id": TELEGRAM_CHAT_ID_CHECKIN,
            "text": message,
            "parse_mode": "HTML"  # Cho phép format đẹp
        }
        async with httpx.AsyncClient() as client:
            res = await client.post(url, json=payload)
            if res.status_code != 200:
                print(f"❌ Lỗi gửi tin nhắn: {res.text}")
                return False
            return True
    except Exception as e:
        print(f"💥 Lỗi gửi message Telegram: {e}")
        return False
async def test_send_booking_message():
    """
    Gửi thử mẫu nội dung thông báo giữ vé.
    """
    sample_message = (
        "Đã giữ vé GP7C6H thành công\n"
        "HAN-ICN 2026/06/18 - 2026/06/20\n"
        "NGUYEN VAN A"
    )
    return await send_mess(sample_message)

def test_send_booking_message_sync():
    """
    Hàm sync để test nhanh từ script thường.
    """
    return asyncio.run(test_send_booking_message())
