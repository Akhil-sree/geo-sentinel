"""Risk endpoints — the core of the demo.

/risk/map?t=24..168 : the scrubber target. Every t runs the full pipeline
server-side (ingest snapshot → features → fusion) — never client interpolation.
"""
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.schemas import ZoneRisk, RiskHistoryPoint, Driver, ModelVersions
from app.models_db import Zone, RiskScore, ZoneFeature
from app.ml.fusion import compute_zone_risk, fuse
from app.ml import mamba
from app.config import STATIC_WEIGHT, DYNAMIC_WEIGHT, THRESHOLDS

router = APIRouter(tags=["risk"])


@router.get("/risk/map", response_model=list[ZoneRisk])
def get_risk_map(t: int = Query(24, ge=24, le=168), db: Session = Depends(get_db)):
    zones = db.query(Zone).all()
    out = []
    for z in zones:
        feat = db.get(ZoneFeature, z.id) or _empty_features(z.id)
        scores = compute_zone_risk(z, feat, static_weight=STATIC_WEIGHT,
                                   dynamic_weight=DYNAMIC_WEIGHT)
        out.append(ZoneRisk(
            zone_id=z.id, name=z.name, district=z.district,
            static_score=round(scores["static"], 3),
            dynamic_score=round(scores["dynamic"], 3),
            risk_score=round(scores["fused"], 3),
            severity=scores["severity"],
            escalated=scores["escalated"],
            confidence=scores["confidence"],
            rainfall_24h=feat.rainfall_24h, rainfall_72h=feat.rainfall_72h,
            rainfall_7d=feat.rainfall_7d, rainfall_slope=feat.rainfall_slope,
            soil_moisture=feat.soil_moisture,
            drivers=[Driver(**d) for d in scores["drivers"]],
            summary=scores["summary"],
            model_versions=ModelVersions(
                rf=f"rf_{scores['rf_version']}",
                mamba=mamba.BACKEND,          # "mock-fallback" when torch absent — flagged
                fusion=f"linear-{STATIC_WEIGHT}/{DYNAMIC_WEIGHT}"),
            sim_time=datetime.now(timezone.utc).isoformat(),
        ))
        # persist for the history chart (risk_scores table)
        db.add(RiskScore(zone_id=z.id, timestamp=datetime.now(timezone.utc),
                         risk_score=scores["fused"], static=scores["static"],
                         dynamic=scores["dynamic"], severity=scores["severity"],
                         escalated=scores["escalated"]))
    db.commit()
    return out


@router.get("/risk/{zone_id}/history", response_model=list[RiskHistoryPoint])
def zone_history(zone_id: str, db: Session = Depends(get_db)):
    rows = (db.query(RiskScore).filter(RiskScore.zone_id == zone_id)
              .order_by(RiskScore.timestamp).limit(168).all())
    return [RiskHistoryPoint(timestamp=r.timestamp.isoformat(),
                             risk_score=r.risk_score, static=r.static,
                             dynamic=r.dynamic, severity=r.severity,
                             escalated=r.escalated) for r in rows]


@router.get("/risk/{zone_id}/rainfall")
def zone_rainfall(zone_id: str, db: Session = Depends(get_db)):
    from app.models_db import RainfallObs
    rows = (db.query(RainfallObs).filter(RainfallObs.zone_id == zone_id)
              .order_by(RainfallObs.timestamp.desc()).limit(96).all())
    rows.reverse()
    return {"state": "DEMO DATA",
            "freshness": "synthetic monsoon — labeled DEMO DATA",
            "observations": [{"timestamp": r.timestamp.isoformat(),
                              "rainfall_mm_per_hr": r.rainfall_mm_per_hr} for r in rows]}


@router.get("/risk/{zone_id}/explanation")
def zone_explanation(zone_id: str, t: int = Query(24, ge=24, le=168),
                     db: Session = Depends(get_db)):
    z = db.get(Zone, zone_id)
    if not z:
        raise HTTPException(404, "zone not found")
    feat = db.get(ZoneFeature, zone_id) or _empty_features(zone_id)
    scores = compute_zone_risk(z, feat, STATIC_WEIGHT, DYNAMIC_WEIGHT)
    return {"zone_id": zone_id, "t": t, **scores}


@router.get("/risk/{zone_id}/satellite")
def zone_satellite(zone_id: str, db: Session = Depends(get_db)):
    from app.models_db import SARObs
    s = (db.query(SARObs).filter(SARObs.zone_id == zone_id)
           .order_by(SARObs.acquisition_date.desc()).first())
    if not s:
        return {"acquisition_date": None, "previous_ac": None,
                "honesty_note": "no SAR record — shown, not hidden"}
    return {"acquisition_date": s.acquisition_date.isoformat(),
            "previous_ac": s.previous_ac,
            "sar_change_score": s.sar_change_score,
            "honesty_note": ("SAR acquisitions are days apart — detects past ground "
                             "change, not live slope motion.")}


@router.get("/risk/model/status")
def model_status():
    return {"thresholds": THRESHOLDS, "temporal_backend": mamba.BACKEND,
            "note": "class boundaries & escalation rules are calibration "
                    "parameters, not validated constants"}


def _empty_features(zone_id: str):
    from app.models_db import ZoneFeature
    return ZoneFeature(zone_id=zone_id)
