import time
import subprocess

while True:
    print("🕒 Chạy getcokivna.py để renew cookie...")
    subprocess.run(["python", "getcokivna.py"])
    print("✅ Xong! Ngủ 180s ..\n")
    subprocess.run(["python", "getcokivj.py"])
    print("✅ Xong! Ngủ 180s ..\n")
    time.sleep(120)  # 300 giây = 5 phút
