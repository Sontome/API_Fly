import httpx
import json
import os

# 👉 Thêm token và chat_id vào config, hoặc gán trực tiếp luôn
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "7843918695:AAGnIVDjJV52Citq0mn8zOQ0_Wr0MmD45qA")



async def send_mess(message: str):
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": "-4819854186",
        "text": message,
        "parse_mode": "HTML"  # Cho phép format đẹp
    }

    try:
        async with httpx.AsyncClient() as client:
            res = await client.post(url, json=payload)
            if res.status_code != 200:
                print(f"❌ Lỗi gửi tin nhắn: {res.text}")
    except Exception as e:
        print(f"💥 Lỗi gửi message Telegram: {e}")

