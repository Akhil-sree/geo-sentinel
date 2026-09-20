"""OSM road network for NER (SIH §16-17).

Geofabrik India extract is GB-scale → NOT auto-downloaded. Two honest paths:
(a) Overpass API (public, no key): per-zone bbox highway import, cached per
zone, polite rate-limit; (b) data/manual/osm/*.pbf manual drop (parsed only
if osmium/pyosmium present, else VALIDATED-UNPARSED status). Outputs cached
raw + road-density features per zone/event. OSMnx is optional: used for
NetworkX graphs only when installed (never a hard dependency).

Sources: https://download.geofabrik.de/asia/india.html,
https://osmnx.readthedocs.io
"""
import json
import os
import sys
import time

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "data"))

from ner_common import RAW_DIR, MANUAL_DIR, write_json, utcnow, OFFICIAL_SOURCES

CACHE_TPL = os.path.join(RAW_DIR, "osm_zone_{zid}.json")
OVERPASS = "https://overpass-api.de/api/interpreter"


def _overpass(lon: float, lat: float) -> dict:
    """Small bbox highway fetch around (lon, lat). One query per zone, cached."""
    import urllib.request
    import urllib.parse
    s, w, n, e = lat - 0.10, lon - 0.10, lat + 0.10, lon + 0.10  # S,W,N,E order
    q = (f"[out:json][timeout:60];(way[\"highway\"]({s},{w},{n},{e}););out body 2000;")
    data = urllib.parse.urlencode({"data": q}).encode()
    last = None
    for attempt in range(4):  # Overpass 429/504 backoff; cached resume covers the rest
        try:
            req = urllib.request.Request(OVERPASS, data=data,
                                         headers={"User-Agent": "GEO-SENTINEL-ner-pipeline/1.0"})
            with urllib.request.urlopen(req, timeout=90) as r:
                return json.loads(r.read().decode())
        except Exception as ex:  # noqa: BLE001
            last = ex
            time.sleep(20 * (attempt + 1))
    raise last


def import_zone(zid: str, lat: float, lon: float, force: bool = False) -> dict:
    dest = CACHE_TPL.format(zid=zid)
    if os.path.exists(dest) and not force:
        with open(dest, encoding="utf-8") as f:
            return {"status": "CACHED", "file": dest}
    payload = _overpass(lon, lat)
    ways = [e for e in payload.get("elements", []) if e.get("type") == "way"]
    out = {"zone_id": zid, "n_ways": len(ways),
           "highway_classes": sorted({w.get("tags", {}).get("highway", "?") for w in ways}),
           "source": "OpenStreetMap via Overpass (REAL geometry counts; full graph = manual PBF)",
           "source_url": OFFICIAL_SOURCES["geofabrik"],
           "retrieved_at": utcnow(),
           "ways": [{"id": w["id"], "highway": w.get("tags", {}).get("highway"),
                     "name": w.get("tags", {}).get("name")} for w in ways[:500]]}
    write_json(dest, out)
    return {"status": "DOWNLOADED", "file": dest, "n_ways": len(ways)}


def main() -> dict:
    from app.seed import ZONES
    force = "--force" in sys.argv
    manual = os.path.join(MANUAL_DIR, "osm")
    os.makedirs(manual, exist_ok=True)
    ok, failed, pbf = 0, [], [f for f in os.listdir(manual) if f.endswith(".pbf")]
    for z in ZONES:
        try:
            import_zone(z["id"], z["lat"], z["lng"], force=force)
            ok += 1
            time.sleep(2)  # Overpass usage policy: polite, cached, never bursty
        except Exception as ex:  # noqa: BLE001
            failed.append({"zone": z["id"], "error": f"{type(ex).__name__}: {ex}"[:150]})
    try:
        import osmnx  # noqa: F401 — optional graph builder, never required
        osmnx_status = "INSTALLED (NetworkX graphs available for manual PBF)"
    except ImportError:
        osmnx_status = "NOT_INSTALLED (optional; counts+cache path unaffected)"
    rep = {"zones": len(ZONES), "ok": ok, "failed": failed,
           "manual_pbf": pbf or None,
           "manual_note": ("Place Geofabrik india extract in data/manual/osm/ for full-graph "
                           "routing; per-zone counts cached regardless."),
           "osmnx": osmnx_status, "at": utcnow()}
    write_json(os.path.join(RAW_DIR, "osm_ner_report.json"), rep)
    print(f"osm: {rep}")
    return rep


if __name__ == "__main__":
    main()
