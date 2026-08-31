"""SMS delivery providers.

MockSMSProvider (default): logs messages to the alerts table + stdout,
masked demo numbers, EN/HI templates, no network calls.
TwilioProvider: activates ONLY when TWILIO_ACCOUNT_SID/AUTH_TOKEN exist.
Real deployment additionally requires DLT-registered sender IDs (India)
and state SDMA authorization — enforced by alert gating upstream.
"""
import os
import re
from datetime import datetime, timezone

TEMPLATES = {
    "en": {
        "HIGH":     ("GEO-SENTINEL: High landslide risk advisory for {zone} "
                     "({district}). Avoid steep slopes and road cuts during heavy rain. "
                     "Zone-level advisory only."),
        "VERY_HIGH": ("GEO-SENTINEL: VERY HIGH landslide risk for {zone} ({district}). "
                      "Avoid slopes/road cuts; follow local authorities. "
                      "Zone-level advisory only."),
    },
    "hi": {
        "HIGH":     ("GEO-SENTINEL: {zone} ({district}) mein bhukhamp/landslide ka "
                     "uchch jokhim. Bhaari baarish mein steep dhalano se bachein. "
                     "Yeh salah hai, aadesh nahi."),
        "VERY_HIGH": ("GEO-SENTINEL: {zone} ({district}) mein bahut uchch landslide "
                      "jokhim. Dhalano/road cuts se bachein, sthaniya prashasan ka "
                      "palein. Yeh salah hai, aadesh nahi."),
    },
}

_mask = lambda num: re.sub(r"\d(?=.*\d{2})", "*", num or "demo-number")


class MockSMSProvider:
    name = "mock"

    def send(self, to: str, message: str, recipient_name: str = "") -> dict:
        ts = datetime.now(timezone.utc).isoformat()
        print(f"[MockSMS] {_mask(to)} ({recipient_name}): {message}")
        return {"provider": self.name, "to": _mask(to), "status": "SENT (mock)",
                "at": ts, "detail": "demo console — no SMS transmitted"}


class TwilioProvider:
    name = "twilio"

    def __init__(self):
        if not (os.getenv("TWILIO_ACCOUNT_SID") and os.getenv("TWILIO_AUTH_TOKEN")):
            raise RuntimeError("Twilio credentials not set — use MockSMSProvider")
        self.from_number = os.environ["TWILIO_FROM"]

    def send(self, to: str, message: str, recipient_name: str = "") -> dict:
        from twilio.rest import Client  # optional dependency
        client = Client(os.environ["TWILIO_ACCOUNT_SID"], os.environ["TWILIO_AUTH_TOKEN"])
        msg = client.messages.create(body=message, from_=self.from_number, to=to)
        return {"provider": self.name, "to": to, "status": str(msg.status),
                "at": datetime.now(timezone.utc).isoformat(), "detail": msg.sid}


def get_sms_provider():
    if os.getenv("SMS_PROVIDER") == "twilio":
        try:
            return TwilioProvider()
        except RuntimeError:
            print("[sms] Twilio config incomplete — falling back to Mock (flagged)")
    return MockSMSProvider()
