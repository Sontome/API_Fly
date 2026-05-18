# send_email_ticket.py

import os
import base64
import mimetypes
from dotenv import load_dotenv
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email import encoders

from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
import requests


# =====================================================
# LOAD ENV
# =====================================================

load_dotenv()


# =====================================================
# CONFIG
# =====================================================

CLIENT_ID = os.getenv("GMAIL_CLIENT_ID")

CLIENT_SECRET = os.getenv(
    "GMAIL_CLIENT_SECRET"
)

REFRESH_TOKEN = os.getenv(
    "GMAIL_REFRESH_TOKEN"
)

GMAIL_ACCOUNT = os.getenv(
    "GMAIL_ACCOUNT"
)
# GET EMAIL SUBJECT
# =====================================================

def get_email_subject(
    flight_date,
    customer_name,
    salutation,
    phone
):

    try:

        

        # =====================================================
        # BUILD SUBJECT
        # =====================================================

        subject = (
            f"{salutation} "
            f"{customer_name} - "
            
            f"{flight_date} "
            f"- {phone}"
        )
        if  not phone :
            subject = (
                f"{salutation} "
                f"{customer_name} - "
                
                f"{flight_date} "
                
            )
        print(f"EMAIL SUBJECT: {subject}")

        return subject

    except Exception as e:

        print(f"GET SUBJECT ERROR: {str(e)}")

        return (
            f"{salutation} "
            f"{customer_name}"
        )
# =====================================================
# BUILD GMAIL SERVICE
# =====================================================

def get_gmail_service():

    creds = Credentials(
        None,
        refresh_token=REFRESH_TOKEN,
        token_uri="https://oauth2.googleapis.com/token",
        client_id=CLIENT_ID,
        client_secret=CLIENT_SECRET,
        scopes=[
            "https://www.googleapis.com/auth/gmail.send"
        ]
    )

    service = build(
        "gmail",
        "v1",
        credentials=creds
    )

    return service


# =====================================================
# SEND EMAIL
# =====================================================

