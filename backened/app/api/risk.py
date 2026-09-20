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

from fastapi import APIRouter, Depends, HTTPException, Query
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


def _require_zone(db: Session, zone_id: str) -> Zone:
    """Shared 404 contract for every zone-scoped endpoint.

    Unknown zones raise 404 (never HTTP-200 error-dicts); valid zones with
    no observations keep their documented empty states (`state: empty`,
    `[]`, `NO_DATA`). The global frontend banner ignores 404s, so a typo'd
    zone must not flip the app to BACKEND UNAVAILABLE.
    """
    zone = db.get(Zone, zone_id)
    if zone is None:
        raise HTTPException(status_code=404, detail=f"zone not found: {zone_id}")
    return zone


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
            "ruggedness": z.ruggedness,
            "road_proximity": z.road_proximity,
            "drainage_proximity": z.drainage_proximity,
            "settlement_density": z.settlement_density,
            "sar_acquisition_date": z.sar_acquisition_date,
            "sar_change_score": z.sar_change_score,
        }
        for z in db.query(Zone).all()
    ]


@router.get("/landslides/gsi")
def gsi_slides():
    """REAL GSI landslide inventory (865 Meghalaya slides, CC0-1.0).

    Catalog occurrences with coordinates; year-or-unknown resolution —
    for GIS display + spatial features, NOT temporal sequences.
    """
    import csv as _csv
    import os as _os
    fn = _os.path.join(_os.path.dirname(__file__), "..", "..", "data",
                       "processed", "gsi_slides_meghalaya.csv")
    if not _os.path.exists(fn):
        return {"status": "UNAVAILABLE — run data/process_gsi.py",
                "slides": []}
    with open(fn, encoding="utf-8") as f:
        rows = list(_csv.DictReader(f))
    return {"status": "OBSERVED (GSI catalog, CC0-1.0 via bharatlas)",
            "n": len(rows),
            "note": "Occurrence catalog, year-or-unknown dating — display + "
                    "spatial features only",
            "slides": [{"id": int(r["slide_id"]), "lat": float(r["lat"]),
                        "lng": float(r["lng"]), "district": r["district"],
                        "year": int(r["year"]) or None,
                        "trigger": r["trigger"], "activity": r["activity"]}
                       for r in rows]}


