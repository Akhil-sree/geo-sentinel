"""Alert gating policy.

Rules (enforced, unit-testable):
  1. Only severity >= HIGH is dispatchable.
  2. Language: advisory only — NEVER evacuation directives, never
     house-level claims. Templates come from providers/sms.py.
  3. Every dispatched message is persisted for the AlertConsole audit log.
"""
from app.providers.sms import TEMPLATES


def eligible_for_alert(severity: str) -> bool:
    return severity in ("HIGH", "VERY_HIGH")


def compose_message(severity: str, zone_name: str, district: str, lang: str = "en") -> str:
    if not eligible_for_alert(severity):
        raise ValueError(f"severity {severity} below dispatch threshold")
    tpl = TEMPLATES.get(lang) or TEMPLATES["en"]
    return tpl[severity].format(zone=zone_name, district=district)
