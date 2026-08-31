"""
SMS provider abstraction.

Providers:
    - MockSMSProvider  -> default demo provider
    - TwilioProvider   -> production adapter
    - MSG91Provider    -> production adapter

Provider selection:
    SMS_PROVIDER environment variable.

Messages are reviewed, localized templates stored in:
    alerts/templates/<lang>.json

Emergency instructions must NEVER be machine translated.

Alerts are severity-tiered and do not issue evacuation orders.
"""

import json
import logging
import os

from ..database import SessionLocal
from ..models_db import Alert, Recipient, AuditLog


log = logging.getLogger("alerts")


TPL_DIR = os.path.join(
    os.path.dirname(__file__),
    "templates",
)


def _template(
    lang: str,
    severity: str,
) -> str:
    """
    Load a reviewed alert template.

    Falls back to English if the requested language
    template does not exist.
    """

    path = os.path.join(
        TPL_DIR,
        f"{lang}.json",
    )

    fallback = os.path.join(
        TPL_DIR,
        "en.json",
    )

    template_path = (
        path
        if os.path.exists(path)
        else fallback
    )

    with open(
        template_path,
        "r",
        encoding="utf-8",
    ) as f:

        templates = json.load(f)

    if severity not in templates:
        raise KeyError(
            f"Severity '{severity}' is not defined "
            f"in template '{template_path}'."
        )

    return templates[severity]


class SMSProvider:
    """
    Base interface for SMS providers.
    """

    def send(
        self,
        phone: str,
        message: str,
    ) -> str:
        raise NotImplementedError


class MockSMSProvider(SMSProvider):
    """
    Demo SMS provider.

    Does not send real messages.
    """

    def send(
        self,
        phone: str,
        message: str,
    ) -> str:

        log.info(
            "MOCK SMS -> %s: %s",
            phone,
            message,
        )

        return "DELIVERED (mock)"


class TwilioProvider(SMSProvider):
    """
    Twilio production adapter.

    Real credentials must come from environment/configuration.
    """

    def __init__(self):
        from ..config import settings

        self.sid = getattr(
            settings,
            "TWILIO_ACCOUNT_SID",
            None,
        )

        self.token = getattr(
            settings,
            "TWILIO_AUTH_TOKEN",
            None,
        )

        self.sender = getattr(
            settings,
            "TWILIO_FROM_NUMBER",
            None,
        )

    def send(
        self,
        phone: str,
        message: str,
    ) -> str:

        if not self.sid:
            raise RuntimeError(
                "Twilio is not configured: "
                "TWILIO_ACCOUNT_SID is missing."
            )

        if not self.token:
            raise RuntimeError(
                "Twilio is not configured: "
                "TWILIO_AUTH_TOKEN is missing."
            )

        if not self.sender:
            raise RuntimeError(
                "Twilio is not configured: "
                "TWILIO_FROM_NUMBER is missing."
            )

        # Production implementation should perform
        # an authenticated POST to the Twilio REST API.
        raise NotImplementedError(
            "Configure Twilio REST API credentials "
            "and HTTP dispatch."
        )


class MSG91Provider(SMSProvider):
    """
    MSG91 production adapter.

    Credentials must come from environment/configuration.
    """

    def __init__(self):
        from ..config import settings

        self.api_key = getattr(
            settings,
            "MSG91_API_KEY",
            None,
        )

        self.sender = getattr(
            settings,
            "MSG91_SENDER_ID",
            None,
        )

    def send(
        self,
        phone: str,
        message: str,
    ) -> str:

        if not self.api_key:
            raise RuntimeError(
                "MSG91 is not configured: "
                "MSG91_API_KEY is missing."
            )

        # Production implementation should perform
        # an authenticated POST to MSG91.
        raise NotImplementedError(
            "Configure MSG91 REST API credentials "
            "and HTTP dispatch."
        )


def get_sms_provider() -> SMSProvider:
    """
    Select SMS provider using SMS_PROVIDER.

    Supported values:

        mock
        twilio
        msg91

    Default:
        mock
    """

    provider_name = os.getenv(
        "SMS_PROVIDER",
        "mock",
    ).lower()

    providers = {
        "mock": MockSMSProvider,
        "twilio": TwilioProvider,
        "msg91": MSG91Provider,
    }

    provider_class = providers.get(
        provider_name,
        MockSMSProvider,
    )

    if provider_name not in providers:
        log.warning(
            "Unknown SMS_PROVIDER='%s'. "
            "Falling back to MockSMSProvider.",
            provider_name,
        )

    return provider_class()


def dispatch_alert(
    zone_id: str,
    severity: str,
    zone_name: str,
    district: str,
):
    """
    Dispatch a severity-tiered alert.

    The rule engine must already have determined
    that the alert is eligible.

    Pipeline:

        severity gate
             ↓
        recipient selection
             ↓
        reviewed localized template
             ↓
        SMS provider
             ↓
        delivery record
             ↓
        audit log

    No evacuation orders are generated by this function.
    """

    # ---------------------------------------------------------
    # Severity gate
    # ---------------------------------------------------------

    if severity not in (
        "HIGH",
        "VERY_HIGH",
    ):

        return {
            "sent": 0,
            "detail": (
                "Below HIGH severity — "
                "alert not eligible."
            ),
        }

    db = SessionLocal()

    provider = get_sms_provider()

    sent = []

    try:

        # -----------------------------------------------------
        # Select active recipients
        # -----------------------------------------------------

        recipients = (
            db.query(Recipient)
            .filter(
                Recipient.zone_id == zone_id,
                Recipient.active.is_(True),
            )
            .all()
        )

        # -----------------------------------------------------
        # Generate and dispatch messages
        # -----------------------------------------------------

        for recipient in recipients:

            message_template = _template(
                recipient.preferred_language,
                severity,
            )

            message = message_template.format(
                zone=zone_name,
                district=district,
            )

            try:

                status = provider.send(
                    recipient.phone_number,
                    message,
                )

            except Exception as exc:

                status = f"FAILED: {exc}"

                log.exception(
                    "SMS delivery failed for %s",
                    recipient.phone_number,
                )

            # -------------------------------------------------
            # Store alert record
            # -------------------------------------------------

            db.add(
                Alert(
                    zone_id=zone_id,
                    severity=severity,
                    message=message,
                    language=(
                        recipient.preferred_language
                    ),
                    recipient=(
                        recipient.phone_number
                    ),
                    recipient_name=(
                        recipient.name
                    ),
                    provider=(
                        provider.__class__.__name__
                    ),
                    status=status,
                )
            )

            # -------------------------------------------------
            # API result
            # -------------------------------------------------

            sent.append({
                "to": recipient.phone_number,
                "name": recipient.name,
                "language": (
                    recipient.preferred_language
                ),
                "message": message,
                "status": status,
            })

        # -----------------------------------------------------
        # Audit log
        # -----------------------------------------------------

        db.add(
            AuditLog(
                action="ALERT_DISPATCH",
                detail=(
                    f"zone={zone_id} "
                    f"sev={severity} "
                    f"n={len(sent)}"
                ),
            )
        )

        db.commit()

    except Exception:

        db.rollback()

        log.exception(
            "Alert dispatch failed for zone=%s",
            zone_id,
        )

        raise

    finally:

        db.close()

    return {
        "sent": len(sent),
        "messages": sent,
    }