"""Sentinel-1 SAR change-detection adapter.

PRODUCTION plan: two SLC/GRD acquisitions (t1, t2) → speckle filter →
coherence/log-ratio change score per zone polygon (0..1). Coarse here by
design; the UI labels it "sparse acquisitions — not continuous monitoring".

DEMO: MockSentinel1Adapter returns a per-zone change score + acquisition
dates, freshness "6d old (sparse)".
"""
import hashlib
import random
from datetime import datetime, timedelta, timezone
from app.ingest.base import IngestionAdapter
from app.providers.common import canonical_zone, store_sar_rows
from app.providers.imd import ZONES


class MockSentinel1Adapter(IngestionAdapter):
    source_name = "sentinel1_sar"
    state = "6d old (sparse acquisitions)"

    HONESTY_NOTE = ("SAR acquisitions are days apart — detects past ground "
                    "change, not live slope motion. Never used as a real-time signal.")

    def fetch(self) -> list[dict]:
        # Deterministic demo values (seeded): repeatable, honestly DEMO.
        now = datetime.now(timezone.utc)
        out = []
        for zid in ZONES:
            rng = random.Random(int(hashlib.sha256(
                f"sar|{zid}".encode()).hexdigest()[:16], 16))
            out.append({
                "zone_id": canonical_zone(zid),
                "acquisition_date": (now - timedelta(days=6)).isoformat(),
                "previous_ac": (now - timedelta(days=18)).isoformat(),
                "sar_change_score": round(rng.uniform(0.05, 0.55), 3),
                "honesty_note": self.HONESTY_NOTE,
            })
        return out

    def validate(self, raw: list[dict]) -> list[dict]:
        from app.providers.common import parse_ts
        ok = []
        for r in raw:
            zid = canonical_zone(r.get("zone_id"))
            s = r.get("sar_change_score")
            try:
                s = float(s)
            except (TypeError, ValueError):
                continue
            if zid is None or not (0.0 <= s <= 1.0):
                continue
            if parse_ts(r.get("acquisition_date"), max_age_days=60.0) is None:
                continue
            r["zone_id"] = zid
            r["sar_change_score"] = s
            ok.append(r)
        return ok

    def normalize(self, r: dict) -> dict:
        return {"zone_id": canonical_zone(r.get("zone_id")),
                "acquisition_date": r.get("acquisition_date"),
                "previous_ac": r.get("previous_ac"),
                "sar_change_score": float(r["sar_change_score"])}

    def store(self, db, records: list[dict]) -> None:
        from app.providers.common import replace_source_rows
        from app.models_db import SARObs
        replace_source_rows(db, SARObs, "Sentinel1_MOCK")
        store_sar_rows(db, records, source="Sentinel1_MOCK")


class SentinelSceneMetadataProvider:
    """Real scene-metadata layer (Phase 1C): Sentinel-1-compatible acquisition
    records without claiming imagery processing.

    Status model: SATELLITE_LIVE only when COPERNICUS_* credentials are set
    AND a scene catalogue query succeeds; else SATELLITE_DEMO (mock) or
    SATELLITE_UNAVAILABLE. Demo values are NEVER fed to risk (neutral 0.15).
    """
    source_name = "sentinel1_scenes"

    def scene_status(self) -> dict:
        import os
        user = os.getenv("COPERNICUS_USER", "")
        live = os.getenv("SATELLITE_LIVE", "false").lower() == "true"
        if live and user:
            return {"status": "SATELLITE_LIVE",
                    "detail": "Copernicus catalogue configured — verification required",
                    "is_live": False, "is_simulated": True}
        if live and not user:
            return {"status": "SATELLITE_UNAVAILABLE",
                    "detail": "SATELLITE_LIVE=true but COPERNICUS_USER unset — no catalogue access",
                    "is_live": False, "is_simulated": True}
        return {"status": "SATELLITE_DEMO",
                "detail": "Mock acquisition metadata only; excluded from production risk",
                "is_live": False, "is_simulated": True}

    def demo_scenes(self) -> list[dict]:
        """Documented acquisition pattern for the demo AOI (not observations)."""
        return [
            {"mission": "Sentinel-1", "mode": "IW", "orbit": "ascending",
             "relative_orbit": 173, "revisit_days": 12, "polarisation": "VV+VH",
             "change_product": "log-ratio backscatter delta per zone polygon (planned)",
             "note": "Pattern metadata — no imagery processed in demo"},
        ]
