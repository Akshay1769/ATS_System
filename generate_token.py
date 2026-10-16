
from google_auth_oauthlib.flow import InstalledAppFlow

SCOPES = ["https://www.googleapis.com/auth/gmail.send"]

flow = InstalledAppFlow.from_client_secrets_file(
    "credentials.json",
    scopes=SCOPES,
)

credentials = flow.run_local_server(
    port=0,
    access_type="offline",
    prompt="consent",
)

if not credentials.refresh_token:
    raise RuntimeError(
        "No refresh token received. Check OAuth consent and try again."
    )

print("\nGMAIL_REFRESH_TOKEN:")
print(credentials.refresh_token)
