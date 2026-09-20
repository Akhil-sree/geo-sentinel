"""Soil moisture adapter — NASA SMAP.

Honesty note baked in: SMAP has ~2–3 day latency and coarse resolution
(~9–36 km), so the freshness chip always reads "2d old (regional proxy)".
It is a regional proxy for saturation, NOT slope-instrument data.
"""
import hashlib
import random
from datetime import datetime, timedelta, timezone
from app.ingest.base import IngestionAdapter
from app.providers.common import CANONICAL_ZONES, canonical_zone, store_soil_rows
from app.providers.imd import ZONES


def _det_rng(*parts: str) -> random.Random:
    """Deterministic per-zone/day RNG — DEMO_MODE is repeatable, no random
    values on every refresh (ponytail: seeded stdlib, no new dep)."""
    h = hashlib.sha256("|".join(parts).encode()).hexdigest()
    return random.Random(int(h[:16], 16))


class MockSMAPAdapter(IngestionAdapter):
    source_name = "soil_moisture"
    state = "2d old (regional proxy)"

    def fetch(self) -> list[dict]:
        now = datetime.now(timezone.utc)
        # demo: wetness correlates with rainfall history; base 0.3–0.75
        out = []
        for zid in ZONES:
            wetness = 0.35 + 0.45 * (int(hashlib.sha256(zid.encode()).hexdigest()[:8], 16) % 100) / 100
            for d in range(7, 2, -1):            # only up to 2 days ago (latency)
                rng = _det_rng(zid, (now - timedelta(days=d)).strftime("%Y-%m-%d"))
                sm = min(0.95, max(0.05, wetness + rng.uniform(-0.08, 0.08)))
                out.append({"zone_id": canonical_zone(zid),
                            "timestamp": (now - timedelta(days=d)).isoformat(),
                            "soil_moisture": round(sm, 3),
                            "soil_moisture_source": "MODELED_PROXY",
                            "soil_moisture_status": "SIMULATED"})
        return out

    def validate(self, raw: list[dict]) -> list[dict]:
        from app.providers.common import parse_ts
        ok = []
        for r in raw:
            zid = canonical_zone(r.get("zone_id"))
            if not zid or r.get("soil_moisture") is None:
                continue
            try:
                sm = float(r["soil_moisture"])
            except (TypeError, ValueError):
                continue
            if not (0.0 <= sm <= 1.0):
                continue
            if parse_ts(r.get("timestamp")) is None:
                continue
            r["zone_id"] = zid
            r["soil_moisture"] = sm
            ok.append(r)
        return ok

    def normalize(self, r: dict) -> dict:
        return {"zone_id": canonical_zone(r.get("zone_id")),
                "timestamp": r.get("timestamp"),
                "soil_moisture": float(r["soil_moisture"])}

    def store(self, db, records: list[dict]) -> None:
        # Explicitly a MODELED proxy (rain-derived), never labeled observed.
        # Full-window snapshot: replace, don't append.
        from app.providers.common import replace_source_rows
        from app.models_db import SoilMoistureObservation
        replace_source_rows(db, SoilMoistureObservation, "SMAP_MOCK")
        store_soil_rows(db, records, source="SMAP_MOCK",
                        quality="DEMO_DATA — modeled proxy, not observed")
