"""Automatic alert evaluation (Phase 5): risk → threshold → dedup/cooldown → dispatch.

Called by the worker after each ingestion cycle AND available manually via
POST /api/alerts/evaluate. Never spams: per-zone cooldown
(ALERT_COOLDOWN_MIN, default 360) + severity-escalation-only resend.
"""
import os
from datetime import datetime, timedelta, timezone
from sqlalchemy.orm import Session
from app.models_db import Alert, RiskScore

COOLDOWN_MIN = float(os.getenv("ALERT_COOLDOWN_MIN", "360"))
SEV_RANK = {"LOW": 0, "MODERATE": 1, "HIGH": 2, "VERY_HIGH": 3}


def auto_evaluate_alerts(db: Session) -> dict:
    try:
        from app.services.sim import run_pipeline
        from app.alerts.sms import dispatch_alert
        from app.models_db import Zone
        scores = run_pipeline(168)
        fired, skipped = [], []
        for s in scores:
            if SEV_RANK.get(s["severity"], 0) < SEV_RANK["HIGH"]:
                continue
            last = (db.query(Alert).filter(Alert.zone_id == s["zone_id"])
                    .order_by(Alert.created_at.desc()).first())
            if last and last.created_at:
                age = datetime.now(timezone.utc) - last.created_at.replace(tzinfo=timezone.utc)
                escalated = SEV_RANK.get(s["severity"], 0) > SEV_RANK.get(last.severity, 0)
                if age < timedelta(minutes=COOLDOWN_MIN) and not escalated:
                    skipped.append({"zone": s["zone_id"], "reason": "cooldown"})
                    continue
            z = db.get(Zone, s["zone_id"])
            try:
                dispatch_alert(s["zone_id"], s["severity"],
                               z.name if z else s["zone_id"],
                               z.district if z else "")
                fired.append({"zone": s["zone_id"], "severity": s["severity"]})
            except Exception as e:
                skipped.append({"zone": s["zone_id"], "reason": str(e)[:120]})
        return {"evaluated": len(scores), "fired": fired, "skipped": skipped,
                "cooldown_min": COOLDOWN_MIN}
    except Exception as e:
        return {"evaluated": 0, "fired": [], "skipped": [],
                "error": str(e)[:200]}
