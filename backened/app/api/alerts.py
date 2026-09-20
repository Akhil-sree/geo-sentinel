"""
Alert API routes.

Provides:
    - Manual alert dispatch
    - Alert delivery history
"""

from datetime import UTC, datetime

from fastapi import APIRouter, Depends, Header, HTTPException, Request
from sqlalchemy.orm import Session

import app.config as cfg

from ..alerts.sms import dispatch_alert
from ..auth import _client_ip, guard, rate_limit, require_role
from ..database import get_db
from ..models_db import Alert, Zone
from ..schemas import SendAlertIn

router = APIRouter()


def _cooldown_ok(db: Session, zone_id: str, severity: str) -> None:
    rank = {"LOW": 0, "MODERATE": 1, "HIGH": 2, "VERY_HIGH": 3}
    last = (db.query(Alert).filter(Alert.zone_id == zone_id)
            .order_by(Alert.created_at.desc()).first())
    if not last or not last.created_at:
        return
    from datetime import timedelta
    age = datetime.now(UTC) - last.created_at.replace(tzinfo=UTC)
    escalated = rank.get(severity, 0) > rank.get(last.severity, 0)
    if age < timedelta(minutes=cfg.ALERT_COOLDOWN_MIN) and not escalated:
        raise HTTPException(status_code=429, detail=(
            f"Alert cooldown active ({cfg.ALERT_COOLDOWN_MIN:.0f} min) — "
            "duplicate suppressed unless severity escalates."))


# =============================================================
# SEND ALERT
# =============================================================

@router.post("/alerts/send")
def send_alert(
    a: SendAlertIn,
    db: Session = Depends(get_db),
    request: Request = None,
    x_api_key: str | None = Header(default=None),
    role: str = Depends(require_role("operator", "admin")),
):
    """
    Send a severity-gated alert to recipients associated
    with the selected zone. Guarded: operator/admin role when keys
    are configured, rate-limited, cooldown-deduplicated.
    """
    rate_limit(_client_ip(request))
    auth = guard(x_api_key)

    zone = db.get(Zone, a.zone_id)

    if zone is None:
        raise HTTPException(
            status_code=404,
            detail="Zone not found",
        )

    _cooldown_ok(db, a.zone_id, a.severity)
    out = dispatch_alert(
        a.zone_id,
        a.severity,
        zone.name,
        zone.district,
    )
    out["auth_mode"] = auth["auth_mode"]
    return out


@router.post("/alerts/evaluate")
def evaluate(db: Session = Depends(get_db),
             x_api_key: str | None = Header(default=None),
             role: str = Depends(require_role("operator", "admin"))):
    """Run automatic threshold evaluation (worker calls this on schedule)."""
    from app.ingest.autoeval import auto_evaluate_alerts
    guard(x_api_key)
    return auto_evaluate_alerts(db)


@router.post("/alerts/{alert_id}/ack")
def ack(alert_id: int, db: Session = Depends(get_db),
        x_api_key: str | None = Header(default=None),
        role: str = Depends(require_role("operator", "admin"))):
    """Acknowledge an alert (escalation workflow). Audited."""
    from app.models_db import AuditLog
    guard(x_api_key)
    al = db.get(Alert, alert_id)
    if not al:
        raise HTTPException(status_code=404, detail="Alert not found")
    al.status = f"{al.status} | ACK"
    db.add(AuditLog(action="ALERT_ACK", detail=f"alert={alert_id} zone={al.zone_id}"))
    db.commit()
    return {"id": alert_id, "status": al.status}


@router.get("/alerts/{alert_id}/lifecycle")
def lifecycle(alert_id: int, db: Session = Depends(get_db)):
    """Explicit alert state machine (Phase 23): TRIGGERED → SENT →
    ACKNOWLEDGED → RESOLVED, derived from the Alert row + audit trail."""
    from app.models_db import AuditLog
    al = db.get(Alert, alert_id)
    if not al:
        raise HTTPException(status_code=404, detail="Alert not found")
    stages = [{"stage": "TRIGGERED",
               "at": al.created_at.isoformat() if al.created_at else None}]
    if al.status and "FAILED" not in al.status:
        stages.append({"stage": "SENT",
                       "at": al.created_at.isoformat() if al.created_at else None,
                       "provider": al.provider, "delivery": al.status})
    for action, stage in (("ALERT_ACK", "ACKNOWLEDGED"),
                          ("ALERT_RESOLVE", "RESOLVED")):
        # Exact token match ("alert=1 " must NOT match "alert=16 ...").
        row = (db.query(AuditLog)
               .filter(AuditLog.action == action,
                       AuditLog.detail.contains(f"alert={alert_id} "))
               .order_by(AuditLog.created_at.desc()).first())
        if row:
            stages.append({"stage": stage,
                           "at": row.created_at.isoformat() if row.created_at else None})
    if al.status and "ACK" in al.status and not any(
            s["stage"] == "ACKNOWLEDGED" for s in stages):
        stages.append({"stage": "ACKNOWLEDGED", "at": None})
    if al.status and "RESOLVED" in al.status and not any(
            s["stage"] == "RESOLVED" for s in stages):
        stages.append({"stage": "RESOLVED", "at": None})
    return {"id": alert_id, "zone_id": al.zone_id, "severity": al.severity,
            "stages": stages, "current": stages[-1]["stage"]}


@router.post("/alerts/{alert_id}/resolve")
def resolve(alert_id: int, db: Session = Depends(get_db),
            x_api_key: str | None = Header(default=None),
            role: str = Depends(require_role("operator", "admin"))):
    """Resolve an alert (closes the lifecycle). Audited."""
    from app.models_db import AuditLog
    guard(x_api_key)
    al = db.get(Alert, alert_id)
    if not al:
        raise HTTPException(status_code=404, detail="Alert not found")
    al.status = f"{al.status} | RESOLVED"
    db.add(AuditLog(action="ALERT_RESOLVE", detail=f"alert={alert_id} zone={al.zone_id}"))
    db.commit()
    return {"id": alert_id, "status": al.status}


# =============================================================
# ALERT HISTORY
# =============================================================

@router.get("/alerts")
def alert_history(
    db: Session = Depends(get_db),
):
    """
    Return the latest 50 alert delivery records.
    """

    alerts = (
        db.query(Alert)
        .order_by(Alert.created_at.desc())
        .limit(50)
        .all()
    )

    return [
        {
            "zone_id": alert.zone_id,
            "severity": alert.severity,
            "to": alert.recipient,
            "name": alert.recipient_name,
            "lang": alert.language,
            "message": alert.message,
            "status": alert.status,
            "provider": alert.provider,
            "at": (
                alert.created_at.isoformat()
                if alert.created_at
                else None
            ),
        }
        for alert in alerts
    ]


@router.get("/alerts/languages")
def alert_languages():
    """Language abstraction status: reviewed vs pending-review (fallback EN).

    Safety-critical text is never machine-translated — as/mni/kha/garo/bn
    drafts stay unserved until native-speaker review flips lang_status.json.
    """
    import json as _json
    import os as _os

    from app.alerts import sms as _sms
    with open(_os.path.join(_sms.TPL_DIR, "lang_status.json"), encoding="utf-8") as f:
        statuses = _json.load(f)
    return {"served": ["en", "hi"], "fallback": "en",
            "statuses": statuses,
            "policy": "Only reviewed templates are served; all others fall back to EN — safety-critical text is never machine-translated"}