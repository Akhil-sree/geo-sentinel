"""Alert delivery layer — gating + message templates + recipient directory.

Providers live in app/providers/sms.py; this package owns the POLICY:
who is eligible, which severity tier, what language, what the message
may and may not say.
"""
from app.notify.gating import compose_message, eligible_for_alert
from app.notify.directory import get_directory

__all__ = ["compose_message", "eligible_for_alert", "get_directory"]
