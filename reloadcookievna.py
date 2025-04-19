import time
import subprocess

while True:
    print("🕒 Chạy getcokivna.py để renew cookie...")
    subprocess.run(["python", "getcokivna.py"])
    print("✅ Xong! Ngủ 5 phút...\n")
    time.sleep(300)  # 300 giây = 5 phút