"""Unified honesty endpoint: provider + model + satellite status.

GET /api/data-status → every source labeled LIVE / CACHED / SIMULATED /
STALE / UNAVAILABLE with is_live/is_simulated flags. Frontend renders
these verbatim — never infer liveness from mere data presence.
"""
import os

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.ingest.runner import provider_states
from app.ml.mamba_model import temporal_status
from app.ml.rf_model import rf_status

router = APIRouter()


@router.get("/data-status")
def data_status(db: Session = Depends(get_db)):
    providers = provider_states(db)
    sat_enabled = os.getenv("SATELLITE_LIVE", "false").lower() == "true"
    for p in providers:
        if p["source"] == "sentinel1_sar" and not sat_enabled:
            p["freshness"] = "SIMULATED"
            p["quality"] = "SATELLITE_STANDBY — mock value, excluded from production risk"
            p["is_live"] = False
            p["is_simulated"] = True
    # Degraded mode (Phase 22): core rainfall EXPIRED/UNAVAILABLE means
    # risk runs on stale inputs — exposed, never silently mocked.
    rain = next((p for p in providers if p["source"] == "rainfall"), {})
    degraded = rain.get("tier") in ("EXPIRED", "UNAVAILABLE")
    return {
        "mode": ("DEMO_MODE" if os.getenv("DEMO_MODE", "false").lower() == "true"
                 else "PRODUCTION"),
        "degraded": degraded,
        "degradation_reason": ("rainfall EXPIRED/UNAVAILABLE — risk uses "
                               "last good inputs" if degraded else None),
        "providers": providers,
        "models": {
            "static_rf": rf_status(),
            "temporal": temporal_status(),
        },
        "delivery": {
            "sms": ("MOCK DELIVERY — logged only"
                    if os.getenv("SMS_PROVIDER", "mock") == "mock"
                    else "LIVE provider configured — verification required"),
            **_email_status(),
            **_push_status(),
            "alert_lifecycle": "cooldown + escalation-only resend + ack/resolve + audit history",
        },
        "providers_selected": {
            "weather": os.getenv("WEATHER_PROVIDER", os.getenv("RAIN_PROVIDER", "mock")),
            "soil": os.getenv("SOIL_PROVIDER", "modeled"),
            "satellite": os.getenv("SATELLITE_PROVIDER", "demo"),
            "push": os.getenv("PUSH_PROVIDER", "mock"),
        },
    }


def _email_status() -> dict:
    try:
        from app.alerts.email import delivery_status
        return delivery_status()
    except Exception:
        return {"email": "UNAVAILABLE"}


def _push_status() -> dict:
    try:
        from app.notify.push import push_status
        return push_status()
    except Exception:
        return {"push": "UNAVAILABLE"}


@router.get("/model/reliability")
def model_reliability():
    """Measured reliability data (Phase 7): per-bin accuracy vs confidence
    from out-of-fold probabilities, plus calibration statuses. Empty bins
    are null — never interpolated. If a model has no bins, it is UNMEASURED.
    """
    from app.ml import registry as _reg
    out = []
    for m in _reg.all_models():
        metrics = m.get("metrics", {})
        if "reliability_bins" in metrics:
            out.append({"model_id": m["model_id"], "version": m["version"],
                        "calibration_status": m.get("calibration_status",
                                                   "uncalibrated"),
                        "ece": metrics.get("ece"), "brier": metrics.get("brier"),
                        "bins": metrics["reliability_bins"]})
    return {"models": out or "UNMEASURED — run app.ml.train_rf.main_event()",
            "note": "Bins from spatial GroupKFold out-of-fold probabilities"}


@router.get("/jobs")
def jobs(db: Session = Depends(get_db)):
    """Job ledger (Phase 10): ingestion jobs with id, timing, per-source
    outcome. Idempotency: re-running a job never duplicates observations
    (exact zone/timestamp/source dedup + snapshot replace + trim)."""
    from app.models_db import IngestionLog
    rows = (db.query(IngestionLog)
            .filter(IngestionLog.source == "ingestion_job")
            .order_by(IngestionLog.ran_at.desc()).limit(20).all())
    return {"jobs": [{"job_id": (r.detail.split()[0] if r.detail else None),
                      "status": r.status, "detail": r.detail,
                      "at": r.ran_at.isoformat() if r.ran_at else None}
                     for r in rows],
            "idempotency": "zone+timestamp+source dedup; mock snapshots replace"}


