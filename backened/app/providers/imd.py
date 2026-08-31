"""Rainfall adapter.

DEMO: MockIMDAdapter generates a deterministic synthetic 7-day monsoon
(plays with the frontend scrubber — sim_time offsets the curve).
PRODUCTION: RealIMDAdapter activates only when IMD_API_BASE env var is set.
Every response surfaced by the API carries state="DEMO DATA" until the
real adapter is active.
"""
import os
import math
from datetime import datetime, timedelta, timezone
from app.ingest.base import IngestionAdapter

ZONES = ["MZ-CHERRAPUNJI", "MZ-MAWSYNRAM", "MZ-SOHPUNG", "MZ-MAWKYRWAT",
         "MZ-SHILLONG", "MZ-TURA", "MZ-WILLNAGAR", "MZ-JAINTIA"]


def _monsoon_mm(zone_id: str, sim_hour: int, phase: int) -> float:
    """Synthetic intensity curve: 4 phases over 168h, per-zone amplitude.
    sim_hour = 24..168 (frontend scrubber), phase = hours since real now
    (production path just uses the observed series)."""
    amplitude = {"MZ-CHERRAPUNJI": 60.0, "MZ-MAWSYNRAM": 55.0,
                 "MZ-SOHPUNG": 40.0, "MZ-MAWKYRWAT": 25.0}.get(zone_id, 18.0)
    # build-up → intense → peak → decay
    if sim_hour < 48:      peak = 0.15
    elif sim_hour < 96:    peak = 0.45
    elif sim_hour < 140:   peak = 0.85
    else:                  peak = 1.0
    diurnal = 0.6 + 0.4 * math.sin(sim_hour / 3.0)
    return max(0.0, amplitude * peak * diurnal)


class MockIMDAdapter(IngestionAdapter):
    source_name = "rainfall"
    state = "DEMO DATA"

    def __init__(self, sim_time: int | None = None):
        self.sim_time = sim_time   # demo scrubber position; None = latest

    def fetch(self) -> list[dict]:
        now = datetime.now(timezone.utc)
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
        ok = []
        for r in raw:
            if r.get("zone_id") and r.get("rainfall_mm_per_hr") is not None:
                mm = float(r["rainfall_mm_per_hr"])
                if 0.0 <= mm < 500.0:            # plausibility gate
                    r["rainfall_mm_per_hr"] = mm
                    ok.append(r)
        return ok


class RealIMDAdapter(MockIMDAdapter):
    """Activates only when IMD_API_BASE is set. Same contract; different fetch."""
    state = "LIVE"
    REAL_MODE_ACTIVE = bool(os.getenv("IMD_API_BASE"))

    def fetch(self) -> list[dict]:
        import httpx
        base = os.environ["IMD_API_BASE"]
        resp = httpx.get(f"{base}/rainfall/hourly",
                         params={"state": "MEGHALAYA", "hours": 168}, timeout=30)
        resp.raise_for_status()
        return resp.json()["observations"]
