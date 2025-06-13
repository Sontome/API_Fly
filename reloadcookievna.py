import time
import subprocess

while True:
    print("🕒 Chạy getcokivna.py để renew cookie...")
    subprocess.run(["python", "getcokivna.py"])
    print("✅ Xong! Ngủ 180s ..\n")
    
    time.sleep(600)  # 300 giây = 5 phút
