import subprocess
import re
import os
import requests

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "7359295123:AAGz0rHge3L5gM-XJmyzNq6sayULdHO4-qE")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "-1002520783135")

def send_telegram_message(message):
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    data = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": message,
        "parse_mode": "HTML"
    }
    try:
        res = requests.post(url, data=data)
        if res.status_code == 200:
            print("✅ Gửi Telegram ")
        else:
            print(f"❌ Gửi Telegram fail: {res.status_code} - {res.text}")
    except Exception as e:
        print(f"❌ Exception khi gửi Telegram: {e}")

def start_cloudflared():
    process = subprocess.Popen(
        ['cloudflared', 'tunnel', '--url', 'http://localhost:8000'],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True
    )

    url_found = False

    for line in process.stdout:
        print(line.strip())

        if not url_found:
            match = re.search(r'https://[-\w]+\.trycloudflare\.com', line)
            if match:
                url = match.group(0)
                print(f"✅ Link tunnel: {url}")

                with open("public_url.txt", "w") as f:
                    f.write(url)

                send_telegram_message(f"🚀 Link Cloudflared :\n{url}")
                url_found = True

start_cloudflared()