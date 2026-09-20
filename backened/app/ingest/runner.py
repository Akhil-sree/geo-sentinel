"""Pipeline runner: executes every registered adapter against the DB,
then persists derived per-zone features used by the risk engine.

Contract honored per adapter: retries with backoff inside adapter.run();
a failed source lands in IngestionLog as STALE — it never blocks the
other sources, and its staleness is surfaced via /admin/data.
"""
from datetime import datetime, timedelta, timezone
from sqlalchemy.orm import Session

from app.models_db import IngestionLog, RainfallObs, SoilMoistureObs, SARObs
from app.providers.imd import MockIMDAdapter
from app.providers.smap import MockSMAPAdapter
from app.providers.sentinel1 import MockSentinel1Adapter


def _adapters():
    """Real adapters substitute here when env selects them —
    the runner never changes, only this registry does.
    RAIN_PROVIDER=openmeteo → live keyless Open-Meteo (UNVERIFIED until
    first OK run); default mock. Satellite has NO live path: mock values
    are quarantined as SATELLITE_DEMO and neutralized in the risk path."""
    import os
    chain = []
    if os.getenv("RAIN_PROVIDER", "mock").lower() == "openmeteo":
        from app.providers.openmeteo import OpenMeteoRainAdapter, OpenMeteoSoilAdapter
        chain = [OpenMeteoRainAdapter(), OpenMeteoSoilAdapter()]
    else:
        chain = [MockIMDAdapter(), MockSMAPAdapter()]
    chain.append(MockSentinel1Adapter())  # DEMO only — see provider_states
    return chain


def run_ingestion(db: Session) -> dict:
    """Run all adapters → store canonical observations → return job summary.

    Job record: job_id, started/completed_at, duration_s, per-source status,
    data_version. One adapter's failure never kills the run; failures land
    as STALE (never silently mocked).
    """
    import time as _time
    import uuid as _uuid
    job_id = f"ingest-{_uuid.uuid4().hex[:8]}"
    started = datetime.now(timezone.utc)
    t0 = _time.time()
    results = []
    for adapter in _adapters():
        s0 = _time.time()
        try:
            out = adapter.run(db)                    # contract handles retry/STALE
            out["duration_s"] = round(_time.time() - s0, 2)
            results.append(out)
        except Exception as e:                        # defensive: one adapter
            results.append({"source": adapter.source_name,   # must never kill the run
                            "status": "STALE", "detail": str(e),
                            "duration_s": round(_time.time() - s0, 2)})

    _persist_features(db)
    from app.providers.common import trim_observations
    trimmed = trim_observations(db)
    completed = datetime.now(timezone.utc)
    summary = {"job_id": job_id,
               "started_at": started.isoformat(),
               "completed_at": completed.isoformat(),
               "duration_s": round(_time.time() - t0, 2),
               "status": "OK" if all(r.get("status") in ("OK", "EMPTY") for r in results) else "DEGRADED",
               "data_version": started.strftime("obs-%Y%m%dT%H%MZ"),
               "trimmed": trimmed,
               "ran_at": completed.isoformat(), "sources": results}
    try:
        db.add(IngestionLog(source="ingestion_job", status=summary["status"],
                            detail=f"{job_id} {len(results)} sources in {summary['duration_s']}s"))
        db.commit()
    except Exception as e:
        _log.getLogger("geo-sentinel").debug("Ingestion log commit failed: %s", e)
        db.rollback()
    return summary


def _persist_features(db: Session) -> None:
    """Upsert per-zone derived features from the latest observations.

    Features consumed by compute_zone_risk():
      rainfall_24h, rainfall_72h, rainfall_7d, rainfall_slope (24h trend),
      soil_moisture (latest, with latency honesty), sar_change_score.
    """
    now = datetime.now(timezone.utc)
    rain_rows = db.query(RainfallObs).filter(
        RainfallObs.timestamp >= now - timedelta(days=8)).all()

    by_zone: dict[str, list[RainfallObs]] = {}
    for r in rain_rows:
        by_zone.setdefault(r.zone_id, []).append(r)

    for zid, rows in by_zone.items():
        rows.sort(key=lambda x: x.timestamp)
        vals = [x.rainfall_mm_per_hr for x in rows]
        last24 = sum(vals[-24:]) or 0.0
        last72 = sum(vals[-72:]) or 0.0
        last7d = sum(vals[-168:]) or 0.0
        prev24 = sum(vals[-48:-24]) or 0.0
        # store derived snapshot on the zone row via a simple feature upsert
        _upsert_feature(db, zid, {
            "rainfall_24h": round(last24, 1),
            "rainfall_72h": round(last72, 1),
            "rainfall_7d": round(last7d, 1),
            "rainfall_slope": round(last24 - prev24, 1),   # 24h-over-24h trend
        })

    # Latest observation per zone (not last-row-wins): soil + SAR.
    def _key(ts):
        if ts is None:
            return datetime.min  # naive floor; all comparisons naive
        return ts.replace(tzinfo=None)
    _min = datetime.min
    latest_soil: dict[str, SoilMoistureObs] = {}
    for sm in db.query(SoilMoistureObs).all():
        cur = latest_soil.get(sm.zone_id)
        if cur is None or _key(sm.timestamp) > _key(cur.timestamp):
            latest_soil[sm.zone_id] = sm
    for zid, sm in latest_soil.items():
        _upsert_feature(db, zid, {"soil_moisture": sm.soil_moisture})

    latest_sar: dict[str, SARObs] = {}
    for s in db.query(SARObs).all():
        cur = latest_sar.get(s.zone_id)
        if cur is None or _key(s.acquisition_date) > _key(cur.acquisition_date):
            latest_sar[s.zone_id] = s
    for zid, s in latest_sar.items():
        _upsert_feature(db, zid, {"sar_change_score": s.sar_change_score})

    db.commit()


