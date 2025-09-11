from __future__ import print_function
import os
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

# Scope chỉ đọc Gmail
SCOPES = ['https://www.googleapis.com/auth/gmail.readonly']

# Lấy đường dẫn tuyệt đối cho file token & client_secret
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
TOKEN_PATH = os.path.join(BASE_DIR, 'token.json')
CLIENT_SECRET_PATH = os.path.join(BASE_DIR, 'client_secret.json')

def get_gmail_service():
    creds = None

    # Nếu token đã tồn tại, load
    if os.path.exists(TOKEN_PATH):
        creds = Credentials.from_authorized_user_file(TOKEN_PATH, SCOPES)

    # Nếu token không hợp lệ hoặc không tồn tại, refresh hoặc tạo mới
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            # Mở trình duyệt để login lần đầu
            flow = InstalledAppFlow.from_client_secrets_file(CLIENT_SECRET_PATH, SCOPES)
            creds = creds = flow.run_local_server(port=0)
        # Lưu token để lần sau dùng luôn
        with open(TOKEN_PATH, 'w') as token_file:
            token_file.write(creds.to_json())

    # Tạo service Gmail API
    service = build('gmail', 'v1', credentials=creds)
    return service


if __name__ == "__main__":
    service = get_gmail_service()
    profile = service.users().getProfile(userId='me').execute()
    print("Email đang dùng:", profile.get("emailAddress"))

