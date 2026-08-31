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
    """Real adapters substitute here when env credentials exist —
    the runner never changes, only this registry does."""
    return [MockIMDAdapter(), MockSMAPAdapter(), MockSentinel1Adapter()]


def run_ingestion(db: Session) -> dict:
    """Run all adapters → store canonical observations → return summary."""
    results = []
    for adapter in _adapters():
        try:
            results.append(adapter.run(db))          # contract handles retry/STALE
        except Exception as e:                        # defensive: one adapter
            results.append({"source": adapter.source_name,   # must never kill the run
                            "status": "STALE", "detail": str(e)})

    _persist_features(db)
    return {"ran_at": datetime.now(timezone.utc).isoformat(), "sources": results}


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

    for sm in db.query(SoilMoistureObs).all():
        _upsert_feature(db, sm.zone_id, {"soil_moisture": sm.soil_moisture})

    for s in db.query(SARObs).all():
        _upsert_feature(db, s.zone_id, {"sar_change_score": s.sar_change_score})

    db.commit()


def _upsert_feature(db: Session, zone_id: str, patch: dict) -> None:
    from app.models_db import ZoneFeature
    row = db.get(ZoneFeature, zone_id)
    if row is None:
        row = ZoneFeature(zone_id=zone_id, **patch)
        db.add(row)
    else:
        for k, v in patch.items():
            setattr(row, k, v)


def get_freshness_snapshot(db: Session) -> dict:
    """What /admin/data serves — the honesty layer's source of truth.
    STALE/DEMO states are reported verbatim; the UI renders them as-is."""
    recent = (db.query(IngestionLog)
                .order_by(IngestionLog.at.desc())
                .limit(12).all())
    freshness = []
    for src, state_cls in [("rainfall", MockIMDAdapter),
                           ("soil_moisture", MockSMAPAdapter),
                           ("sentinel1_sar", MockSentinel1Adapter)]:
        last = next((l for l in recent if l.source == src), None)
        freshness.append({
            "source": src,
            "state": state_cls.state if last and last.status in ("OK", "EMPTY")
                     else "STALE — no recent successful run",
            "note": getattr(state_cls, "HONESTY_NOTE", "mock provider — DEMO DATA"),
        })
    return {
        "mode": "DEMO_MODE — synthetic monsoon, labeled DEMO DATA",
        "freshness": freshness,
        "recent_ingestion_runs": [
            {"source": l.source, "status": l.status, "detail": l.detail, "at": l.at}
            for l in recent
        ],
    }
