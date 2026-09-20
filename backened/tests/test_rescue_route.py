"""Rescue route contract + geometry regression tests (§26).

Proves: real road geometry (never straight lines), no duplicates/reversals,
blocked-road exclusion, honest unavailable responses, derived ETA.
"""
import math

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)

ORIGIN = {"origin_lat": 25.30, "origin_lng": 91.58}  # Z2 Mawsynram
DEST = {"destination_lat": 25.62, "destination_lng": 91.90}  # Z3 Shillong


def _post(body):
    r = client.post("/api/rescue/route", json=body)
    assert r.status_code == 200, r.text
    return r.json()


def _haversine_m(lat1, lon1, lat2, lon2):
    R = 6371000.0
    dlat, dlon = math.radians(lat2 - lat1), math.radians(lon2 - lon1)
    a = math.sin(dlat / 2) ** 2 + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon / 2) ** 2
    return R * 2 * math.asin(math.sqrt(a))


def test_post_explicit_contract_keys():
    d = _post({**ORIGIN, **DEST})
    assert d["route_available"] is True
    for key in ("origin", "destination", "algorithm", "geometry", "distance_km",
                "eta_min", "eta_basis", "segments", "blocked_avoided",
                "road_count", "exposure", "explanation", "demo_labels"):
        assert key in d, f"missing key {key}"
    assert d["origin"] == {"lat": 25.30, "lng": 91.58}
    assert d["destination"] == {"lat": 25.62, "lng": 91.90}
    assert d["algorithm"] == "A* (distance-optimal)"
    assert d["exposure"]["weighted"] is False  # honest: distance-optimal only


def test_geometry_is_real_road_path():
    d = _post({**ORIGIN, **DEST})
    coords = d["geometry"]["coordinates"]
    assert d["geometry"]["type"] == "LineString"
    assert len(coords) > 2, "must not be a 2-point straight line"
    # begins near origin, ends near destination (graph snap tolerance 3km)
    assert _haversine_m(25.30, 91.58, coords[0][1], coords[0][0]) < 3000
    assert _haversine_m(25.62, 91.90, coords[-1][1], coords[-1][0]) < 3000
    # no consecutive duplicates
    for a, b in zip(coords, coords[1:]):
        assert a != b
    # no immediate full reversals (A->B->A)
    pts = [tuple(c) for c in coords]
    for a, b, c_ in zip(pts, pts[1:], pts[2:]):
        assert not (a == c_ and a != b), f"reversal at {b}"
    # distance derived from segments, ETA derived from distance
    seg_sum = sum(s["length_m"] for s in d["segments"])
    assert abs(d["distance_km"] * 1000 - seg_sum) / max(seg_sum, 1) < 0.05
    assert d["eta_min"] == round(d["distance_km"] / 40.0 * 60)
    assert d["road_count"] == len(d["segments"]) > 0


def test_blocked_roads_excluded():
    blocked = set(client.get("/api/rescue/blocked-roads").json()["blocked_road_ids"])
    assert len(blocked) == 3
    d = _post({**ORIGIN, **DEST})
    used = {s["road_id"] for s in d["segments"]}
    assert not (used & blocked), f"blocked road routed: {used & blocked}"
    for s in d["segments"]:
        assert s["status"] == "OPEN"


def test_nearest_safe_zone_mode():
    d = _post(dict(ORIGIN))
    assert d["route_available"] is True
    assert d["destination"]["id"].startswith("sz-")
    assert d["destination"]["name"]
    assert len(d["geometry"]["coordinates"]) > 2


def test_unavailable_route_has_no_geometry():
    d = _post({"origin_lat": 25.51, "origin_lng": 90.20})  # Z5 Tura fragment
    assert d["route_available"] is False
    assert d["geometry"]["coordinates"] == []
    assert d["distance_km"] == 0
    assert d["eta_min"] == 0
    assert d["road_count"] == 0


def test_get_route_parity():
    r = client.get("/api/rescue/route", params={
        "danger_lat": 25.30, "danger_lng": 91.58,
        "safe_lat": 25.62, "safe_lng": 91.90})
    assert r.status_code == 200
    d = r.json()
    assert d["route_available"] is True
    assert d["distance_km"] > 0
    assert len(d["geometry"]["coordinates"]) > 2
    assert d["algorithm"] == "A* (distance-optimal)"


def test_snap_distances_reported():
    d = _post({**ORIGIN, **DEST})
    assert isinstance(d["origin_snap_m"], (int, float))
    assert isinstance(d["destination_snap_m"], (int, float))
    assert d["origin_snap_m"] >= 0 and d["destination_snap_m"] >= 0


def test_route_geometry_alias_matches_geometry():
    """Map contract: route_geometry ([lat,lng]) is the geometry
    ([lng,lat]) reordered — same points, never a straight line."""
    d = _post({**ORIGIN, **DEST})
    assert d["status"] == "ok"
    geom = d["geometry"]["coordinates"]
    rg = d["route_geometry"]
    assert len(rg) == len(geom) > 2
    for (lng, lat), (rlat, rlng) in zip(geom, rg):
        assert (rlat, rlng) == (lat, lng)
    assert d["roads_used"] == d["segments"]
    assert d["roads_avoided"] == d["blocked_avoided"]


def test_auto_mode_returns_ranked_options():
    d = _post(dict(ORIGIN))
    assert d["route_available"] is True
    assert d["destination"]["type"] == "safe_zone"
    assert d["destination"]["is_demo"] is True
    assert d["origin"]["type"] == "risk_zone"
    opts = d["options"]
    assert len(opts) >= 1
    dists = [o["distance_km"] for o in opts]
    assert dists == sorted(dists), "options must be ranked nearest-first"
    assert all(o["distance_km"] >= d["distance_km"] for o in opts)
    for o in opts:
        assert o["id"].startswith("sz-") and o["name"]


def test_eight_demo_safe_zones_labeled():
    zones = client.get("/api/rescue/safe-zones").json()["safe_zones"]
    assert len(zones) == 8
    ids = {z["id"] for z in zones}
    assert {"sz-6", "sz-7", "sz-8"} <= ids
    for z in zones:
        assert z["is_demo"] is True
        assert z["demo_label"] == "DEMO SAFE ZONE"


def test_new_safe_zones_reachable():
    # Sohra risk point reaches the new nearby demo safe zones by road.
    for zone_id, lat, lng in (("sz-6", 25.27, 91.73), ("sz-7", 25.32, 91.60)):
        d = _post({"origin_lat": 25.26, "origin_lng": 91.73,
                   "destination_lat": lat, "destination_lng": lng})
        assert d["route_available"] is True, zone_id
        assert len(d["route_geometry"]) > 2, zone_id
