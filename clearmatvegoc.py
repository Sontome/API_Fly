#!/usr/bin/python3
import os, time

FOLDER = "/root/matvegoc"
now = time.time()

for f in os.listdir(FOLDER):
    path = os.path.join(FOLDER, f)
    if os.path.isfile(path):
        if now - os.path.getmtime(path) > 23328000:
            os.remove(path)
