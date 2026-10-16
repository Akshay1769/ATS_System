import base64
import html
import os
from email.errors import HeaderParseError
from email.headerregistry import Address
from email.mime.application import MIMEApplication
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.utils import formataddr
from urllib.parse import urlsplit

from dotenv import load_dotenv
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build

load_dotenv()

GMAIL_SENDER = os.getenv("GMAIL_SENDER")
GMAIL_CLIENT_ID = os.getenv("GMAIL_CLIENT_ID")
GMAIL_CLIENT_SECRET = os.getenv("GMAIL_CLIENT_SECRET")
GMAIL_REFRESH_TOKEN = os.getenv("GMAIL_REFRESH_TOKEN")
GMAIL_SEND_SCOPE = "https://www.googleapis.com/auth/gmail.send"
INTERVIEW_APP_HOST = "xhiremain.vercel.app"


def _validate_gmail_sender(sender):
    try:
        address = Address(addr_spec=sender)
    except (HeaderParseError, ValueError) as error:
        raise ValueError(
            "GMAIL_SENDER must be a single email address configured for this "
            "Gmail account."
        ) from error
    if address.addr_spec != sender:
        raise ValueError(
            "GMAIL_SENDER must be a single email address configured for this "
            "Gmail account."
        )


def _validate_interview_url(interview_link):
    if any(
        ord(character) <= 0x20 or ord(character) == 0x7F or character == "\\"
        for character in interview_link
    ):
        raise ValueError("Interview link contains invalid URL characters.")

    parsed_url = urlsplit(interview_link)
    allowed_hosts = {INTERVIEW_APP_HOST}

    configured_base_url = os.getenv("BASE_URL", "")
    configured_base = urlsplit(configured_base_url)
    configured_host = configured_base.hostname
    if configured_base.scheme == "https" and configured_host:
        allowed_hosts.add(configured_host.lower())

    if (
        parsed_url.scheme != "https"
        or not parsed_url.hostname
        or parsed_url.hostname.lower() not in allowed_hosts
        or parsed_url.username is not None
        or parsed_url.password is not None
        or parsed_url.port not in (None, 443)
    ):
        raise ValueError("Interview link must be an HTTPS URL on the configured app domain.")

    return html.escape(interview_link, quote=True)


def send_email_to(to_email, subject, body_html, company_name="", attachment_path=None):
    missing_settings = [
        name
        for name, value in (
            ("GMAIL_SENDER", GMAIL_SENDER),
            ("GMAIL_CLIENT_ID", GMAIL_CLIENT_ID),
            ("GMAIL_CLIENT_SECRET", GMAIL_CLIENT_SECRET),
            ("GMAIL_REFRESH_TOKEN", GMAIL_REFRESH_TOKEN),
        )
        if not value
    ]
    if missing_settings:
        raise RuntimeError(
            f"Missing required Gmail settings: {', '.join(missing_settings)}"
        )

    _validate_gmail_sender(GMAIL_SENDER)

    try:
        message = MIMEMultipart()
        message["Subject"] = subject
        message["To"] = to_email
        message["From"] = formataddr((company_name, GMAIL_SENDER))
        message.attach(MIMEText(body_html, "html"))

        if attachment_path:
            with open(attachment_path, 'rb') as f:
                attachment = MIMEApplication(f.read())
                attachment.add_header(
                    "Content-Disposition",
                    "attachment",
                    filename=os.path.basename(attachment_path),
                )
                message.attach(attachment)

        credentials = Credentials(
            token=None,
            refresh_token=GMAIL_REFRESH_TOKEN,
            token_uri="https://oauth2.googleapis.com/token",
            client_id=GMAIL_CLIENT_ID,
            client_secret=GMAIL_CLIENT_SECRET,
            scopes=[GMAIL_SEND_SCOPE],
        )
        gmail = build(
            "gmail",
            "v1",
            credentials=credentials,
            cache_discovery=False,
        )
        raw_message = base64.urlsafe_b64encode(message.as_bytes()).decode("ascii")
        # Gmail enforces that From is the OAuth account or a verified send-as alias.
        result = gmail.users().messages().send(
            userId="me",
            body={"raw": raw_message},
        ).execute()

        print(f"Gmail accepted message. Message ID: {result.get('id')}")
    except Exception as e:
        print("================================")
        print("EMAIL ERROR")
        status = getattr(getattr(e, "resp", None), "status", None)
        if status is not None:
            print(f"{type(e).__name__} (HTTP {status})")
        else:
            print(type(e).__name__)
        print("================================")
        raise


