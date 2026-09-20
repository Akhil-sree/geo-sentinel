"""Real DEM acquisition (Phase 12): 5x5 SRTM-30m grid per zone centroid.

Source: OpenTopodata /v1/srtm30m (keyless, 100 locations/call, ~1-2 calls).
Derives elevation (center), slope + aspect (Horn 3x3 on center cell),
ruggedness (std) and relief (max-min) over the 150m window.
Stores raw grids (data/raw/dem_{zid}.json) + TerrainDEM rows + provenance.

Legacy STATIC seed profiles are untouched (legacy RF path unchanged).
Run: python scripts/fetch_dem.py [--fetch] [--store]
"""
import datetime as dt
import json
import math
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from app.seed import ZONES  # noqa: E402

RAW = os.path.join(os.path.dirname(__file__), "..", "data", "raw")
STEP_M = 30.0
M_PER_DEG = 111320.0


def grid(lat, lng, n=5):
    dlat = STEP_M / M_PER_DEG
    dlng = STEP_M / (M_PER_DEG * math.cos(math.radians(lat)))
    pts = []
    for i in range(-(n // 2), n // 2 + 1):
        for j in range(-(n // 2), n // 2 + 1):
            pts.append((round(lat + i * dlat, 6), round(lng + j * dlng, 6)))
    return pts


def fetch():
    import httpx
    os.makedirs(RAW, exist_ok=True)
    locs, owners = [], []
    for z in ZONES:
        fn = os.path.join(RAW, f"dem_{z['id']}.json")
        if os.path.exists(fn):
            print("cached", fn)
            continue
        for la, ln in grid(z["lat"], z["lng"]):
            locs.append(f"{la},{ln}")
            owners.append(z["id"])
    pending = sorted({o for o in owners if not os.path.exists(
        os.path.join(RAW, f"dem_{o}.json"))})
    if not pending:
        return
    # 100 locations/call
    idx = [i for i, o in enumerate(owners) if o in pending]
    for s in range(0, len(idx), 100):
        chunk = idx[s:s + 100]
        r = httpx.get("https://api.opentopodata.org/v1/srtm30m",
                      params={"locations": "|".join(locs[i] for i in chunk)},
                      timeout=60)
        r.raise_for_status()
        res = r.json()["results"]
        assert len(res) == len(chunk), "short DEM response"
        by_zone = {}
        for i, cell in zip(chunk, res):
            assert cell["dataset"] == "srtm30m", cell
            by_zone.setdefault(owners[i], []).append(cell["elevation"])
        for zid, elevs in by_zone.items():
            assert len(elevs) == 25 and all(e is not None for e in elevs), zid
            json.dump(
                {"zone_id": zid, "dataset": "srtm30m", "step_m": STEP_M,
                 "retrieved_at": dt.datetime.now(dt.timezone.utc).isoformat(),
                 "elevations_m": elevs},
                open(os.path.join(RAW, f"dem_{zid}.json"), "w"))
            print("fetched", zid)


def derive(elevs):
    """Horn (1981) slope/aspect on center 3x3 of the 5x5 grid (z[12] center)."""
    import numpy as np
    g = np.asarray(elevs, dtype=float).reshape(5, 5)
    c = g[1:4, 1:4]
    dzdx = ((c[0, 2] + 2 * c[1, 2] + c[2, 2])
            - (c[0, 0] + 2 * c[1, 0] + c[2, 0])) / (8 * STEP_M)
    dzdy = ((c[2, 0] + 2 * c[2, 1] + c[2, 2])
            - (c[0, 0] + 2 * c[0, 1] + c[0, 2])) / (8 * STEP_M)
    slope = math.degrees(math.atan(math.hypot(dzdx, dzdy)))
    aspect = (math.degrees(math.atan2(dzdx, -dzdy)) + 360) % 360
    return {"elevation_m": round(float(g[2, 2]), 1),
            "slope_deg": round(float(slope), 2),
            "aspect_deg": round(float(aspect), 1),
            "ruggedness_m": round(float(g.std()), 2),
            "relief_m": round(float(g.max() - g.min()), 1)}


def store():
    from app.database import SessionLocal
    from app.models_db import TerrainDEM
    db = SessionLocal()
    try:
        for z in ZONES:
            fn = os.path.join(RAW, f"dem_{z['id']}.json")
            raw = json.load(open(fn))
            d = derive(raw["elevations_m"])
            row = db.get(TerrainDEM, z["id"])
            if row is None:
                row = TerrainDEM(zone_id=z["id"])
                db.add(row)
            row.dem_source = "SRTM GL1 30m via OpenTopodata"
            row.resolution_m = 30.0
            row.retrieved_at = dt.datetime.fromisoformat(raw["retrieved_at"])
            for k, v in d.items():
                setattr(row, k, v)
            print(z["id"], d)
        db.commit()
    finally:
        db.close()


if __name__ == "__main__":
    if "--fetch" in sys.argv:
        fetch()
    if "--store" in sys.argv:
        store()
    if len(sys.argv) < 2:
        print("usage: fetch_dem.py [--fetch] [--store]")