def send_email_ticket(
    email,
    customer_name,
    salutation,
    phone,
    attachments,
    flight_date
):

    try:
        # DETECT TEMPLATE
        # =====================================================

        first_file = ""

        if attachments:

            first_file = os.path.basename(
                attachments[0]
            ).upper()

        print(f"FIRST FILE: {first_file}")
        print(f"SENDING EMAIL TO: {email}")

        # =====================================================
        # CREATE MESSAGE
        # =====================================================

        message = MIMEMultipart()

        message["To"] = email

        message["From"] = GMAIL_ACCOUNT

        subject = get_email_subject(
            flight_date=flight_date,
            customer_name=customer_name,
            salutation=salutation,
            phone=phone
        )

        message["Subject"] = subject

        # =====================================================
        # BODY
        # =====================================================

        bodyVNA = f"""
            <div style="background-color:#efefef;background-color:#efefef;box-sizing:border-box;color:#0a0a0a;font-family:'Arial',Helvetica,sans-serif;font-size:16px;font-weight:400;line-height:1.3;margin:0 auto;max-width:960px;min-width:100%;padding:0;text-align:left;width:100%!important">
<span style="color:#efefef;display:none!important;font-size:1px;line-height:1px;max-height:0px;max-width:0px;opacity:0;overflow:hidden"></span>
<table style="background:none;border-collapse:collapse;border-spacing:0;color:#0a0a0a;font-family:'Arial',Helvetica,sans-serif;font-size:16px;font-weight:400;height:100%;line-height:1.3;margin:0;padding:0;text-align:left;vertical-align:top;width:100%">
    <tbody><tr style="padding:0;text-align:left;vertical-align:top">
        <td align="center" valign="top" style="border-collapse:collapse!important;color:#0a0a0a;font-family:'Arial',Helvetica,sans-serif;font-size:16px;font-weight:400;line-height:1.3;margin:0;padding:0;text-align:left;vertical-align:top;word-wrap:break-word">
            <center style="min-width:680px;width:100%">
               
                <table align="center" style="border-radius:15px;overflow:hidden;background:#006883;background-color:#006883;border-collapse:collapse;border-spacing:0;float:none;margin:0 auto;padding:0;text-align:center;vertical-align:top;width:680px;max-width:680px">
                    <tbody>
                    <tr style="padding:0;text-align:left;vertical-align:top">
                        <td style="border-collapse:collapse!important;color:#0a0a0a;font-family:'Arial',Helvetica,sans-serif;font-size:16px;font-weight:400;line-height:1.3;margin:0;padding:0;text-align:left;vertical-align:top;word-wrap:break-word">
                            <table style="border-collapse:collapse;border-spacing:0;display:table;padding:0;text-align:left;vertical-align:top;width:100%">
                                <tbody>
                                <tr style="padding:0;text-align:left;vertical-align:top">
                                    <th style="color:#0a0a0a;font-family:'Arial',Helvetica,sans-serif;font-size:16px;font-weight:400;line-height:1.3;margin:0 auto;padding:0;padding-bottom:0;padding-left:0;padding-right:0;text-align:left;width:680px">
                                        <table style="border-collapse:collapse;border-spacing:0;padding:0;text-align:left;vertical-align:top;width:100%">
                                            <tbody><tr style="padding:0;text-align:left;vertical-align:top">
                                                <th style="color:#0a0a0a;font-family:'Arial',Helvetica,sans-serif;font-size:16px;font-weight:400;line-height:1.3;margin:0;padding:0;padding-bottom:0;text-align:left">
                                                    <table align="center" style="background:#0080a1;background-color:#0080a1;border-collapse:collapse;border-spacing:0;margin:0 auto;padding:0;text-align:inherit;vertical-align:top;width:100%">
                                                        <tbody>
                                                        <tr style="padding:0;text-align:left;vertical-align:top">
                                                            <td style="border-collapse:collapse!important;color:#0a0a0a;font-family:'Arial',Helvetica,sans-serif;font-size:16px;font-weight:400;line-height:1.3;margin:0;padding:0;text-align:left;vertical-align:top;word-wrap:break-word">
                                                                <table style="border-collapse:collapse;border-spacing:0;display:table;padding:0;text-align:left;vertical-align:top;width:100%">
                                                                    <tbody>
                                                                    <tr style="padding:0;text-align:left;vertical-align:top">
                                                                        <th style="color:#0a0a0a;font-family:'Arial',Helvetica,sans-serif;font-size:16px;font-weight:400;line-height:1.3;margin:0 auto 20px;padding:0;padding-bottom:0;padding-left:0!important;padding-right:0!important;text-align:left;width:50%">
                                                                            <table style="border-collapse:collapse;border-spacing:0;padding:0;text-align:left;vertical-align:top;width:100%">
                                                                                <tbody><tr style="padding:0;text-align:left;vertical-align:top">
                                                                                    <th style="color:#0a0a0a;font-family:'Arial',Helvetica,sans-serif;font-size:16px;font-weight:400;line-height:1.3;margin:0;padding:0;padding-bottom:0;text-align:left">
                                                                                        <table style="border-collapse:collapse;border-spacing:0;padding:0;text-align:left;vertical-align:top;width:100%">
                                                                                            <tbody>
                                                                                            <tr style="padding:0;text-align:left;vertical-align:top">
                                                                                                <td height="15px" style="border-collapse:collapse!important;color:#0a0a0a;font-family:'Arial',Helvetica,sans-serif;font-size:15px;font-weight:400;line-height:15px;margin:0;padding:0;text-align:left;vertical-align:top;word-wrap:break-word">
                                                                                                    &nbsp;
                                                                                                </td>
                                                                                            </tr>
                                                                                            </tbody>
                                                                                        </table>
                                                                                        <table align="center" style="border-collapse:collapse;border-spacing:0;padding:0;vertical-align:top;width:100%">
                                                                                            <tbody>
                                                                                            <tr>
                                                                                                <td valign="middle" width="50%">
                                                                                                    <table align="center" border="0" cellpadding="0" cellspacing="0" width="100%">
                                                                                                        <tbody>
                                                                                                        <tr>
                                                                                                            <td valign="middle">
                                                                                                                <center style="min-width:590px;width:100%">
                                                                                                                    <img src="https://ci3.googleusercontent.com/meips/ADKq_NYhJjxaW8Wogcv2zzqNNnOyj57tS9iimkdOxKnaLGjyk0DtI44qRYz_0HLgW5ORSlkSaVHvAC_6HMJ4dHkbN0YyZsgftJeU8uCSsTKeCSBBJXtQMEsFaj_d4vfv5CwaYCzoevy2flMhiF5JrHevAP0s7Q=s0-d-e1-ft#http://enewsletter-vietnamairlines.com/html/email/y22/220624_ec_Template/assets/img/logo.png" alt="Logo" style="clear:both;display:block;width:224px;max-width:100%;outline:none;text-decoration:none;text-align:left;margin:0" class="CToWUd" data-bit="iit">
                                                                                                                </center>
                                                                                                            </td>
                                                                                                        </tr>
                                                                                                        </tbody>
                                                                                                    </table>
                                                                                                </td>
                                                                                            </tr>
                                                                                            </tbody>
                                                                                        </table>
                                                                                        <table style="border-collapse:collapse;border-spacing:0;padding:0;text-align:left;vertical-align:top;width:100%">
                                                                                            <tbody>
                                                                                            <tr style="padding:0;text-align:left;vertical-align:top">
                                                                                                <td height="15px" style="border-collapse:collapse!important;color:#0a0a0a;font-family:'Arial',Helvetica,sans-serif;font-size:15px;font-weight:400;line-height:15px;margin:0;padding:0;text-align:left;vertical-align:top;word-wrap:break-word">
                                                                                                    &nbsp;
                                                                                                </td>
                                                                                            </tr>
                                                                                            </tbody>
                                                                                        </table>
                                                                                    </th>
                                                                                </tr>
                                                                            </tbody></table>
                                                                        </th>
                                                                    </tr>
                                                                    </tbody>
                                                                </table>
                                                            </td>
                                                        </tr>
                                                        </tbody>
                                                    </table>
                                                </th>
                                            </tr>
                                        </tbody></table>
                                    </th>
                                </tr>
                                </tbody>
                            </table>

                            <table style="border-collapse:collapse;border-spacing:0;display:table;padding:0;text-align:left;vertical-align:top;width:100%;background-color:#1c3144">
                                <tbody>
                                <tr style="padding:0;text-align:left;vertical-align:top">
                                    <th style="color:#0a0a0a;font-family:'Arial',Helvetica,sans-serif;font-size:16px;font-weight:400;line-height:1.3;margin:0 auto;padding:0;padding-bottom:0;padding-left:0;padding-right:0;text-align:left;width:630px">
                                        <table style="border-collapse:collapse;border-spacing:0;padding:0;text-align:left;vertical-align:top;width:100%">
                                            <tbody><tr style="padding:0;text-align:left;vertical-align:top">
                                                <th style="color:#0a0a0a;font-family:'Arial',Helvetica,sans-serif;font-size:16px;font-weight:400;line-height:1.3;margin:0;padding:0;text-align:left">
                                                    <table align="center" style="background:#fff;background-color:#fff;border-collapse:collapse;border-spacing:0;margin:0 auto;padding:0;text-align:inherit;vertical-align:top;width:100%">
                                                        <tbody>
                                                        <tr style="padding:0;text-align:left;vertical-align:top">
                                                            <td style="border-collapse:collapse!important;color:#0a0a0a;font-family:'Arial',Helvetica,sans-serif;font-size:16px;font-weight:400;line-height:1.3;margin:0;padding:0;text-align:left;vertical-align:top;word-wrap:break-word">
                                                                <center style="min-width:590px;width:100%">
                                                                    <img src="https://raw.githubusercontent.com/Sontome/icon/main/banner_vna_mail.jpg" alt="" align="center" style="clear:both;display:block;float:none;margin:0 auto;width:100%;max-width:100%;height:auto;outline:none;text-align:center;text-decoration:none" width="681" height="406" class="CToWUd a6T" data-bit="iit" tabindex="0"><div class="a6S" dir="ltr" style="opacity: 0.01; left: 838.8px; top: 717.5px;"><span data-is-tooltip-wrapper="true" class="a5q" jsaction="JIbuQc:.CLIENT"></span></div>
                                                                </center>
                                                            </td>
                                                        </tr>
                                                        </tbody>
                                                    </table>
                                                </th>
                                            </tr>
                                        </tbody></table>
                                    </th>
                                </tr>
                                </tbody>
                            </table>

                            <table style="border-collapse:collapse;border-spacing:0;display:table;padding:0;text-align:left;vertical-align:top;width:100%;background-color:#fff">
                                <tbody>
                                <tr style="padding:0;text-align:left;vertical-align:top">
                                    <th style="color:#0a0a0a;font-family:'Arial',Helvetica,sans-serif;font-size:16px;font-weight:400;line-height:1.3;margin:0 auto;padding:0;padding-bottom:0;padding-left:0;padding-right:0;text-align:left;width:630px">
                                        <table style="border-collapse:collapse;border-spacing:0;padding:0;text-align:left;vertical-align:top;width:100%">
                                            <tbody><tr style="padding:0;text-align:left;vertical-align:top">
                                                <th style="color:#0a0a0a;font-family:'Arial',Helvetica,sans-serif;font-size:16px;font-weight:400;line-height:1.3;margin:0;padding:0;text-align:left">
                                                    <table style="border-collapse:collapse;border-spacing:0;display:table;padding:0;text-align:left;vertical-align:top;width:100%">
                                                        <tbody>
                                                        <tr style="padding:0;text-align:left;vertical-align:top">
                                                            <th style="color:#0a0a0a;font-family:'Arial',Helvetica,sans-serif;font-size:16px;font-weight:400;line-height:1.3;margin:0 auto;padding:0;padding-left:35px;padding-right:35px;text-align:left;width:100%">
                                                                <table style="border-collapse:collapse;border-spacing:0;padding:0;text-align:left;vertical-align:top;width:100%">
                                                                    <tbody><tr style="padding:0;text-align:left;vertical-align:top">
                                                                        <th style="color:#000000;font-family:'Arial',Helvetica,sans-serif;font-size:16px;font-weight:400;line-height:1.3;margin:0;padding:0;text-align:left">
                                                                            <table style="border-collapse:collapse;border-spacing:0;display:none;padding:0;text-align:left;vertical-align:top;width:100%">
                                                                                <tbody>
                                                                                <tr style="padding:0;text-align:left;vertical-align:top">
                                                                                    <td height="50" style="margin:0;border-collapse:collapse!important;color:#0a0a0a;font-family:'Arial',Helvetica,sans-serif;font-size:5px;font-weight:normal;line-height:50px;margin:0;padding:0;text-align:left;vertical-align:top;word-wrap:break-word">
                                                                                        &nbsp;
                                                                                    </td>
                                                                                </tr>
                                                                                </tbody>
                                                                            </table>
                                                                            <table style="border-collapse:collapse;border-spacing:0;padding:0;text-align:left;vertical-align:top;width:100%">
                                                                                <tbody>
                                                                                <tr style="padding:0;text-align:left;vertical-align:top">
                                                                                    <td height="50" style="border-collapse:collapse!important;color:#0a0a0a;font-family:'Arial',Helvetica,sans-serif;font-size:10px;font-weight:normal;line-height:50px;margin:0;padding:0;text-align:left;vertical-align:top;word-wrap:break-word">
                                                                                        &nbsp;
                                                                                    </td>
                                                                                </tr>
                                                                                </tbody>
                                                                            </table>
                                                                            <p><strong>Chào {salutation} {customer_name},</strong></p>
<p>Hanvietair xin gửi {salutation} vé điện tử xác nhận hành trình như ảnh đính kèm.</p>
<p>Có thắc mắc gì, {salutation} vui lòng liên hệ với Hanvietair để được giải đáp.</p>
<p>Chúc {salutation} thượng lộ bình an.</p><br>

<p>Xin trân trọng cảm ơn Quý khách đã lựa chọn sử dụng dịch vụ của Hanvietair.</p>
                                                                            <table style="border-collapse:collapse;border-spacing:0;display:none;padding:0;text-align:left;vertical-align:top;width:100%">
                                                                                <tbody>
                                                                                <tr style="padding:0;text-align:left;vertical-align:top">
                                                                                    <td height="30px" style="Margin:0;border-collapse:collapse!important;color:#0a0a0a;font-family:'Arial',Helvetica,sans-serif;font-size:5px;font-weight:normal;line-height:30px;margin:0;padding:0;text-align:left;vertical-align:top;word-wrap:break-word">
                                                                                        &nbsp;
                                                                                    </td>
                                                                                </tr>
                                                                                </tbody>
                                                                            </table>
                                                                            <table style="border-collapse:collapse;border-spacing:0;padding:0;text-align:left;vertical-align:top;width:100%">
                                                                                <tbody>
                                                                                <tr style="padding:0;text-align:left;vertical-align:top">
                                                                                    <td height="30px" style="border-collapse:collapse!important;color:#0a0a0a;font-family:'Arial',Helvetica,sans-serif;font-size:10px;font-weight:normal;line-height:30px;margin:0;padding:0;text-align:left;vertical-align:top;word-wrap:break-word">
                                                                                        &nbsp;
                                                                                    </td>
                                                                                </tr>
                                                                                </tbody>
                                                                            </table>
                                                                            <p style="color:#0d6981;font-family:'Arial',Helvetica,sans-serif;font-size:14px;font-weight:300;line-height:24px;margin:0;margin-bottom:0;padding:0;text-align:center">
                                                                            Vui lòng nhấn vào liên kết dưới đây để xem các ưu đãi của Hanvietair&nbsp;<a href="https://hanvietair.com/" target="_blank">
  https://hanvietair.com/
</a>.
                                                                            </p>
                                                                            <table style="border-collapse:collapse;border-spacing:0;display:none;padding:0;text-align:left;vertical-align:top;width:100%">
                                                                                <tbody>
                                                                                <tr style="padding:0;text-align:left;vertical-align:top">
                                                                                    <td height="20" style="margin:0;border-collapse:collapse!important;color:#0a0a0a;font-family:'Arial',Helvetica,sans-serif;font-size:5px;font-weight:normal;line-height:20px;margin:0;padding:0;text-align:left;vertical-align:top;word-wrap:break-word">
                                                                                        &nbsp;
                                                                                    </td>
                                                                                </tr>
                                                                                </tbody>
                                                                            </table>
                                                                            <table style="border-collapse:collapse;border-spacing:0;padding:0;text-align:left;vertical-align:top;width:100%">
                                                                                <tbody>
                                                                                <tr style="padding:0;text-align:left;vertical-align:top">
                                                                                    <td height="20" style="border-collapse:collapse!important;color:#0a0a0a;font-family:'Arial',Helvetica,sans-serif;font-size:10px;font-weight:normal;line-height:20px;margin:0;padding:0;text-align:left;vertical-align:top;word-wrap:break-word">
                                                                                        &nbsp;
                                                                                    </td>
                                                                                </tr>
                                                                                </tbody>
                                                                            </table>
                                                                        </th>
                                                                        <th style="color:#0a0a0a;font-family:'Arial',Helvetica,sans-serif;font-size:16px;font-weight:400;line-height:1.3;margin:0;padding:0!important;text-align:left;width:0"></th>
                                                                    </tr>
                                                                </tbody></table>
                                                            </th>
                                                        </tr>
                                                        </tbody>
                                                    </table>
                                                </th>
                                            </tr>
                                        </tbody></table>
                                    </th>
                                </tr>
                                </tbody>
                            </table>

                            <table style="background:#0080a1;background-color:#0080a1;border-collapse:collapse;border-spacing:0;display:table;padding:0;text-align:left;vertical-align:top;width:100%">
                                <tbody>
                                <tr style="padding:0;text-align:left;vertical-align:top">
                                    <th style="color:#0a0a0a;font-family:'Arial',Helvetica,sans-serif;font-size:13px;font-weight:400;line-height:1.3;margin:0 auto;padding:0;padding-bottom:0!important;padding-left:0;padding-right:0;text-align:left;width:680px">
                                        <table style="border-collapse:collapse;border-spacing:0;padding:0;text-align:left;vertical-align:top;width:100%">
                                            <tbody><tr style="padding:0;text-align:left;vertical-align:top">
                                                <th style="color:#0a0a0a;font-family:'Arial',Helvetica,sans-serif;font-size:13px;font-weight:400;line-height:1.3;margin:0;padding:0;text-align:left">
                                                    <table align="center" style="background:none;background-color:transparent;border-collapse:collapse;border-spacing:0;margin:0 auto;padding:0;text-align:inherit;vertical-align:top;width:100%">
                                                        <tbody>
                                                        <tr style="padding:0;text-align:left;vertical-align:top">
                                                            <td style="border-collapse:collapse!important;color:#0a0a0a;font-family:'Arial',Helvetica,sans-serif;font-size:13px;font-weight:400;line-height:1.3;margin:0;padding:0;text-align:left;vertical-align:top;word-wrap:break-word">
                                                                <table style="border-collapse:collapse;border-spacing:0;display:table;padding:0;text-align:left;vertical-align:top;width:100%">
                                                                    <tbody>
                                                                    <tr style="padding:0;text-align:left;vertical-align:top">
                                                                        <th style="color:#0a0a0a;font-family:'Arial',Helvetica,sans-serif;font-size:13px;font-weight:400;line-height:1.3;margin:0 auto;padding:0;padding-left:35px;padding-right:35px;text-align:left;width:100%">
                                                                            <table style="border-collapse:collapse;border-spacing:0;padding:0;text-align:left;vertical-align:top;width:100%">
                                                                                <tbody><tr style="padding:0;text-align:left;vertical-align:top">
                                                                                    <th style="color:#0a0a0a;font-family:'Arial',Helvetica,sans-serif;font-size:13px;font-weight:400;line-height:1.3;margin:0;padding:0;text-align:left">
                                                                                        <table style="border-collapse:collapse;border-spacing:0;padding:0;text-align:left;vertical-align:top;width:100%">
                                                                                            <tbody>
                                                                                            <tr style="padding:0;text-align:left;vertical-align:top">
                                                                                                <td height="50px" style="Margin:0;border-collapse:collapse!important;color:#0a0a0a;font-family:'Arial',Helvetica,sans-serif;font-size:5px;font-weight:400;line-height:50px;margin:0;padding:0;text-align:left;vertical-align:top;word-wrap:break-word">
                                                                                                    &nbsp;
                                                                                                </td>
                                                                                            </tr>
                                                                                            </tbody>
                                                                                        </table>
                                                                                        <table style="border-collapse:collapse;border-spacing:0;padding:0;text-align:left;vertical-align:top;width:100%">
                                                                                            <tbody>
                                                                                            <tr style="padding:0;text-align:left;vertical-align:top">
                                                                                                <td style="border-collapse:collapse!important;color:#0a0a0a;font-family:'Arial',Helvetica,sans-serif;font-size:10px;font-weight:400;line-height:10px;margin:0;text-align:left;vertical-align:top;word-wrap:break-word">
                                                                                                    <table align="center" bgcolor="#0080a1" border="0" cellpadding="0" cellspacing="0" style="background:#0080a1;background-color:#0080a1;border-collapse:collapse;border-spacing:0;display:table;padding:0;text-align:left;vertical-align:top;width:100%;max-width:680px">
                                                                                                        <tbody>
                                                                                                        <tr>
                                                                                                            <td align="left" style="border:none;padding:0;font-family:'Arial',Helvetica,sans-serif;font-size:16px;line-height:20px;background-color:#0080a1;color:#000" valign="top">
                                                                                                                <table style="background-color:#0080a1;border:none;border-collapse:collapse;border-color:#aaaaaa;border-spacing:0;color:#aaaaaa;font-family:'Arial',Helvetica,sans-serif;font-size:16px;padding:0;text-align:left;vertical-align:top;width:100%" width="100%" cellspacing="0" cellpadding="10" border="1">
                                                                                                                    <tbody>
                                                                                                                    <tr style="padding:0;text-align:left;vertical-align:top">
                                                                                                                        <td align="center" valign="middle" style="background-color:#0080a1;border-collapse:collapse!important;border:none;color:#0b7190;font-family:'Arial',Helvetica,sans-serif;font-size:16px;font-weight:400;line-height:1.3;margin:0;padding:0;text-align:left;vertical-align:middle;width:190px;word-wrap:break-word">
                                                                                                                            <table style="background-color:#0080a1;border:none;border-collapse:collapse;border-color:#aaaaaa;border-spacing:0;color:#aaaaaa;font-family:'Arial',Helvetica,sans-serif;font-size:16px;padding:0;text-align:left;vertical-align:top;width:100%" width="100%" cellspacing="0" cellpadding="10" border="1">
                                                                                                                                <tbody>
                                                                                                                                <tr style="padding:0;text-align:left;vertical-align:top">
                                                                                                                                    <td align="center" valign="middle" style="background-color:#0080a1;border-collapse:collapse!important;border:none;color:#0b7190;font-family:'Arial',Helvetica,sans-serif;font-size:16px;font-weight:400;line-height:1.3;margin:0;padding:0;text-align:right;vertical-align:middle;word-wrap:break-word;width:35px">
                                                                                                                                        <a href="https://hanvietair.com/" target="_blank">
  <span>
  <img src="https://raw.githubusercontent.com/Sontome/icon/main/logohva.png"
       width="35"
       height="35"
       style="border-radius:11px; display:block;"
       alt="">
</span>
                                                                                                                                    </a></td>
                                                                                                                                    <td align="center" valign="middle" style="background-color:#0080a1;border-collapse:collapse!important;border:none;color:#fefefe;font-family:'Arial',Helvetica,sans-serif;font-size:10px;font-weight:400;line-height:1.3;margin:0;padding:0 0 0 10px;text-align:left;vertical-align:middle;word-wrap:break-word">
                                                                                                                                        <p style="margin:0;padding:0">
                                                                                                                                            <strong>HANVIETAIR</strong>
                                                                                                                                                                                                      
                                                                                                                                        </p>
                                                                                                                                    </td>
                                                                                                                                </tr>
                                                                                                                                </tbody>
                                                                                                                            </table>
                                                                                                                        </td>
                                                                                                                    </tr>
                                                                                                                    </tbody>
                                                                                                                </table>
                                                                                                            </td>
                                                                                                        </tr>
                                                                                                        </tbody>
                                                                                                    </table>
                                                                                                    <table style="border-collapse:collapse;border-spacing:0;padding:0;text-align:left;vertical-align:top;width:100%">
                                                                                                        <tbody>
                                                                                                        <tr style="padding:0;text-align:left;vertical-align:top">
                                                                                                            <td height="10" style="border-collapse:collapse!important;color:#0a0a0a;font-family:'Arial',Helvetica,sans-serif;font-size:10px;font-weight:400;line-height:10px;margin:0;padding:0;text-align:left;vertical-align:top;word-wrap:break-word">
                                                                                                                &nbsp;
                                                                                                            </td>
                                                                                                        </tr>
                                                                                                        </tbody>
                                                                                                    </table>
                                                                                                    <table align="center" bgcolor="#0080a1" border="0" cellpadding="0" cellspacing="0" style="background:#0080a1;background-color:#0080a1;border-collapse:collapse;border-spacing:0;display:table;padding:0;text-align:left;vertical-align:top;width:100%;max-width:680px">
                                                                                                        <tbody>
                                                                                                        <tr>
                                                                                                            <td style="color:#0a0a0a;font-family:'Arial',Helvetica,sans-serif;font-size:16px;font-weight:400;line-height:1.3;margin:0;padding:0;text-align:center">
                                                                                                                <p style="color:#0a0a0a;font-family:'Arial',Helvetica,sans-serif;font-size:13px;font-weight:400;line-height:1.3;margin:0;padding:0;text-align:left"><a href="https://www.facebook.com/HanVietAirCom/" target="_blank">
                                                                                                                    <img src="https://ci3.googleusercontent.com/meips/ADKq_NZF98G0OL3BgI_lLy3SD4FqSzJSDsmupkdcXznapwH3sleGeaIXEuc3eNJ-VEffbUtaI9L7xSYBzmi-2VheH0f1IiJRNrVmLzDvUHSO6JHg2jEmKah9ngBl5vNIPV5hufYPPfv-X_lkRnlooWbrttZoapaOmmBYJesUgdI=s0-d-e1-ft#https://enewsletter-vietnamairlines.com/html/email/y22/220624_ec_Template/assets/img/icon_facebook.png" alt="Facebook" style="border:none;clear:both;display:inline-block;width:30px;height:auto;max-width:100%;outline:none;text-decoration:none;vertical-align:middle" class="CToWUd" data-bit="iit"></a>&nbsp;
                                                                                                                    <a href="https://www.youtube.com/@hanvietair" target="_blank"><img src="https://ci3.googleusercontent.com/meips/ADKq_Na4-hoPnWQukd_g0neyj2w5euiGD2wehAE9aOa9KipZ5Az8ZHoEn6zl-k5M0dvDTgNLCaUmho6isbYaElcgKpYZFIRykxsmi9erqsaOdelgvOrt9GuDtDjI5-dN5RKgf2jEtOTPkom37sKCDZRa5Ab_paq1W82fFVWPGw=s0-d-e1-ft#https://enewsletter-vietnamairlines.com/html/email/y22/220624_ec_Template/assets/img/icon_youtube.png" alt="Youtube" style="border:none;clear:both;display:inline-block;width:30px;height:auto;max-width:100%;outline:none;text-decoration:none;vertical-align:middle" class="CToWUd" data-bit="iit"></a>&nbsp;
                                                                                                                    <a href="https://www.instagram.com/hanvietaircom/" target="_blank"><img src="https://ci3.googleusercontent.com/meips/ADKq_NbOGdSzvHATRVEfjQsKK4Foe8vD3qchotcH4bpkVGwILnQk9qY95623oRpY-SJX9i9Z7knxEaCai3cbETjLiTrNntfpTUh9Z5-3yYKuTOvP3l7M4mH4HHp8vGn5hum9kvJWTOFv4-5T3kD0tovZsFClvrYZUiLJ0nMpGLVg=s0-d-e1-ft#https://enewsletter-vietnamairlines.com/html/email/y22/220624_ec_Template/assets/img/icon_instagram.png" alt="Youtube" style="border:none;clear:both;display:inline-block;width:30px;height:auto;max-width:100%;outline:none;text-decoration:none;vertical-align:middle" class="CToWUd" data-bit="iit"></a>&nbsp;
                                                                                                                    <a href="https://www.tiktok.com/@hanvietair" target="_blank"><img src="https://raw.githubusercontent.com/Sontome/icon/main/tiktok.png"
     alt="TikTok"
     width="30"
     height="30"
     style="
       box-sizing:border-box;
       padding:5px;
       border-radius:50%;
       border:1px solid #ffffff;
       background:transparent;
       display:inline-block;
       vertical-align:middle;
     "></a>
                                                                                                                </p>
                                                                                                            </td>
                                                                                                        </tr>
                                                                                                        </tbody>
                                                                                                    </table>
                                                                                                </td>
                                                                                                <td style="border-collapse:collapse!important;color:#0a0a0a;font-family:'Arial',Helvetica,sans-serif;font-size:10px;font-weight:400;padding-left:20px;padding-right:20px;line-height:10px;margin:0;text-align:left;vertical-align:top;word-wrap:break-word">
                                                                                                    <table align="center" bgcolor="#0080a1" border="0" cellpadding="0" cellspacing="0" style="background:#0080a1;background-color:#0080a1;border-collapse:collapse;border-spacing:0;display:table;padding:0;text-align:left;vertical-align:top;width:100%;max-width:680px">
                                                                                                        <tbody>
                                                                                                        <tr>
                                                                                                            <td style="color:#0a0a0a;font-family:'Arial',Helvetica,sans-serif;font-size:12px;font-weight:400;line-height:1.3;margin:0;padding:0;text-align:center">
                                                                                                                <p style="color:#feffff;font-family:'Arial',Helvetica,sans-serif;font-size:12px;font-weight:400;line-height:1.4;margin:0;margin-top:0;margin-bottom:0;padding:0;text-align:left">
                                                                                                                    Đặt
                                                                                                                    vé
                                                                                                                    ngay
                                                                                                                    tại:
                                                                                                                    <a href="https://hanvietair.com/vi" target="_blank"> https://hanvietair.com </a>
                                                                                                                </p>
                                                                                                                <table style="border-collapse:collapse;border-spacing:0;padding:0;text-align:left;vertical-align:top;width:100%">
                                                                                                                    <tbody>
                                                                                                                    <tr style="padding:0;text-align:left;vertical-align:top">
                                                                                                                        <td height="5px" style="Margin:0;border-collapse:collapse!important;color:#0a0a0a;font-family:'Arial',Helvetica,sans-serif;font-size:5px;font-weight:400;line-height:5px;margin:0;padding:0;text-align:left;vertical-align:top;word-wrap:break-word">
                                                                                                                            &nbsp;
                                                                                                                        </td>
                                                                                                                    </tr>
                                                                                                                    </tbody>
                                                                                                                </table>
                                                                                                                <p style="color:#feffff;font-family:'Arial',Helvetica,sans-serif;font-size:12px;font-weight:400;line-height:1.4;margin:0;margin-bottom:0;padding:0;text-align:left">Tổng đài:
                                                                                                                   
                                                                                                                    <strong> 070-3546-3396
                                                                                                                   </strong>
                                                                                                                </p>
                                                                                                                <table style="border-collapse:collapse;border-spacing:0;padding:0;text-align:left;vertical-align:top;width:100%">
                                                                                                                    <tbody>
                                                                                                                    <tr style="padding:0;text-align:left;vertical-align:top">
                                                                                                                        <td height="5px" style="Margin:0;border-collapse:collapse!important;color:#0a0a0a;font-family:'Arial',Helvetica,sans-serif;font-size:5px;font-weight:400;line-height:5px;margin:0;padding:0;text-align:left;vertical-align:top;word-wrap:break-word">
                                                                                                                            &nbsp;
                                                                                                                        </td>
                                                                                                                    </tr>
                                                                                                                    </tbody>
                                                                                                                </table>
                                                                                                                <p style="color:#feffff;font-family:'Arial',Helvetica,sans-serif;font-size:12px;font-weight:400;line-height:1.4;margin:0;margin-bottom:0;padding:0;text-align:left">
                                                                                                                    Hotline:
                                                                                                                    <strong> 010-3546-3396
                                                                                                                        </strong>
                                                                                                                </p>
                                                                                                                <table style="border-collapse:collapse;border-spacing:0;padding:0;text-align:left;vertical-align:top;width:100%">
                                                                                                                    <tbody>
                                                                                                                    <tr style="padding:0;text-align:left;vertical-align:top">
                                                                                                                        <td height="5px" style="Margin:0;border-collapse:collapse!important;color:#0a0a0a;font-family:'Arial',Helvetica,sans-serif;font-size:5px;font-weight:400;line-height:5px;margin:0;padding:0;text-align:left;vertical-align:top;word-wrap:break-word">
                                                                                                                            &nbsp;
                                                                                                                        </td>
                                                                                                                    </tr>
                                                                                                                    </tbody>
                                                                                                                </table>
                                                                                                                <p style="color:#feffff;font-family:'Arial',Helvetica,sans-serif;font-size:12px;font-weight:400;line-height:1.4;margin:0;margin-bottom:0;padding:0;text-align:left">
                                                                                                                    Email:
                                                                                                                    <strong>Hanvietair@gmail.com
                                                                                                                        
                                                                                                                        </strong>
                                                                                                                </p>
                                                                                                            </td>
                                                                                                        </tr>
                                                                                                        </tbody>
                                                                                                    </table>
                                                                                                </td>
                                                                                                <td align="center" valign="top">
                                                                                                    <table align="center" border="0" cellpadding="0" cellspacing="0" width="100%">
                                                                                                        <tbody>
                                                                                                        <tr>
                                                                                                            <td style="text-align:center" valign="top">
                                                                                                                <a href="#m_6655506731917057407_m_-5242890253129022313_" style="color:#ffffff;font-family:'Arial',Helvetica,sans-serif;font-weight:400;font-size:10px;line-height:1.3;margin:0;margin-bottom:20px;padding:0;text-align:center;text-decoration:none"><span>
                                                                        <img src="https://ci3.googleusercontent.com/meips/ADKq_NbtXXX7ecC_BhFL_dLKs_Vb9WBVFR8oCQR4Jw2qVtSGUW0Vt_WYQVvo3fWwvLS8HctrP9OUbwjM_JEsAoalA6Sv18udpk5v0HKk8ySl4jzf8CXN2FeVMzMkLXqXkcPUp2nM5RAnj1y4h-Zl60LWLbi9A5uowqM=s0-d-e1-ft#https://enewsletter-vietnamairlines.com/html/email/y22/220624_ec_Template/assets/img/icon_dl.png" alt="" width="15" height="14" class="CToWUd" data-bit="iit">&nbsp;</span>TẢI
                                                                                                                    APP
                                                                                                                    NGAY</a>
                                                                                                                <table style="border-collapse:collapse;border-spacing:0;padding:0;text-align:left;vertical-align:top;width:100%">
                                                                                                                    <tbody>
                                                                                                                    <tr style="padding:0;text-align:left;vertical-align:top">
                                                                                                                        <td height="5px" style="border-collapse:collapse!important;color:#0a0a0a;font-family:'Arial',Helvetica,sans-serif;font-size:10px;font-weight:400;line-height:5px;margin:0;padding:0;text-align:left;vertical-align:top;word-wrap:break-word">
                                                                                                                            &nbsp;
                                                                                                                        </td>
                                                                                                                    </tr>
                                                                                                                    </tbody>
                                                                                                                </table>
                                                                                                                <a href="https://apps.apple.com/us/app/hanvietair/id6756371831"
   target="_blank"
   data-clicktracking="off">
                                                                                                                    <img src="https://ci3.googleusercontent.com/meips/ADKq_Nbs5XVidQ6HnjEz88U-fiGCvgpitwOKdxnRh15G8nQU2sXNik3ObZEQxyYCp25r-JnfQeVL_SddHQ9muKNF5Dd1aNMWAZHcSrSXCs48TYJK8Jln7b13TzX8xsDsXHAcbAiKQmQxCgh6p2yfyX1osczCrYFTRtg=s0-d-e1-ft#http://enewsletter-vietnamairlines.com/html/email/y22/220624_ec_Template/assets/img/icon_ios.png" alt="IOS" style="border:none;clear:both;display:inline-block;max-width:100%;outline:none;text-decoration:none;vertical-align:middle;width:87px;margin:0;padding:0" class="CToWUd" data-bit="iit"></a>
                                                                                                                <table style="border-collapse:collapse;border-spacing:0;padding:0;text-align:left;vertical-align:top;width:100%">
                                                                                                                    <tbody>
                                                                                                                    <tr style="padding:0;text-align:left;vertical-align:top">
                                                                                                                        <td height="3px" style="border-collapse:collapse!important;color:#0a0a0a;font-family:'Arial',Helvetica,sans-serif;font-size:10px;font-weight:400;line-height:3px;margin:0;padding:0;text-align:left;vertical-align:top;word-wrap:break-word">
                                                                                                                            &nbsp;
                                                                                                                        </td>
                                                                                                                    </tr>
                                                                                                                    </tbody>
                                                                                                                </table>
                                                                                                                <a href="https://play.google.com/store/apps/details?id=com.hanvietairapp&hl=vi"
   target="_blank"
   data-clicktracking="off">
                                                                                                                    <img src="https://ci3.googleusercontent.com/meips/ADKq_NZxpUGGJU6FDB-OLSb_fBcXdyHsuN0uHkqwdmJGSgpPtrcmyfVDK-K_aX3sd8KQUnFBevOYkKRx18oxzHCU2PrP37QQbG7JVYo9E-Ywzndl0PFY7rMLTh6lT1Xnb99LI1ECuvhyV7tJDG8k4KgbtYlkgMV6BM0hAI8l=s0-d-e1-ft#http://enewsletter-vietnamairlines.com/html/email/y22/220624_ec_Template/assets/img/icon_android.png" alt="Android" style="border:none;clear:both;display:inline-block;max-width:100%;outline:none;text-decoration:none;vertical-align:middle;width:87px;margin:0;padding:0" class="CToWUd" data-bit="iit"></a>
                                                                                                                <table style="border-collapse:collapse;border-spacing:0;padding:0;text-align:left;vertical-align:top;width:100%">
                                                                                                                    <tbody>
                                                                                                                    <tr style="padding:0;text-align:left;vertical-align:top">
                                                                                                                        <td height="15px" style="border-collapse:collapse!important;color:#0a0a0a;font-family:'Arial',Helvetica,sans-serif;font-size:10px;font-weight:400;line-height:15px;margin:0;padding:0;text-align:left;vertical-align:top;word-wrap:break-word">
                                                                                                                            &nbsp;
                                                                                                                        </td>
                                                                                                                    </tr>
                                                                                                                    </tbody>
                                                                                                                </table>
                                                                                                            </td>
                                                                                                        </tr>
                                                                                                        </tbody>
                                                                                                    </table>
                                                                                                </td>
                                                                                            </tr>
                                                                                            </tbody>
                                                                                        </table>

                                                                                        <table style="border-collapse:collapse;border-spacing:0;padding:0;text-align:left;vertical-align:top;width:100%">
                                                                                            <tbody>
                                                                                            <tr style="padding:0;text-align:left;vertical-align:top">
                                                                                                <td style="border-collapse:collapse!important;color:#0a0a0a;font-family:'Arial',Helvetica,sans-serif;font-size:10px;font-weight:400;line-height:10px;margin:0;text-align:left;vertical-align:top;word-wrap:break-word">
                                                                                                    <table style="border-collapse:collapse;border-spacing:0;padding:0;text-align:left;vertical-align:top;width:100%">
                                                                                                        <tbody>
                                                                                                        <tr style="padding:0;text-align:left;vertical-align:top">
                                                                                                            <td height="30px" style="border-collapse:collapse!important;color:#0a0a0a;font-family:'Arial',Helvetica,sans-serif;font-size:10px;font-weight:400;line-height:30px;margin:0;padding:0;text-align:left;vertical-align:top;word-wrap:break-word;border-bottom:1px solid #7cb3c1">
                                                                                                                &nbsp;
                                                                                                            </td>
                                                                                                        </tr>
                                                                                                        </tbody>
                                                                                                    </table>
                                                                                                    <table style="border-collapse:collapse;border-spacing:0;padding:0;text-align:left;vertical-align:top;width:100%">
                                                                                                        <tbody>
                                                                                                        <tr style="padding:0;text-align:left;vertical-align:top">
                                                                                                            <td height="20px" style="border-collapse:collapse!important;color:#0a0a0a;font-family:'Arial',Helvetica,sans-serif;font-size:10px;font-weight:400;line-height:20px;margin:0;padding:0;text-align:left;vertical-align:top;word-wrap:break-word">
                                                                                                                &nbsp;
                                                                                                            </td>
                                                                                                        </tr>
                                                                                                        </tbody>
                                                                                                    </table>
                                                                                                    <p style="color:#feffff;font-family:'Arial',Helvetica,sans-serif;font-size:13px;font-weight:400;line-height:1.4;margin:0;margin-bottom:0;padding:0;text-align:center">
                                                                                                        <span style="border-right:1px solid #4f9cc6;color:#feffff;font-family:'Arial',Helvetica,sans-serif;font-weight:400;line-height:1.3;margin:0;padding:0 10px 0 5px;text-align:left;text-decoration:none">© 2026 HANVIETAIR</span>
                                                                                                       
                                                                                                    </p>
                                                                                                    <table style="border-collapse:collapse;border-spacing:0;padding:0;text-align:left;vertical-align:top;width:100%">
                                                                                                        <tbody>
                                                                                                        <tr style="padding:0;text-align:left;vertical-align:top">
                                                                                                            <td height="20px" style="border-collapse:collapse!important;color:#0a0a0a;font-family:'Arial',Helvetica,sans-serif;font-size:10px;font-weight:400;line-height:20px;margin:0;padding:0;text-align:left;vertical-align:top;word-wrap:break-word">
                                                                                                                &nbsp;
                                                                                                            </td>
                                                                                                        </tr>
                                                                                                        </tbody>
                                                                                                    </table>
                                                                                                </td>
                                                                                            </tr>
                                                                                            </tbody>
                                                                                        </table>
                                                                                    </th>
                                                                                    <th style="color:#0a0a0a;font-family:'Arial',Helvetica,sans-serif;font-size:16px;font-weight:400;line-height:1.3;margin:0;padding:0!important;text-align:left;width:0"></th>
                                                                                </tr>
                                                                            </tbody></table>
                                                                        </th>
                                                                    </tr>
                                                                    </tbody>
                                                                </table>
                                                            </td>
                                                        </tr>
                                                        </tbody>
                                                    </table>
                                                </th>
                                            </tr>
                                        </tbody></table>
                                    </th>
                                </tr>
                                </tbody>
                            </table>
                        </td>
                    </tr>
                    </tbody>
                </table>
                <table style="border-collapse:collapse;border-spacing:0;float:none;margin:0 auto;padding:0;text-align:center;vertical-align:top;width:100%">
                    <tbody>
                    <tr style="padding:0;text-align:left;vertical-align:top">
                        <td height="50px" style="border-collapse:collapse!important;color:#0a0a0a;font-family:'Arial',Helvetica,sans-serif;font-size:50px;font-weight:400;line-height:50px;margin:0;padding:0;text-align:left;vertical-align:top;word-wrap:break-word">
                            &nbsp;
                        </td>
                    </tr>
                    </tbody>
                </table>
            </center>
        </td>
    </tr>
</tbody></table>


<div style="display:none;white-space:nowrap;font:15px courier;line-height:0">
    &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp;
    &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp;
    &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp;
</div>
</div>
        """