hr_body_html = '''
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>ATS Score Results</title>
    <style>
        body {
            font-family: Arial, sans-serif;
            color: #333;
            margin: 0;
            padding: 0;
            background-color: #f4f4f4;
        }
        .container {
            width: 100%;
            max-width: 600px;
            margin: 0 auto;
            background-color: #fff;
            border: 1px solid #ddd;
            border-radius: 8px;
            overflow: hidden;
        }
        .header {
            background-color: #007bff;
            color: #fff;
            padding: 20px;
            text-align: center;
        }
        .header h1 {
            margin: 0;
        }
        .content {
            padding: 20px;
        }
        .content p {
            font-size: 16px;
            line-height: 1.5;
        }
        .footer {
            background-color: #f4f4f4;
            padding: 10px;
            text-align: center;
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>ATS Score Results</h1>
        </div>
        <div class="content">
            <p>Dear Company and Team,</p>
            <p>We are pleased to inform you that the candidates who have passed the ATS score are included in the attached CSV file.</p>
            <p>For any further details or questions, please do not hesitate to reach out.</p>
            <p>Best regards,</p>
            <p>Company</p>
        </div>
        <div class="footer">
            <p>&copy; 2024 Company. All rights reserved.</p>
        </div>
    </div>
</body>
</html>

'''


def candidate_email_body(candidate_name, interview_link , role_name,company_name):
    candidate_name = html.escape(str(candidate_name), quote=True)
    interview_link = _validate_interview_url(interview_link)
    role_name = html.escape(str(role_name), quote=True)
    company_name = html.escape(str(company_name), quote=True)

    body_html = f'''
    <div style="font-family: Arial, sans-serif; font-size:14px; color:#000; line-height:1.6;">

        <p>
            <strong></strong> Application Update: {candidate_name} - {role_name} Role
        </p>

        <p>Dear Candidate,</p>

        <p>
            Thank you for your interest in the Software Engineer position at {company_name} and for taking the time to submit your application.
        </p>

        <p>
            We are pleased to inform you that your profile has been <strong>shortlisted</strong> for the next stage of our recruitment process.
        </p>

        <p>
            As part of the next step, you are invited to complete your interview using the link below:
        </p>

        <div style="text-align:center; margin:30px 0;">
            <a href="{interview_link}"
                style="
                    background:#4f46e5;
                    color:white;
                    padding:12px 24px;
                    text-decoration:none;
                    border-radius:6px;
                    font-weight:500;
                    display:inline-block;
                ">
                Start Interview
            </a>
        </div>

        <p>
            We recommend completing the interview at your earliest convenience.
            Further instructions will be shared upon successful completion.
        </p>

        <p>
            Thank you for your interest in joining our team.
            We look forward to your participation in the next stage of the process.
        </p>

        <p>
            Sincerely,
        </p>

        <p>
            <strong>Talent Acquisition Team</strong>
        </p>

    </div>
    '''
    return body_html


def rejection_email_body(candidate_name, role_name, company_name):
    candidate_name = html.escape(str(candidate_name), quote=True)
    role_name = html.escape(str(role_name), quote=True)
    company_name = html.escape(str(company_name), quote=True)

    body_html = f'''
    <div style="font-family: Arial, sans-serif; font-size:14px; color:#000; line-height:1.6;">

        <p>
            <strong></strong> Application Update: {candidate_name} - {role_name} Role
        </p>

        <p>Dear {candidate_name},</p>

        <p>
            Thank you for your interest in the {role_name} position at {company_name} and for taking the time to apply.
        </p>

        <p>
            After careful review of your application, we regret to inform you that
            you have not been selected for the next stage of the recruitment process.
        </p>

        <p>
            We truly appreciate your interest in our company and encourage you to
            apply again for future opportunities that match your profile and experience.
        </p>

        <p>
            We wish you all the best in your career journey and future endeavors.
        </p>

        <p>
            Sincerely,
        </p>

        <p>
            <strong>Talent Acquisition Team</strong>
        </p>

    </div>
    '''

    return body_html