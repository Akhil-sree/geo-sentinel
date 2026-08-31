"""Soil moisture adapter — NASA SMAP.

Honesty note baked in: SMAP has ~2–3 day latency and coarse resolution
(~9–36 km), so the freshness chip always reads "2d old (regional proxy)".
It is a regional proxy for saturation, NOT slope-instrument data.
"""
import os
import random
from datetime import datetime, timedelta, timezone
from app.ingest.base import IngestionAdapter
from app.providers.imd import ZONES


class MockSMAPAdapter(IngestionAdapter):
    source_name = "soil_moisture"
    state = "2d old (regional proxy)"

    def fetch(self) -> list[dict]:
        now = datetime.now(timezone.utc)
        # demo: wetness correlates with rainfall history; base 0.3–0.75
        out = []
        for zid in ZONES:
            wetness = 0.35 + 0.45 * (hash(zid) % 100) / 100
            for d in range(7, 2, -1):            # only up to 2 days ago (latency)
                sm = min(0.95, max(0.05, wetness + random.uniform(-0.08, 0.08)))
                out.append({"zone_id": zid,
                            "timestamp": (now - timedelta(days=d)).isoformat(),
                            "soil_moisture": round(sm, 3)})
        return out

    def validate(self, raw: list[dict]) -> list[dict]:
        ok = []
        for r in raw:
            if r.get("zone_id") and r.get("soil_moisture") is not None:
                sm = float(r["soil_moisture"])
                if 0.0 <= sm <= 1.0:
                    r["soil_moisture"] = sm
                    ok.append(r)
        return ok