def _upsert_feature(db: Session, zone_id: str, patch: dict) -> None:
    """Upsert against a preloaded map: Session.get() misses PENDING rows
    when autoflush is off, which duplicated ZoneFeature rows (IntegrityError
    on commit). One SELECT up front; single commit at the end."""
    from app.models_db import ZoneFeature
    cache = getattr(db, "_zf_cache", None)
    if cache is None:
        cache = {r.zone_id: r for r in db.query(ZoneFeature).all()}
        db._zf_cache = cache
    row = cache.get(zone_id)
    if row is None:
        row = ZoneFeature(zone_id=zone_id, **patch)
        db.add(row)
        cache[zone_id] = row
    else:
        for k, v in patch.items():
            setattr(row, k, v)


def provider_states(db: Session) -> list[dict]:
    """Machine-readable honesty layer for /api/data-status."""
    import os
    recent = (db.query(IngestionLog).order_by(IngestionLog.ran_at.desc()).limit(12).all())
    live_rain = os.getenv("RAIN_PROVIDER", "mock").lower() == "openmeteo"
    # Freshness tiers (Phase 22): FRESH / STALE / EXPIRED / UNAVAILABLE
    # by age of last OK run. Thresholds are policy parameters (documented).
    TIERS = {"rainfall": (360, 1440), "soil_moisture": (360, 1440),
             "sentinel1_sar": (12 * 1440, 30 * 1440)}  # (fresh_min, stale_min)

    def _tier(src: str, last) -> tuple[str, float | None]:
        if last is None or last.status != "OK" or not last.ran_at:
            return "UNAVAILABLE", None
        age = (datetime.now(timezone.utc) - last.ran_at.replace(
            tzinfo=timezone.utc)).total_seconds() / 60
        fresh_min, stale_min = TIERS.get(src, (360, 1440))
        if age <= fresh_min:
            return "FRESH", age
        if age <= stale_min:
            return "STALE", age
        return "EXPIRED", age

    def state_for(src: str, live: bool, demo_label: str) -> dict:
        last = next((l for l in recent if l.source == src), None)
        tier, age = _tier(src, last)
        if tier == "FRESH":
            fresh = "LIVE" if live else "SIMULATED"
            return {"source": src, "freshness": fresh, "tier": tier,
                    "age_min": round(age, 1),
                    "quality": "LIVE" if live else demo_label,
                    "is_live": live, "is_simulated": not live,
                    "observed_at": last.ran_at.isoformat() if last.ran_at else None}
        return {"source": src,
                "freshness": ("STALE — no recent successful run"
                              if tier in ("STALE", "UNAVAILABLE")
                              else "EXPIRED — too old for risk use"),
                "tier": tier,
                "age_min": round(age, 1) if age is not None else None,
                "quality": demo_label, "is_live": False, "is_simulated": True,
                "observed_at": (last.ran_at.isoformat()
                                if last and last.ran_at else None)}
    from app.providers.sentinel1 import SentinelSceneMetadataProvider
    sat = SentinelSceneMetadataProvider().scene_status()
    soil_quality = ("LIVE — modeled proxy (not observed)" if live_rain
                    else "DEMO_DATA (rain-derived proxy)")
    states = [
        state_for("rainfall", live_rain, "DEMO_DATA (synthetic monsoon)"),
        state_for("soil_moisture", live_rain, soil_quality),
        {"source": "sentinel1_sar", "freshness": sat["status"],
         "tier": "STALE",  # periodic sensor by design; see scene_status
         "age_min": None,
         "quality": ("SATELLITE_DEMO — deterministic mock, excluded from production risk"
                     if sat["status"] == "SATELLITE_DEMO" else sat["detail"]),
         "is_live": False, "is_simulated": True, "observed_at": None},
    ]
    # Feature-level provenance: the model must know observed vs modeled soil.
    try:
        latest_sm = (db.query(SoilMoistureObs).order_by(
            SoilMoistureObs.timestamp.desc()).first())
        for p in states:
            if p["source"] == "soil_moisture" and latest_sm is not None:
                src = (latest_sm.source or "")
                p["soil_moisture_source"] = ("OBSERVED" if src.startswith("SMAP_LIVE")
                                             else "MODELED")
                p["soil_moisture_status"] = p["freshness"]
    except Exception as e:
        _log.getLogger("geo-sentinel").debug("Soil moisture source enhancement failed: %s", e)
    return states
