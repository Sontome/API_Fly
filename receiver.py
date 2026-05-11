#!/usr/bin/python3

import sys
import os
import re
import uuid
import traceback
import email
import mimetypes
from email import policy
from email.header import decode_header
from datetime import datetime

from dotenv import load_dotenv
from supabase import create_client

# =========================
# ENV
# =========================

load_dotenv("/opt/mail_receiver/.env")

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY")

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

# =========================
# PATHS
# =========================

today = datetime.now()

SAVE_DIR = f"/data/inbound_mail/{today:%Y/%m/%d}"

LOG_DIR = "/data/inbound_logs"

ACCESS_LOG = f"{LOG_DIR}/mail_access.log"
ERROR_LOG = f"{LOG_DIR}/mail_error.log"
DEBUG_LOG = f"{LOG_DIR}/mail_debug.log"

os.makedirs(SAVE_DIR, exist_ok=True)
os.makedirs(LOG_DIR, exist_ok=True)

# =========================
# HELPERS
# =========================

def write_log(path, message):
    with open(path, "a") as f:
        f.write(f"{datetime.now()} | {message}\n")


def decode_mime_header(value):
    if not value:
        return ""

    decoded = decode_header(value)

    result = ""

    for part, encoding in decoded:

        if isinstance(part, bytes):
            result += part.decode(encoding or "utf-8", errors="ignore")
        else:
            result += part

    return result.strip()


# =========================
# START
# =========================

try:

    write_log(DEBUG_LOG, "========== NEW MAIL ==========")

    raw = sys.stdin.buffer.read()

    write_log(DEBUG_LOG, f"RAW SIZE = {len(raw)} bytes")

    msg = email.message_from_bytes(raw, policy=policy.default)

    # =========================
    # HEADER
    # =========================

    sender = msg.get("From", "")
    raw_subject = msg.get("Subject", "")

    subject = decode_mime_header(raw_subject)
    body = ""

    if msg.is_multipart():
    
        for part in msg.walk():
    
            content_type = part.get_content_type()
            disposition = str(part.get("Content-Disposition"))
    
            if content_type == "text/plain" and "attachment" not in disposition:
    
                charset = part.get_content_charset() or "utf-8"
    
                try:
                    body = part.get_payload(decode=True).decode(charset, errors="ignore")
                except:
                    pass
    
                break
    
    else:
    
        charset = msg.get_content_charset() or "utf-8"
    
        try:
            body = msg.get_payload(decode=True).decode(charset, errors="ignore")
        except:
            pass
            
    write_log(DEBUG_LOG, f"SENDER RAW = {sender}")
    write_log(DEBUG_LOG, f"SUBJECT = {subject}")
    write_log(DEBUG_LOG, f"BODY = {body}")
    m = re.match(r'(.*)<(.+)>', sender)

    if m:
        sender_name = m.group(1).strip().replace('"', '')
        sender_email = m.group(2).strip()
    else:
        sender_name = sender
        sender_email = sender

    sender_name = decode_mime_header(sender_name)

    write_log(DEBUG_LOG, f"SENDER NAME = {sender_name}")
    write_log(DEBUG_LOG, f"SENDER EMAIL = {sender_email}")

    attachment_count = 0

    # =========================
    # ATTACHMENTS
    # =========================

    for part in msg.walk():

        content_disposition = str(part.get("Content-Disposition", ""))
    
        filename = part.get_filename()
    
        # skip body
        if part.get_content_maintype() == "multipart":
            continue
    
        # skip text thường
        if not filename and "attachment" not in content_disposition.lower():
            continue
    
        # decode filename
        if filename:
            filename = decode_mime_header(filename)
            filename = os.path.basename(filename)
        else:
            ext = mimetypes.guess_extension(part.get_content_type()) or ".bin"
            filename = f"unknown{ext}"
    
        write_log(DEBUG_LOG, f"FOUND ATTACHMENT = {filename}")
    
        data = part.get_payload(decode=True)
    
        if not data:
            write_log(DEBUG_LOG, f"EMPTY DATA = {filename}")
            continue
    
        size_kb = round(len(data) / 1024, 2)
    
        ext = os.path.splitext(filename)[1]
    
        new_name = f"{uuid.uuid4()}{ext}"
    
        save_path = os.path.join(SAVE_DIR, new_name)
    
        with open(save_path, "wb") as f:
            f.write(data)
    
        relative_path = save_path.replace("/data/inbound_mail/", "")
    
        write_log(
            DEBUG_LOG,
            f"SAVED = {filename} -> {save_path} ({size_kb} KB)"
        )
    
        payload = {
            "sender_name": sender_name,
            "sender_email": sender_email,
            "subject": subject,
            "file_name": filename,
            "file_path": relative_path,
            "status": "NEW"
        }
    
        res = (
            supabase
            .table("inbound_email")
            .insert(payload)
            .execute()
        )
    
        write_log(DEBUG_LOG, f"SUPABASE RESPONSE = {res}")
    
        write_log(
            ACCESS_LOG,
            f"{sender_email} | {subject} | {filename} | {size_kb} KB"
        )
    
        attachment_count += 1

    # =========================
    # NO ATTACHMENT
    # =========================

    if attachment_count == 0:
        payload = {
            "sender_name": sender_name,
            "sender_email": sender_email,
            "subject": subject,
            "file_name": None,
            "file_path": None,
            "status": "NO_ATTACHMENT"
        }
    
        supabase.table("inbound_email").insert(payload).execute()
    
        write_log(
            ACCESS_LOG,
            f"{sender_email} | {subject} | NO ATTACHMENT"
        )
    
        write_log(DEBUG_LOG, f"BODY = {body[:1000]}")

    write_log(DEBUG_LOG, "MAIL PROCESS DONE")

# =========================
# ERROR
# =========================

except Exception as e:

    write_log(ERROR_LOG, "========== ERROR ==========")
    write_log(ERROR_LOG, str(e))
    write_log(ERROR_LOG, traceback.format_exc())
