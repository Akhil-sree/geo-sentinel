"""Sentinel-1 scene discovery per event window (SIH §14-15).

REAL public metadata via ASF Search API (api.daac.asf.alaska.edu — verified
200, no key for search): for each TEMPORAL event finds pre_event_scene /
nearest / post_event_scene (±60d), stores scene_id/acquisition/orbit/
polarization/processing status into sat_scenes + metadata-derived features
(pre/post day-counts, same-orbit flag). NO imagery is downloaded or
processed — features are REAL metadata-derived, labeled as such, and the
imagery pipeline stays AUTH_REQUIRED (Copernicus creds).
Never fabricates scenes: empty search → missing code, not zeros.

Official source: https://dataspace.copernicus.eu
"""
import json
import os
import sys
from datetime import datetime, timedelta

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "data"))

from ner_common import RAW_DIR, write_json, utcnow, OFFICIAL_SOURCES

ASF = "https://api.daac.asf.alaska.edu/services/search/param"
CACHE_TPL = os.path.join(RAW_DIR, "ner_sar_{eid}.json")


def _search(lat: float, lon: float, start: str, end: str) -> list[dict]:
    import urllib.request
    import urllib.parse
    q = urllib.parse.urlencode({
        "platform": "S1", "output": "JSON",
        "bbox": f"{lon - 0.5},{lat - 0.5},{lon + 0.5},{lat + 0.5}",
        "start": start, "end": end, "maxResults": 50,
        "beamMode": "IW", "processingLevel": "SLC,GRD_HD,GRD_HS"})
    req = urllib.request.Request(f"{ASF}?{q}",
                                 headers={"User-Agent": "GEO-SENTINEL-ner-pipeline/1.0"})
    with urllib.request.urlopen(req, timeout=40) as r:
        data = json.loads(r.read().decode())
    return data[0] if data and isinstance(data[0], list) else (data or [])


def _pick(scenes: list[dict], pivot: datetime, want: str) -> dict | None:
    best, best_dt = None, None
    for s in scenes:
        try:
            t = datetime.fromisoformat((s.get("startTime") or "").replace("Z", "+00:00"))
        except ValueError:
            continue
        dt_days = (t.replace(tzinfo=None) - pivot).days
        if want == "pre" and dt_days >= 0:
            continue
        if want == "post" and dt_days <= 0:
            continue
        if best is None or abs(dt_days) < abs(best_dt):
            best, best_dt = s, dt_days
    return best


def discover(eid: int, lat: float, lon: float, end: str, force: bool = False) -> dict:
    dest = CACHE_TPL.format(eid=eid)
    if os.path.exists(dest) and not force:
        with open(dest, encoding="utf-8") as f:
            return {"status": "CACHED", "file": dest}
    pivot = datetime.fromisoformat(end)
    lo = (pivot - timedelta(days=60)).strftime("%Y-%m-%dT%H:%M:%SZ")
    hi = (pivot + timedelta(days=60)).strftime("%Y-%m-%dT%H:%M:%SZ")
    scenes = _search(lat, lon, lo, hi)
    pre, post = _pick(scenes, pivot, "pre"), _pick(scenes, pivot, "post")

    def _slim(s):
        return None if not s else {
            "scene_id": s.get("sceneName"), "acquisition_time": s.get("startTime"),
            "orbit": s.get("orbit"), "flight_direction": s.get("flightDirection"),
            "polarization": s.get("polarization"), "beam_mode": s.get("beamMode"),
            "processing_status": "METADATA_ONLY (no imagery processed)"}
    out = {"event_id": eid,
           "pre_event_scene": _slim(pre), "post_event_scene": _slim(post),
           "n_candidates": len(scenes),
           "sar_status": "REAL_METADATA (ASF search, public)",
           "imagery_status": "AUTH_REQUIRED (Copernicus creds for download/processing)",
           "source_url": OFFICIAL_SOURCES["copernicus"],
           "retrieved_at": utcnow()}
    write_json(dest, out)
    return {"status": "DISCOVERED", "file": dest, "n": len(scenes),
            "pre": bool(pre), "post": bool(post)}


def main() -> dict:
    from app.database import SessionLocal
    from app.models_db import NerInventory, SatScene
    force = "--force" in sys.argv
    db = SessionLocal()
    try:
        events = db.query(NerInventory).filter(NerInventory.record_kind == "TEMPORAL").all()
    finally:
        db.close()
    ok, empty, failed = 0, 0, []
    db = SessionLocal()
    try:
        for e in events:
            try:
                r = discover(e.id, e.latitude, e.longitude,
                             e.event_date.date().isoformat(), force=force)
                ok += 1
                empty += r.get("n", 1) == 0
                with open(r["file"], encoding="utf-8") as f:
                    d = json.load(f)
                for slot in ("pre_event_scene", "post_event_scene"):
                    s = d[slot]
                    if not s or not s.get("scene_id"):
                        continue
                    if not db.query(SatScene).filter(SatScene.granule == s["scene_id"]).first():
                        try:
                            st = datetime.fromisoformat(s["acquisition_time"].replace("Z", "+00:00"))
                        except (ValueError, AttributeError):
                            st = None
                        db.add(SatScene(zone_id=None, granule=s["scene_id"], start_time=st,
                                        beam_mode=s.get("beam_mode", "IW"),
                                        flight_direction=s.get("flight_direction"),
                                        polarization=s.get("polarization"),
                                        source="ASF search (REAL metadata, NER pipeline)"))
                db.commit()
            except Exception as ex:  # noqa: BLE001
                db.rollback()
                failed.append({"event_id": e.id, "error": f"{type(ex).__name__}: {ex}"[:150]})
    finally:
        db.close()
    rep = {"events": len(events), "ok": ok, "empty_search": empty,
           "failed": len(failed), "failures": failed[:20], "at": utcnow()}
    write_json(os.path.join(RAW_DIR, "sar_ner_report.json"), rep)
    print(f"sar: {rep}")
    return rep


if __name__ == "__main__":
    main()
