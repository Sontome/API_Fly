# get_refresh_token.py

from google_auth_oauthlib.flow import InstalledAppFlow

SCOPES = [
    "https://www.googleapis.com/auth/gmail.send"
]

flow = InstalledAppFlow.from_client_secrets_file(
    "credentials.json",
    SCOPES
)

creds = flow.run_local_server(port=0)

print("\n====================")
print("ACCESS TOKEN:")
print(creds.token)

print("\n====================")
print("REFRESH TOKEN:")
print(creds.refresh_token)