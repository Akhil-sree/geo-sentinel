"""Zone DEM grids for observed cell-risk (Phase 11-12).

9x9 SRTM-30m grid @250m spacing per zone centroid (2km window):
81 points x 8 zones = 648 locations (7 API calls, within free limits).
Stores data/raw/demgrid_{zid}.json (lats, lngs, elevations + provenance).

Per-cell slope/aspect derived on read (Horn 3x3). Cells with missing
elevations are dropped (never interpolated silently — flagged).
Run: python scripts/fetch_demgrid.py
"""
import json
import math
import os
import sys
import time

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from app.seed import ZONES  # noqa: E402

RAW = os.path.join(os.path.dirname(__file__), "..", "data", "raw")
N = 9
STEP_M = 250.0
M_PER_DEG = 111320.0


def fetch():
    import httpx
    os.makedirs(RAW, exist_ok=True)
    todo = [z for z in ZONES if not os.path.exists(
        os.path.join(RAW, f"demgrid_{z['id']}.json"))]
    if not todo:
        print("all grids cached")
        return
    locs, owners = [], []
    for z in todo:
        dlat = STEP_M / M_PER_DEG
        dlng = STEP_M / (M_PER_DEG * math.cos(math.radians(z["lat"])))
        for i in range(-(N // 2), N // 2 + 1):
            for j in range(-(N // 2), N // 2 + 1):
                locs.append(f"{round(z['lat'] + i * dlat, 6)},"
                            f"{round(z['lng'] + j * dlng, 6)}")
                owners.append(z["id"])
    for s in range(0, len(locs), 100):
        chunk, own = locs[s:s + 100], owners[s:s + 100]
        r = httpx.get("https://api.opentopodata.org/v1/srtm30m",
                      params={"locations": "|".join(chunk)}, timeout=120)
        r.raise_for_status()
        res = r.json()["results"]
        assert len(res) == len(chunk), "short DEM response"
        grids = {}
        for o, loc, cell in zip(own, chunk, res):
            assert cell["dataset"] == "srtm30m", cell
            grids.setdefault(o, {"lats": [], "lngs": [], "elev": []})
            _la, _ln = loc.split(",")
            grids[o]["lats"].append(float(_la))
            grids[o]["lngs"].append(float(_ln))
            grids[o]["elev"].append(cell["elevation"])
        for zid, g in grids.items():
            # chunk may split a zone across calls: merge with existing part
            fn = os.path.join(RAW, f"demgrid_{zid}.json")
            if os.path.exists(fn):
                old = json.load(open(fn))
                g = {k: old[k] + g[k] for k in ("lats", "lngs", "elev")}
            import datetime as _dt
            json.dump({"zone_id": zid, "n": N, "step_m": STEP_M,
                       "dataset": "srtm30m",
                       "retrieved_at": _dt.datetime.now(
                           _dt.timezone.utc).isoformat(),
                       **g}, open(fn, "w"))
        time.sleep(1)  # be nice to the free tier
    for z in todo:
        fn = os.path.join(RAW, f"demgrid_{z['id']}.json")
        g = json.load(open(fn))
        assert len(g["elev"]) == N * N, f"{z['id']}: {len(g['elev'])} cells"
        missing = sum(1 for e in g["elev"] if e is None)
        print(f"{z['id']}: {N * N} cells, {missing} missing")


if __name__ == "__main__":
    fetch()
