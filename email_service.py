import os
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.application import MIMEApplication

SMTP_PORT = int(os.getenv("SMTP_PORT", 587))
SMTP_SERVER = os.getenv("SMTP_SERVER")
SMTP_USERNAME = os.getenv("SMTP_USER")
SMTP_PASSWORD = os.getenv("SMTP_PASSWORD")
FROM_EMAIL = os.getenv("SMTP_USER")

def send_email_to(to_email, subject, body_html,company_name = "" , attachment_path=None):
    try:
        msg = MIMEMultipart()
        msg['Subject'] = subject
        msg['To'] = to_email
        msg['From'] = f"{company_name} <{FROM_EMAIL}>"

        body_part = MIMEText(body_html, 'html')
        msg.attach(body_part)

        if attachment_path:
            with open(attachment_path, 'rb') as f:
                part = MIMEApplication(f.read())
                part.add_header('Content-Disposition', 'attachment', filename=os.path.basename(attachment_path))
                msg.attach(part)

        with smtplib.SMTP(SMTP_SERVER, int(SMTP_PORT)) as server:
            server.starttls() 
            server.login(SMTP_USERNAME, SMTP_PASSWORD)
            server.send_message(msg)

        print(f"Email sent: {to_email}")
    except smtplib.SMTPAuthenticationError as auth_err:
        print(f"Authentication Error: {auth_err}")
    except Exception as e:
        print(f"Error: {e}")



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