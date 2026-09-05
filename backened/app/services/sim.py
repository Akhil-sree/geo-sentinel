"""
Monsoon Event Simulation.

Advances simulated time, regenerates rainfall and soil-moisture
observations, reruns the complete risk pipeline, and stores
risk history.

This is the hackathon control that makes the whole system visibly
react end-to-end.
"""

import datetime as dt
import math

import pandas as pd

from ..database import SessionLocal
from ..models_db import Zone, RiskScore

from ..ml.features import (
    compute_rainfall_features,
    compute_soil_features,
    build_model_sequence,
)

from ..ml.rf_model import RFModel
from ..ml.mamba_model import get_temporal_model
from ..ml.fusion import fuse
from ..ml.xai import explain


BASE = dt.datetime(2026, 7, 14)


def storm(t):
    """
    Synthetic rainfall storm used by the simulation.

    Produces two rainfall pulses.
    """

    peak1 = 26 * (
        2.718 ** -(
            ((t - 96) / 26) ** 2
        )
    )

    peak2 = 38 * (
        2.718 ** -(
            ((t - 140) / 16) ** 2
        )
    )

    return (
        peak1
        + peak2
        + 0.6
    )


def run_pipeline(t_hours: int):
    """
    Run the complete risk pipeline for all zones
    at simulated time t_hours.

    Pipeline:

        Rainfall
           ↓
        Soil moisture
           ↓
        Feature engineering
           ↓
        Random Forest
           ↓
        Temporal model
           ↓
        Fusion
           ↓
        XAI explanation
           ↓
        RiskScore history
    """

    db = SessionLocal()

    rf = RFModel()
    tm = get_temporal_model()

    results = []

    try:

        zones = db.query(Zone).all()

        for z in zones:

            # -------------------------------------------------
            # 1. Synchronize rainfall
            # -------------------------------------------------

            rain_df = _sync_rain(
                z.id,
                t_hours,
            )

            # -------------------------------------------------
            # 2. Synchronize soil moisture
            # -------------------------------------------------

            soil_df = _sync_soil(
                z.id,
                t_hours,
            )

            # -------------------------------------------------
            # 3. Static RF prediction
            # -------------------------------------------------

            if rf.available():
                rf_res = rf.predict(z)
            else:
                rf_res = _rf_fallback(z)

            # -------------------------------------------------
            # 4. Rainfall features
            # -------------------------------------------------

            rain_features = compute_rainfall_features(
                rain_df
            )

            # -------------------------------------------------
            # 5. Soil features
            # -------------------------------------------------

            soil_features = compute_soil_features(
                soil_df
            )

            # -------------------------------------------------
            # 6. Temporal model sequence
            # -------------------------------------------------

            seq = build_model_sequence(
                rain_df,
                soil_df,
                float(z.sar_change_score or 0.0),
            )

            # -------------------------------------------------
            # 7. Dynamic prediction
            # -------------------------------------------------

            dyn = tm.predict(seq)

            # -------------------------------------------------
            # 8. Fusion
            # -------------------------------------------------

            fusion_result = fuse(
                rf_res["static_score"],
                dyn["dynamic_score"],
                rain_features["rainfall_24h"],
                rain_features["rainfall_72h"],
                soil_features[
                    "soil_moisture_current"
                ],
            )

            # -------------------------------------------------
            # 9. Explainability
            # -------------------------------------------------

            explanation = explain(
                z,
                {
                    **rf_res,
                    "importances": (
                        rf.feature_importances()
                        if rf.available()
                        else {}
                    ),
                },
                dyn,
                rain_features,
                soil_features,
                fusion_result["escalated"],
                fusion_result["escalation_reasons"],
            )

            # -------------------------------------------------
            # 10. Confidence
            # -------------------------------------------------

            confidence = (
                rf_res["static_score"]
                + dyn["dynamic_score"]
            ) / 2.0

            confidence = max(
                0.0,
                min(1.0, confidence),
            )

            # -------------------------------------------------
            # 11. Store risk history
            # -------------------------------------------------

            risk_record = RiskScore(
                zone_id=z.id,

                timestamp=(
                    BASE
                    + dt.timedelta(hours=t_hours)
                ),

                static_score=(
                    rf_res["static_score"]
                ),

                dynamic_score=(
                    dyn["dynamic_score"]
                ),

                risk_score=(
                    fusion_result["risk_score"]
                ),

                severity=(
                    fusion_result["severity"]
                ),

                escalated=(
                    fusion_result["escalated"]
                ),

                confidence=round(
                    confidence,
                    4,
                ),

                rf_version=(
                    rf_res["version"]
                ),

                mamba_version=(
                    dyn["version"]
                ),

                drivers_json=str(
                    explanation.get(
                        "drivers",
                        [],
                    )
                ),
            )

            db.add(risk_record)

            # -------------------------------------------------
            # 12. Slope state analysis
            # -------------------------------------------------

            from ..api.risk import _compute_slope_state
            slope_state = _compute_slope_state(
                rf_res["static_score"],
                dyn["dynamic_score"],
                fusion_result["risk_score"],
                rain_features["rainfall_72h"],
                soil_features["soil_moisture_current"],
                fusion_result["escalated"],
            )

            # -------------------------------------------------
            # 13. Prepare API response
            # -------------------------------------------------

            results.append({
                "zone_id": z.id,

                "name": z.name,

                "district": z.district,

                "static_score": (
                    rf_res["static_score"]
                ),

                "dynamic_score": (
                    dyn["dynamic_score"]
                ),

                "risk_score": (
                    fusion_result["risk_score"]
                ),

                "severity": (
                    fusion_result["severity"]
                ),

                "escalated": (
                    fusion_result["escalated"]
                ),

                "confidence": confidence,

                "rainfall_24h": (
                    rain_features[
                        "rainfall_24h"
                    ]
                ),

                "rainfall_72h": (
                    rain_features[
                        "rainfall_72h"
                    ]
                ),

                "rainfall_7d": (
                    rain_features[
                        "rainfall_7d"
                    ]
                ),

                "rainfall_slope": (
                    rain_features[
                        "rainfall_slope"
                    ]
                ),

                "soil_moisture": (
                    soil_features[
                        "soil_moisture_current"
                    ]
                ),

                "drivers": explanation.get(
                    "drivers",
                    [],
                ),

                "summary": explanation.get(
                    "summary",
                    "",
                ),

                "slope_state": slope_state["state"],
                "slope_state_label": slope_state["label"],
                "slope_state_color": slope_state["color"],
                "slope_stress_score": slope_state["stress_score"],

                "model_versions": {
                    "rf": rf_res["version"],
                    "mamba": dyn["version"],
                    "fusion": fusion_result[
                        "fusion_version"
                    ],
                },

                "sim_time": (
                    BASE
                    + dt.timedelta(
                        hours=t_hours
                    )
                ).isoformat(),
            })

        db.commit()

    except Exception:
        db.rollback()
        raise

    finally:
        db.close()

    return results