@router.get("/worker-status")
def worker_status(db: Session = Depends(get_db)):
    """Operational visibility: last ingestion jobs, worker cadence, failures."""
    from app.models_db import IngestionLog
    recent = (db.query(IngestionLog).order_by(IngestionLog.ran_at.desc())
              .limit(20).all())
    jobs = [r for r in recent if r.source == "ingestion_job"]
    fails = [r for r in recent if r.status in ("STALE", "FAILED")]
    return {"worker_interval_min": float(os.getenv("WORKER_INTERVAL_MIN", "15")),
            "last_job": ({"status": jobs[0].status, "detail": jobs[0].detail,
                          "at": jobs[0].ran_at.isoformat() if jobs[0].ran_at else None}
                         if jobs else None),
            "recent_failures": len(fails),
            "recent_runs": [{"source": r.source, "status": r.status,
                             "detail": r.detail,
                             "at": r.ran_at.isoformat() if r.ran_at else None}
                            for r in recent]}


@router.get("/model/monitor")
def model_monitor(db: Session = Depends(get_db)):
    """Basic model monitoring (Phase 16): drift/validity flags, no auto-retrain.

    Compares the last-24h prediction distribution vs the stored-risk baseline,
    counts missing features, and checks provider freshness. Any significant
    drift returns MODEL MONITORING WARNING — promotion stays manual.
    """
    from datetime import timedelta

    from app.models_db import RainfallObs, RiskScore, SoilMoistureObs
    now = __import__("datetime").datetime.now(__import__("datetime").timezone.utc)
    recent = db.query(RiskScore).filter(
        RiskScore.timestamp >= now - timedelta(hours=24)).all()
    total = db.query(RiskScore).count()
    flags = []
    if total and not recent:
        flags.append("no predictions in last 24h")
    if recent:
        import statistics
        mu = statistics.mean(r.risk_score for r in recent)
        if mu > 0.85 or mu < 0.05:
            flags.append(f"prediction distribution shifted (24h mean {mu:.2f})")
    rain_n = db.query(RainfallObs).count()
    soil_n = db.query(SoilMoistureObs).count()
    if rain_n == 0:
        flags.append("no rainfall observations stored")
    if soil_n == 0:
        flags.append("no soil-moisture observations stored")
    return {"status": ("MODEL MONITORING WARNING: " + "; ".join(flags)
                       if flags else "OK"),
            "flags": flags,
            "predictions_24h": len(recent),
            "predictions_total": total,
            "observations": {"rainfall": rain_n, "soil_moisture": soil_n},
            "note": "Monitoring only — never triggers retraining or promotion"}


@router.get("/ready")
def ready(db: Session = Depends(get_db)):
    try:
        db.execute(__import__("sqlalchemy").text("SELECT 1"))
        db_ok = True
    except Exception:
        db_ok = False
    return {"ready": db_ok, "database": "ok" if db_ok else "unavailable"}


@router.get("/metrics")
def metrics(db: Session = Depends(get_db)):
    """Operational metrics (counts + uptime + request tracing) — request
    counters are in-memory since process start (see app/observability)."""
    import time as _t

    from app.models_db import Alert, CitizenReport, RainfallObs, RiskScore, SensorReading, SoilMoistureObs
    from app.observability import snapshot
    out = {"uptime_process_s": round(_t.perf_counter(), 1),
           "risk_scores": db.query(RiskScore).count(),
           "rainfall_obs": db.query(RainfallObs).count(),
           "soil_obs": db.query(SoilMoistureObs).count(),
           "sensor_readings": db.query(SensorReading).count(),
           "alerts": db.query(Alert).count(),
           "reports": db.query(CitizenReport).count()}
    out["requests"] = snapshot()
    return out
