"""Email notification provider (Phase 4A).

Abstraction mirrors SMS: MockEmailProvider default; SmtpEmailProvider sends
via SMTP when SMTP_HOST/USER/PASS/FROM are set. Delivery mode is always
labeled MOCK/LIVE/UNAVAILABLE — never silently mock.
"""
import logging
import os

log = logging.getLogger("alerts")


class EmailProvider:
    def send(self, to: str, subject: str, body: str) -> str:
        raise NotImplementedError


class MockEmailProvider(EmailProvider):
    def send(self, to: str, subject: str, body: str) -> str:
        log.info("MOCK EMAIL -> %s: %s", to, subject)
        return "QUEUED (mock)"


class SmtpEmailProvider(EmailProvider):
    def __init__(self):
        from app.auth import SecretBox
        self.host = os.getenv("SMTP_HOST", "")
        self.port = int(os.getenv("SMTP_PORT", "587"))
        self.user = os.getenv("SMTP_USER", "")
        # ENC: prefixed values decrypt via FERNET_KEY; never logged
        self.password = SecretBox.reveal(os.getenv("SMTP_PASS", ""))
        self.sender = os.getenv("SMTP_FROM", self.user)

    def configured(self) -> bool:
        return bool(self.host and self.user and self.password)

    def send(self, to: str, subject: str, body: str) -> str:
        if not self.configured():
            raise RuntimeError("SMTP not configured: set SMTP_HOST/USER/PASS/FROM")
        import smtplib
        from email.mime.text import MIMEText
        msg = MIMEText(body, _charset="utf-8")
        msg["Subject"], msg["From"], msg["To"] = subject, self.sender, to
        with smtplib.SMTP(self.host, self.port, timeout=20) as s:
            s.starttls()
            s.login(self.user, self.password)
            s.send_message(msg)
        return "DELIVERED (smtp)"


def get_email_provider() -> EmailProvider:
    if os.getenv("EMAIL_PROVIDER", "mock").lower() == "smtp":
        return SmtpEmailProvider()
    return MockEmailProvider()


def delivery_status() -> dict:
    p = get_email_provider()
    if isinstance(p, MockEmailProvider):
        return {"email": "MOCK DELIVERY — logged only"}
    if isinstance(p, SmtpEmailProvider) and not p.configured():
        return {"email": "UNAVAILABLE — EMAIL_PROVIDER=smtp but credentials unset"}
    return {"email": "LIVE provider configured — verification required"}
