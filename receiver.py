#!/API_Fly/venv/bin/python

import sys
import os
import re
import uuid
import traceback
import email

from email import policy
from datetime import datetime

from dotenv import load_dotenv
from supabase import create_client

load_dotenv("/API_Fly/.env")

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY")

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

today = datetime.now()

SAVE_DIR = f"/data/inbound_mail/{today:%Y/%m/%d}"

os.makedirs(SAVE_DIR, exist_ok=True)

LOG_FILE = "/data/inbound_logs/mail_error.log"
ACCESS_LOG = "/data/inbound_logs/mail_access.log"
try:

    raw = sys.stdin.buffer.read()

    msg = email.message_from_bytes(raw, policy=policy.default)

    sender = msg.get("From", "")
    subject = msg.get("Subject", "")

    m = re.match(r'(.*)<(.+)>', sender)

    if m:
        sender_name = m.group(1).strip().replace('"', '')
        sender_email = m.group(2).strip()
    else:
        sender_name = sender
        sender_email = sender

    for part in msg.iter_attachments():

        filename = part.get_filename()

        if not filename:
            continue

        data = part.get_payload(decode=True)

        ext = os.path.splitext(filename)[1]

        new_name = f"{uuid.uuid4()}{ext}"

        path = os.path.join(SAVE_DIR, new_name)

        with open(path, "wb") as f:
            f.write(data)

        relative_path = path.replace("/data/inbound_mail/", "")

        supabase.table("inbound_email").insert({
            "sender_name": sender_name,
            "sender_email": sender_email,
            "subject": subject,
            "file_name": filename,
            "file_path": relative_path,
            "status": "NEW"
        }).execute()
        with open(ACCESS_LOG, "a") as f:
        f.write(
            f"{datetime.now()} | "
            f"{sender_email} | "
            f"{subject} | "
            f"{filename}\n"
        )

except Exception as e:

    with open(LOG_FILE, "a") as f:
        f.write("\n====================\n")
        f.write(str(datetime.now()) + "\n")
        f.write(str(e) + "\n")
        f.write(traceback.format_exc())
