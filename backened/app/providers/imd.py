"""Rainfall adapter.

DEMO: MockIMDAdapter generates a deterministic synthetic 7-day monsoon
(plays with the frontend scrubber — sim_time offsets the curve).
PRODUCTION: RealIMDAdapter activates only when IMD_API_BASE env var is set.
Every response surfaced by the API carries state="DEMO DATA" until the
real adapter is active.
"""
import math
import os
from datetime import UTC, datetime, timedelta

from app.ingest.base import IngestionAdapter
from app.providers.common import CANONICAL_ZONES, canonical_zone, store_rainfall_rows

# Canonical zone ids (match Zones table). Mock amplitude profile per zone.
ZONES = list(CANONICAL_ZONES)


def _monsoon_mm(zone_id: str, sim_hour: int, phase: int) -> float:
    """Synthetic intensity curve: 4 phases over 168h, per-zone amplitude.
    sim_hour = 24..168 (frontend scrubber), phase = hours since real now
    (production path just uses the observed series)."""
    zid = canonical_zone(zone_id) or zone_id
    amplitude = {"Z1": 60.0, "Z2": 55.0,
                 "Z3": 40.0, "Z4": 25.0}.get(zid, 18.0)
    # build-up → intense → peak → decay
    if sim_hour < 48:
        peak = 0.15
    elif sim_hour < 96:
        peak = 0.45
    elif sim_hour < 140:
        peak = 0.85
    else:
        peak = 1.0
    diurnal = 0.6 + 0.4 * math.sin(sim_hour / 3.0)
    return max(0.0, amplitude * peak * diurnal)


class MockIMDAdapter(IngestionAdapter):
    source_name = "rainfall"
    state = "DEMO DATA"

    def __init__(self, sim_time: int | None = None):
        self.sim_time = sim_time   # demo scrubber position; None = latest

    def fetch(self) -> list[dict]:
        now = datetime.now(UTC)
        out = []
        for zid in ZONES:
            for h in range(168, 0, -1):          # full 7-day series
                sim_hour = self.sim_time if self.sim_time else 168 - h + 24
                mm = _monsoon_mm(zid, max(sim_hour - (168 - h), 24), h)
                out.append({
                    "zone_id": zid,
                    "timestamp": (now - timedelta(hours=h)).isoformat(),
                    "rainfall_mm_per_hr": round(mm, 2),
                })
        return out

    def validate(self, raw: list[dict]) -> list[dict]:
        from app.providers.common import parse_ts
        ok = []
        for r in raw:
            zid = canonical_zone(r.get("zone_id"))
            if not zid or r.get("rainfall_mm_per_hr") is None:
                continue
            try:
                mm = float(r["rainfall_mm_per_hr"])
            except (TypeError, ValueError):
                continue
            if not (0.0 <= mm < 500.0):          # plausibility gate
                continue
            if parse_ts(r.get("timestamp")) is None:  # clock-error gate
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
        # Mock regenerates the full 7-day window every run: replace, don't
        # append (bounds the table; combined with exact-ts dedup = idempotent).
        from app.models_db import RainfallObservation
        from app.providers.common import replace_source_rows
        replace_source_rows(db, RainfallObservation, "IMD_MOCK")
        store_rainfall_rows(db, records, source="IMD_MOCK",
                            quality="DEMO_DATA")


def real_mode_active() -> bool:
    """Read at call time, not import (env may change after startup)."""
    return bool(os.getenv("IMD_API_BASE"))


class RealIMDAdapter(MockIMDAdapter):
    """Activates only when IMD_API_BASE is set. Same contract; different fetch."""
    state = "LIVE"

    def fetch(self) -> list[dict]:
        import httpx
        base = os.environ["IMD_API_BASE"]
        resp = httpx.get(f"{base}/rainfall/hourly",
                         params={"state": "MEGHALAYA", "hours": 168}, timeout=30)
        resp.raise_for_status()
        return resp.json()["observations"]
