import base64
import json
import os
import traceback
from email.utils import formataddr
from urllib.error import HTTPError
from urllib.request import Request, urlopen

from dotenv import load_dotenv

load_dotenv()

RESEND_API_KEY = os.getenv("RESEND_API_KEY")
RESEND_FROM_EMAIL = os.getenv("RESEND_FROM_EMAIL")
RESEND_API_URL = "https://api.resend.com/emails"


def send_email_to(to_email, subject, body_html, company_name="", attachment_path=None):
    missing_settings = [
        name
        for name, value in (
            ("RESEND_API_KEY", RESEND_API_KEY),
            ("RESEND_FROM_EMAIL", RESEND_FROM_EMAIL),
        )
        if not value
    ]
    if missing_settings:
        raise RuntimeError(
            f"Missing required email settings: {', '.join(missing_settings)}"
        )

    try:
        payload = {
            "from": formataddr((company_name, RESEND_FROM_EMAIL)),
            "to": [to_email],
            "subject": subject,
            "html": body_html,
        }

        if attachment_path:
            with open(attachment_path, 'rb') as f:
                payload["attachments"] = [{
                    "filename": os.path.basename(attachment_path),
                    "content": base64.b64encode(f.read()).decode("ascii"),
                }]

        request = Request(
            RESEND_API_URL,
            data=json.dumps(payload).encode("utf-8"),
            headers={
                "Authorization": f"Bearer {RESEND_API_KEY}",
                "Content-Type": "application/json",
            },
            method="POST",
        )
        try:
            with urlopen(request, timeout=30) as response:
                response.read()
        except HTTPError as http_error:
            error_body = http_error.read().decode("utf-8", errors="replace")
            raise RuntimeError(
                f"Resend API returned HTTP {http_error.code}: {error_body}"
            ) from http_error

        print(f"Email sent: {to_email}")
    except Exception as e:
        print("================================")
        print("EMAIL ERROR")
        print(type(e).__name__)
        print(str(e))
        traceback.print_exc()
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