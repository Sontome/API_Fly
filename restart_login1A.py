import os
import signal
import subprocess
import time
WORK_DIR = os.path.expanduser("~/API_Fly/")
# Tên file cần restart
SCRIPT_NAME = "login1A.py"

def kill_process_by_name(name):
    try:
        # Liệt kê process chứa tên file hoặc chrome
        output = subprocess.check_output(["ps", "aux"]).decode("utf-8")
        for line in output.splitlines():
            if name in line and "python" in line:
                pid = int(line.split()[1])
                os.kill(pid, signal.SIGKILL)
        print(f"Đã kill {name} xong")
    except Exception as e:
        print(f"Lỗi khi kill {name}: {e}")

def kill_chrome():
    try:

        subprocess.call(["pkill", "-9", "chrome"])
        subprocess.call(["pkill", "-9", "chromium"])
        print("Đã kill toàn bộ Chrome/Chromium")
    except Exception as e:
        print(f"Lỗi khi kill Chrome: {e}")

def start_script():
    try:
       
        subprocess.Popen(["python3", SCRIPT_NAME])
        print(f"Đã start lại {SCRIPT_NAME}")
    except Exception as e:
        print(f"Lỗi khi start script: {e}")

if __name__ == "__main__":
    # 1. Kill script đang chạy
    kill_process_by_name(SCRIPT_NAME)

    # 2. Kill Chrome để dọn RAM
    kill_chrome()

    # 3. Chờ 3s cho chắc
    time.sleep(3)

    # 4. Start lại script

    start_script()
