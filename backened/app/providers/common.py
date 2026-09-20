"""Provider observation envelope (Phase 2).

Every provider response must map to this metadata so the UI/API can
honestly distinguish LIVE / CACHED / SIMULATED / STALE / UNAVAILABLE.
"""
from datetime import UTC, datetime


def envelope(source: str, source_type: str, observed_at: str | None,
             is_live: bool, is_simulated: bool, quality: str,
             status: str, raw_reference: str = "") -> dict:
    now = datetime.now(UTC).isoformat()
    return {
        "source": source,
        "source_type": source_type,  # rainfall | soil_moisture | satellite | terrain | history
        "observed_at": observed_at or now,
        "received_at": now,
        "quality": quality,  # e.g. DEMO_DATA, REGIONAL_PROXY, SATELLITE_DEMO, LIVE
        "freshness": status,  # LIVE | CACHED | SIMULATED | STALE | UNAVAILABLE
        "is_live": is_live,
        "is_simulated": is_simulated,
        "raw_reference": raw_reference,
    }


# Canonical zone ids ( Zones table uses Z1..Z8 ). Legacy mock MZ-* aliases
# resolve here so every observation lands on a real zone row.
CANONICAL_ZONES = ("Z1", "Z2", "Z3", "Z4", "Z5", "Z6", "Z7", "Z8")
LEGACY_ALIAS = {"MZ-CHERRAPUNJI": "Z1", "MZ-MAWSYNRAM": "Z2", "MZ-SOHPUNG": "Z3",
                "MZ-MAWKYRWAT": "Z4", "MZ-SHILLONG": "Z3", "MZ-TURA": "Z5",
                "MZ-WILLNAGAR": "Z6", "MZ-JAINTIA": "Z7", "MZ-BAGHMARA": "Z8"}


def canonical_zone(zid: str | None) -> str | None:
    if not zid:
        return None
    zid = str(zid).strip().upper()
    if zid in CANONICAL_ZONES:
        return zid
    return LEGACY_ALIAS.get(zid)


def parse_ts(ts, *, max_age_days: float = 10.0, max_future_h: float = 2.0):
    """Parse + validate an observation timestamp. Returns aware datetime or None.

    Rejects unparseable, far-future (>max_future_h) and ancient (>max_age_days)
    stamps so provider clock errors never silently enter the feature store.
    """
    from datetime import timedelta
    try:
        dt = datetime.fromisoformat(str(ts).replace("Z", "+00:00"))
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=UTC)
    except (ValueError, TypeError):
        return None
    now = datetime.now(UTC)
    if dt > now + timedelta(hours=max_future_h):
        return None
    if dt < now - timedelta(days=max_age_days):
        return None
    return dt


def _existing_keys(db, model, source: str) -> set:
    """(zone_id, timestamp, source) already stored — idempotency set."""
    try:
        rows = db.query(model).filter(model.source == source).all()
    except Exception:
        return set()
    ts_col = getattr(model, "timestamp", None) or getattr(model, "acquisition_date", None)
    return {(r.zone_id, getattr(r, ts_col.key).isoformat()
             if getattr(r, ts_col.key) else None, source) for r in rows}


def replace_source_rows(db, model, source: str) -> int:
    """Delete all rows of a snapshot source (mock full-window regeneration)."""
    try:
        n = db.query(model).filter(model.source == source).delete(
            synchronize_session=False)
        db.commit()
        return n
    except Exception:
        db.rollback()
        return 0


def trim_observations(db, rain_days: float = 10.0, soil_days: float = 10.0,
                      sar_days: float = 60.0) -> dict:
    """Bound table growth: drop observations older than the validity window
    (matches parse_ts gates). Live history still accumulates within the
    window — trim only removes expired rows."""
    from datetime import timedelta

    from app.models_db import RainfallObservation, SARObs, SoilMoistureObservation
    now = datetime.now(UTC)
    out = {}
    for model, col, days, key in (
            (RainfallObservation, "timestamp", rain_days, "rainfall"),
            (SoilMoistureObservation, "timestamp", soil_days, "soil"),
            (SARObs, "acquisition_date", sar_days, "sar")):
        try:
            n = db.query(model).filter(
                getattr(model, col) < now - timedelta(days=days)).delete(
                synchronize_session=False)
            out[key] = n
        except Exception:
            db.rollback()
            out[key] = -1
    db.commit()
    return out


def store_rainfall_rows(db, records: list[dict], *, source: str, quality: str) -> int:
    """Persist validated rainfall rows. Idempotent: same (zone, timestamp,
    source) is never stored twice (re-run safe). Returns stored count."""
    from app.models_db import RainfallObservation
    seen = _existing_keys(db, RainfallObservation, source)
    n = skip = 0
    for r in records:
        zid = canonical_zone(r.get("zone_id"))
        ts = parse_ts(r.get("timestamp"))
        try:
            mm = float(r["rainfall_mm_per_hr"])
        except (KeyError, TypeError, ValueError):
            continue
        if zid is None or ts is None or not (0.0 <= mm < 500.0):
            continue
        if (zid, ts.isoformat(), source) in seen:
            skip += 1
            continue
        seen.add((zid, ts.isoformat(), source))
        db.add(RainfallObservation(zone_id=zid, timestamp=ts,
                                   rainfall_mm_per_hr=mm, source=source,
                                   quality_flag=quality))
        n += 1
    db.commit()
    return n


def store_soil_rows(db, records: list[dict], *, source: str, quality: str) -> int:
    from app.models_db import SoilMoistureObservation
    seen = _existing_keys(db, SoilMoistureObservation, source)
    n = 0
    for r in records:
        zid = canonical_zone(r.get("zone_id"))
        ts = parse_ts(r.get("timestamp"))
        try:
            sm = float(r["soil_moisture"])
        except (KeyError, TypeError, ValueError):
            continue
        if zid is None or ts is None or not (0.0 <= sm <= 1.0):
            continue
        if (zid, ts.isoformat(), source) in seen:
            continue
        seen.add((zid, ts.isoformat(), source))
        db.add(SoilMoistureObservation(zone_id=zid, timestamp=ts,
                                       soil_moisture=sm, source=source,
                                       quality_flag=quality))
        n += 1
    db.commit()
    return n


def store_sar_rows(db, records: list[dict], *, source: str) -> int:
    """SAR rows are metadata only — quarantined from the risk path unless
    SATELLITE_LIVE=true (see services/sim.py neutral constant)."""
    from app.models_db import SARObs
    seen = _existing_keys(db, SARObs, source)
    n = 0
    for r in records:
        zid = canonical_zone(r.get("zone_id"))
        ts = parse_ts(r.get("acquisition_date"), max_age_days=60.0)
        try:
            s = float(r["sar_change_score"])
        except (KeyError, TypeError, ValueError):
            continue
        if zid is None or ts is None or not (0.0 <= s <= 1.0):
            continue
        if (zid, ts.isoformat(), source) in seen:
            continue
        seen.add((zid, ts.isoformat(), source))
        db.add(SARObs(zone_id=zid, acquisition_date=ts,
                      previous_ac=r.get("previous_ac"),
                      sar_change_score=s, source=source))
        n += 1
    db.commit()
    return n