# -----------------------------------------------------------------------------------------------------------------


        bodyVJ = f"""
            <div style="background-color:#efefef;background-color:#efefef;box-sizing:border-box;color:#0a0a0a;font-family:'Arial',Helvetica,sans-serif;font-size:16px;font-weight:400;line-height:1.3;margin:0 auto;max-width:960px;min-width:100%;padding:0;text-align:left;width:100%!important">
<span style="color:#efefef;display:none!important;font-size:1px;line-height:1px;max-height:0px;max-width:0px;opacity:0;overflow:hidden"></span>
<table style="background:none;border-collapse:collapse;border-spacing:0;color:#0a0a0a;font-family:'Arial',Helvetica,sans-serif;font-size:16px;font-weight:400;height:100%;line-height:1.3;margin:0;padding:0;text-align:left;vertical-align:top;width:100%">
    <tbody><tr style="padding:0;text-align:left;vertical-align:top">
        <td align="center" valign="top" style="border-collapse:collapse!important;color:#0a0a0a;font-family:'Arial',Helvetica,sans-serif;font-size:16px;font-weight:400;line-height:1.3;margin:0;padding:0;text-align:left;vertical-align:top;word-wrap:break-word">
            <center style="min-width:680px;width:100%">
               
                <table align="center" style="border-radius:15px;overflow:hidden;background:#006883;background-color:#006883;border-collapse:collapse;border-spacing:0;float:none;margin:0 auto;padding:0;text-align:center;vertical-align:top;width:680px;max-width:680px">
                    <tbody>
                    <tr style="padding:0;text-align:left;vertical-align:top">
                        <td style="border-collapse:collapse!important;color:#0a0a0a;font-family:'Arial',Helvetica,sans-serif;font-size:16px;font-weight:400;line-height:1.3;margin:0;padding:0;text-align:left;vertical-align:top;word-wrap:break-word">
                            <table style="border-collapse:collapse;border-spacing:0;display:table;padding:0;text-align:left;vertical-align:top;width:100%">
                                <tbody>
                                <tr style="padding:0;text-align:left;vertical-align:top">
                                    <th style="color:#0a0a0a;font-family:'Arial',Helvetica,sans-serif;font-size:16px;font-weight:400;line-height:1.3;margin:0 auto;padding:0;padding-bottom:0;padding-left:0;padding-right:0;text-align:left;width:680px">
                                        <table style="border-collapse:collapse;border-spacing:0;padding:0;text-align:left;vertical-align:top;width:100%">
                                            <tbody><tr style="padding:0;text-align:left;vertical-align:top">
                                                <th style="color:#0a0a0a;font-family:'Arial',Helvetica,sans-serif;font-size:16px;font-weight:400;line-height:1.3;margin:0;padding:0;padding-bottom:0;text-align:left">
                                                    <table align="center" style="background:#d52b2b;background-color:#d52b2b;border-collapse:collapse;border-spacing:0;margin:0 auto;padding:0;text-align:inherit;vertical-align:top;width:100%">
                                                        <tbody>
                                                        <tr style="padding:0;text-align:left;vertical-align:top">
                                                            <td style="border-collapse:collapse!important;color:#0a0a0a;font-family:'Arial',Helvetica,sans-serif;font-size:16px;font-weight:400;line-height:1.3;margin:0;padding:0;text-align:left;vertical-align:top;word-wrap:break-word">
                                                                <table style="border-collapse:collapse;border-spacing:0;display:table;padding:0;text-align:left;vertical-align:top;width:100%">
                                                                    <tbody>
                                                                    <tr style="padding:0;text-align:left;vertical-align:top">
                                                                        <th style="color:#0a0a0a;font-family:'Arial',Helvetica,sans-serif;font-size:16px;font-weight:400;line-height:1.3;margin:0 auto 20px;padding:0;padding-bottom:0;padding-left:0!important;padding-right:0!important;text-align:left;width:50%">
                                                                            <table style="border-collapse:collapse;border-spacing:0;padding:0;text-align:left;vertical-align:top;width:100%">
                                                                                <tbody><tr style="padding:0;text-align:left;vertical-align:top">
                                                                                    <th style="color:#0a0a0a;font-family:'Arial',Helvetica,sans-serif;font-size:16px;font-weight:400;line-height:1.3;margin:0;padding:0;padding-bottom:0;text-align:left">
                                                                                        <table style="border-collapse:collapse;border-spacing:0;padding:0;text-align:left;vertical-align:top;width:100%">
                                                                                            <tbody>
                                                                                            <tr style="padding:0;text-align:left;vertical-align:top">
                                                                                                <td height="15px" style="border-collapse:collapse!important;color:#0a0a0a;font-family:'Arial',Helvetica,sans-serif;font-size:15px;font-weight:400;line-height:15px;margin:0;padding:0;text-align:left;vertical-align:top;word-wrap:break-word">
                                                                                                    &nbsp;
                                                                                                </td>
                                                                                            </tr>
                                                                                            </tbody>
                                                                                        </table>
                                                                                        <table align="center" style="border-collapse:collapse;border-spacing:0;padding:0;vertical-align:top;width:100%">
                                                                                            <tbody>
                                                                                            <tr>
                                                                                                <td valign="middle" width="50%">
                                                                                                    <table align="center" border="0" cellpadding="0" cellspacing="0" width="100%">
                                                                                                        <tbody>
                                                                                                        <tr>
                                                                                                            <td valign="middle">
                                                                                                                <center style="min-width:590px;width:100%">
                                                                                                                    <img src="https://raw.githubusercontent.com/Sontome/icon/main/logoVJ.png" alt="Logo" style="clear:both;display:block;width:224px;max-width:25%;outline:none;text-decoration:none;text-align:left;margin:0" class="CToWUd" data-bit="iit">
                                                                                                                </center>
                                                                                                            </td>
                                                                                                        </tr>
                                                                                                        </tbody>
                                                                                                    </table>
                                                                                                </td>
                                                                                            </tr>
                                                                                            </tbody>
                                                                                        </table>
                                                                                        <table style="border-collapse:collapse;border-spacing:0;padding:0;text-align:left;vertical-align:top;width:100%">
                                                                                            <tbody>
                                                                                            <tr style="padding:0;text-align:left;vertical-align:top">
                                                                                                <td height="15px" style="border-collapse:collapse!important;color:#0a0a0a;font-family:'Arial',Helvetica,sans-serif;font-size:15px;font-weight:400;line-height:15px;margin:0;padding:0;text-align:left;vertical-align:top;word-wrap:break-word">
                                                                                                    &nbsp;
                                                                                                </td>
                                                                                            </tr>
                                                                                            </tbody>
                                                                                        </table>
                                                                                    </th>
                                                                                </tr>
                                                                            </tbody></table>
                                                                        </th>
                                                                    </tr>
                                                                    </tbody>
                                                                </table>
                                                            </td>
                                                        </tr>
                                                        </tbody>
                                                    </table>
                                                </th>
                                            </tr>
                                        </tbody></table>
                                    </th>
                                </tr>
                                </tbody>
                            </table>

                            <table style="border-collapse:collapse;border-spacing:0;display:table;padding:0;text-align:left;vertical-align:top;width:100%;background-color:#1c3144">
                                <tbody>
                                <tr style="padding:0;text-align:left;vertical-align:top">
                                    <th style="color:#0a0a0a;font-family:'Arial',Helvetica,sans-serif;font-size:16px;font-weight:400;line-height:1.3;margin:0 auto;padding:0;padding-bottom:0;padding-left:0;padding-right:0;text-align:left;width:630px">
                                        <table style="border-collapse:collapse;border-spacing:0;padding:0;text-align:left;vertical-align:top;width:100%">
                                            <tbody><tr style="padding:0;text-align:left;vertical-align:top">
                                                <th style="color:#0a0a0a;font-family:'Arial',Helvetica,sans-serif;font-size:16px;font-weight:400;line-height:1.3;margin:0;padding:0;text-align:left">
                                                    <table align="center" style="background:#fff;background-color:#fff;border-collapse:collapse;border-spacing:0;margin:0 auto;padding:0;text-align:inherit;vertical-align:top;width:100%">
                                                        <tbody>
                                                        <tr style="padding:0;text-align:left;vertical-align:top">
                                                            <td style="border-collapse:collapse!important;color:#0a0a0a;font-family:'Arial',Helvetica,sans-serif;font-size:16px;font-weight:400;line-height:1.3;margin:0;padding:0;text-align:left;vertical-align:top;word-wrap:break-word">
                                                                <center style="min-width:590px;width:100%">
                                                                    <img src="https://raw.githubusercontent.com/Sontome/icon/main/banner_vj_mail.jpg" alt="" align="center" style="clear:both;display:block;float:none;margin:0 auto;width:100%;max-width:100%;height:auto;outline:none;text-align:center;text-decoration:none" width="681" height="406" class="CToWUd a6T" data-bit="iit" tabindex="0"><div class="a6S" dir="ltr" style="opacity: 0.01; left: 838.8px; top: 717.5px;"><span data-is-tooltip-wrapper="true" class="a5q" jsaction="JIbuQc:.CLIENT"><button class="VYBDae-JX-I VYBDae-JX-I-ql-ay5-ays CgzRE" jscontroller="PIVayb" jsaction="click:h5M12e;clickmod:h5M12e;pointerdown:FEiYhc;pointerup:mF5Elf;pointerenter:EX0mI;pointerleave:vpvbp;pointercancel:xyn4sd;contextmenu:xexox;focus:h06R8; blur:zjh6rb;mlnRJb:fLiPzd;" data-idom-class="CgzRE" data-use-native-focus-logic="true" jsname="hRZeKc" aria-label="Tải xuống tệp đính kèm " data-tooltip-enabled="true" data-tooltip-id="tt-c9" data-tooltip-classes="AZPksf" id="" jslog="91252; u014N:cOuCgd,Kr2w4b,xr6bB; 4:WyIjbXNnLWY6MTg1NDgyNzQ5OTI1NjIyODk0NyJd; 43:WyJpbWFnZS9qcGVnIl0."><span class="XjoK4b VYBDae-JX-UHGRz"></span><span class="UTNHae" jscontroller="LBaJxb" jsname="m9ZlFb" soy-skip="" ssk="6:RWVI5c"></span><span class="VYBDae-JX-ank-Rtc0Jf" jsname="S5tZuc" aria-hidden="true"><span class="notranslate bzc-ank" aria-hidden="true"><svg viewBox="0 -960 960 960" height="20" width="20" focusable="false" class=" aoH"><path d="M480-336L288-528l51-51L444-474V-816h72v342L621-579l51,51L480-336ZM263.72-192Q234-192 213-213.15T192-264v-72h72v72H696v-72h72v72q0,29.7-21.16,50.85T695.96-192H263.72Z"></path></svg></span></span><div class="VYBDae-JX-ano"></div></button></span></div>
                                                                </center>
                                                            </td>
                                                        </tr>
                                                        </tbody>
                                                    </table>
                                                </th>
                                            </tr>
                                        </tbody></table>
                                    </th>
                                </tr>
                                </tbody>
                            </table>

                            <table style="border-collapse:collapse;border-spacing:0;display:table;padding:0;text-align:left;vertical-align:top;width:100%;background-color:#fff">
                                <tbody>
                                <tr style="padding:0;text-align:left;vertical-align:top">
                                    <th style="color:#0a0a0a;font-family:'Arial',Helvetica,sans-serif;font-size:16px;font-weight:400;line-height:1.3;margin:0 auto;padding:0;padding-bottom:0;padding-left:0;padding-right:0;text-align:left;width:630px">
                                        <table style="border-collapse:collapse;border-spacing:0;padding:0;text-align:left;vertical-align:top;width:100%">
                                            <tbody><tr style="padding:0;text-align:left;vertical-align:top">
                                                <th style="color:#0a0a0a;font-family:'Arial',Helvetica,sans-serif;font-size:16px;font-weight:400;line-height:1.3;margin:0;padding:0;text-align:left">
                                                    <table style="border-collapse:collapse;border-spacing:0;display:table;padding:0;text-align:left;vertical-align:top;width:100%">
                                                        <tbody>
                                                        <tr style="padding:0;text-align:left;vertical-align:top">
                                                            <th style="color:#0a0a0a;font-family:'Arial',Helvetica,sans-serif;font-size:16px;font-weight:400;line-height:1.3;margin:0 auto;padding:0;padding-left:35px;padding-right:35px;text-align:left;width:100%">
                                                                <table style="border-collapse:collapse;border-spacing:0;padding:0;text-align:left;vertical-align:top;width:100%">
                                                                    <tbody><tr style="padding:0;text-align:left;vertical-align:top">
                                                                        <th style="color:#000000;font-family:'Arial',Helvetica,sans-serif;font-size:16px;font-weight:400;line-height:1.3;margin:0;padding:0;text-align:left">
                                                                            <table style="border-collapse:collapse;border-spacing:0;display:none;padding:0;text-align:left;vertical-align:top;width:100%">
                                                                                <tbody>
                                                                                <tr style="padding:0;text-align:left;vertical-align:top">
                                                                                    <td height="50" style="margin:0;border-collapse:collapse!important;color:#0a0a0a;font-family:'Arial',Helvetica,sans-serif;font-size:5px;font-weight:normal;line-height:50px;margin:0;padding:0;text-align:left;vertical-align:top;word-wrap:break-word">
                                                                                        &nbsp;
                                                                                    </td>
                                                                                </tr>
                                                                                </tbody>
                                                                            </table>
                                                                            <table style="border-collapse:collapse;border-spacing:0;padding:0;text-align:left;vertical-align:top;width:100%">
                                                                                <tbody>
                                                                                <tr style="padding:0;text-align:left;vertical-align:top">
                                                                                    <td height="50" style="border-collapse:collapse!important;color:#0a0a0a;font-family:'Arial',Helvetica,sans-serif;font-size:10px;font-weight:normal;line-height:50px;margin:0;padding:0;text-align:left;vertical-align:top;word-wrap:break-word">
                                                                                        &nbsp;
                                                                                    </td>
                                                                                </tr>
                                                                                </tbody>
                                                                            </table>
                                                                            <p><strong>Chào {salutation} {customer_name},</strong></p>
<p>Hanvietair xin gửi {salutation} vé điện tử xác nhận hành trình như ảnh đính kèm.</p>
<p>Có thắc mắc gì, {salutation} vui lòng liên hệ với Hanvietair để được giải đáp.</p>
<p>Chúc {salutation} thượng lộ bình an.</p><br>

<p>Xin trân trọng cảm ơn Quý khách đã lựa chọn sử dụng dịch vụ của Hanvietair.</p>
                                                                            <table style="border-collapse:collapse;border-spacing:0;display:none;padding:0;text-align:left;vertical-align:top;width:100%">
                                                                                <tbody>
                                                                                <tr style="padding:0;text-align:left;vertical-align:top">
                                                                                    <td height="30px" style="Margin:0;border-collapse:collapse!important;color:#0a0a0a;font-family:'Arial',Helvetica,sans-serif;font-size:5px;font-weight:normal;line-height:30px;margin:0;padding:0;text-align:left;vertical-align:top;word-wrap:break-word">
                                                                                        &nbsp;
                                                                                    </td>
                                                                                </tr>
                                                                                </tbody>
                                                                            </table>
                                                                            <table style="border-collapse:collapse;border-spacing:0;padding:0;text-align:left;vertical-align:top;width:100%">
                                                                                <tbody>
                                                                                <tr style="padding:0;text-align:left;vertical-align:top">
                                                                                    <td height="30px" style="border-collapse:collapse!important;color:#0a0a0a;font-family:'Arial',Helvetica,sans-serif;font-size:10px;font-weight:normal;line-height:30px;margin:0;padding:0;text-align:left;vertical-align:top;word-wrap:break-word">
                                                                                        &nbsp;
                                                                                    </td>
                                                                                </tr>
                                                                                </tbody>
                                                                            </table>
                                                                            <p style="color:#0d6981;font-family:'Arial',Helvetica,sans-serif;font-size:14px;font-weight:300;line-height:24px;margin:0;margin-bottom:0;padding:0;text-align:center">
                                                                            Vui lòng nhấn vào liên kết dưới đây để xem các ưu đãi của Hanvietair&nbsp;<a href="https://hanvietair.com/" target="_blank">
  https://hanvietair.com/
</a>.
                                                                            </p>
                                                                            <table style="border-collapse:collapse;border-spacing:0;display:none;padding:0;text-align:left;vertical-align:top;width:100%">
                                                                                <tbody>
                                                                                <tr style="padding:0;text-align:left;vertical-align:top">
                                                                                    <td height="20" style="margin:0;border-collapse:collapse!important;color:#0a0a0a;font-family:'Arial',Helvetica,sans-serif;font-size:5px;font-weight:normal;line-height:20px;margin:0;padding:0;text-align:left;vertical-align:top;word-wrap:break-word">
                                                                                        &nbsp;
                                                                                    </td>
                                                                                </tr>
                                                                                </tbody>
                                                                            </table>
                                                                            <table style="border-collapse:collapse;border-spacing:0;padding:0;text-align:left;vertical-align:top;width:100%">
                                                                                <tbody>
                                                                                <tr style="padding:0;text-align:left;vertical-align:top">
                                                                                    <td height="20" style="border-collapse:collapse!important;color:#0a0a0a;font-family:'Arial',Helvetica,sans-serif;font-size:10px;font-weight:normal;line-height:20px;margin:0;padding:0;text-align:left;vertical-align:top;word-wrap:break-word">
                                                                                        &nbsp;
                                                                                    </td>
                                                                                </tr>
                                                                                </tbody>
                                                                            </table>
                                                                        </th>
                                                                        <th style="color:#0a0a0a;font-family:'Arial',Helvetica,sans-serif;font-size:16px;font-weight:400;line-height:1.3;margin:0;padding:0!important;text-align:left;width:0"></th>
                                                                    </tr>
                                                                </tbody></table>
                                                            </th>
                                                        </tr>
                                                        </tbody>
                                                    </table>
                                                </th>
                                            </tr>
                                        </tbody></table>
                                    </th>
                                </tr>
                                </tbody>
                            </table>

                            <table style="background:#d52b2b;background-color:#d52b2b;border-collapse:collapse;border-spacing:0;display:table;padding:0;text-align:left;vertical-align:top;width:100%">
                                <tbody>
                                <tr style="padding:0;text-align:left;vertical-align:top">
                                    <th style="color:#0a0a0a;font-family:'Arial',Helvetica,sans-serif;font-size:13px;font-weight:400;line-height:1.3;margin:0 auto;padding:0;padding-bottom:0!important;padding-left:0;padding-right:0;text-align:left;width:680px">
                                        <table style="border-collapse:collapse;border-spacing:0;padding:0;text-align:left;vertical-align:top;width:100%">
                                            <tbody><tr style="padding:0;text-align:left;vertical-align:top">
                                                <th style="color:#0a0a0a;font-family:'Arial',Helvetica,sans-serif;font-size:13px;font-weight:400;line-height:1.3;margin:0;padding:0;text-align:left">
                                                    <table align="center" style="background:none;background-color:transparent;border-collapse:collapse;border-spacing:0;margin:0 auto;padding:0;text-align:inherit;vertical-align:top;width:100%">
                                                        <tbody>
                                                        <tr style="padding:0;text-align:left;vertical-align:top">
                                                            <td style="border-collapse:collapse!important;color:#0a0a0a;font-family:'Arial',Helvetica,sans-serif;font-size:13px;font-weight:400;line-height:1.3;margin:0;padding:0;text-align:left;vertical-align:top;word-wrap:break-word">
                                                                <table style="border-collapse:collapse;border-spacing:0;display:table;padding:0;text-align:left;vertical-align:top;width:100%">
                                                                    <tbody>
                                                                    <tr style="padding:0;text-align:left;vertical-align:top">
                                                                        <th style="color:#0a0a0a;font-family:'Arial',Helvetica,sans-serif;font-size:13px;font-weight:400;line-height:1.3;margin:0 auto;padding:0;padding-left:35px;padding-right:35px;text-align:left;width:100%">
                                                                            <table style="border-collapse:collapse;border-spacing:0;padding:0;text-align:left;vertical-align:top;width:100%">
                                                                                <tbody><tr style="padding:0;text-align:left;vertical-align:top">
                                                                                    <th style="color:#0a0a0a;font-family:'Arial',Helvetica,sans-serif;font-size:13px;font-weight:400;line-height:1.3;margin:0;padding:0;text-align:left">
                                                                                        <table style="border-collapse:collapse;border-spacing:0;padding:0;text-align:left;vertical-align:top;width:100%">
                                                                                            <tbody>
                                                                                            <tr style="padding:0;text-align:left;vertical-align:top">
                                                                                                <td height="50px" style="Margin:0;border-collapse:collapse!important;color:#0a0a0a;font-family:'Arial',Helvetica,sans-serif;font-size:5px;font-weight:400;line-height:50px;margin:0;padding:0;text-align:left;vertical-align:top;word-wrap:break-word">
                                                                                                    &nbsp;
                                                                                                </td>
                                                                                            </tr>
                                                                                            </tbody>
                                                                                        </table>
                                                                                        <table style="border-collapse:collapse;border-spacing:0;padding:0;text-align:left;vertical-align:top;width:100%">
                                                                                            <tbody>
                                                                                            <tr style="padding:0;text-align:left;vertical-align:top">
                                                                                                <td style="border-collapse:collapse!important;color:#0a0a0a;font-family:'Arial',Helvetica,sans-serif;font-size:10px;font-weight:400;line-height:10px;margin:0;text-align:left;vertical-align:top;word-wrap:break-word">
                                                                                                    <table align="center" bgcolor="#d52b2b" border="0" cellpadding="0" cellspacing="0" style="background:#d52b2b;background-color:#d52b2b;border-collapse:collapse;border-spacing:0;display:table;padding:0;text-align:left;vertical-align:top;width:100%;max-width:680px">
                                                                                                        <tbody>
                                                                                                        <tr>
                                                                                                            <td align="left" style="border:none;padding:0;font-family:'Arial',Helvetica,sans-serif;font-size:16px;line-height:20px;background-color:#d52b2b;color:#000" valign="top">
                                                                                                                <table style="background-color:#d52b2b;border:none;border-collapse:collapse;border-color:#aaaaaa;border-spacing:0;color:#aaaaaa;font-family:'Arial',Helvetica,sans-serif;font-size:16px;padding:0;text-align:left;vertical-align:top;width:100%" width="100%" cellspacing="0" cellpadding="10" border="1">
                                                                                                                    <tbody>
                                                                                                                    <tr style="padding:0;text-align:left;vertical-align:top">
                                                                                                                        <td align="center" valign="middle" style="background-color:#d52b2b;border-collapse:collapse!important;border:none;color:#0b7190;font-family:'Arial',Helvetica,sans-serif;font-size:16px;font-weight:400;line-height:1.3;margin:0;padding:0;text-align:left;vertical-align:middle;width:190px;word-wrap:break-word">
                                                                                                                            <table style="background-color:#d52b2b;border:none;border-collapse:collapse;border-color:#aaaaaa;border-spacing:0;color:#aaaaaa;font-family:'Arial',Helvetica,sans-serif;font-size:16px;padding:0;text-align:left;vertical-align:top;width:100%" width="100%" cellspacing="0" cellpadding="10" border="1">
                                                                                                                                <tbody>
                                                                                                                                <tr style="padding:0;text-align:left;vertical-align:top">
                                                                                                                                    <td align="center" valign="middle" style="background-color:#d52b2b;border-collapse:collapse!important;border:none;color:#0b7190;font-family:'Arial',Helvetica,sans-serif;font-size:16px;font-weight:400;line-height:1.3;margin:0;padding:0;text-align:right;vertical-align:middle;word-wrap:break-word;width:35px">
                                                                                                                                        <a href="https://hanvietair.com/" target="_blank"><span>
  <img src="https://raw.githubusercontent.com/Sontome/icon/main/logohva.png"
       width="35"
       height="35"
       style="border-radius:11px; display:block;"
       alt="">
</span>
                                                                                                                                    </a></td>
                                                                                                                                    <td align="center" valign="middle" style="background-color:#d52b2b;border-collapse:collapse!important;border:none;color:#fefefe;font-family:'Arial',Helvetica,sans-serif;font-size:10px;font-weight:400;line-height:1.3;margin:0;padding:0 0 0 10px;text-align:left;vertical-align:middle;word-wrap:break-word">
                                                                                                                                        <p style="margin:0;padding:0">
                                                                                                                                            <strong>HANVIETAIR</strong>
                                                                                                                                                                                                      
                                                                                                                                        </p>
                                                                                                                                    </td>
                                                                                                                                </tr>
                                                                                                                                </tbody>
                                                                                                                            </table>
                                                                                                                        </td>
                                                                                                                    </tr>
                                                                                                                    </tbody>
                                                                                                                </table>
                                                                                                            </td>
                                                                                                        </tr>
                                                                                                        </tbody>
                                                                                                    </table>
                                                                                                    <table style="border-collapse:collapse;border-spacing:0;padding:0;text-align:left;vertical-align:top;width:100%">
                                                                                                        <tbody>
                                                                                                        <tr style="padding:0;text-align:left;vertical-align:top">
                                                                                                            <td height="10" style="border-collapse:collapse!important;color:#0a0a0a;font-family:'Arial',Helvetica,sans-serif;font-size:10px;font-weight:400;line-height:10px;margin:0;padding:0;text-align:left;vertical-align:top;word-wrap:break-word">
                                                                                                                &nbsp;
                                                                                                            </td>
                                                                                                        </tr>
                                                                                                        </tbody>
                                                                                                    </table>
                                                                                                    <table align="center" bgcolor="#d52b2b" border="0" cellpadding="0" cellspacing="0" style="background:#d52b2b;background-color:#d52b2b;border-collapse:collapse;border-spacing:0;display:table;padding:0;text-align:left;vertical-align:top;width:100%;max-width:680px">
                                                                                                        <tbody>
                                                                                                        <tr>
                                                                                                            <td style="color:#0a0a0a;font-family:'Arial',Helvetica,sans-serif;font-size:16px;font-weight:400;line-height:1.3;margin:0;padding:0;text-align:center">
                                                                                                                <p style="color:#0a0a0a;font-family:'Arial',Helvetica,sans-serif;font-size:13px;font-weight:400;line-height:1.3;margin:0;padding:0;text-align:left"><a href="https://www.facebook.com/HanVietAirCom/" target="_blank">
                                                                                                                    <img src="https://ci3.googleusercontent.com/meips/ADKq_NZF98G0OL3BgI_lLy3SD4FqSzJSDsmupkdcXznapwH3sleGeaIXEuc3eNJ-VEffbUtaI9L7xSYBzmi-2VheH0f1IiJRNrVmLzDvUHSO6JHg2jEmKah9ngBl5vNIPV5hufYPPfv-X_lkRnlooWbrttZoapaOmmBYJesUgdI=s0-d-e1-ft#https://enewsletter-vietnamairlines.com/html/email/y22/220624_ec_Template/assets/img/icon_facebook.png" alt="Facebook" style="border:none;clear:both;display:inline-block;width:30px;height:auto;max-width:100%;outline:none;text-decoration:none;vertical-align:middle" class="CToWUd" data-bit="iit"></a>&nbsp;
                                                                                                                    <a href="https://www.youtube.com/@hanvietair" target="_blank"><img src="https://ci3.googleusercontent.com/meips/ADKq_Na4-hoPnWQukd_g0neyj2w5euiGD2wehAE9aOa9KipZ5Az8ZHoEn6zl-k5M0dvDTgNLCaUmho6isbYaElcgKpYZFIRykxsmi9erqsaOdelgvOrt9GuDtDjI5-dN5RKgf2jEtOTPkom37sKCDZRa5Ab_paq1W82fFVWPGw=s0-d-e1-ft#https://enewsletter-vietnamairlines.com/html/email/y22/220624_ec_Template/assets/img/icon_youtube.png" alt="Youtube" style="border:none;clear:both;display:inline-block;width:30px;height:auto;max-width:100%;outline:none;text-decoration:none;vertical-align:middle" class="CToWUd" data-bit="iit"></a>&nbsp;
                                                                                                                    <a href="https://www.instagram.com/hanvietaircom/" target="_blank"><img src="https://ci3.googleusercontent.com/meips/ADKq_NbOGdSzvHATRVEfjQsKK4Foe8vD3qchotcH4bpkVGwILnQk9qY95623oRpY-SJX9i9Z7knxEaCai3cbETjLiTrNntfpTUh9Z5-3yYKuTOvP3l7M4mH4HHp8vGn5hum9kvJWTOFv4-5T3kD0tovZsFClvrYZUiLJ0nMpGLVg=s0-d-e1-ft#https://enewsletter-vietnamairlines.com/html/email/y22/220624_ec_Template/assets/img/icon_instagram.png" alt="Youtube" style="border:none;clear:both;display:inline-block;width:30px;height:auto;max-width:100%;outline:none;text-decoration:none;vertical-align:middle" class="CToWUd" data-bit="iit"></a>&nbsp;
                                                                                                                    <a href="https://www.tiktok.com/@hanvietair" target="_blank"><img src="https://raw.githubusercontent.com/Sontome/icon/main/tiktok.png"
     alt="TikTok"
     width="30"
     height="30"
     style="
       box-sizing:border-box;
       padding:5px;
       border-radius:50%;
       border:1px solid #ffffff;
       background:transparent;
       display:inline-block;
       vertical-align:middle;
     "></a>
                                                                                                                </p>
                                                                                                            </td>
                                                                                                        </tr>
                                                                                                        </tbody>
                                                                                                    </table>
                                                                                                </td>
                                                                                                <td style="border-collapse:collapse!important;color:#0a0a0a;font-family:'Arial',Helvetica,sans-serif;font-size:10px;font-weight:400;padding-left:20px;padding-right:20px;line-height:10px;margin:0;text-align:left;vertical-align:top;word-wrap:break-word">
                                                                                                    <table align="center" bgcolor="#d52b2b" border="0" cellpadding="0" cellspacing="0" style="background:#d52b2b;background-color:#d52b2b;border-collapse:collapse;border-spacing:0;display:table;padding:0;text-align:left;vertical-align:top;width:100%;max-width:680px">
                                                                                                        <tbody>
                                                                                                        <tr>
                                                                                                            <td style="color:#0a0a0a;font-family:'Arial',Helvetica,sans-serif;font-size:12px;font-weight:400;line-height:1.3;margin:0;padding:0;text-align:center">
                                                                                                                <p style="color:#feffff;font-family:'Arial',Helvetica,sans-serif;font-size:12px;font-weight:400;line-height:1.4;margin:0;margin-top:0;margin-bottom:0;padding:0;text-align:left">
                                                                                                                    Đặt
                                                                                                                    vé
                                                                                                                    ngay
                                                                                                                    tại:
                                                                                                                    <a href="https://hanvietair.com/vi" target="_blank"> https://hanvietair.com </a>
                                                                                                                </p>
                                                                                                                <table style="border-collapse:collapse;border-spacing:0;padding:0;text-align:left;vertical-align:top;width:100%">
                                                                                                                    <tbody>
                                                                                                                    <tr style="padding:0;text-align:left;vertical-align:top">
                                                                                                                        <td height="5px" style="Margin:0;border-collapse:collapse!important;color:#0a0a0a;font-family:'Arial',Helvetica,sans-serif;font-size:5px;font-weight:400;line-height:5px;margin:0;padding:0;text-align:left;vertical-align:top;word-wrap:break-word">
                                                                                                                            &nbsp;
                                                                                                                        </td>
                                                                                                                    </tr>
                                                                                                                    </tbody>
                                                                                                                </table>
                                                                                                                <p style="color:#feffff;font-family:'Arial',Helvetica,sans-serif;font-size:12px;font-weight:400;line-height:1.4;margin:0;margin-bottom:0;padding:0;text-align:left">Tổng đài:
                                                                                                                  
                                                                                                                    <strong>070-3546-3396
                                                                                                                   </strong>
                                                                                                                </p>
                                                                                                                <table style="border-collapse:collapse;border-spacing:0;padding:0;text-align:left;vertical-align:top;width:100%">
                                                                                                                    <tbody>
                                                                                                                    <tr style="padding:0;text-align:left;vertical-align:top">
                                                                                                                        <td height="5px" style="Margin:0;border-collapse:collapse!important;color:#0a0a0a;font-family:'Arial',Helvetica,sans-serif;font-size:5px;font-weight:400;line-height:5px;margin:0;padding:0;text-align:left;vertical-align:top;word-wrap:break-word">
                                                                                                                            &nbsp;
                                                                                                                        </td>
                                                                                                                    </tr>
                                                                                                                    </tbody>
                                                                                                                </table>
                                                                                                                <p style="color:#feffff;font-family:'Arial',Helvetica,sans-serif;font-size:12px;font-weight:400;line-height:1.4;margin:0;margin-bottom:0;padding:0;text-align:left">
                                                                                                                    Hotline:
                                                                                                                    <strong> 010-3546-3396
                                                                                                                        </strong>
                                                                                                                </p>
                                                                                                                <table style="border-collapse:collapse;border-spacing:0;padding:0;text-align:left;vertical-align:top;width:100%">
                                                                                                                    <tbody>
                                                                                                                    <tr style="padding:0;text-align:left;vertical-align:top">
                                                                                                                        <td height="5px" style="Margin:0;border-collapse:collapse!important;color:#0a0a0a;font-family:'Arial',Helvetica,sans-serif;font-size:5px;font-weight:400;line-height:5px;margin:0;padding:0;text-align:left;vertical-align:top;word-wrap:break-word">
                                                                                                                            &nbsp;
                                                                                                                        </td>
                                                                                                                    </tr>
                                                                                                                    </tbody>
                                                                                                                </table>
                                                                                                                <p style="color:#feffff;font-family:'Arial',Helvetica,sans-serif;font-size:12px;font-weight:400;line-height:1.4;margin:0;margin-bottom:0;padding:0;text-align:left">
                                                                                                                    Email:
                                                                                                                    <strong>Hanvietair@gmail.com
                                                                                                                        
                                                                                                                        </strong>
                                                                                                                </p>
                                                                                                            </td>
                                                                                                        </tr>
                                                                                                        </tbody>
                                                                                                    </table>
                                                                                                </td>
                                                                                                <td align="center" valign="top">
                                                                                                    <table align="center" border="0" cellpadding="0" cellspacing="0" width="100%">
                                                                                                        <tbody>
                                                                                                        <tr>
                                                                                                            <td style="text-align:center" valign="top">
                                                                                                                <a href="#m_6655506731917057407_m_-5242890253129022313_" style="color:#ffffff;font-family:'Arial',Helvetica,sans-serif;font-weight:400;font-size:10px;line-height:1.3;margin:0;margin-bottom:20px;padding:0;text-align:center;text-decoration:none"><span>
                                                                        <img src="https://ci3.googleusercontent.com/meips/ADKq_NbtXXX7ecC_BhFL_dLKs_Vb9WBVFR8oCQR4Jw2qVtSGUW0Vt_WYQVvo3fWwvLS8HctrP9OUbwjM_JEsAoalA6Sv18udpk5v0HKk8ySl4jzf8CXN2FeVMzMkLXqXkcPUp2nM5RAnj1y4h-Zl60LWLbi9A5uowqM=s0-d-e1-ft#https://enewsletter-vietnamairlines.com/html/email/y22/220624_ec_Template/assets/img/icon_dl.png" alt="" width="15" height="14" class="CToWUd" data-bit="iit">&nbsp;</span>TẢI
                                                                                                                    APP
                                                                                                                    NGAY</a>
                                                                                                                <table style="border-collapse:collapse;border-spacing:0;padding:0;text-align:left;vertical-align:top;width:100%">
                                                                                                                    <tbody>
                                                                                                                    <tr style="padding:0;text-align:left;vertical-align:top">
                                                                                                                        <td height="5px" style="border-collapse:collapse!important;color:#0a0a0a;font-family:'Arial',Helvetica,sans-serif;font-size:10px;font-weight:400;line-height:5px;margin:0;padding:0;text-align:left;vertical-align:top;word-wrap:break-word">
                                                                                                                            &nbsp;
                                                                                                                        </td>
                                                                                                                    </tr>
                                                                                                                    </tbody>
                                                                                                                </table>
                                                                                                                <a href="https://apps.apple.com/us/app/hanvietair/id6756371831"
   target="_blank"
   data-clicktracking="off">
                                                                                                                    <img src="https://ci3.googleusercontent.com/meips/ADKq_Nbs5XVidQ6HnjEz88U-fiGCvgpitwOKdxnRh15G8nQU2sXNik3ObZEQxyYCp25r-JnfQeVL_SddHQ9muKNF5Dd1aNMWAZHcSrSXCs48TYJK8Jln7b13TzX8xsDsXHAcbAiKQmQxCgh6p2yfyX1osczCrYFTRtg=s0-d-e1-ft#http://enewsletter-vietnamairlines.com/html/email/y22/220624_ec_Template/assets/img/icon_ios.png" alt="IOS" style="border:none;clear:both;display:inline-block;max-width:100%;outline:none;text-decoration:none;vertical-align:middle;width:87px;margin:0;padding:0" class="CToWUd" data-bit="iit"></a>
                                                                                                                <table style="border-collapse:collapse;border-spacing:0;padding:0;text-align:left;vertical-align:top;width:100%">
                                                                                                                    <tbody>
                                                                                                                    <tr style="padding:0;text-align:left;vertical-align:top">
                                                                                                                        <td height="3px" style="border-collapse:collapse!important;color:#0a0a0a;font-family:'Arial',Helvetica,sans-serif;font-size:10px;font-weight:400;line-height:3px;margin:0;padding:0;text-align:left;vertical-align:top;word-wrap:break-word">
                                                                                                                            &nbsp;
                                                                                                                        </td>
                                                                                                                    </tr>
                                                                                                                    </tbody>
                                                                                                                </table>
                                                                                                                <a href="https://play.google.com/store/apps/details?id=com.hanvietairapp&hl=vi"
   target="_blank"
   data-clicktracking="off">
                                                                                                                    <img src="https://ci3.googleusercontent.com/meips/ADKq_NZxpUGGJU6FDB-OLSb_fBcXdyHsuN0uHkqwdmJGSgpPtrcmyfVDK-K_aX3sd8KQUnFBevOYkKRx18oxzHCU2PrP37QQbG7JVYo9E-Ywzndl0PFY7rMLTh6lT1Xnb99LI1ECuvhyV7tJDG8k4KgbtYlkgMV6BM0hAI8l=s0-d-e1-ft#http://enewsletter-vietnamairlines.com/html/email/y22/220624_ec_Template/assets/img/icon_android.png" alt="Android" style="border:none;clear:both;display:inline-block;max-width:100%;outline:none;text-decoration:none;vertical-align:middle;width:87px;margin:0;padding:0" class="CToWUd" data-bit="iit"></a>
                                                                                                                <table style="border-collapse:collapse;border-spacing:0;padding:0;text-align:left;vertical-align:top;width:100%">
                                                                                                                    <tbody>
                                                                                                                    <tr style="padding:0;text-align:left;vertical-align:top">
                                                                                                                        <td height="15px" style="border-collapse:collapse!important;color:#0a0a0a;font-family:'Arial',Helvetica,sans-serif;font-size:10px;font-weight:400;line-height:15px;margin:0;padding:0;text-align:left;vertical-align:top;word-wrap:break-word">
                                                                                                                            &nbsp;
                                                                                                                        </td>
                                                                                                                    </tr>
                                                                                                                    </tbody>
                                                                                                                </table>
                                                                                                            </td>
                                                                                                        </tr>
                                                                                                        </tbody>
                                                                                                    </table>
                                                                                                </td>
                                                                                            </tr>
                                                                                            </tbody>
                                                                                        </table>

                                                                                        <table style="border-collapse:collapse;border-spacing:0;padding:0;text-align:left;vertical-align:top;width:100%">
                                                                                            <tbody>
                                                                                            <tr style="padding:0;text-align:left;vertical-align:top">
                                                                                                <td style="border-collapse:collapse!important;color:#0a0a0a;font-family:'Arial',Helvetica,sans-serif;font-size:10px;font-weight:400;line-height:10px;margin:0;text-align:left;vertical-align:top;word-wrap:break-word">
                                                                                                    <table style="border-collapse:collapse;border-spacing:0;padding:0;text-align:left;vertical-align:top;width:100%">
                                                                                                        <tbody>
                                                                                                        <tr style="padding:0;text-align:left;vertical-align:top">
                                                                                                            <td height="30px" style="border-collapse:collapse!important;color:#0a0a0a;font-family:'Arial',Helvetica,sans-serif;font-size:10px;font-weight:400;line-height:30px;margin:0;padding:0;text-align:left;vertical-align:top;word-wrap:break-word;border-bottom:1px solid #7cb3c1">
                                                                                                                &nbsp;
                                                                                                            </td>
                                                                                                        </tr>
                                                                                                        </tbody>
                                                                                                    </table>
                                                                                                    <table style="border-collapse:collapse;border-spacing:0;padding:0;text-align:left;vertical-align:top;width:100%">
                                                                                                        <tbody>
                                                                                                        <tr style="padding:0;text-align:left;vertical-align:top">
                                                                                                            <td height="20px" style="border-collapse:collapse!important;color:#0a0a0a;font-family:'Arial',Helvetica,sans-serif;font-size:10px;font-weight:400;line-height:20px;margin:0;padding:0;text-align:left;vertical-align:top;word-wrap:break-word">
                                                                                                                &nbsp;
                                                                                                            </td>
                                                                                                        </tr>
                                                                                                        </tbody>
                                                                                                    </table>
                                                                                                    <p style="color:#feffff;font-family:'Arial',Helvetica,sans-serif;font-size:13px;font-weight:400;line-height:1.4;margin:0;margin-bottom:0;padding:0;text-align:center">
                                                                                                        <span style="border-right:1px solid #4f9cc6;color:#feffff;font-family:'Arial',Helvetica,sans-serif;font-weight:400;line-height:1.3;margin:0;padding:0 10px 0 5px;text-align:left;text-decoration:none">© 2026 HANVIETAIR</span>
                                                                                                       
                                                                                                    </p>
                                                                                                    <table style="border-collapse:collapse;border-spacing:0;padding:0;text-align:left;vertical-align:top;width:100%">
                                                                                                        <tbody>
                                                                                                        <tr style="padding:0;text-align:left;vertical-align:top">
                                                                                                            <td height="20px" style="border-collapse:collapse!important;color:#0a0a0a;font-family:'Arial',Helvetica,sans-serif;font-size:10px;font-weight:400;line-height:20px;margin:0;padding:0;text-align:left;vertical-align:top;word-wrap:break-word">
                                                                                                                &nbsp;
                                                                                                            </td>
                                                                                                        </tr>
                                                                                                        </tbody>
                                                                                                    </table>
                                                                                                </td>
                                                                                            </tr>
                                                                                            </tbody>
                                                                                        </table>
                                                                                    </th>
                                                                                    <th style="color:#0a0a0a;font-family:'Arial',Helvetica,sans-serif;font-size:16px;font-weight:400;line-height:1.3;margin:0;padding:0!important;text-align:left;width:0"></th>
                                                                                </tr>
                                                                            </tbody></table>
                                                                        </th>
                                                                    </tr>
                                                                    </tbody>
                                                                </table>
                                                            </td>
                                                        </tr>
                                                        </tbody>
                                                    </table>
                                                </th>
                                            </tr>
                                        </tbody></table>
                                    </th>
                                </tr>
                                </tbody>
                            </table>
                        </td>
                    </tr>
                    </tbody>
                </table>
                <table style="border-collapse:collapse;border-spacing:0;float:none;margin:0 auto;padding:0;text-align:center;vertical-align:top;width:100%">
                    <tbody>
                    <tr style="padding:0;text-align:left;vertical-align:top">
                        <td height="50px" style="border-collapse:collapse!important;color:#0a0a0a;font-family:'Arial',Helvetica,sans-serif;font-size:50px;font-weight:400;line-height:50px;margin:0;padding:0;text-align:left;vertical-align:top;word-wrap:break-word">
                            &nbsp;
                        </td>
                    </tr>
                    </tbody>
                </table>
            </center>
        </td>
    </tr>
</tbody></table>


<div style="display:none;white-space:nowrap;font:15px courier;line-height:0">
    &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp;
    &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp;
    &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp;
</div>
</div>


        """




        body = bodyVNA

        if "VJ" in first_file:

            body = bodyVJ

        elif "VNA" in first_file:

            body = bodyVNA
        else :
            body = bodyVNA

        print("EMAIL TEMPLATE SELECTED")
        message.attach(
            MIMEText(body, "html", "utf-8")
        )

        # =====================================================
        # ATTACHMENTS
        # =====================================================

        for file_path in attachments:

            if not os.path.exists(file_path):

                print(f"FILE NOT FOUND: {file_path}")
                continue

            original_filename = os.path.basename(
                file_path
            )

            # =====================================================
            # AUTO CLEAN FILENAME
            # =====================================================

            # ví dụ:
            # output_8f3f9a98d708414e88c30ba26c12f24b_VNA-EK794F-NGUYEN.pdf
            # ->
            # VNA-EK794F-NGUYEN.pdf

            filename = original_filename

            if original_filename.startswith("output_"):

                parts = original_filename.split("_", 2)

                if len(parts) >= 3:

                    filename = parts[2]

            print(f"ATTACHMENT NAME: {filename}")

            mime_type, _ = mimetypes.guess_type(file_path)

            if mime_type:

                main_type, sub_type = mime_type.split("/")

            else:

                main_type = "application"
                sub_type = "octet-stream"

            with open(file_path, "rb") as f:

                part = MIMEBase(
                    main_type,
                    sub_type
                )

                part.set_payload(f.read())

            encoders.encode_base64(part)

            part.add_header(
                "Content-Disposition",
                f'attachment; filename="{filename}"'
            )

            message.attach(part)

            print(f"ATTACHED: {filename}")

        # =====================================================
        # ENCODE
        # =====================================================

        raw_message = base64.urlsafe_b64encode(
            message.as_bytes()
        ).decode()

        # =====================================================
        # SEND
        # =====================================================

        service = get_gmail_service()

        result = (
            service.users()
            .messages()
            .send(
                userId="me",
                body={
                    "raw": raw_message
                }
            )
            .execute()
        )

        print(f"EMAIL SENT: {result}")

        return {
            "success": True,
            "message_id": result.get("id")
        }

    except Exception as e:

        print(f"SEND EMAIL ERROR: {str(e)}")

        return {
            "success": False,
            "error": str(e)
        }

# send_email_ticket(
#     email="devilrauxanhk17@gmail.com",
#     customer_name="Nguyễn Văn A",
#     salutation="Bạn",
#     attachments=["C:\\Users\\Admin\\AppData\\Local\\Temp\\tmplzfe_qp1\\output_ab3c95d327354ccb817a0082a8205769_VJ-X2DSUZ.pdf"]
# )