#!/usr/bin/python3

import sys
import os
import re
import uuid
import traceback
import email
import mimetypes
import requests
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
def send_notification(message):

    try:

        response = requests.post(
            "http://127.0.0.1:8000/send",
            json={
                "message": message
            },
            timeout=30
        )

        write_log(
            DEBUG_LOG,
            f"SEND NOTIFY RESPONSE = {response.text}"
        )

    except Exception as e:

        write_log(
            ERROR_LOG,
            f"SEND NOTIFY ERROR = {str(e)}"
        )

        write_log(
            ERROR_LOG,
            traceback.format_exc()
        )
def check_payment_api(hang, file_path):

    try:

        endpoint = None

        if hang == "VJ":
            endpoint = "http://127.0.0.1:8000/check-payment-vj/"

        elif hang == "VNA":
            endpoint = "http://127.0.0.1:8000/check-payment-vna/"

        else:
            return None

        with open(file_path, "rb") as f:

            files = {
                "file": (
                    os.path.basename(file_path),
                    f,
                    "application/pdf"
                )
            }

            response = requests.post(
                endpoint,
                files=files,
                timeout=120
            )

        write_log(
            DEBUG_LOG,
            f"PAYMENT API RESPONSE = {response.text}"
        )

        if response.status_code != 200:
            return None

        return response.json()

    except Exception as e:

        write_log(
            ERROR_LOG,
            f"CHECK PAYMENT ERROR = {str(e)}"
        )

        write_log(
            ERROR_LOG,
            traceback.format_exc()
        )

        return None
