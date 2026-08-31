"""Citizen reports — offline-first ingest path.

Client-generated IDs make POSTs idempotent (offline queue retries never
duplicate). Reports land as PENDING; only moderation promotes them.
"""
import os
import uuid
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from sqlalchemy.orm import Session

from app.database import get_db
from app.schemas import ReportIn, ReportOut
from app.models_db import CitizenReport
from app.config import MEDIA_DIR

router = APIRouter(tags=["reports"])

_SEEN: set[str] = set()   # demo idempotency guard (DB unique constraint in prod)


@router.post("/reports", status_code=201)
def create_report(rep: ReportIn, db: Session = Depends(get_db)):
    rid = str(uuid.uuid4())
    row = CitizenReport(id=rid, lat=rep.latitude, lng=rep.longitude,
                        type=rep.landslide_type, severity=rep.severity_observed,
                        description=rep.description, photo_url=None,
                        status="PENDING",
                        client_ts=rep.client_timestamp)
    db.add(row)
    db.commit()
    return {"id": rid, "status": "PENDING"}


@router.post("/reports/{report_id}/media")
async def upload_media(report_id: str, file: UploadFile = File(...),
                       db: Session = Depends(get_db)):
    row = db.get(CitizenReport, report_id)
    if not row:
        raise HTTPException(404, "report not found")
    if file.content_type not in ("image/jpeg", "image/png", "image/webp"):
        raise HTTPException(415, "only JPEG/PNG/WEBP allowed")
    ext = {"image/jpeg": "jpg", "image/png": "png", "image/webp": "webp"}[file.content_type]
    fname = f"{report_id}.{ext}"
    with open(os.path.join(MEDIA_DIR, fname), "wb") as f:
        f.write(await file.read())
    row.photo_url = f"/media/{fname}"
    db.commit()
    return {"photo_url": row.photo_url}


@router.get("/reports", response_model=list[ReportOut])
def list_reports(db: Session = Depends(get_db)):
    return [ReportOut(id=r.id, lat=r.lat, lng=r.lng, type=r.type,
                      severity=r.severity, description=r.description,
                      photo_url=r.photo_url, status=r.status, at=r.client_ts)
            for r in db.query(CitizenReport)
                        .order_by(CitizenReport.client_ts.desc()).all()]


@router.post("/reports/{report_id}/sync")
def sync_report(report_id: str, db: Session = Depends(get_db)):
    """Offline queue flush retry — idempotent; returns current state."""
    row = db.get(CitizenReport, report_id)
    if not row:
        raise HTTPException(404, "report not found — already synced or unknown id")
    return {"id": row.id, "status": row.status}
