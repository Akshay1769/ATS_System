import base64
import inspect
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from email import policy
from email.parser import BytesParser
from io import StringIO
from pathlib import Path
from unittest.mock import Mock, patch

import email_service


class GmailEmailServiceTests(unittest.TestCase):
    def setUp(self):
        self.settings = (
            patch.object(email_service, "GMAIL_SENDER", "recruiter@example.com"),
            patch.object(email_service, "GMAIL_CLIENT_ID", "client-id"),
            patch.object(email_service, "GMAIL_CLIENT_SECRET", "client-secret"),
            patch.object(email_service, "GMAIL_REFRESH_TOKEN", "refresh-token"),
        )
        for setting in self.settings:
            setting.start()
            self.addCleanup(setting.stop)

    def send_with_mocked_gmail(
        self,
        recipient,
        subject,
        body_html,
        company_name,
        attachment_path=None,
    ):
        send_request = Mock()
        send_request.execute.return_value = {"id": "mock-message-id"}
        messages = Mock()
        messages.send.return_value = send_request
        users = Mock()
        users.messages.return_value = messages
        gmail = Mock()
        gmail.users.return_value = users

        output = StringIO()
        with (
            patch.object(email_service, "build", return_value=gmail) as build,
            redirect_stdout(output),
        ):
            result = email_service.send_email_to(
                recipient,
                subject,
                body_html,
                company_name=company_name,
                attachment_path=attachment_path,
            )

        build.assert_called_once()
        args, kwargs = build.call_args
        self.assertEqual(args, ("gmail", "v1"))
        self.assertEqual(kwargs["credentials"].scopes, [email_service.GMAIL_SEND_SCOPE])
        self.assertEqual(kwargs["cache_discovery"], False)
        users.messages.assert_called_once()
        messages.send.assert_called_once()
        send_request.execute.assert_called_once_with()

        call = messages.send.call_args.kwargs
        self.assertEqual(call["userId"], "me")
        message = BytesParser(policy=policy.default).parsebytes(
            base64.urlsafe_b64decode(call["body"]["raw"])
        )
        self.assertEqual(message["To"], recipient)
        self.assertEqual(message["Subject"], subject)
        self.assertEqual(message["From"], f"{company_name} <recruiter@example.com>")
        html_part = next(
            part for part in message.walk() if part.get_content_type() == "text/html"
        )
        self.assertEqual(html_part.get_content(), body_html)
        self.assertIn("Gmail accepted message. Message ID: mock-message-id", output.getvalue())
        self.assertNotIn("client-secret", output.getvalue())
        self.assertNotIn("refresh-token", output.getvalue())
        return result, message, output.getvalue()

    def test_interview_template_is_sent_unchanged(self):
        self.assertEqual(
            tuple(inspect.signature(email_service.send_email_to).parameters),
            ("to_email", "subject", "body_html", "company_name", "attachment_path"),
        )
        interview_link = "https://xhiremain.vercel.app/call/abc"
        body_html = email_service.candidate_email_body(
            "<Candidate>", interview_link, "Engineer & Lead", "Example Co"
        )

        result, message, _ = self.send_with_mocked_gmail(
            "candidate@example.com",
            "Interview Invitation",
            body_html,
            "Example Co",
        )

        self.assertIsNone(result)
        self.assertIn(interview_link, body_html)
        self.assertIn("&lt;Candidate&gt; - Engineer &amp; Lead Role", body_html)
        self.assertNotIn("<Candidate>", body_html)
        self.assertIn(
            f'href="{interview_link}"',
            next(
                part.get_content()
                for part in message.walk()
                if part.get_content_type() == "text/html"
            ),
        )

    def test_rejection_template_is_sent_unchanged(self):
        body_html = email_service.rejection_email_body(
            "<Candidate>", "<Engineer>", "Example & Co"
        )

        result, _, _ = self.send_with_mocked_gmail(
            "candidate@example.com",
            "Application Update",
            body_html,
            "Example & Co",
        )

        self.assertIsNone(result)
        self.assertIn("Dear &lt;Candidate&gt;", body_html)
        self.assertIn("the &lt;Engineer&gt; position at Example &amp; Co", body_html)
        self.assertIn("not been selected", body_html)

    def test_interview_template_rejects_unsafe_urls(self):
        unsafe_urls = (
            "javascript:alert(1)",
            "https://xhiremain.vercel.app.attacker.example/call/abc",
            "https://attacker.example/call/abc",
            "http://xhiremain.vercel.app/call/abc",
            "//xhiremain.vercel.app/call/abc",
            "https://xhiremain.vercel.app/call/abc\n@attacker.example",
            r"https://xhiremain.vercel.app\@attacker.example/call/abc",
        )

        for interview_link in unsafe_urls:
            with self.subTest(interview_link=interview_link):
                with self.assertRaises(ValueError):
                    email_service.candidate_email_body(
                        "Candidate", interview_link, "Engineer", "Example Co"
                    )

    def test_interview_url_is_html_escaped_once(self):
        interview_link = (
            "https://xhiremain.vercel.app/call/abc?source=email&next=step"
        )
        body_html = email_service.candidate_email_body(
            "Candidate", interview_link, "Engineer", "Example Co"
        )

        self.assertIn(
            'href="https://xhiremain.vercel.app/call/abc?source=email&amp;next=step"',
            body_html,
        )
        self.assertNotIn("&amp;amp;", body_html)

    def test_configured_https_base_domain_is_allowed(self):
        with patch.dict(
            email_service.os.environ,
            {"BASE_URL": "https://interviews.example.org"},
        ):
            body_html = email_service.candidate_email_body(
                "Candidate",
                "https://interviews.example.org/call/abc",
                "Engineer",
                "Example Co",
            )
        self.assertIn('href="https://interviews.example.org/call/abc"', body_html)

    def test_attachment_is_included_in_gmail_message(self):
        body_html = email_service.rejection_email_body(
            "Candidate", "Engineer", "Example Co"
        )
        with tempfile.TemporaryDirectory() as temp_dir:
            attachment_path = Path(temp_dir) / "resume.txt"
            attachment_path.write_bytes(b"mock resume bytes")
            result, message, _ = self.send_with_mocked_gmail(
                "candidate@example.com",
                "Application Update",
                body_html,
                "Example Co",
                attachment_path=str(attachment_path),
            )

        self.assertIsNone(result)
        attachment = next(
            part for part in message.walk() if part.get_filename() == "resume.txt"
        )
        self.assertEqual(attachment.get_payload(decode=True), b"mock resume bytes")

    def test_gmail_api_failure_is_logged_and_reraised(self):
        gmail = Mock()
        gmail.users.return_value.messages.return_value.send.return_value.execute.side_effect = (
            ValueError("mock Gmail API failure")
        )
        output = StringIO()

        with (
            patch.object(email_service, "build", return_value=gmail),
            redirect_stdout(output),
            redirect_stderr(StringIO()),
            self.assertRaisesRegex(ValueError, "mock Gmail API failure"),
        ):
            email_service.send_email_to(
                "candidate@example.com",
                "Application Update",
                "<p>Test</p>",
            )

        self.assertIn("EMAIL ERROR\nValueError", output.getvalue())
        self.assertNotIn("mock Gmail API failure", output.getvalue())
        self.assertNotIn("candidate@example.com", output.getvalue())

    def test_sender_configuration_must_be_a_single_address(self):
        for sender in (
            "Recruiter <recruiter@example.com>",
            "recruiter@example.com, attacker@example.com",
            "recruiter@",
        ):
            with self.subTest(sender=sender):
                with self.assertRaises(ValueError):
                    email_service._validate_gmail_sender(sender)


if __name__ == "__main__":
    unittest.main()
