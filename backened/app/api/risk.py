"""
Risk API routes for GEO-SENTINEL.

Provides:
    - Risk map
    - Zone information
    - Risk history
    - Rainfall observations
    - Soil-moisture observations
    - Explainability
    - Sentinel-1 SAR information
    - Historical landslides
    - Model status
"""

import datetime as dt

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from ..database import get_db
from ..models_db import (
    Zone,
    RiskScore,
    RainfallObservation,
    SoilMoistureObservation,
    LandslideEvent,
)

from ..services import sim
from ..ml.mamba_model import get_temporal_model


router = APIRouter()


# =============================================================
# RISK MAP
# =============================================================

@router.get("/risk/map")
def risk_map(
    t: int = Query(24, ge=24, le=168),
    db: Session = Depends(get_db),
):
    """
    Run the complete risk pipeline at simulated time t.

    Demo Monsoon Event scrubber:
        24 <= t <= 168 hours
    """

    return sim.run_pipeline(t)


# =============================================================
# ZONES
# =============================================================

@router.get("/zones")
def zones(
    db: Session = Depends(get_db),
):
    """
    Return all monitored zones.
    """

    return [
        {
            "id": z.id,
            "name": z.name,
            "district": z.district,
            "lat": z.latitude,
            "lng": z.longitude,
            "slope": z.slope,
            "elevation": z.elevation,
            "population": z.population,
            "sar_acquisition_date": z.sar_acquisition_date,
            "sar_change_score": z.sar_change_score,
        }
        for z in db.query(Zone).all()
    ]


# =============================================================
# RISK HISTORY
# =============================================================

@router.get("/risk/{zone_id}/history")
def risk_history(
    zone_id: str,
    db: Session = Depends(get_db),
):
    """
    Return historical risk scores for a zone.
    """

    rows = (
        db.query(RiskScore)
        .filter(RiskScore.zone_id == zone_id)
        .order_by(RiskScore.timestamp)
        .all()
    )

    return [
        {
            "timestamp": r.timestamp.isoformat(),
            "risk_score": r.risk_score,
            "static": r.static_score,
            "dynamic": r.dynamic_score,
            "severity": r.severity,
            "escalated": r.escalated,
        }
        for r in rows
    ]


# =============================================================
# RAINFALL
# =============================================================

@router.get("/risk/{zone_id}/rainfall")
def zone_rainfall(
    zone_id: str,
    db: Session = Depends(get_db),
):
    """
    Return rainfall observations for a zone.

    Mock observations are explicitly marked as DEMO_DATA.
    """

    rows = (
        db.query(RainfallObservation)
        .filter(RainfallObservation.zone_id == zone_id)
        .order_by(RainfallObservation.timestamp)
        .all()
    )

    if not rows:
        return {
            "state": "empty",
            "detail": (
                "Rainfall data unavailable — "
                "no valid observations."
            ),
        }

    return {
        "state": "ok",
        "freshness": (
            "DEMO DATA — simulated IMD rainfall observations."
        ),
        "observations": [
            {
                "timestamp": r.timestamp.isoformat(),
                "rainfall_mm_per_hr": r.rainfall_mm_per_hr,
                "quality_flag": getattr(
                    r,
                    "quality_flag",
                    "DEMO_DATA",
                ),
            }
            for r in rows
        ],
    }


# =============================================================
# SOIL MOISTURE
# =============================================================

@router.get("/risk/{zone_id}/soil-moisture")
def zone_soil(
    zone_id: str,
    db: Session = Depends(get_db),
):
    """
    Return SMAP soil-moisture observations.

    SMAP is a coarse regional proxy and is not an
    in-situ soil-moisture sensor.
    """

    rows = (
        db.query(SoilMoistureObservation)
        .filter(
            SoilMoistureObservation.zone_id == zone_id
        )
        .order_by(
            SoilMoistureObservation.timestamp
        )
        .all()
    )

    return {
        "state": "ok" if rows else "empty",
        "label": (
            "Regional SMAP soil-moisture proxy — "
            "coarse resolution, not an in-situ sensor."
        ),
        "freshness": (
            "Periodic satellite-derived observation; "
            "not continuous live monitoring."
        ),
        "observations": [
            {
                "timestamp": r.timestamp.isoformat(),
                "soil_moisture": r.soil_moisture,
                "quality_flag": getattr(
                    r,
                    "quality_flag",
                    "DEMO_DATA",
                ),
            }
            for r in rows[-48:]
        ],
    }


# =============================================================
# EXPLANATION
# =============================================================

@router.get("/risk/{zone_id}/explanation")
def zone_explanation(
    zone_id: str,
    t: int = Query(168, ge=24, le=168),
):
    """
    Return risk score, severity, drivers and explanation
    for a zone at the requested simulated time.
    """

    results = sim.run_pipeline(t)

    result = next(
        (
            r
            for r in results
            if r["zone_id"] == zone_id
        ),
        None,
    )

    if not result:
        return {
            "error": "zone not found"
        }

    return {
        "risk_score": result["risk_score"],
        "severity": result["severity"],
        "drivers": result["drivers"],
        "summary": result["summary"],
        "model_versions": result["model_versions"],
    }


# =============================================================
# SENTINEL-1 SAR
# =============================================================

@router.get("/risk/{zone_id}/satellite")
def zone_sar(
    zone_id: str,
    db: Session = Depends(get_db),
):
    """
    Return Sentinel-1 acquisition metadata and
    SAR change score.
    """

    z = db.get(Zone, zone_id)

    if z is None:
        return {
            "error": "zone not found"
        }

    return {
        "acquisition_date": z.sar_acquisition_date,
        "previous_acquisition_date": (
            z.sar_previous_acquisition_date
        ),
        "change_score": z.sar_change_score,
        "honesty_note": (
            "Sentinel-1 is a periodic sensor — "
            "this is NOT live monitoring. "
            "Missing SAR is never treated as zero change."
        ),
    }


# =============================================================
# HISTORICAL LANDSLIDES
# =============================================================

@router.get("/landslides")
def landslides(
    db: Session = Depends(get_db),
):
    """
    Return historical landslide inventory.
    """

    events = (
        db.query(LandslideEvent)
        .order_by(LandslideEvent.event_date)
        .all()
    )

    return [
        {
            "zone_id": event.zone_id,
            "event_date": event.event_date.isoformat(),
            "type": event.landslide_type,
            "trigger": getattr(
                event,
                "trigger",
                None,
            ),
            "source": event.source,
        }
        for event in events
    ]


# =============================================================
# MODEL STATUS
# =============================================================

@router.get("/model/status")
def model_status():
    """
    Return the status of the temporal model and
    model-version metadata.
    """

    tm = get_temporal_model()

    return {
        "temporal_backend": tm.backend(),
        "note": (
            "Fallback is explicit. If PyTorch is unavailable, "
            "the mock heuristic is flagged and is never silently "
            "presented as Mamba."
        ),
        "versions": {
            "rf": "rf_2026_01",
            "mamba": "mamba_2026_01",
            "fusion": "fusion_v1",
        },
        "validation": (
            "Spatial-block CV; temporal split "
            "leakage-controlled."
        ),
    }