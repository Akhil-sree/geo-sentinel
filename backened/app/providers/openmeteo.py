"""Live rainfall + soil-moisture via Open-Meteo (keyless, verifiable).

Docs: https://open-meteo.com/en/docs — hourly `precipitation` (mm) and
`soil_moisture_3_9cm` (m3/m3). No credentials. If unreachable, fetch()
raises → runner marks source STALE (never silently replaced by mock).

Env:
  RAIN_PROVIDER=openmeteo|mock (default mock — safe demo default)
  OPENMETEO_TIMEOUT_S (default 15)

Zone coordinates come from the seeded Meghalaya zones (data-driven,
no hardcoded meteorology).
"""
import os
import time
from datetime import datetime, timezone
from app.ingest.base import IngestionAdapter
from app.providers.common import (CANONICAL_ZONES, canonical_zone, parse_ts,
                                  store_rainfall_rows, store_soil_rows)

API = "https://api.open-meteo.com/v1/forecast"
TIMEOUT = float(os.getenv("OPENMETEO_TIMEOUT_S", "15"))
CACHE_TTL_S = float(os.getenv("OPENMETEO_CACHE_S", "600"))  # 10-min cache
_CACHE: dict[str, tuple[float, list[dict]]] = {}  # key -> (fetched_at, rows)
_LAST_FETCH_META: dict = {}  # latency/freshness evidence for health endpoint


def provider_health() -> dict:
    """Evidence for /api/data-status: last latency, freshness, cache state."""
    meta = dict(_LAST_FETCH_META)
    if not meta:
        return {"provider": "openmeteo", "state": "UNVERIFIED",
                "detail": "No successful fetch yet this process lifetime"}
    age = time.time() - meta.get("fetched_at", 0)
    meta["cache_age_s"] = round(age, 1)
    meta["cache_state"] = "CACHED" if age < CACHE_TTL_S else "STALE"
    return meta

# Zone centroids (seed geography — the only hardcoded part, clearly labeled)
ZONE_LATLNG = {
    "Z1": (25.30, 91.70), "Z2": (25.30, 91.58), "Z3": (25.62, 91.90),
    "Z4": (25.52, 91.27), "Z5": (25.51, 90.20), "Z6": (25.60, 90.46),
    "Z7": (25.45, 92.20), "Z8": (25.39, 90.63),
}
# Provider uses internal Z1..Z8 ids (canonical); legacy MZ-* aliases resolved on store.
LEGACY_ALIAS = {"MZ-CHERRAPUNJI": "Z1", "MZ-MAWSYNRAM": "Z2", "MZ-SOHPUNG": "Z3",
                "MZ-MAWKYRWAT": "Z4", "MZ-SHILLONG": "Z3", "MZ-TURA": "Z5",
                "MZ-WILLNAGAR": "Z6", "MZ-JAINTIA": "Z7"}


def _cached_fetch(key: str, params: dict) -> tuple[list[str], list, str | None]:
    """One cached hourly-variable fetch for a zone. Returns (times, vals, utc_iso_now).

    Raises on transport/HTTP errors (→ runner marks source STALE, never mocked).
    Handles HTTP 429 explicitly so rate limiting is visible, not silent."""
    import httpx
    now_iso = datetime.now(timezone.utc).isoformat()
    hit = _CACHE.get(key)
    if hit and time.time() - hit[0] < CACHE_TTL_S:
        return hit[1][0], hit[1][1], now_iso
    t0 = time.time()
    try:
        r = httpx.get(API, params=params, timeout=TIMEOUT)
    except Exception as e:
        raise RuntimeError(f"Open-Meteo unreachable: {type(e).__name__}: {e}")
    if r.status_code == 429:
        raise RuntimeError("Open-Meteo rate-limited (HTTP 429) — backing off, source STALE")
    r.raise_for_status()
    try:
        hourly = r.json().get("hourly", {})
    except Exception:
        raise RuntimeError("Open-Meteo returned malformed (non-JSON) response")
    times, vals = hourly.get("time", []), None
    for k in ("precipitation", "soil_moisture_3_9cm"):
        if k in hourly:
            vals = hourly.get(k, [])
            break
    if not times or vals is None or len(times) != len(vals):
        raise RuntimeError("Open-Meteo response missing/mismatched hourly series")
    latency = round(time.time() - t0, 2)
    _LAST_FETCH_META.update({"provider": "openmeteo", "state": "LIVE",
                             "last_latency_s": latency, "fetched_at": time.time(),
                             "received_at": now_iso})
    _CACHE[key] = (time.time(), (times, vals))
    return times, vals, now_iso


