import os
import shutil
import zipfile
import tempfile
import requests
from .mail_queue_service import MailQueueService
from .send_email_ticket import send_email_ticket
from urllib.parse import unquote
from .log_mail_queue_service import LogMailQueueService
# =========================
# DEBUG MODE
# =========================
DEBUG_MODE = 1


def debug_log(message):

    if DEBUG_MODE == 1:
        print(f"[DEBUG] {message}")


# =========================
# MOCK: FETCH TICKET API
# =========================

def fetch_ticket_zip(pnrs: list,type: int=0,banner: str=""):

    debug_log(f"FETCH TICKET FOR PNRS: {pnrs}")
    debug_log(f"FETCH TICKET FOR TYPE: {type}")
    debug_log(f"FETCH TICKET FOR BANNER: {banner}")
    
    """
    SUCCESS:
    API trả trực tiếp binary file zip

    ERROR:
    {
        "error": "...",
        "missing_pnrs": [...]
    }
    """

    try:

        # =========================
        # PARSE PNR LIST
        # =========================

        # ["ABC123", "ABCDEF"]
        # -> "ABC123,ABCDEF"

        pnr_string = ",".join(pnrs)

        debug_log(f"PARSED PNR STRING: {pnr_string}")

        # =========================
        # CALL API
        # =========================

        response = requests.post(
            "https://apilive.hanvietair.com/process-pdf-pnr-v2/",
            headers={
                "accept": "application/json",
                "Content-Type": "application/x-www-form-urlencoded"
            },
            data={
                "pnr_list": pnr_string,
                "option": banner,
                "type": type
            },
            timeout=120
        )

        debug_log(f"API STATUS: {response.status_code}")

        # =========================
        # SUCCESS => FILE ZIP
        # =========================

        content_type = response.headers.get(
            "Content-Type",
            ""
        )

        if (
            response.status_code == 200
            and "application/zip" in content_type
        ):

            temp_dir = tempfile.mkdtemp()

            # =====================================================
            # GET ORIGINAL FILENAME
            # =====================================================

            filename = "tickets.zip"

            content_disposition = response.headers.get(
                "Content-Disposition",
                ""
            )

            print(
                f"CONTENT DISPOSITION: "
                f"{content_disposition}"
            )

            # =====================================================
            # RFC5987
            # filename*=utf-8''abc.zip
            # =====================================================

            if "filename*=" in content_disposition:

                filename = (
                    content_disposition
                    .split("filename*=")[-1]
                    .strip()
                )

                # remove utf-8''
                if "''" in filename:

                    filename = filename.split(
                        "''",
                        1
                    )[-1]

                filename = unquote(filename)

            # =====================================================
            # NORMAL filename=
            # =====================================================

            elif "filename=" in content_disposition:

                filename = (
                    content_disposition
                    .split("filename=")[-1]
                    .strip('"')
                    .strip()
                )

            print(f"ZIP FILENAME: {filename}")

            zip_path = os.path.join(
                temp_dir,
                filename
            )

            with open(zip_path, "wb") as f:
                f.write(response.content)

            debug_log(f"ZIP SAVED: {zip_path}")

            return {
                "success": True,
                "zip_path": zip_path
            }

        # =========================
        # ERROR RESPONSE
        # =========================

        try:

            error_data = response.json()

            debug_log(f"API ERROR RESPONSE: {error_data}")

            return {
                "error": error_data.get(
                    "error",
                    "Không lấy được vé"
                ),
                "missing_pnrs": error_data.get(
                    "missing_pnrs",
                    []
                )
            }

        except Exception:

            debug_log(f"RAW ERROR RESPONSE: {response.text}")

            return {
                "error": response.text
            }

    except Exception as e:

        debug_log(f"FETCH TICKET ERROR: {str(e)}")

        return {
            "error": str(e)
        }





