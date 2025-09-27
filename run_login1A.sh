#!/bin/bash
# Chạy logout trước cho chắc
/usr/bin/python3 /root/API_Fly/logout1A.py || true

# Chờ 3 giây
sleep 3

# Rồi mới chạy login
exec /usr/bin/python3 /root/API_Fly/login1A.py
