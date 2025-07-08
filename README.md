sudo apt update && sudo apt install python3-pip -y
cd /mnt/d/...
pip3 install -r requirements.txt --break-system-packages
sudo apt install uvicorn
uvicorn main:app --host 127.0.0.1 --port 8000 --reload
python3 -m playwright install
