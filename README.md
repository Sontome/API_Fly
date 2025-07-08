sudo apt update && sudo apt install python3-pip -y
cd /mnt/d/...
pip3 install -r requirements.txt --break-system-packages
sudo apt install uvicorn
sudo ln -s /usr/bin/python3 /usr/bin/python
python3 -m playwright install
python3 -m playwright install-deps


uvicorn main:app --host 127.0.0.1 --port 8000 --reload
