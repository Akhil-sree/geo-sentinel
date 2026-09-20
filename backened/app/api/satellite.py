"""Satellite integration boundary (Sentinel-1 SAR first-class).

GET  /api/satellite/status  — credential-gated provider state; honest
       NOT_CONFIGURED/AUTH_REQUIRED vs DEMO/MOCK, never fake success
GET  /api/satellite/scenes  — acquisition metadata (SatScene + live-catalog note)
POST /api/satellite/change  — demonstrable SAR change-detection interface:
       takes pre/post change scores, returns delta + landslide-candidate flag.
       Labeled DEMO unless provider credentials mark it OBSERVED.
GET  /api/satellite/features/{zone_id} — stored satellite features

Nothing here enters the production risk path (quarantined by design —
see services/sim.py); features are stored for GIS display + future use.
"""
import os
from datetime import datetime, timezone

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.database import get_db
from app.models_db import SatScene, SatelliteFeature, Zone

router = APIRouter()


def provider_state() -> dict:
    live = os.getenv("SATELLITE_LIVE", "false").lower() == "true"
    user = os.getenv("COPERNICUS_USER", "") or os.getenv("SENTINEL_CLIENT_ID", "")
    provider = os.getenv("SATELLITE_PROVIDER", "demo")
    if provider == "sentinel1" and live and user:
        return {"provider": "sentinel1", "state": "CONFIGURED",
                "detail": "Credentialed Sentinel-1 path enabled — verify via scenes"}
    if provider == "sentinel1" and live and not user:
        return {"provider": "sentinel1", "state": "AUTH_REQUIRED",
                "detail": "Satellite imagery provider configured but credentials unavailable"}
    if provider == "sentinel1" and not live:
        return {"provider": "sentinel1", "state": "NOT_CONFIGURED",
                "detail": "Set SATELLITE_LIVE=true + credentials to enable"}
    return {"provider": "demo", "state": "MOCK",
            "detail": "SATELLITE_DEMO — mock change values, excluded from production risk"}


@router.get("/satellite/status")
def sat_status():
    return provider_state()


@router.get("/satellite/scenes")
def sat_scenes(db: Session = Depends(get_db)):
    rows = db.query(SatScene).order_by(SatScene.start_time.desc()).limit(50).all()
    return {"provider": provider_state(),
            "n": len(rows),
            "note": "Acquisition METADATA only — no imagery processed, nothing enters risk",
            "scenes": [{"granule": r.granule, "zone_id": r.zone_id,
                        "start_time": r.start_time.isoformat() if r.start_time else None,
                        "beam_mode": r.beam_mode, "polarization": r.polarization,
                        "flight_direction": r.flight_direction} for r in rows]}


class ChangeIn(BaseModel):
    zone_id: str
    scene_id: str | None = None
    pre_score: float
    post_score: float
    threshold: float = 0.25


@router.post("/satellite/change")
def sat_change(body: ChangeIn, db: Session = Depends(get_db)):
    """Demonstrable change-detection step: delta + candidate decision.

    Transparent arithmetic (no black box): delta = post − pre;
    candidate = delta ≥ threshold. Stored as MODELED/DEMO feature.
    """
    if not db.query(Zone).filter(Zone.id == body.zone_id).first():
        from fastapi import HTTPException
        raise HTTPException(status_code=422, detail="Unknown zone_id")
    st = provider_state()
    delta = round(body.post_score - body.pre_score, 4)
    candidate = bool(delta >= body.threshold)
    feat = SatelliteFeature(zone_id=body.zone_id,
                            acquisition_date=datetime.now(timezone.utc),
                            scene_id=body.scene_id, change_score=body.post_score,
                            candidate=candidate,
                            status=("OBSERVED" if st["state"] == "CONFIGURED" else "DEMO"),
                            source=("sentinel1" if st["state"] == "CONFIGURED"
                                    else "SATELLITE_DEMO"))
    db.add(feat)
    db.commit()
    return {"zone_id": body.zone_id, "delta": delta, "candidate": candidate,
            "threshold": body.threshold, "method": "delta = post − pre; candidate = delta ≥ threshold",
            "status": feat.status, "feature_id": feat.id,
            "note": "Stored for GIS display; quarantined from production risk"}


@router.get("/satellite/features/{zone_id}")
def sat_features(zone_id: str, db: Session = Depends(get_db)):
    rows = (db.query(SatelliteFeature).filter(SatelliteFeature.zone_id == zone_id)
            .order_by(SatelliteFeature.acquisition_date.desc()).limit(20).all())
    return {"zone_id": zone_id,
            "features": [{"acquisition_date": r.acquisition_date.isoformat(),
                          "scene_id": r.scene_id, "change_score": r.change_score,
                          "candidate": r.candidate, "status": r.status,
                          "source": r.source} for r in rows]}
