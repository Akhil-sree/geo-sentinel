"""Historical rainfall per dated event (SIH §7).

Open-Meteo archive API (public, keyless): hourly precipitation +
soil_moisture_3_9cm (ERA5-Land MODELED — tagged, never sensor data) for a
30d pre-event window + event day, aligned to event lat/lon. Raw payloads
cached per event (resume-safe); per-event failures → rainfall_failed_events
log, never a pipeline crash. Only data at/before event end is stored
(pre-event clip enforced at build; raw cache keeps the fetched window for
audit, features clip to ≤T).
"""
import json
import os
import sys
import time

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "data"))

from ner_common import RAW_DIR, write_json, utcnow, OFFICIAL_SOURCES

ARCHIVE = "https://archive-api.open-meteo.com/v1/archive"
FAILED_LOG = os.path.join(RAW_DIR, "rainfall_failed_events.csv")
CACHE_TPL = os.path.join(RAW_DIR, "ner_rain_{eid}.json")


def _window(lat: float, lon: float, end: str, days: int = 31) -> dict:
    import urllib.request
    import urllib.parse
    from datetime import datetime
    end_d = datetime.fromisoformat(end).date()
    start_d = (end_d - __import__("datetime").timedelta(days=days)).isoformat()
    q = urllib.parse.urlencode({
        "latitude": lat, "longitude": lon,
        "start_date": start_d, "end_date": end_d.isoformat(),
        "hourly": "precipitation,soil_moisture_3_9cm", "timezone": "UTC"})
    req = urllib.request.Request(f"{ARCHIVE}?{q}",
                                 headers={"User-Agent": "GEO-SENTINEL-ner-pipeline/1.0"})
    with urllib.request.urlopen(req, timeout=40) as r:
        return json.loads(r.read().decode())


def fetch_event(eid: int, lat: float, lon: float, end: str,
                force: bool = False) -> dict:
    dest = CACHE_TPL.format(eid=eid)
    if os.path.exists(dest) and not force:
        with open(dest, encoding="utf-8") as f:
            return {"status": "CACHED", "file": dest,
                    "hours": len(json.load(f)["hourly"].get("time", []))}
    payload = _window(lat, lon, end)
    hours = payload.get("hourly", {}).get("time", [])
    if not hours:
        raise RuntimeError("archive returned no hourly rows")
    payload["_meta"] = {"event_id": eid, "lat": lat, "lon": lon, "event_end": end,
                        "provider": "openmeteo-archive",
                        "source_url": OFFICIAL_SOURCES["openmeteo_archive"],
                        "rainfall_quality": "REAL (ERA5 observed blend)",
                        "soil_quality": "MODELED (ERA5-Land reanalysis — not sensor data)",
                        "retrieved_at": utcnow()}
    write_json(dest, payload)
    return {"status": "DOWNLOADED", "file": dest, "hours": len(hours)}


def main() -> dict:
    from app.database import SessionLocal
    from app.models_db import NerInventory, TrainingSample
    force = "--force" in sys.argv
    only = [a.split("=", 1)[1] for a in sys.argv if a.startswith("--only=")]
    db = SessionLocal()
    try:
        q = db.query(NerInventory).filter(NerInventory.record_kind == "TEMPORAL")
        if only:
            q = q.filter(NerInventory.id.in_([int(x) for x in only[0].split(",")]))
        events = q.all()
        ctrls = db.query(TrainingSample).filter(
            TrainingSample.label == "NO_RECORDED_LANDSLIDE").all()
    finally:
        db.close()
    ok, failed, cached = 0, [], 0
    jobs = [(e.id, e.latitude, e.longitude, e.event_date.date().isoformat())
            for e in events]
    jobs += [(f"C{c.id}", c.latitude, c.longitude, c.event_date.date().isoformat())
             for c in ctrls]
    for eid, lat, lon, end in jobs:
        try:
            r = fetch_event(eid, lat, lon, end, force=force)
            ok += 1
            cached += r["status"] == "CACHED"
            time.sleep(1)  # batched politely, not N×burst
        except Exception as ex:  # noqa: BLE001 — one failure never kills the build
            failed.append({"event_id": str(eid), "error": f"{type(ex).__name__}: {ex}"[:150]})
    with open(FAILED_LOG, "w", encoding="utf-8") as f:
        f.write("event_id,error\n")
        for x in failed:
            f.write(f"{x['event_id']},{x['error']}\n")
    rep = {"events": len(events), "controls": len(ctrls), "ok": ok, "cached": cached,
           "failed": len(failed), "failed_log": FAILED_LOG, "at": utcnow()}
    print(f"rainfall: {rep}")
    return rep


if __name__ == "__main__":
    main()
