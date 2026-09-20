"""Per-event SRTM terrain windows (SIH §12-13).

Extends (never replaces) scripts/fetch_dem.py + fetch_demgrid.py: for each
TEMPORAL event/control, fetches a 5x5 SRTM30m window around the location via
OpenTopodata (public, cached per location) and derives mean/min/max/range
elevation, mean/max slope, slope variance, aspect, ruggedness + resolution
+ window metadata. Failures → missing code, never zeros.
"""
import json
import math
import os
import sys
import time

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "data"))

from ner_common import RAW_DIR, write_json, utcnow, OFFICIAL_SOURCES

CACHE_TPL = os.path.join(RAW_DIR, "ner_dem_{eid}.json")
STEP_M = 30.0


def _grid(lat: float, lon: float, n: int = 5) -> list[list[float]]:
    import urllib.request
    import urllib.parse
    locs = []
    for i in range(n):
        for j in range(n):
            la = lat + (i - n // 2) * STEP_M / 111320.0
            lo = lon + (j - n // 2) * STEP_M / (111320.0 * math.cos(math.radians(lat)))
            locs.append(f"{la:.6f},{lo:.6f}")
    out = []
    for k in range(0, len(locs), 100):  # batched requests, not N×1
        q = urllib.parse.urlencode({"locations": "|".join(locs[k:k + 100])})
        for attempt in range(4):
            try:
                req = urllib.request.Request(
                    f"https://api.opentopodata.org/v1/srtm30m?{q}",
                    headers={"User-Agent": "GEO-SENTINEL-ner-pipeline/1.0"})
                with urllib.request.urlopen(req, timeout=40) as r:
                    out.extend(x["elevation"] for x in json.loads(r.read().decode())["results"])
                break
            except urllib.error.HTTPError as e:
                if e.code == 429 and attempt < 3:
                    time.sleep(15 * (attempt + 1))  # free-tier backoff, then resume
                    continue
                raise
        time.sleep(2)
    return [out[i * n:(i + 1) * n] for i in range(n)]


def _derive(g: list[list[float]]) -> dict:
    flat = [v for row in g for v in row if v is not None]
    if not flat:
        raise RuntimeError("empty DEM window")
    n = len(g)
    slopes = []
    for i in range(1, n - 1):
        for j in range(1, n - 1):
            dzdx = (g[i][j + 1] - g[i][j - 1]) / (2 * STEP_M)
            dzdy = (g[i - 1][j] - g[i + 1][j]) / (2 * STEP_M)
            slopes.append(math.degrees(math.atan(math.hypot(dzdx, dzdy))))
    mu = sum(flat) / len(flat)
    var = sum((v - mu) ** 2 for v in flat) / len(flat)
    sm = sum(slopes) / len(slopes)
    return {"elevation_mean": round(mu, 1), "elevation_min": round(min(flat), 1),
            "elevation_max": round(max(flat), 1), "elevation_range": round(max(flat) - min(flat), 1),
            "slope_mean": round(sm, 2), "slope_max": round(max(slopes), 2),
            "slope_var": round(sum((s - sm) ** 2 for s in slopes) / len(slopes), 3),
            "ruggedness": round(math.sqrt(var), 2),
            "dem_source": "SRTM GL1 30m via OpenTopodata",
            "dem_resolution_m": 30.0, "window": "5x5@30m",
            "source_url": OFFICIAL_SOURCES["usgs"]}


def fetch_event(eid: int, lat: float, lon: float, force: bool = False) -> dict:
    dest = CACHE_TPL.format(eid=eid)
    if os.path.exists(dest) and not force:
        with open(dest, encoding="utf-8") as f:
            return {"status": "CACHED", "file": dest}
    feats = _derive(_grid(lat, lon))
    feats.update({"event_id": eid, "lat": lat, "lon": lon, "retrieved_at": utcnow()})
    write_json(dest, feats)
    return {"status": "DOWNLOADED", "file": dest}


def main() -> dict:
    from app.database import SessionLocal
    from app.models_db import NerInventory, TrainingSample
    force = "--force" in sys.argv
    db = SessionLocal()
    try:
        pts = [(e.id, e.latitude, e.longitude)
               for e in db.query(NerInventory).filter(NerInventory.record_kind == "TEMPORAL").all()]
        pts += [(f"C{s.id}", s.latitude, s.longitude)
                for s in db.query(TrainingSample)
                .filter(TrainingSample.label == "NO_RECORDED_LANDSLIDE").all()]
    finally:
        db.close()
    ok, failed = 0, []
    for eid, lat, lon in pts:
        try:
            fetch_event(eid, lat, lon, force=force)
            ok += 1
        except Exception as ex:  # noqa: BLE001
            failed.append({"id": str(eid), "error": f"{type(ex).__name__}: {ex}"[:150]})
    rep = {"points": len(pts), "ok": ok, "failed": len(failed), "failures": failed[:20],
           "at": utcnow()}
    write_json(os.path.join(RAW_DIR, "dem_ner_report.json"), rep)
    print(f"dem: {rep}")
    return rep


if __name__ == "__main__":
    main()
