"""
Alert API routes.

Provides:
    - Manual alert dispatch
    - Alert delivery history
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..database import get_db
from ..models_db import Alert, Zone
from ..schemas import AlertOut
from ..alerts.sms import dispatch_alert


router = APIRouter()


# =============================================================
# SEND ALERT
# =============================================================

@router.post("/alerts/send")
def send_alert(
    a: AlertOut,
    db: Session = Depends(get_db),
):
    """
    Send a severity-gated alert to recipients associated
    with the selected zone.
    """

    zone = db.get(Zone, a.zone_id)

    if zone is None:
        raise HTTPException(
            status_code=404,
            detail="Zone not found",
        )

    return dispatch_alert(
        a.zone_id,
        a.severity,
        zone.name,
        zone.district,
    )


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