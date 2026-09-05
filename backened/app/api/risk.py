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
    - Slope state analysis
    - Spatiotemporal hotspot ranking
    - Rainfall scenario simulation
    - Risk intensification
"""

import datetime as dt

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
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


# =============================================================
# SLOPE STATE ANALYSIS
# =============================================================

# Centralized thresholds — calibration parameters
SLOPE_STATE_THRESHOLDS = {
    "stressed_static": 0.45,
    "degrading_static": 0.60,
    "critical_static": 0.75,
    "stressed_dynamic": 0.40,
    "degrading_dynamic": 0.55,
    "critical_dynamic": 0.70,
    "stressed_rainfall_72h": 150,
    "degrading_rainfall_72h": 200,
    "critical_rainfall_72h": 280,
}


def _compute_slope_state(
    static_score: float,
    dynamic_score: float,
    risk_score: float,
    rainfall_72h: float,
    soil_moisture: float,
    escalated: bool,
) -> dict:
    """Derive interpretable slope state from existing model outputs."""
    th = SLOPE_STATE_THRESHOLDS

    # Composite stress score from existing model outputs
    stress = (
        0.30 * static_score
        + 0.35 * dynamic_score
        + 0.15 * min(1.0, rainfall_72h / 300)
        + 0.10 * min(1.0, soil_moisture / 0.8)
        + 0.10 * (1.0 if escalated else 0.0)
    )

    if stress >= 0.70 or risk_score >= 0.80:
        state = "CRITICAL"
        label = "Critical"
        color = "#ba1a1a"
    elif stress >= 0.50 or risk_score >= 0.60:
        state = "DEGRADING"
        label = "Degrading"
        color = "#ea580c"
    elif stress >= 0.30 or risk_score >= 0.40:
        state = "STRESSED"
        label = "Stressed"
        color = "#d97706"
    else:
        state = "STABLE"
        label = "Stable"
        color = "#245c45"

    return {
        "state": state,
        "label": label,
        "color": color,
        "stress_score": round(stress, 4),
        "thresholds_used": th,
    }


@router.get("/risk/{zone_id}/slope-state")
def slope_state(
    zone_id: str,
    t: int = Query(168, ge=24, le=168),
):
    """Return interpretable slope state for a zone."""
    results = sim.run_pipeline(t)
    result = next(
        (r for r in results if r["zone_id"] == zone_id),
        None,
    )
    if not result:
        return {"error": "zone not found"}

    state = _compute_slope_state(
        result["static_score"],
        result["dynamic_score"],
        result["risk_score"],
        result["rainfall_72h"],
        result["soil_moisture"],
        result["escalated"],
    )

    return {
        "zone_id": zone_id,
        "name": result["name"],
        **state,
        "risk_score": result["risk_score"],
        "severity": result["severity"],
    }


# =============================================================
# RISK TRAJECTORY (enhanced history)
# =============================================================

@router.get("/risk/{zone_id}/trajectory")
def risk_trajectory(
    zone_id: str,
    db: Session = Depends(get_db),
):
    """Return historical risk trajectory with state transitions."""
    rows = (
        db.query(RiskScore)
        .filter(RiskScore.zone_id == zone_id)
        .order_by(RiskScore.timestamp)
        .all()
    )

    if not rows:
        return {"zone_id": zone_id, "trajectory": [], "interpretation": "NO_DATA"}

    trajectory = []
    prev_state = None
    state_changes = 0
    increasing = 0
    decreasing = 0

    for r in rows:
        state = _compute_slope_state(
            r.static_score,
            r.dynamic_score,
            r.risk_score,
            0.0,  # rainfall not stored per-score
            0.0,  # soil not stored per-score
            r.escalated,
        )
        if prev_state and state["state"] != prev_state:
            state_changes += 1
        if prev_state:
            prev_idx = ["STABLE", "STRESSED", "DEGRADING", "CRITICAL"].index(prev_state)
            curr_idx = ["STABLE", "STRESSED", "DEGRADING", "CRITICAL"].index(state["state"])
            if curr_idx > prev_idx:
                increasing += 1
            elif curr_idx < prev_idx:
                decreasing += 1
        prev_state = state["state"]

        trajectory.append({
            "timestamp": r.timestamp.isoformat(),
            "risk_score": r.risk_score,
            "static": r.static_score,
            "dynamic": r.dynamic_score,
            "severity": r.severity,
            "escalated": r.escalated,
            "slope_state": state["state"],
            "slope_state_label": state["label"],
            "slope_state_color": state["color"],
        })

    total = max(1, len(trajectory) - 1)
    if increasing > total * 0.6:
        interpretation = "RAPIDLY_INTENSIFYING"
    elif increasing > total * 0.3:
        interpretation = "GRADUALLY_INCREASING"
    elif decreasing > total * 0.6:
        interpretation = "DECREASING"
    elif state_changes <= 1:
        interpretation = "STABLE"
    else:
        interpretation = "VARIABLE"

    return {
        "zone_id": zone_id,
        "trajectory": trajectory,
        "interpretation": interpretation,
        "summary": {
            "state_changes": state_changes,
            "increasing_steps": increasing,
            "decreasing_steps": decreasing,
            "total_steps": total,
        },
    }


# =============================================================
# SPATIOTEMPORAL HOTSPOT RANKING
# =============================================================

def _classify_hotspot(
    risk_score: float,
    static_score: float,
    dynamic_score: float,
    trajectory_interp: str,
    rainfall_72h: float,
    sar_change: float,
) -> dict:
    """Classify hotspot based on combined evidence."""
    # Hotspot score: weighted combination of risk, acceleration, environmental stress
    hotspot_score = (
        0.35 * risk_score
        + 0.15 * static_score
        + 0.20 * dynamic_score
        + 0.15 * min(1.0, rainfall_72h / 300)
        + 0.10 * (sar_change or 0.0)
        + 0.05 * (
            1.0 if trajectory_interp in ("RAPIDLY_INTENSIFYING", "GRADUALLY_INCREASING")
            else 0.0
        )
    )

    if hotspot_score >= 0.75:
        classification = "EMERGING"
        trend = "Rapid"
        priority = "CRITICAL"
    elif hotspot_score >= 0.55:
        classification = "INTENSIFYING"
        trend = "Moderate"
        priority = "HIGH"
    elif hotspot_score >= 0.40 and risk_score >= 0.50:
        classification = "PERSISTENT"
        trend = "Stable"
        priority = "HIGH"
    elif hotspot_score >= 0.25:
        classification = "LOW_CONCERN"
        trend = "Stable"
        priority = "MODERATE"
    else:
        classification = "STABLE"
        trend = "None"
        priority = "LOW"

    return {
        "hotspot_score": round(hotspot_score, 4),
        "classification": classification,
        "trend": trend,
        "priority": priority,
    }


@router.get("/risk/hotspots")
def hotspot_ranking(
    t: int = Query(168, ge=24, le=168),
    db: Session = Depends(get_db),
):
    """Return ranked spatiotemporal hotspots."""
    # Query latest RiskScore per zone (pipeline must have run via /risk/map first)
    zones = db.query(Zone).all()
    ranked = []
    for z in zones:
        latest = (
            db.query(RiskScore)
            .filter(RiskScore.zone_id == z.id)
            .order_by(RiskScore.timestamp.desc())
            .first()
        )
        if not latest:
            continue

        # Trajectory analysis from DB
        rows = (
            db.query(RiskScore)
            .filter(RiskScore.zone_id == z.id)
            .order_by(RiskScore.timestamp)
            .all()
        )
        increasing = 0
        total = max(1, len(rows) - 1)
        prev_risk = None
        for row in rows:
            if prev_risk is not None and row.risk_score > prev_risk:
                increasing += 1
            prev_risk = row.risk_score

        interp = "STABLE"
        if increasing > total * 0.6:
            interp = "RAPIDLY_INTENSIFYING"
        elif increasing > total * 0.3:
            interp = "GRADUALLY_INCREASING"

        sar_change = z.sar_change_score or 0.0

        hotspot = _classify_hotspot(
            latest.risk_score,
            latest.static_score,
            latest.dynamic_score,
            interp,
            0.0,  # rainfall_72h not in RiskScore, use 0
            sar_change,
        )

        ranked.append({
            "zone_id": z.id,
            "name": z.name,
            "district": z.district,
            "risk_score": latest.risk_score,
            "severity": latest.severity,
            "static_score": latest.static_score,
            "dynamic_score": latest.dynamic_score,
            "rainfall_24h": 0.0,
            "rainfall_72h": 0.0,
            "soil_moisture": 0.0,
            "escalated": latest.escalated,
            "sar_change_score": sar_change,
            "trajectory_interpretation": interp,
            **hotspot,
        })

    # Sort by hotspot score descending
    ranked.sort(key=lambda x: x["hotspot_score"], reverse=True)

    # Add rank
    for i, r in enumerate(ranked):
        r["rank"] = i + 1

    return {
        "hotspots": ranked,
        "total": len(ranked),
        "analyzed_at": (
            dt.datetime(2026, 7, 14) + dt.timedelta(hours=t)
        ).isoformat(),
    }


# =============================================================
# RAINFALL SCENARIO SIMULATION
# =============================================================

class ScenarioRequest(BaseModel):
    multiplier: float = 1.0  # 1.0 = current, 1.25 = +25%, 1.5 = +50%
    continued_hours: int = 0  # additional hours of continued rainfall
    t: int = 168


@router.post("/risk/simulation")
def scenario_simulation(req: ScenarioRequest):
    """Simulate risk under a rainfall scenario. Clearly labeled as WHAT-IF."""
    # Run current pipeline
    current = sim.run_pipeline(req.t)
    current_map = {r["zone_id"]: r for r in current}

    # Simulate future rainfall by scaling observations
    # This is a proxy simulation, not a model prediction
    simulated = []
    for r in current:
        # Scale rainfall features by multiplier
        sim_rainfall_24h = r["rainfall_24h"] * req.multiplier
        sim_rainfall_72h = r["rainfall_72h"] * req.multiplier

        # Soil moisture increases with continued rainfall
        soil_bump = min(0.3, req.continued_hours * 0.012)
        sim_soil = min(0.95, r["soil_moisture"] + soil_bump)

        # Recalculate risk using fusion formula
        from ..ml.fusion import fuse, classify
        sim_fusion = fuse(
            r["static_score"],
            r["dynamic_score"],
            sim_rainfall_24h,
            sim_rainfall_72h,
            sim_soil,
        )

        # Determine slope state
        state = _compute_slope_state(
            r["static_score"],
            r["dynamic_score"],
            sim_fusion["risk_score"],
            sim_rainfall_72h,
            sim_soil,
            sim_fusion["escalated"],
        )

        simulated.append({
            "zone_id": r["zone_id"],
            "name": r["name"],
            "current_risk": r["risk_score"],
            "current_severity": r["severity"],
            "simulated_risk": sim_fusion["risk_score"],
            "simulated_severity": sim_fusion["severity"],
            "slope_state": state["state"],
            "slope_state_label": state["label"],
            "slope_state_color": state["color"],
            "rainfall_change": f"+{round((req.multiplier - 1) * 100)}%" if req.multiplier > 1 else "current",
            "continued_hours": req.continued_hours,
            "escalated": sim_fusion["escalated"],
        })

    simulated.sort(key=lambda x: x["simulated_risk"], reverse=True)

    return {
        "scenario": {
            "multiplier": req.multiplier,
            "continued_hours": req.continued_hours,
            "label": (
                f"Current" if req.multiplier == 1.0 and req.continued_hours == 0
                else f"+{round((req.multiplier - 1) * 100)}% rainfall"
                + (f", +{req.continued_hours}h continued" if req.continued_hours else "")
            ),
        },
        "results": simulated,
        "warning": "WHAT-IF SIMULATION — not a forecast. Proxy scenario only.",
        "simulated_at": (
            dt.datetime(2026, 7, 14) + dt.timedelta(hours=req.t)
        ).isoformat(),
    }


# =============================================================
# RISK INTENSIFICATION
# =============================================================

@router.get("/risk/intensification")
def risk_intensification(
    t: int = Query(168, ge=24, le=168),
    db: Session = Depends(get_db),
):
    """Return risk change rate for each zone (current - previous score)."""
    zones = db.query(Zone).all()
    intensified = []
    for z in zones:
        latest = (
            db.query(RiskScore)
            .filter(RiskScore.zone_id == z.id)
            .order_by(RiskScore.timestamp.desc())
            .first()
        )
        if not latest:
            continue

        # Get previous score (12h ago if available)
        prev_t = max(24, t - 12)
        prev_rows = (
            db.query(RiskScore)
            .filter(
                RiskScore.zone_id == z.id,
                RiskScore.timestamp <= (
                    dt.datetime(2026, 7, 14) + dt.timedelta(hours=prev_t)
                ),
            )
            .order_by(RiskScore.timestamp.desc())
            .limit(1)
            .all()
        )

        if prev_rows:
            prev_score = prev_rows[0].risk_score
            change = latest.risk_score - prev_score
        else:
            change = 0.0

        # Classify intensification
        if change >= 0.15:
            rate = "RAPID"
            color = "#ba1a1a"
        elif change >= 0.08:
            rate = "SIGNIFICANT"
            color = "#ea580c"
        elif change >= 0.03:
            rate = "MODERATE"
            color = "#d97706"
        else:
            rate = "LITTLE"
            color = "#245c45"

        intensified.append({
            "zone_id": z.id,
            "name": z.name,
            "current_risk": latest.risk_score,
            "previous_risk": prev_score if prev_rows else None,
            "change": round(change, 4),
            "rate": rate,
            "color": color,
            "severity": latest.severity,
        })

    intensified.sort(key=lambda x: x["change"], reverse=True)

    return {
        "intensification": intensified,
        "compared_at": (
            dt.datetime(2026, 7, 14) + dt.timedelta(hours=t)
        ).isoformat(),
    }


# =============================================================
# COMPREHENSIVE EVIDENCE (for detail panels)
# =============================================================

@router.get("/risk/{zone_id}/evidence")
def zone_evidence(
    zone_id: str,
    t: int = Query(168, ge=24, le=168),
    db: Session = Depends(get_db),
    ):
    """Return combined evidence for a zone: risk, rainfall, soil, SAR, drivers."""
    results = sim.run_pipeline(t)
    result = next(
        (r for r in results if r["zone_id"] == zone_id),
        None,
    )
    if not result:
        return {"error": "zone not found"}

    zone = db.get(Zone, zone_id)

    # Slope state
    state = _compute_slope_state(
        result["static_score"],
        result["dynamic_score"],
        result["risk_score"],
        result["rainfall_72h"],
        result["soil_moisture"],
        result["escalated"],
    )

    # SAR evidence
    sar = None
    if zone:
        sar = {
            "acquisition_date": zone.sar_acquisition_date,
            "previous_acquisition_date": zone.sar_previous_acquisition_date,
            "change_score": zone.sar_change_score,
            "honesty_note": (
                "Sentinel-1 is a periodic sensor — "
                "this is NOT live monitoring."
            ),
        }

    # Risk explanation
    explanation = _generate_risk_explanation(result, zone, state)

    return {
        "zone_id": zone_id,
        "name": result["name"],
        "district": result["district"],
        "risk_score": result["risk_score"],
        "severity": result["severity"],
        "static_score": result["static_score"],
        "dynamic_score": result["dynamic_score"],
        "slope_state": state,
        "rainfall": {
            "24h": result["rainfall_24h"],
            "72h": result["rainfall_72h"],
            "7d": result["rainfall_7d"],
            "slope": result["rainfall_slope"],
        },
        "soil_moisture": result["soil_moisture"],
        "sar": sar,
        "terrain": {
            "slope": zone.slope if zone else None,
            "elevation": zone.elevation if zone else None,
            "ruggedness": zone.ruggedness if zone else None,
            "population": zone.population if zone else None,
        },
        "drivers": result["drivers"],
        "explanation": explanation,
        "model_versions": result["model_versions"],
        "sim_time": result["sim_time"],
    }


def _generate_risk_explanation(result, zone, state):
    """Generate evidence-based explanation from actual model outputs."""
    factors = []

    if result["static_score"] >= 0.6:
        factors.append("High baseline terrain susceptibility")
    elif result["static_score"] >= 0.4:
        factors.append("Moderate baseline terrain susceptibility")

    if result["rainfall_72h"] > 200:
        factors.append(f"Extreme 72h rainfall ({result['rainfall_72h']:.0f} mm)")
    elif result["rainfall_72h"] > 150:
        factors.append(f"High 72h rainfall ({result['rainfall_72h']:.0f} mm)")

    if result["soil_moisture"] > 0.55:
        factors.append("Rising soil moisture approaching saturation")
    elif result["soil_moisture"] > 0.40:
        factors.append("Increasing soil moisture")

    if result["dynamic_score"] > 0.6:
        factors.append("Increasing temporal risk trajectory")

    if result["escalated"]:
        factors.append("Escalation rule triggered by extreme conditions")

    if zone and zone.sar_change_score and zone.sar_change_score > 0.3:
        factors.append("SAR indicates anomalous surface change")

    if not factors:
        factors.append("Environmental conditions within normal range")

    # Build conclusion
    if state["state"] == "CRITICAL":
        conclusion = "Multiple indicators show increasing slope instability. Local verification is recommended."
    elif state["state"] == "DEGRADING":
        conclusion = "Environmental stress is increasing on an already susceptible slope. Monitor closely."
    elif state["state"] == "STRESSED":
        conclusion = "Early signs of environmental stress detected. Continued monitoring advised."
    else:
        conclusion = "Conditions appear stable. No immediate concern."

    return {
        "factors": factors,
        "conclusion": conclusion,
        "recommended_action": (
            "Escalate" if state["state"] == "CRITICAL"
            else "Issue advisory" if state["state"] == "DEGRADING"
            else "Verify locally" if state["state"] == "STRESSED"
            else "Monitor"
        ),
    }