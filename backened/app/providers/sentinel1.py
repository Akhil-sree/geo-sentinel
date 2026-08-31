"""Sentinel-1 SAR change-detection adapter.

PRODUCTION plan: two SLC/GRD acquisitions (t1, t2) → speckle filter →
coherence/log-ratio change score per zone polygon (0..1). Coarse here by
design; the UI labels it "sparse acquisitions — not continuous monitoring".

DEMO: MockSentinel1Adapter returns a per-zone change score + acquisition
dates, freshness "6d old (sparse)".
"""
import os
import random
from datetime import datetime, timedelta, timezone
from app.ingest.base import IngestionAdapter
from app.providers.imd import ZONES


class MockSentinel1Adapter(IngestionAdapter):
    source_name = "sentinel1_sar"
    state = "6d old (sparse acquisitions)"

    HONESTY_NOTE = ("SAR acquisitions are days apart — detects past ground "
                    "change, not live slope motion. Never used as a real-time signal.")

    def fetch(self) -> list[dict]:
        now = datetime.now(timezone.utc)
        out = []
        for zid in ZONES:
            out.append({
                "zone_id": zid,
                "acquisition_date": (now - timedelta(days=6)).isoformat(),
                "previous_ac": (now - timedelta(days=18)).isoformat(),
                "sar_change_score": round(random.uniform(0.05, 0.55), 3),
                "honesty_note": self.HONESTY_NOTE,
            })
        return out

    def validate(self, raw: list[dict]) -> list[dict]:
        ok = []
        for r in raw:
            s = r.get("sar_change_score")
            if r.get("zone_id") and s is not None and 0.0 <= float(s) <= 1.0:
                r["sar_change_score"] = float(s)
                ok.append(r)
        return ok
