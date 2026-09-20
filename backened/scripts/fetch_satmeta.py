"""Real satellite metadata acquisition (Phase 13): ASF Vertex discovery.

Per seed event: Sentinel-1 scenes intersecting the zone centroid within
±15 days. Stores raw responses (data/raw/sat_{zid}_{date}.json) + SatScene
rows (granule, time, beam, orbit, URL, md5).

METADATA ONLY: no imagery downloaded/processed; nothing enters risk.
Status stays SATELLITE_METADATA (observed catalog records) — NOT
SATELLITE_LIVE (no acquisition pipeline). Run: python scripts/fetch_satmeta.py
"""
import datetime as dt
import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from app.seed import ZONES, EVENTS  # noqa: E402

RAW = os.path.join(os.path.dirname(__file__), "..", "data", "raw")
API = "https://api.daac.asf.alaska.edu/services/search/param"


def fetch():
    import httpx
    os.makedirs(RAW, exist_ok=True)
    zmap = {z["id"]: z for z in ZONES}
    seen = set()
    for zid, d, _t in EVENTS:
        fn = os.path.join(RAW, f"sat_{zid}_{d.replace('-', '')}.json")
        if os.path.exists(fn):
            print("cached", fn)
            continue
        ev = dt.datetime.fromisoformat(d)
        z = zmap[zid]
        r = httpx.get(API, params={
            "platform": "SENTINEL-1",
            "intersectsWith": f"POINT({z['lng']} {z['lat']})",
            "start": (ev - dt.timedelta(days=15)).strftime("%Y-%m-%dT00:00:00Z"),
            "end": (ev + dt.timedelta(days=15)).strftime("%Y-%m-%dT00:00:00Z"),
            "output": "JSON"}, timeout=60)
        r.raise_for_status()
        j = r.json()
        scenes = [s[0] if isinstance(s, list) else s for s in j]
        keep = [{"granule": s.get("granuleName"),
                 "startTime": s.get("startTime"),
                 "beamMode": s.get("beamMode"),
                 "flightDirection": s.get("flightDirection"),
                 "polarization": s.get("polarization"),
                 "downloadUrl": s.get("downloadUrl"),
                 "md5sum": s.get("md5sum")} for s in scenes]
        json.dump({"zone_id": zid, "event_date": d, "n_scenes": len(keep),
                   "retrieved_at": dt.datetime.now(dt.timezone.utc).isoformat(),
                   "scenes": keep}, open(fn, "w"), indent=1)
        print("fetched", fn, len(keep), "scenes")


def store():
    import glob as _glob
    from dateutil.parser import isoparse as _parse
    from app.database import SessionLocal
    from app.models_db import SatScene
    db = SessionLocal()
    try:
        n = 0
        for fn in sorted(_glob.glob(os.path.join(RAW, "sat_*.json"))):
            p = json.load(open(fn))
            for s in p["scenes"]:
                if not s.get("granule"):
                    continue
                if db.query(SatScene).filter(
                        SatScene.granule == s["granule"]).first():
                    continue
                try:
                    st = _parse(s["startTime"]) if s.get("startTime") else None
                except Exception:
                    st = None
                db.add(SatScene(zone_id=p["zone_id"], granule=s["granule"],
                                start_time=st, beam_mode=s.get("beamMode", "IW"),
                                flight_direction=s.get("flightDirection"),
                                polarization=s.get("polarization"),
                                download_url=s.get("downloadUrl"),
                                md5=s.get("md5sum")))
                n += 1
        db.commit()
        print(f"stored {n} new scenes")
    finally:
        db.close()


if __name__ == "__main__":
    fetch()
    store()