@router.get("/gis/provenance")
def gis_provenance(db: Session = Depends(get_db)):
    """Source/date/resolution/status for every GIS layer (Phase 5).

    Response shape is fixed; layers stay STATIC until real village/road/
    boundary/population datasets land.
    """
    from app.seed import TERRAIN_META, GIS_META
    from app.providers.sentinel1 import SentinelSceneMetadataProvider
    from app.models_db import TerrainDEM, SatScene
    dem_n = db.query(TerrainDEM).count() if db else 0
    try:
        sat_n = db.query(SatScene).count() if db else 0
    except Exception as e:
        _log.getLogger("geo-sentinel").debug("SatScene count failed: %s", e)
        sat_n = 0
    sat = SentinelSceneMetadataProvider().scene_status()
    sat["observed_catalog_records"] = sat_n
    if sat_n:
        sat["detail"] += (f" {sat_n} real S1 acquisition records (ASF "
                          "discovery, metadata only — no imagery, no risk use).")
    return {"terrain": TERRAIN_META, "gis": GIS_META,
            "dem_observed": {"source": "SRTM GL1 30m via OpenTopodata",
                             "resolution_m": 30,
                             "zones_covered": dem_n,
                             "status": "OBSERVED" if dem_n else "UNAVAILABLE",
                             "note": ("150m-window derivatives; legacy STATIC "
                                      "profiles remain authoritative for RF path")},
            "satellite": sat,
            "history": {"source": "seed demo inventory (10 events 2022-2024)",
                        "status": "STATIC", "dataset_version": "events_v2",
                        "gsi_catalog": "865 OBSERVED slides (CC0-1.0) at "
                                       "/api/landslides/gsi + events_v3 spatial features"},
            "temporal": {"dataset_version": "seq_real_v1",
                         "source": "Open-Meteo archive ERA5 (rain observed "
                                   "blend, soil MODELED), pre-event only",
                         "status": "OBSERVED/MODELED"}}


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
    _require_zone(db, zone_id)

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
    _require_zone(db, zone_id)

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
    _require_zone(db, zone_id)

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
    db: Session = Depends(get_db),
):
    """
    Return risk score, severity, drivers and explanation
    for a zone at the requested simulated time.
    """
    _require_zone(db, zone_id)

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
        raise HTTPException(status_code=404, detail=f"zone not found: {zone_id}")

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

    z = _require_zone(db, zone_id)

    return {
        "acquisition_date": z.sar_acquisition_date,
        "previous_acquisition_date": (
            z.sar_previous_acquisition_date
        ),
        "change_score": z.sar_change_score,
        "status": "SATELLITE_DEMO — mock value, excluded from production risk scoring",
        "is_live": False,
        "is_simulated": True,
        "honesty_note": (
            "Sentinel-1 is a periodic sensor — "
            "this is NOT live monitoring. "
            "Missing SAR is never treated as zero change. "
            "No live satellite provider is configured (SATELLITE_LIVE=false)."
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
# LANDSLIDE INVENTORY (spatial vs temporal split)
# =============================================================

@router.get("/landslides/inventory")
def landslide_inventory(db: Session = Depends(get_db)):
    """Provenance-tracked inventory split.

    temporal: dated events (landslide_events) — MAY train temporal models.
    spatial:  year-unknown occurrences (spatial_inventory + GSI CSV) —
              GIS/spatial-prior ONLY, never temporal labels.
    """
    from ..models_db import SpatialInventory
    temporal = (db.query(LandslideEvent).order_by(LandslideEvent.event_date).all())
    spatial = (db.query(SpatialInventory).limit(500).all())
    return {
        "temporal": {
            "n": len(temporal), "use": "temporal training labels (dated)",
            "events": [{"zone_id": e.zone_id,
                        "event_date": e.event_date.isoformat() if e.event_date else None,
                        "type": e.landslide_type, "source": e.source,
                        "confidence": getattr(e, "confidence", None)} for e in temporal],
        },
        "spatial": {
            "n": len(spatial), "use": "GIS display + spatial prior ONLY — never temporal labels",
            "records": [{"lat": r.latitude, "lng": r.longitude,
                         "district": r.district, "source": r.source,
                         "data_quality": r.data_quality} for r in spatial],
        },
        "provenance": "Every record carries source + data_quality; spatial-only rows are query-separated by table",
    }


@router.get("/risk/{zone_id}/rainfall-windows")
def zone_rainfall_windows(zone_id: str, db: Session = Depends(get_db)):
    """Normalized rainfall windows: 1/3/6/12/24/72h, 7d cumulative,
    intensity, antecedent — with Observed/Modeled/Scenario labeling."""
    _require_zone(db, zone_id)
    import pandas as pd
    from ..ml.features import compute_rainfall_features
    rows = (db.query(RainfallObservation)
            .filter(RainfallObservation.zone_id == zone_id)
            .order_by(RainfallObservation.timestamp).all())
    if not rows:
        return {"zone_id": zone_id, "state": "empty",
                "detail": "No rainfall observations — run ingestion first"}
    df = pd.DataFrame([{"timestamp": r.timestamp,
                        "rainfall_mm_per_hr": r.rainfall_mm_per_hr} for r in rows])
    feats = compute_rainfall_features(df)
    src = rows[-1].source or ""
    kind = ("Observed" if "LIVE" in (rows[-1].quality_flag or "") or "OPENMETEO" in src
            else "Modeled" if "MODELED" in src else "Scenario" if "SIM" in src or "MOCK" in src
            else "Observed")
    return {"zone_id": zone_id, "state": "ok", "data_kind": kind,
            "windows_mm": {k: round(feats[k], 2) for k in
                           ("rainfall_1h", "rainfall_3h", "rainfall_6h", "rainfall_12h",
                            "rainfall_24h", "rainfall_72h", "rainfall_7d")},
            "intensity_mm_per_hr": round(feats["rainfall_rate"], 2),
            "antecedent_7d_mm": round(feats["antecedent_rainfall"], 2),
            "trend": round(feats["rainfall_slope"], 3),
            "acceleration": round(feats["rainfall_acceleration"], 3),
            "source": src, "quality_flag": rows[-1].quality_flag,
            "forecast_note": "Forecast values come from Open-Meteo forecast_days=1 when RAIN_PROVIDER=openmeteo; otherwise Scenario (synthetic)"}


@router.get("/exposure/villages")
def exposure_villages(db: Session = Depends(get_db)):
    """Village + infrastructure exposure registry (STATIC indicative demo data)."""
    from ..models_db import Village, Infrastructure
    villages = db.query(Village).all()
    infra = db.query(Infrastructure).all()
    return {
        "status": "STATIC — indicative demo registry, not census",
        "villages": [{"name": v.name, "zone_id": v.zone_id, "lat": v.latitude,
                      "lng": v.longitude, "population": v.population,
                      "criticality": v.criticality} for v in villages],
        "infrastructure": [{"name": i.name, "kind": i.kind, "zone_id": i.zone_id,
                            "lat": i.latitude, "lng": i.longitude,
                            "criticality": i.criticality} for i in infra],
    }


# =============================================================
# MODEL STATUS
# =============================================================

@router.get("/model/status")
@router.get("/risk/model/status")
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
    db: Session = Depends(get_db),
):
    """Return interpretable slope state for a zone."""
    _require_zone(db, zone_id)
    results = sim.run_pipeline(t)
    result = next(
        (r for r in results if r["zone_id"] == zone_id),
        None,
    )
    if not result:
        raise HTTPException(status_code=404, detail=f"zone not found: {zone_id}")

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
    _require_zone(db, zone_id)
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
    # Fresh pipeline values for rainfall/soil context (RiskScore rows don't store them)
    try:
        pipe = {r["zone_id"]: r for r in sim.run_pipeline(t)}
    except Exception as e:
        _log.getLogger("geo-sentinel").warning(
            "Pipeline run failed for hotspot ranking: %s", e)
        pipe = {}
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

        live = pipe.get(z.id) or {}
        rain_72h = float(live.get("rainfall_72h", 0.0) or 0.0)
        rain_24h = float(live.get("rainfall_24h", 0.0) or 0.0)
        soil = float(live.get("soil_moisture", 0.0) or 0.0)

        hotspot = _classify_hotspot(
            latest.risk_score,
            latest.static_score,
            latest.dynamic_score,
            interp,
            rain_72h,
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
            "rainfall_24h": round(rain_24h, 1),
            "rainfall_72h": round(rain_72h, 1),
            "soil_moisture": round(soil, 3),
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
        "analyzed_at": dt.datetime.now(dt.timezone.utc).isoformat(),
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
        "simulated_at": dt.datetime.now(dt.timezone.utc).isoformat(),
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

        # Get previous score (12h ago if available). RiskScore rows use the
        # scenario clock, so compare against the centralized sim epoch.
        from app.services.sim import BASE as SIM_EPOCH
        prev_t = max(24, t - 12)
        prev_rows = (
            db.query(RiskScore)
            .filter(
                RiskScore.zone_id == z.id,
                RiskScore.timestamp <= (SIM_EPOCH + dt.timedelta(hours=prev_t)),
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
        "compared_at": dt.datetime.now(dt.timezone.utc).isoformat(),
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
    zone = _require_zone(db, zone_id)
    results = sim.run_pipeline(t)
    result = next(
        (r for r in results if r["zone_id"] == zone_id),
        None,
    )
    if not result:
        raise HTTPException(status_code=404, detail=f"zone not found: {zone_id}")

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

    # Drilldown completeness (Phase 12): history, vulnerable roads,
    # active alerts, and data freshness alongside the scores.
    from app.models_db import (LandslideEvent, RoadSegment, Alert,
                               RainfallObservation, SoilMoistureObservation)
    events = (db.query(LandslideEvent)
              .filter(LandslideEvent.zone_id == zone_id)
              .order_by(LandslideEvent.event_date.desc()).all())
    roads = (db.query(RoadSegment)
             .filter((RoadSegment.from_zone == zone_id) |
                     (RoadSegment.to_zone == zone_id)).all())
    active_alerts = (db.query(Alert).filter(Alert.zone_id == zone_id)
                     .order_by(Alert.created_at.desc()).limit(5).all())
    last_rain = (db.query(RainfallObservation)
                 .filter(RainfallObservation.zone_id == zone_id)
                 .order_by(RainfallObservation.timestamp.desc()).first())
    last_soil = (db.query(SoilMoistureObservation)
                 .filter(SoilMoistureObservation.zone_id == zone_id)
                 .order_by(SoilMoistureObservation.timestamp.desc()).first())

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
            "dem_observed": _dem_block(db, zone_id),
        },
        "history": [{"event_date": e.event_date.isoformat()
                     if e.event_date else None,
                     "type": e.landslide_type, "source": e.source}
                    for e in events],
        "vulnerable_roads": [{"name": r.name, "status": r.status,
                              "blockage_reason": r.blockage_reason,
                              "length_km": r.length_km}
                             for r in roads if r.status != "OPEN"],
        "active_alerts": [{"severity": a.severity, "status": a.status,
                           "at": a.created_at.isoformat()
                           if a.created_at else None}
                          for a in active_alerts],
        "freshness": {
            "rainfall": {"observed_at": last_rain.timestamp.isoformat()
                         if last_rain and last_rain.timestamp else None,
                         "source": last_rain.source if last_rain else None,
                         "quality": last_rain.quality_flag if last_rain else None},
            "soil_moisture": {"observed_at": last_soil.timestamp.isoformat()
                              if last_soil and last_soil.timestamp else None,
                              "source": last_soil.source if last_soil else None,
                              "quality": last_soil.quality_flag if last_soil else None},
        },
        "drivers": result["drivers"],
        "explanation": explanation,
        "model_versions": result["model_versions"],
        "sim_time": result["sim_time"],
    }


def _dem_block(db, zone_id: str) -> dict | None:
    """Observed DEM derivatives (SRTM 30m) alongside STATIC seed profiles."""
    from app.models_db import TerrainDEM
    try:
        r = db.get(TerrainDEM, zone_id)
    except Exception as e:
        _log.getLogger("geo-sentinel").debug("TerrainDEM lookup failed: %s", e)
        return None
    if r is None or r.elevation_m is None:
        return {"status": "UNAVAILABLE — run scripts/fetch_dem.py"}
    return {"status": "OBSERVED", "source": r.dem_source,
            "resolution_m": r.resolution_m,
            "resolution_note": "SRTM GL1 30m; 5x5-window derivatives (~150m); cell grids 9x9@250m",
            "elevation_m": r.elevation_m, "slope_deg": r.slope_deg,
            "aspect_deg": r.aspect_deg, "ruggedness_m": r.ruggedness_m,
            "relief_m": r.relief_m,
            "curvature": (round(r.ruggedness_m / max(r.relief_m, 1.0), 4)
                          if r.ruggedness_m is not None and r.relief_m else None),
            "curvature_kind": "ESTIMATED convexity proxy (ruggedness/relief) — not a full-raster curvature product",
            "note": "150m-window local derivatives; seed profiles unchanged"}


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


# =============================================================
# PER-CELL RISK GRID (flagship zone deep-dive)
# =============================================================

def _generate_hex_grid(lat, lng, radius_km=4.0, cell_size_km=0.4):
    """Generate hex grid points within a circular area."""
    import math
    cells = []
    dx = cell_size_km
    dy = cell_size_km * math.sqrt(3) / 2
    cos_lat = math.cos(math.radians(lat))

    rows = int(radius_km / dy) + 1
    cols = int(radius_km / (dx / 2)) + 1

    for r in range(-rows, rows + 1):
        for c in range(-cols, cols + 1):
            cell_lat = lat + r * dy / 111.0
            offset = (dx / 2) if r % 2 else 0
            cell_lng = lng + (c * dx + offset) / (111.0 * cos_lat)
            dist = math.sqrt(((cell_lat - lat) * 111) ** 2 + ((cell_lng - lng) * 111 * cos_lat) ** 2)
            if dist <= radius_km:
                cells.append({"lat": cell_lat, "lng": cell_lng, "dist_km": dist})
    return cells


def _perturb_features(zone, dist_km, rng):
    """Generate spatially-varying terrain features for a cell."""
    import numpy as np
    base_slope = float(zone.slope)
    base_elev = float(zone.elevation)
    base_rugged = float(zone.ruggedness)
    base_road = float(zone.road_proximity)
    base_drain = float(zone.drainage_proximity)
    base_settle = float(zone.settlement_density)
    base_sar = float(zone.sar_change_score or 0.0)

    # Spatially correlated noise: closer cells have similar features
    noise_scale = max(0.1, dist_km / 5.0)

    return [
        max(0, min(60, base_slope + rng.normal(0, 6 * noise_scale))),
        max(0, min(1.0, base_elev / 2000.0 + rng.normal(0, 0.08 * noise_scale))),
        max(0, min(1.0, base_rugged + rng.normal(0, 0.12 * noise_scale))),
        max(0, min(1.0, base_road + rng.normal(0, 0.10 * noise_scale))),
        max(0, min(1.0, base_drain + rng.normal(0, 0.10 * noise_scale))),
        max(0, min(1.0, base_settle + rng.normal(0, 0.08 * noise_scale))),
        max(0, min(1.0, base_sar + rng.normal(0, 0.06 * noise_scale))),
    ]


def _observed_cells(zone_id: str, stride: int = 1):
    """Real DEM cells: 9x9 SRTM grid → per-cell slope (Horn), elevation,
    local ruggedness. Returns (cells, meta) or (None, reason). No synthesis:
    missing elevations drop the cell."""
    import json as _json
    import math as _math
    import os as _os
    import re as _re
    import numpy as _np
    # P2: zone_id is user-controlled — allowlist it so `../` or absolute
    # paths can never escape data/raw.
    if not _re.match(r"^[A-Za-z0-9][A-Za-z0-9_-]*$", zone_id or ""):
        return None, "unknown zone"
    _base = _os.path.normpath(_os.path.join(_os.path.dirname(__file__), "..",
                                            "..", "data", "raw"))
    fn = _os.path.normpath(_os.path.join(_base, f"demgrid_{zone_id}.json"))
    if _os.path.dirname(fn) != _base or not _os.path.isfile(fn):
        return None, "no DEM grid — run scripts/fetch_demgrid.py"
    with open(fn, encoding="utf-8") as _f:
        g = _json.load(_f)
    n, step = g["n"], g["step_m"]
    elev = _np.asarray(g["elev"], dtype=float).reshape(n, n)
    lats = _np.asarray(g["lats"]).reshape(n, n)
    lngs = _np.asarray(g["lngs"]).reshape(n, n)
    cells = []
    for i in range(1, n - 1, stride):
        for j in range(1, n - 1, stride):
            c = elev[i - 1:i + 2, j - 1:j + 2]
            if _np.isnan(c).any():
                continue  # drop, never interpolate silently
            dzdx = ((c[0, 2] + 2 * c[1, 2] + c[2, 2])
                    - (c[0, 0] + 2 * c[1, 0] + c[2, 0])) / (8 * step)
            dzdy = ((c[2, 0] + 2 * c[2, 1] + c[2, 2])
                    - (c[0, 0] + 2 * c[0, 1] + c[0, 2])) / (8 * step)
            slope = _math.degrees(_math.atan(_math.hypot(dzdx, dzdy)))
            cells.append({"lat": float(lats[i, j]), "lng": float(lngs[i, j]),
                          "dist_km": 0.0, "slope_dem": slope,
                          "elev_dem": float(elev[i, j]),
                          "rugged_dem": float(c.std())})
    meta = {"dataset": g["dataset"], "step_m": step, "grid": f"{n}x{n}",
            "stride": stride}
    return cells, meta


@router.get("/risk/{zone_id}/cell-grid")
def cell_risk_grid(
    zone_id: str,
    t: int = Query(168, ge=24, le=168),
    resolution: int = Query(20, ge=10, le=30),
    mode: str = Query("observed", description="observed (real DEM), legacy (seeded noise), or demo (slope-driven illustration)"),
    db: Session = Depends(get_db),
):
    """
    Per-cell risk grid for the flagship zone deep-dive.
    mode=observed (default): real SRTM cells (slope/elevation/ruggedness
    from the zone DEM grid; road/drain/settlement are zone context).
    mode=legacy: seeded-noise perturbation (reproducible demo, labeled).
    mode=demo: observed cells with slope-driven display spread so the
    demo map shows spatial variation (labeled DEMO SCENARIO, not a prediction).
    Runs the trained RF model on each terrain cell independently.
    """
    import numpy as np
    from ..ml.rf_model import RFModel

    zone = db.query(Zone).filter(Zone.id == zone_id).first()
    if not zone:
        raise HTTPException(status_code=404, detail="zone not found")

    rf = RFModel()
    if not rf.available():
        raise HTTPException(status_code=503, detail="RF model not trained")

    # Run pipeline to get dynamic score and environmental context
    results = sim.run_pipeline(t)
    zone_result = next((r for r in results if r["zone_id"] == zone_id), None)
    dynamic_score = zone_result["dynamic_score"] if zone_result else 0.5
    rainfall_72h = zone_result["rainfall_72h"] if zone_result else 0.0
    soil_moisture = zone_result["soil_moisture"] if zone_result else 0.3

    if mode == "legacy":
        # Generate hex grid
        lat = float(zone.latitude)
        lng = float(zone.longitude)
        cell_size_km = 8.0 / resolution  # roughly covers 4km radius
        grid = _generate_hex_grid(lat, lng, radius_km=3.5, cell_size_km=cell_size_km)
        dem_meta = None
        cell_method = "legacy seeded-noise perturbation (demo)"
        use_observed = False
    else:
        # observed AND demo both use real DEM geometry; demo only changes display spread
        grid, dem_meta = _observed_cells(zone_id, stride=1 if resolution >= 18 else 2)
        if grid is None:
            if mode == "demo":
                lat = float(zone.latitude)
                lng = float(zone.longitude)
                cell_size_km = 8.0 / resolution
                grid = _generate_hex_grid(lat, lng, radius_km=3.5, cell_size_km=cell_size_km)
                dem_meta = None
                use_observed = False
            else:
                return {"error": dem_meta, "cells": []}
        else:
            use_observed = True
        cell_method = (
            "demo slope-driven illustration (DEMO SCENARIO — not a prediction)"
            if mode == "demo" else
            f"observed-DEM ({dem_meta['dataset']}, {dem_meta['grid']}@{dem_meta['step_m']}m)"
        )

    rng = np.random.RandomState(42)  # reproducible

    # Feature rows first (same order → identical rng stream), then ONE
    # batched predict_proba: same outputs as per-cell calls, ~48x faster.
    feat_rows = []
    for cell in grid:
        if use_observed:
            feat_rows.append([
                max(0, min(60, cell["slope_dem"])),
                max(0, min(1.0, cell["elev_dem"] / 2000.0)),
                max(0, min(1.0, cell["rugged_dem"] / 15.0)),
                float(zone.road_proximity),
                float(zone.drainage_proximity),
                float(zone.settlement_density),
                0.15,  # SAR neutral (quarantined)
            ])
        else:
            feat_rows.append(_perturb_features(zone, cell["dist_km"], rng))
    proba_all = rf.model.predict_proba(feat_rows)
    classes = list(rf.model.classes_)

    # Demo display spread: per-cell slope normalized across THIS grid.
    # Grounded in real observed slope (or the perturbed slope feature),
    # anchored to the zone's dynamic level, seeded per zone (reproducible).
    demo_slopes = None
    demo_rng = None
    demo_anchor = None
    if mode == "demo":
        if use_observed:
            demo_slopes = [cell["slope_dem"] for cell in grid]
        else:
            demo_slopes = [row[0] for row in feat_rows]
        demo_rng = np.random.RandomState(abs(hash(zone_id)) % (2 ** 31))
        demo_anchor = min(0.95, max(0.05, dynamic_score))

    from ..ml.fusion import fuse, classify

    cells = []
    for ci, (cell, pred) in enumerate(zip(grid, proba_all)):
        static_score = sum(p * c / 2.0 for p, c in zip(pred, classes))
        static_score = min(1.0, max(0.0, static_score))

        # Combine with dynamic for fused risk
        soil_cell = (soil_moisture if use_observed
                     else min(0.95, soil_moisture + rng.normal(0, 0.05)))
        fusion = fuse(
            static_score, dynamic_score,
            rainfall_72h * max(0.3, 1.0 - cell["dist_km"] / 5.0),
            rainfall_72h,
            soil_cell,
        )

        risk_score = fusion["risk_score"]
        severity = fusion["severity"]
        escalated = fusion["escalated"]
        if mode == "demo":
            lo, hi = min(demo_slopes), max(demo_slopes)
            s_norm = (demo_slopes[ci] - lo) / (hi - lo) if hi > lo else 0.5
            jitter = demo_rng.normal(0, 0.02)
            risk_score = round(min(0.98, max(0.05,
                demo_anchor * 0.45 + (0.10 + 0.85 * s_norm) * 0.55 + jitter)), 4)
            severity = classify(risk_score)

        # Slope state
        state = _compute_slope_state(
            static_score, dynamic_score, risk_score,
            rainfall_72h, soil_moisture, escalated,
        )

        entry = {
            "lat": cell["lat"],
            "lng": cell["lng"],
            "static_score": round(static_score, 4),
            "risk_score": risk_score,
            "severity": severity,
            "slope_state": state["state"],
            "slope_state_color": state["color"],
            "stress_score": round(state["stress_score"], 4),
            "escalated": escalated,
        }
        if use_observed:
            entry["slope_dem_deg"] = round(cell["slope_dem"], 2)
            entry["elev_dem_m"] = round(cell["elev_dem"], 1)
        cells.append(entry)

    statics = {c["static_score"] for c in cells}
    if mode == "demo":
        resolution_note = (
            "DEMO SCENARIO — display spread driven by observed per-cell slope, "
            "anchored to the zone advisory level; illustrative, not a prediction.")
    else:
        resolution_note = (
            "Observed SRTM cells carry real per-cell slope/elevation, but the "
            "zone-scale RF assigns identical leaves at this resolution "
            f"({len(statics)} distinct static value(s)) — the grid exposes "
            "the model's sub-zone blindness honestly; finer discrimination "
            "needs denser inventory + retraining, not interpolation.")
    return {
        "zone_id": zone_id,
        "name": zone.name,
        "cell_count": len(cells),
        "resolution": resolution,
        "cell_method": cell_method,
        "dem": dem_meta,
        "demo": mode == "demo",
        "cells": cells,
        "resolution_note": resolution_note,
    }


# =============================================================
# TEMPORAL CELL GRID (flagship zone animation)
# =============================================================

@router.get("/risk/{zone_id}/cell-grid/temporal")
def temporal_cell_grid(
    zone_id: str,
    db: Session = Depends(get_db),
    resolution: int = Query(12, ge=8, le=16),
    mode: str = Query("observed", description="observed (model output) or demo (slope-driven illustration)"),
):
    """
    Per-cell risk at multiple timesteps for temporal animation.
    Returns cell grids at T-72h, T-48h, T-24h, NOW.
    mode=demo spreads cells by per-cell slope so the
    animation shows variation (DEMO SCENARIO — not a prediction).
    Optimized: runs pipeline once per unique timestep, uses batch RF prediction.
    """
    import numpy as np
    from ..ml.rf_model import RFModel

    zone = db.query(Zone).filter(Zone.id == zone_id).first()
    if not zone:
        raise HTTPException(status_code=404, detail=f"zone not found: {zone_id}")

    rf = RFModel()
    if not rf.available():
        return {"error": "RF model not trained", "timesteps": []}

    timesteps = [96, 120, 144, 168]
    t_labels = ["T-72h", "T-48h", "T-24h", "NOW"]

    lat = float(zone.latitude)
    lng = float(zone.longitude)
    cell_size_km = 8.0 / resolution
    grid = _generate_hex_grid(lat, lng, radius_km=3.5, cell_size_km=cell_size_km)

    rng_base = np.random.RandomState(42)
    base_features = np.array([_perturb_features(zone, c["dist_km"], rng_base) for c in grid])

    # Batch predict static scores once — same for all timesteps
    static_scores = rf.model.predict_proba(base_features)
    classes = list(rf.model.classes_)
    static_vec = np.array([min(1.0, max(0.0, sum(p * c / 2.0 for p, c in zip(proba, classes)))) for proba in static_scores])

    from ..ml.fusion import fuse, classify

    demo_slopes = None
    if mode == "demo":
        slopes = list(base_features[:, 0])
        lo, hi = min(slopes), max(slopes)
        demo_slopes = [(s - lo) / (hi - lo) if hi > lo else 0.5 for s in slopes]

    timesteps_data = []
    for ti, (t_val, t_label) in enumerate(zip(timesteps, t_labels)):
        results = sim.run_pipeline(t_val)
        zone_result = next((r for r in results if r["zone_id"] == zone_id), None)
        dynamic_score = zone_result["dynamic_score"] if zone_result else 0.5
        rainfall_72h = zone_result["rainfall_72h"] if zone_result else 0.0
        soil_moisture = zone_result["soil_moisture"] if zone_result else 0.3

        rng = np.random.RandomState(42 + ti)
        demo_rng = np.random.RandomState(abs(hash((zone_id, ti))) % (2 ** 31)) if mode == "demo" else None
        demo_anchor = min(0.95, max(0.05, dynamic_score)) if mode == "demo" else None
        cells = []
        for ci, cell in enumerate(grid):
            soil_proj = min(0.95, soil_moisture + rng.normal(0, 0.03))
            rain_local = rainfall_72h * max(0.3, 1.0 - cell["dist_km"] / 5.0)

            fusion = fuse(
                float(static_vec[ci]), dynamic_score,
                rain_local, rainfall_72h, soil_proj,
            )
            risk_score = fusion["risk_score"]
            severity = fusion["severity"]
            escalated = fusion["escalated"]
            if mode == "demo":
                jitter = demo_rng.normal(0, 0.02)
                risk_score = round(min(0.98, max(0.05,
                    demo_anchor * 0.45 + (0.10 + 0.85 * demo_slopes[ci]) * 0.55 + jitter)), 4)
                severity = classify(risk_score)
            state = _compute_slope_state(
                float(static_vec[ci]), dynamic_score, risk_score,
                rainfall_72h, soil_proj, escalated,
            )

            cells.append({
                "lat": cell["lat"],
                "lng": cell["lng"],
                "risk_score": risk_score,
                "severity": severity,
                "slope_state": state["state"],
                "slope_state_color": state["color"],
                "stress_score": round(state["stress_score"], 4),
            })

        timesteps_data.append({
            "t": t_val,
            "label": t_label,
            "cells": cells,
        })

    return {
        "zone_id": zone_id,
        "name": zone.name,
        "cell_method": (
            "demo slope-driven illustration (DEMO SCENARIO — not a prediction)"
            if mode == "demo" else "model output per cell"),
        "demo": mode == "demo",
        "timesteps": timesteps_data,
    }


# =============================================================
# WEATHER-LINKED RISK FORECAST
# =============================================================

@router.get("/risk/{zone_id}/forecast")
def weather_forecast(
    zone_id: str,
    t: int = Query(168, ge=24, le=168),
    db: Session = Depends(get_db),
):
    """
    Weather-linked risk forecast for a zone.
    Projects rainfall and risk trajectory forward 72 hours.
    """
    import math

    zone = _require_zone(db, zone_id)

    # Run current pipeline for baseline
    results = sim.run_pipeline(t)
    zone_result = next((r for r in results if r["zone_id"] == zone_id), None)
    if not zone_result:
        raise HTTPException(status_code=404, detail=f"zone not found: {zone_id}")

    # Synthetic forecast: extend storm pattern forward
    base_rain_24h = zone_result["rainfall_24h"]
    base_rain_72h = zone_result["rainfall_72h"]
    soil = zone_result["soil_moisture"]
    static = zone_result["static_score"]
    dynamic = zone_result["dynamic_score"]

    forecast_hours = [24, 48, 72]
    forecasts = []

    for fh in forecast_hours:
        # Project rainfall: assume monsoon trend continues
        t_future = t + fh
        # Synthetic: rainfall ramps up then tapers
        rain_multiplier = 1.0 + 0.3 * math.sin(math.pi * t_future / 200)
        projected_rain_24h = base_rain_24h * rain_multiplier
        projected_rain_72h = base_rain_72h * (1 + 0.1 * fh / 72)
        projected_soil = min(0.95, soil + 0.01 * fh / 24)

        from ..ml.fusion import fuse
        fusion = fuse(static, dynamic, projected_rain_24h, projected_rain_72h, projected_soil)

        state = _compute_slope_state(
            static, dynamic, fusion["risk_score"],
            projected_rain_72h, projected_soil, fusion["escalated"],
        )

        # Rainfall intensity label
        if projected_rain_24h > 100:
            rain_label = "HEAVY"
            rain_color = "#ba1a1a"
        elif projected_rain_24h > 60:
            rain_label = "MODERATE"
            rain_color = "#ea580c"
        elif projected_rain_24h > 30:
            rain_label = "LIGHT"
            rain_color = "#d97706"
        else:
            rain_label = "NONE"
            rain_color = "#245c45"

        forecasts.append({
            "hours_ahead": fh,
            "projected_rainfall_24h": round(projected_rain_24h, 1),
            "projected_rainfall_72h": round(projected_rain_72h, 1),
            "projected_soil_moisture": round(projected_soil, 3),
            "projected_risk": round(fusion["risk_score"], 4),
            "projected_severity": fusion["severity"],
            "slope_state": state["state"],
            "slope_state_label": state["label"],
            "slope_state_color": state["color"],
            "escalated": fusion["escalated"],
            "rainfall_intensity": rain_label,
            "rainfall_color": rain_color,
        })

    # Overall forecast verdict
    last = forecasts[-1]
    first = forecasts[0]
    risk_change = last["projected_risk"] - first["projected_risk"]

    if risk_change > 0.15:
        verdict = "RAPID DETERIORATION expected"
        verdict_color = "#ba1a1a"
    elif risk_change > 0.05:
        verdict = "GRADUAL INCREASE in risk"
        verdict_color = "#ea580c"
    elif risk_change < -0.05:
        verdict = "IMPROVING conditions"
        verdict_color = "#245c45"
    else:
        verdict = "STABLE conditions expected"
        verdict_color = "#d97706"

    return {
        "zone_id": zone_id,
        "name": zone.name,
        "current_risk": zone_result["risk_score"],
        "current_severity": zone_result["severity"],
        "forecasts": forecasts,
        "verdict": verdict,
        "verdict_color": verdict_color,
        "confidence_note": "Synthetic forecast based on monsoon pattern projection. Not operational weather data.",
    }


# =============================================================
# EMERGENCY RESPONSE PRIORITISATION
# =============================================================

@router.get("/risk/emergency-priorities")
def emergency_priorities(
    t: int = Query(168, ge=24, le=168),
    db: Session = Depends(get_db),
):
    """
    Emergency response prioritisation across all zones.
    Ranks zones by composite urgency score for dispatch planning.
    """
    results = sim.run_pipeline(t)

    from app.models_db import CitizenReport as _CR
    import math as _m
    open_reports = db.query(_CR).filter(
        _CR.status.in_(["PENDING", "VERIFIED"])).all()

    def _near(lat, lng, max_km=30.0):
        n = 0
        for rep in open_reports:
            if rep.latitude is None:
                continue
            a = (_m.sin(_m.radians(rep.latitude - lat) / 2) ** 2
                 + _m.cos(_m.radians(lat)) * _m.cos(_m.radians(rep.latitude))
                 * _m.sin(_m.radians(rep.longitude - lng) / 2) ** 2)
            if 2 * 6371.0 * _m.asin(_m.sqrt(a)) <= max_km:
                n += 1
        return n

    priorities = []
    for r in results:
        zone = db.query(Zone).filter(Zone.id == r["zone_id"]).first()
        if not zone:
            continue

        # Urgency composite: risk * 0.4 + population_exposure * 0.25 + road_inaccessibility * 0.2 + sar_change * 0.15
        pop_norm = min(1.0, zone.population / 150000)
        road_inv = 1.0 - float(zone.road_proximity)  # harder to reach = higher priority
        sar_norm = float(zone.sar_change_score or 0)

        urgency = (
            0.40 * r["risk_score"]
            + 0.25 * pop_norm
            + 0.20 * road_inv
            + 0.15 * sar_norm
        )

        # Priority tier
        if urgency >= 0.6 or r["risk_score"] >= 0.75:
            tier = "CRITICAL"
            tier_color = "#ba1a1a"
            response_time = "2-4 hours"
        elif urgency >= 0.45 or r["risk_score"] >= 0.55:
            tier = "HIGH"
            tier_color = "#ea580c"
            response_time = "4-8 hours"
        elif urgency >= 0.3:
            tier = "MEDIUM"
            tier_color = "#d97706"
            response_time = "8-24 hours"
        else:
            tier = "LOW"
            tier_color = "#245c45"
            response_time = "24-48 hours"

        # Evacuation route status
        if zone.road_proximity >= 0.7:
            evac_status = "ACCESSIBLE"
            evac_color = "#245c45"
        elif zone.road_proximity >= 0.5:
            evac_status = "LIMITED"
            evac_color = "#d97706"
        else:
            evac_status = "BLOCKED RISK"
            evac_color = "#ba1a1a"

        # Why-this-rank reasons (Phase 23): each urgency term explained
        nearby_reports = _near(zone.latitude, zone.longitude)
        reasons = []
        if r["risk_score"] >= 0.55:
            reasons.append(f"HIGH hazard (risk {r['risk_score']:.2f})")
        elif r["risk_score"] >= 0.4:
            reasons.append(f"elevated hazard (risk {r['risk_score']:.2f})")
        if pop_norm >= 0.3:
            reasons.append(f"high exposed population ({zone.population})")
        if road_inv >= 0.5:
            reasons.append("hard to reach (low road proximity)")
        if r["escalated"]:
            reasons.append("extreme-event escalation active")
        if nearby_reports:
            reasons.append(f"{nearby_reports} unverified field report(s) "
                           "within 30km")
        if not reasons:
            reasons.append("routine monitoring — no acute drivers")

        priorities.append({
            "zone_id": r["zone_id"],
            "name": r["name"],
            "district": r["district"],
            "risk_score": r["risk_score"],
            "severity": r["severity"],
            "slope_state": r["slope_state"],
            "slope_state_label": r["slope_state_label"],
            "slope_state_color": r["slope_state_color"],
            "escalated": r["escalated"],
            "population": zone.population,
            "road_proximity": zone.road_proximity,
            "urgency_score": round(urgency, 4),
            "reasons": reasons,
            "tier": tier,
            "tier_color": tier_color,
            "response_time": response_time,
            "evac_status": evac_status,
            "evac_color": evac_color,
        })

    priorities.sort(key=lambda x: x["urgency_score"], reverse=True)

    # Assign rank
    for i, p in enumerate(priorities):
        p["rank"] = i + 1

    return {
        "priorities": priorities,
        "total": len(priorities),
        "analyzed_at": dt.datetime.now(dt.timezone.utc).isoformat(),
    }