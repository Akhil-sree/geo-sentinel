"""Alert dispatch — severity-gated, advisory-only language, audit-logged."""
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.models_db import Zone, AlertLog
from app.notify.gating import eligible_for_alert, compose_message
from app.notify.directory import get_directory
from app.providers.sms import get_sms_provider

router = APIRouter(tags=["alerts"])


@router.post("/alerts/send")
def send_alert(zone_id: str, severity: str, lang: str = "en",
               db: Session = Depends(get_db)):
    if not eligible_for_alert(severity):
        raise HTTPException(409, f"severity {severity} below HIGH dispatch threshold")

    zone = db.get(Zone, zone_id)
    if not zone:
        raise HTTPException(404, "zone not found")

    message = compose_message(severity, zone.name, zone.district, lang)
    provider = get_sms_provider()
    results = []
    for recip in get_directory().get(zone_id, []):
        result = provider.send(recip["phone"], message, recip["name"])
        row = AlertLog(zone_id=zone_id, severity=severity, message=message,
                       provider=result["provider"], status=result["status"],
                       to=result["to"], recipient_name=recip["name"], lang=lang,
                       at=result["at"])
        db.add(row)
        results.append(result)
    db.commit()
    return {"sent": len(results), "provider": provider.name, "results": results}


@router.get("/alerts")
def list_alerts(db: Session = Depends(get_db)):
    return [{"severity": a.severity, "zone_id": a.zone_id, "message": a.message,
             "provider": a.provider, "status": a.status, "lang": a.lang,
             "to": a.to, "recipient_name": a.recipient_name, "at": a.at}
            for a in db.query(AlertLog).order_by(AlertLog.at.desc()).limit(100).all()]