def _rf_fallback(z):
    """
    Heuristic structural susceptibility fallback
    when no trained RF artifact exists.

    This is NOT a trained model.
    It is explicitly labeled as a fallback.
    """

    x = (
        min(
            1.0,
            float(z.slope) / 55.0,
        ) * 0.30

        + float(z.ruggedness) * 0.22

        + float(z.road_proximity) * 0.18

        + float(z.drainage_proximity) * 0.14

        + min(
            1.0,
            float(z.elevation) / 2000.0,
        ) * 0.10

        + float(z.settlement_density) * 0.06
    )

    score = 1.0 / (
        1.0
        + math.exp(
            -(x - 0.42) * 7.5
        )
    )

    return {
        "static_score": float(score),

        "class_probs": {},

        "version": "rf_untrained_fallback",
    }


def _sync_rain(
    zone_id,
    t_hours,
):
    """
    Generate and synchronize synthetic rainfall
    observations for a zone.
    """

    db = SessionLocal()

    try:

        from ..models_db import RainfallObservation

        # Remove previous simulated observations
        db.query(
            RainfallObservation
        ).filter(
            RainfallObservation.zone_id
            == zone_id
        ).delete(
            synchronize_session=False
        )

        # Generate synthetic hourly rainfall using the storm curve
        for h in range(1, t_hours + 1):
            ts = BASE + dt.timedelta(hours=h)
            mm = storm(h)
            db.add(
                RainfallObservation(
                    zone_id=zone_id,
                    timestamp=ts,
                    rainfall_mm_per_hr=round(mm, 2),
                    source="IMD_MOCK",
                    quality_flag="DEMO_DATA",
                )
            )

        db.commit()

        rows = (
            db.query(
                RainfallObservation
            )
            .filter(
                RainfallObservation.zone_id
                == zone_id
            )
            .order_by(
                RainfallObservation.timestamp
            )
            .all()
        )

        df = pd.DataFrame([
            {
                "timestamp": row.timestamp,
                "rainfall_mm_per_hr": (
                    row.rainfall_mm_per_hr
                ),
            }
            for row in rows
        ])

        return df.sort_values(
            "timestamp"
        )

    except Exception:
        db.rollback()
        raise

    finally:
        db.close()


def _sync_soil(
    zone_id,
    t_hours,
):
    """
    Generate and synchronize synthetic SMAP
    soil-moisture observations for a zone.
    """

    db = SessionLocal()

    try:

        from ..models_db import SoilMoistureObservation

        # Remove previous simulated observations
        db.query(
            SoilMoistureObservation
        ).filter(
            SoilMoistureObservation.zone_id
            == zone_id
        ).delete(
            synchronize_session=False
        )

        # Generate synthetic daily soil moisture (SMAP-style sparse cadence)
        base_moisture = 0.35 + 0.30 * (abs(hash(zone_id)) % 100) / 100
        for h in range(0, t_hours + 1, 12):  # every 12 hours
            rain_so_far = sum(storm(i) for i in range(max(1, h - 72), h + 1))
            saturation = min(0.92, base_moisture + rain_so_far * 0.0008)
            ts = BASE + dt.timedelta(hours=h)
            db.add(
                SoilMoistureObservation(
                    zone_id=zone_id,
                    timestamp=ts,
                    soil_moisture=round(saturation, 3),
                    source="SMAP_MOCK",
                    quality_flag="DEMO_DATA",
                )
            )

        db.commit()

        rows = (
            db.query(
                SoilMoistureObservation
            )
            .filter(
                SoilMoistureObservation.zone_id
                == zone_id
            )
            .order_by(
                SoilMoistureObservation.timestamp
            )
            .all()
        )

        df = pd.DataFrame([
            {
                "timestamp": row.timestamp,
                "soil_moisture": (
                    row.soil_moisture
                ),
            }
            for row in rows
        ])

        return df.sort_values(
            "timestamp"
        )

    except Exception:
        db.rollback()
        raise

    finally:
        db.close()