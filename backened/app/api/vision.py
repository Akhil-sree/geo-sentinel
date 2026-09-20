"""Vision API endpoints — image upload, SegFormer analysis, observation records."""
import datetime as dt
import json
import os

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from sqlalchemy.orm import Session

from app.config import MEDIA_DIR
from app.database import get_db
from app.ml.vision.inference import analyze_image
from app.ml.vision.model import model_info
from app.models_db import VisionObservation
from app.services.vision_observation import corroborate

router = APIRouter(tags=["vision"])


@router.post("/vision/analyze")
async def analyze_report_image(
    file: UploadFile = File(...),
    report_id: str = Form(None),
    latitude: float = Form(None),
    longitude: float = Form(None),
    zone_id: str = Form(None),
    db: Session = Depends(get_db),
):
    """Upload an image for SegFormer analysis. Produces segmentation mask + observation record."""
    from app.api.reports import ALLOWED as _ALLOWED
    from app.api.reports import MAX_SIZE as _MAX
    from app.api.reports import _check_magic as _magic
    from app.auth import rate_limit as _rl
    _rl("vision", limit=30)
    content_type = file.content_type or ""
    if content_type not in _ALLOWED or not content_type.startswith("image/"):
        raise HTTPException(status_code=415, detail="Only JPEG/PNG/WEBP images are allowed")
    # bounded read: 8 MB cap enforced during streaming, not after
    chunks, total = [], 0
    while True:
        piece = await file.read(65536)
        if not piece:
            break
        total += len(piece)
        if total > _MAX:
            raise HTTPException(status_code=413, detail="Image exceeds 8 MB")
        chunks.append(piece)
    content = b"".join(chunks)
    if not _magic(content[:32], content_type):
        raise HTTPException(status_code=422, detail="File content does not match declared image type")

    result = analyze_image(
        image_bytes=content,
        content_type=content_type,
        report_id=report_id,
        latitude=latitude,
        longitude=longitude,
        zone_id=zone_id,
    )

    # Save image to media (server-derived safe name — client filename never trusted)
    import secrets as _secrets
    image_path = (f"observations/{dt.datetime.now().strftime('%Y%m%d_%H%M%S')}"
                  f"_{_secrets.token_hex(6)}{_ALLOWED[content_type]}")
    full_path = os.path.join(MEDIA_DIR, image_path)
    os.makedirs(os.path.dirname(full_path), exist_ok=True)
    with open(full_path, "wb") as f:
        f.write(content)

    # Store observation record
    obs = VisionObservation(
        report_id=report_id,
        model_name=result.get("model_name", "segformer-b0"),
        model_mode=result.get("model_mode", "demo"),
        confidence=result["confidence"],
        pixel_ratio=result["affected_pixel_ratio"],
        severity=result["observation_severity"],
        landslide_detected=result["landslide_detected"],
        geometry_json=json.dumps(result.get("geometry")) if result.get("geometry") else None,
        image_path=image_path,
        zone_id=zone_id,
        latitude=latitude,
        longitude=longitude,
        warning=result.get("warning"),
    )
    db.add(obs)
    db.commit()
    db.refresh(obs)

    # Corroborate with existing risk if zone_id provided
    corroboration = None
    if zone_id:
        corroboration = corroborate(db, zone_id, result["observation_severity"], result["confidence"])

    return {
        "observation_id": obs.id,
        **result,
        "corroboration": corroboration,
    }


@router.get("/vision/observations")
def list_observations(
    limit: int = 50,
    db: Session = Depends(get_db),
):
    """List recent vision observations."""
    rows = (
        db.query(VisionObservation)
        .order_by(VisionObservation.created_at.desc())
        .limit(limit)
        .all()
    )
    return {
        "observations": [
            {
                "id": r.id,
                "report_id": r.report_id,
                "model_name": r.model_name,
                "model_mode": r.model_mode,
                "confidence": r.confidence,
                "pixel_ratio": r.pixel_ratio,
                "severity": r.severity,
                "landslide_detected": r.landslide_detected,
                "zone_id": r.zone_id,
                "latitude": r.latitude,
                "longitude": r.longitude,
                "image_path": r.image_path,
                "warning": r.warning,
                "geometry": json.loads(r.geometry_json) if r.geometry_json else None,
                "created_at": r.created_at.isoformat() if r.created_at else None,
            }
            for r in rows
        ],
        "total": len(rows),
    }


@router.get("/vision/observations/{obs_id}")
def get_observation(obs_id: int, db: Session = Depends(get_db)):
    """Get a single observation by ID."""
    r = db.get(VisionObservation, obs_id)
    if not r:
        raise HTTPException(status_code=404, detail="Observation not found")
    return {
        "id": r.id,
        "report_id": r.report_id,
        "model_name": r.model_name,
        "model_mode": r.model_mode,
        "confidence": r.confidence,
        "pixel_ratio": r.pixel_ratio,
        "severity": r.severity,
        "landslide_detected": r.landslide_detected,
        "zone_id": r.zone_id,
        "latitude": r.latitude,
        "longitude": r.longitude,
        "image_path": r.image_path,
        "warning": r.warning,
        "geometry": json.loads(r.geometry_json) if r.geometry_json else None,
        "created_at": r.created_at.isoformat() if r.created_at else None,
    }


@router.get("/vision/reports/{report_id}")
def get_report_observations(report_id: str, db: Session = Depends(get_db)):
    """Get all observations associated with a citizen report."""
    rows = (
        db.query(VisionObservation)
        .filter(VisionObservation.report_id == report_id)
        .order_by(VisionObservation.created_at.desc())
        .all()
    )
    return {
        "report_id": report_id,
        "observations": [
            {
                "id": r.id,
                "model_name": r.model_name,
                "model_mode": r.model_mode,
                "confidence": r.confidence,
                "pixel_ratio": r.pixel_ratio,
                "severity": r.severity,
                "landslide_detected": r.landslide_detected,
                "geometry": json.loads(r.geometry_json) if r.geometry_json else None,
                "created_at": r.created_at.isoformat() if r.created_at else None,
            }
            for r in rows
        ],
        "total": len(rows),
    }


@router.get("/vision/model/status")
def vision_model_status():
    """Return vision model configuration and status."""
    info = model_info()
    return {
        **info,
        "note": (
            "This is a DEMO observation model using pretrained SegFormer-B0 on ADE20K. "
            "It is NOT a trained landslide detector. "
            "A fine-tuned checkpoint is required for production use."
        ),
    }


@router.get("/vision/corroboration/{zone_id}")
def zone_corroboration(zone_id: str, db: Session = Depends(get_db)):
    """Get the latest observation corroboration for a zone."""
    latest_obs = (
        db.query(VisionObservation)
        .filter(VisionObservation.zone_id == zone_id)
        .order_by(VisionObservation.created_at.desc())
        .first()
    )
    if not latest_obs:
        return {
            "zone_id": zone_id,
            "corroboration": "NO_OBSERVATIONS",
            "explanation": "No visual observations available for this zone.",
        }
    return corroborate(db, zone_id, latest_obs.severity, latest_obs.confidence)
