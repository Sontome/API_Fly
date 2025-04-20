@echo off
echo 🌀 Đang khởi chạy Cloudflared + Bot Telegram...
cd /d %~dp0



:: 1. Chạy reloadcookievna.py
start "" python reloadcookievna.py

:: 2. Chạy Cloudflared và gửi link Telegram
start "" python start_cloudflared.py

:: 3. Chạy FastAPI với Uvicorn
start "" uvicorn main:app --reload