# =========================
# EXTRACT ZIP
# =========================
def extract_zip(zip_path: str):

    debug_log(f"EXTRACT ZIP: {zip_path}")

    extract_dir = tempfile.mkdtemp()

    with zipfile.ZipFile(zip_path, "r") as zip_ref:
        zip_ref.extractall(extract_dir)

    attachment_files = []

    for root, _, files in os.walk(extract_dir):

        for file in files:

            file_path = os.path.join(root, file)

            attachment_files.append(file_path)

            debug_log(f"EXTRACTED FILE: {file_path}")

    debug_log(f"EXTRACT SUCCESS: {extract_dir}")

    return extract_dir, attachment_files


# =========================
# CLEANUP TEMP FILES
# =========================
def cleanup_temp_files(*paths):

    for path in paths:

        try:

            if os.path.isfile(path):

                os.remove(path)

                debug_log(f"FILE DELETED: {path}")

            elif os.path.isdir(path):

                shutil.rmtree(path)

                debug_log(f"DIRECTORY DELETED: {path}")

        except Exception as e:

            print(f"CLEANUP ERROR: {e}")


# =========================
# PROCESS MAIL QUEUE
# =========================
def process_mail_queue():

    debug_log("START PROCESS MAIL QUEUE")

    queues = MailQueueService.get_by_status(
        "pending"
    )

    debug_log(f"FOUND {len(queues)} PENDING QUEUES")

    for queue in queues:

        queue_id = queue["id"]

        try:

            debug_log(f"PROCESS QUEUE: {queue_id}")

            pnrs = queue["pnrs"]
            email = queue["email"]
            customer_name=queue["customer_name"]
            salutation=queue["salutation"]
            phone = queue["phone"]

            # =========================
            # FETCH TICKET
            # =========================

            result = fetch_ticket_zip(
                pnrs=pnrs,
                type=queue["type"],
                banner=queue["banner"]
            )

            # =========================
            # CASE: MISSING PNR
            # =========================

            if result.get("error"):

                missing_pnrs = result.get(
                    "missing_pnrs",
                    []
                )

                debug_log(
                    f"MISSING PNR: {missing_pnrs}"
                )

                MailQueueService.update(
                    queue_id=queue_id,
                    data={
                        "status": "pending",
                        "missing_pnrs": missing_pnrs
                    }
                )

                debug_log(
                    f"QUEUE UPDATED WAITING_TICKET: {queue_id}"
                )

                continue

            # =========================
            # SUCCESS
            # =========================

            zip_path = result["zip_path"]
            flight_date = os.path.splitext(
                os.path.basename(zip_path)
            )[0]
            extract_dir, attachments = extract_zip(
                zip_path
            )

            # =========================
            # SEND MAIL
            # =========================

            send_email_ticket(
                email=email,
                customer_name=customer_name,
                salutation=salutation,
                phone=phone,
                attachments=attachments,
                flight_date=flight_date

            )

            # =========================
            # UPDATE STATUS
            # =========================
            # LOG MAIL SENT
            # =========================

            for pnr in pnrs:

                try:

                    LogMailQueueService.create(
                        pnr=pnr,
                        email=email,
                        customer_name=customer_name,
                        salutation=salutation,
                        phone=phone,
                        mail_type="ticket"
                    )

                    debug_log(
                        f"LOG MAIL CREATED: {pnr}"
                    )

                except Exception as e:

                    debug_log(
                        f"LOG MAIL ERROR {pnr}: {str(e)}"
                    )
            MailQueueService.update(
                queue_id=queue_id,
                data={
                    "status": "sent",
                    "missing_pnrs": []
                }
            )

            debug_log(
                f"QUEUE SENT SUCCESS: {queue_id}"
            )

            # =========================
            # CLEANUP
            # =========================

            cleanup_temp_files(
                zip_path,
                extract_dir
            )

        except Exception as e:

            print(f"PROCESS ERROR: {e}")

            MailQueueService.update(
                queue_id=queue_id,
                data={
                    
                    "last_error": str(e)
                }
            )

            debug_log(
                f"QUEUE FAILED: {queue_id}"
            )


# =========================
# RUN
# =========================
if __name__ == "__main__":

    process_mail_queue()
