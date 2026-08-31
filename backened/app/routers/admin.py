"""Honesty endpoints: data freshness, model metrics, report moderation."""
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.models_db import CitizenReport
from app.ingest.runner import get_freshness_snapshot

router = APIRouter(tags=["admin"])


@router.get("/admin/data")
def data_freshness(db: Session = Depends(get_db)):
    return get_freshness_snapshot(db)


@router.get("/admin/model/metrics")
def model_metrics():
    # served from the training metadata persisted at train time —
    # never hand-copied numbers in the UI
    from app.ml.rf_model import load_metrics
    return load_metrics()


@router.post("/admin/moderate/{report_id}")
def moderate(report_id: str, decision: str, db: Session = Depends(get_db)):
    if decision not in ("VERIFIED", "REJECTED", "USED_FOR_TRAINING"):
        raise HTTPException(422, "decision must be VERIFIED | REJECTED | USED_FOR_TRAINING")
    row = db.get(CitizenReport, report_id)
    if not row:
        raise HTTPException(404, "report not found")
    row.status = decision
    db.commit()
    return {"id": report_id, "status": row.status}