class OpenMeteoRainAdapter(IngestionAdapter):
    """OBSERVED precipitation (gauge/radar/model blend from Open-Meteo).

    source_type=rainfall, is_live=True after first verified run.
    Missing hours → row dropped (never zero-filled silently); stale provider
    → STALE via base retry contract, never replaced by mock.
    """
    source_name = "rainfall"
    state = "LIVE (Open-Meteo observed precipitation, UNVERIFIED until first successful run)"

    def fetch(self) -> list[dict]:
        out = []
        for zid, (lat, lon) in ZONE_LATLNG.items():
            times, vals, _ = _cached_fetch(
                f"rain|{zid}",
                {"latitude": lat, "longitude": lon, "hourly": "precipitation",
                 "past_days": 7, "forecast_days": 1, "timezone": "UTC"})
            for t, mm in zip(times[-168:], vals[-168:]):
                if mm is None:  # missing-data: skip, don't invent zeros
                    continue
                out.append({"zone_id": zid, "timestamp": t,
                            "rainfall_mm_per_hr": float(mm),
                            "source_type": "rainfall",
                            "is_live": True, "is_simulated": False})
        if not out:
            raise RuntimeError("Open-Meteo returned no hourly rows")
        return out

    def validate(self, raw):
        ok = []
        for r in raw:
            zid = canonical_zone(r.get("zone_id"))
            try:
                mm = float(r["rainfall_mm_per_hr"])
            except (KeyError, TypeError, ValueError):
                continue
            if not (0.0 <= mm < 500.0) or zid is None:
                continue
            if parse_ts(r.get("timestamp")) is None:  # bad/future/ancient stamp
                continue
            r["zone_id"] = zid
            r["rainfall_mm_per_hr"] = mm
            ok.append(r)
        return ok

    def normalize(self, r: dict) -> dict:
        return {"zone_id": canonical_zone(r.get("zone_id")),
                "timestamp": r.get("timestamp"),
                "rainfall_mm_per_hr": float(r["rainfall_mm_per_hr"])}

    def store(self, db, records: list[dict]) -> None:
        if not records:
            # Live provider yielding zero usable rows is a failure, not a
            # clean empty: raise so the run lands as STALE, never LIVE.
            raise RuntimeError("Open-Meteo rainfall: 0 usable rows after validation")
        store_rainfall_rows(db, records, source="OPENMETEO_LIVE", quality="LIVE")


class OpenMeteoSoilAdapter(IngestionAdapter):
    """MODELED soil moisture (ERA5-Land reanalysis via Open-Meteo).

    Explicitly NOT observed/SMAP: soil_moisture_source=MODELED,
    quality=MODELED_PROXY. The ML feature layer receives the source tag so
    the model knows which one it gets (Phase 1B).
    """
    source_name = "soil_moisture"
    state = "LIVE (Open-Meteo MODELED soil moisture, coarse — regional proxy)"

    def fetch(self) -> list[dict]:
        out = []
        for zid, (lat, lon) in ZONE_LATLNG.items():
            times, vals, _ = _cached_fetch(
                f"soil|{zid}",
                {"latitude": lat, "longitude": lon, "hourly": "soil_moisture_3_9cm",
                 "past_days": 7, "forecast_days": 1, "timezone": "UTC"})
            for t, sm in zip(times[-168:], vals[-168:]):
                if sm is None:
                    continue
                out.append({"zone_id": zid, "timestamp": t,
                            "soil_moisture": round(min(1.0, max(0.0, float(sm))), 3),
                            "soil_moisture_source": "MODELED",
                            "soil_moisture_status": "LIVE"})
        if not out:
            raise RuntimeError("Open-Meteo returned no soil rows")
        return out

    def validate(self, raw):
        ok = []
        for r in raw:
            zid = canonical_zone(r.get("zone_id"))
            try:
                sm = float(r["soil_moisture"])
            except (KeyError, TypeError, ValueError):
                continue
            if not (0.0 <= sm <= 1.0) or zid is None:
                continue
            if parse_ts(r.get("timestamp")) is None:
                continue
            r["zone_id"] = zid
            r["soil_moisture"] = sm
            r["soil_moisture_source"] = "MODELED"
            r["soil_moisture_status"] = "LIVE"
            ok.append(r)
        return ok

    def normalize(self, r: dict) -> dict:
        return {"zone_id": canonical_zone(r.get("zone_id")),
                "timestamp": r.get("timestamp"),
                "soil_moisture": float(r["soil_moisture"])}

    def store(self, db, records: list[dict]) -> None:
        if not records:
            raise RuntimeError("Open-Meteo soil: 0 usable rows after validation")
        store_soil_rows(db, records, source="OPENMETEO_MODELED",
                        quality="LIVE — modeled proxy (not observed)")