def generate_custom_filename(sender_email, subject, original_filename):

    sender_email = sender_email.lower().strip()

    result = {
        "file_name": original_filename,
        "type": None,
        "pnr": None,
        "name": None
    }

    # =========================
    # VietJet
    # =========================

    if sender_email == "noreply.itinerary@vietjetair.com":

        match = re.match(
            r"Itinerary-([A-Z0-9]+)\.pdf",
            original_filename,
            re.I
        )

        if match:

            booking_code = match.group(1).upper()

            result["file_name"] = f"VJ-{booking_code}.pdf"
            result["type"] = "VJ"
            result["pnr"] = booking_code

            return result

    # =========================
    # Vietnam Airlines
    # =========================

    elif sender_email == "no-reply@service.vietnamairlines.com":

        booking_code = None
        passenger_name = None

        # CASE 1
        match = re.search(
            r"-\s*([A-Z0-9]+)\s+(?:cho|for)\s+(.+)",
            subject,
            re.I
        )

        if match:

            booking_code = match.group(1).upper()

            passenger_name = match.group(2).strip()

        else:

            # CASE 2 Korean
            match = re.search(
                r"(.+?)\s+님을\s+위해.*?-\s*([A-Z0-9]+)",
                subject,
                re.I
            )

            if match:

                passenger_name = match.group(1).strip()

                booking_code = match.group(2).upper()

        if booking_code:

            result["type"] = "VNA"
            result["pnr"] = booking_code

        if passenger_name:

            passenger_name = passenger_name.replace("/", " ")

            passenger_name = re.sub(
                r"\s+",
                " ",
                passenger_name
            ).strip()

            passenger_name = re.sub(
                r'[\\/:*?"<>|]',
                '',
                passenger_name
            )

            result["name"] = passenger_name

        if booking_code and passenger_name:

            result["file_name"] = (
                f"VNA-{booking_code}-{passenger_name}.pdf"
            )

            return result

    return result
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
    # =========================
    # FLIGHT CHANGE DETECTION
    # =========================
    
    flight_change_rules = [
    
        {
            # "sender": "noreply.19001886@ses.vietjetair.com",
            "sender": "devilrauxanhk17@gmail.com",
            "subject": "Thông báo lịch bay thay đổi",
            "hang": "VJ"
        },
    
        {
            "sender": "sc@info.vietnamairlines.com",
            "subject": "THÔNG BÁO THAY ĐỔI LỊCH BAY",
            "hang": "VNA"
        }
    ]
    
    is_flight_change = False

    normalized_subject = re.sub(
        r"\s+",
        " ",
        subject
    ).strip().lower()
    write_log(
                DEBUG_LOG,
                f"FLIGHT CHANGE MATCHED = {sender_email} | {subject}"
            )
    for rule in flight_change_rules:
    
        expected_subject = re.sub(
            r"\s+",
            " ",
            rule["subject"]
        ).strip().lower()
    
        if (
            sender_email.lower().strip() == rule["sender"].lower().strip()
            and expected_subject in normalized_subject
        ):
    
            is_flight_change = True
    
            payload = {
    
                "sender_name": sender_name,
    
                "sender_email": sender_email,
    
                "subject": subject,
    
                "body": body,
    
                "hang": rule["hang"],
    
                "status": "FLIGHT_CHANGE",
    
                "file_name": None,
    
                "file_path": None
            }
    
            res = (
                supabase
                .table("inbound_email")
                .insert(payload)
                .execute()
            )
    
            write_log(
                DEBUG_LOG,
                f"FLIGHT CHANGE INSERT = {res}"
            )
    
            
            
            break
    attachment_count = 0
    allowed_attachment_senders = [
    
        "noreply.itinerary@vietjetair.com",
    
        "no-reply@service.vietnamairlines.com"
    ]
    # =========================
    # ATTACHMENTS
    # =========================
    if sender_email.lower().strip() in allowed_attachment_senders:
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
        
            # custom filename
            file_info = generate_custom_filename(
                sender_email=sender_email,
                subject=subject,
                original_filename=filename
            )
            
            final_filename = file_info["file_name"]
            
            final_filename = re.sub(
                r'[\\/:*?"<>|]',
                '',
                final_filename
            )
            
            save_path = os.path.join(SAVE_DIR, final_filename)
        
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
                "file_name": final_filename,
                "file_path": relative_path,
                "hang": file_info["type"],
                "pnr": file_info["pnr"],
                "customer": file_info["name"],
                "status": "NEW"
            }
        
            res = (
                supabase
                .table("inbound_email")
                .insert(payload)
                .execute()
            )
        
            write_log(DEBUG_LOG, f"SUPABASE RESPONSE = {res}")
            # CHECK PAYMENT
            # =========================
            
            if file_info["type"] in ["VJ", "VNA"]:
            
                payment_result = check_payment_api(
                    hang=file_info["type"],
                    file_path=save_path
                )
            
                if payment_result:
            
                    payment_status = (
                        str(payment_result.get("paymentstatus"))
                        .lower()
                        == "true"
                    )
            
                    if payment_status:
            
                        result_data = payment_result.get("result", {})
            
                        ticket_payload = {
            
                            "pnr": file_info["pnr"],
            
                            "hang": file_info["type"],
            
                            # VNA ưu tiên name cũ
                            "name": (
                                file_info["name"]
                                or payment_result.get("name")
                            ),
            
                            "paymentstatus": True,
            
                            "trip1": result_data.get("trip1"),
                            "day1": result_data.get("day1"),
                            "time1": result_data.get("time1"),
            
                            "trip2": result_data.get("trip2"),
                            "day2": result_data.get("day2"),
                            "time2": result_data.get("time2"),
            
                            "trip3": result_data.get("trip3"),
                            "day3": result_data.get("day3"),
                            "time3": result_data.get("time3"),
            
                            "trip4": result_data.get("trip4"),
                            "day4": result_data.get("day4"),
                            "time4": result_data.get("time4"),
            
                            "file_path": relative_path
                        }
            
                        ticket_res = (
                            supabase
                            .table("ticket_log")
                            .insert(ticket_payload)
                            .execute()
                        )
            
                        write_log(
                            DEBUG_LOG,
                            f"TICKET LOG INSERT = {ticket_res}"
                        )
                        # SEND NOTIFICATION
                        # =========================
                        
                        notify_message = (
                            f"Đã có mặt vé  PNR: {file_info['pnr']}"
                        )
                        
                        send_notification(notify_message)
            write_log(
                ACCESS_LOG,
                f"{sender_email} | {subject} | {filename} | {size_kb} KB"
            )
        
            attachment_count += 1

    # =========================
    # NO ATTACHMENT
    # =========================

    if attachment_count == 0 and not is_flight_change:
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
