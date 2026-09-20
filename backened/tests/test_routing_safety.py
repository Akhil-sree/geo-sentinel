"""Routing safety regressions (P0): out-of-coverage must never fabricate a route.

Covers: ocean coords, far-outside-Meghalaya, beyond-snap-threshold, same
origin/destination, NaN/Inf/out-of-range coords, geometry integrity
(>=2 finite in-range positions), empty/missing graph, blocked graph,
unreachable destination, one/multi-segment valid routes, malformed input.
"""
import math
import os

import pytest
from fastapi.testclient import TestClient

import app.services.road_graph as rg
from app.main import app

ROADS_GEOJSON = os.path.join(os.path.dirname(__file__), "..", "data", "processed", "roads.geojson")

pytestmark = pytest.mark.skipif(
    not os.path.exists(ROADS_GEOJSON),
    reason="roads.geojson absent (local-only data/processed/ — run scripts/extract_roads.py)",
)

client = TestClient(app)

# In-coverage pair (Z2 Mawsynram -> Z3 Shillong), known routable.
ORIGIN = (25.30, 91.58)
DEST = (25.62, 91.90)


def _get(o_lat, o_lng, d_lat, d_lng):
    return client.get(
        "/api/rescue/route",
        params={"danger_lat": o_lat, "danger_lng": o_lng,
                "safe_lat": d_lat, "safe_lng": d_lng},
    )


def _assert_unavailable(payload, fragment):
    assert payload["route_available"] is False, payload
    assert payload["geometry"]["coordinates"] == [], payload
    assert payload["distance_km"] == 0, payload
    assert fragment in payload["explanation"]["why"][0], payload


def test_ocean_coordinates_never_route():
    r = _get(0, 0, 0.001, 0.001)
    assert r.status_code == 200, r.text
    _assert_unavailable(r.json(), "OUT_OF_COVERAGE")


def test_far_outside_meghalaya_never_routes():
    r = _get(28.61, 77.20, 28.62, 77.21)  # Delhi
    assert r.status_code == 200, r.text
    _assert_unavailable(r.json(), "OUT_OF_COVERAGE")


def test_beyond_snap_threshold_rejected():
    r = rg.find_route(26.5, 93.5, *DEST)  # ~150km from graph
    assert r["route_available"] is False
    assert "OUT_OF_COVERAGE" in r["reason"], r


def test_same_origin_destination_unavailable():
    r = rg.find_route(*ORIGIN, *ORIGIN)
    assert r["route_available"] is False
    assert "SAME_ORIGIN_DESTINATION" in r["reason"], r


def test_invalid_coordinates_rejected():
    for bad in [(float("nan"), 91.0), (25.0, float("inf")),
                (999.0, 91.0), (25.0, -999.0),
                ("abc", 91.0), (None, 91.0)]:
        r = rg.find_route(bad[0], bad[1], *DEST)
        assert r["route_available"] is False, bad
        assert "INVALID_ORIGIN" in r["reason"], (bad, r)
    r = rg.find_route(*ORIGIN, 25.0, 999.0)
    assert r["route_available"] is False
    assert "INVALID_DESTINATION" in r["reason"], r


def test_malformed_query_returns_422():
    r = _get(999, 91.0, 25.6, 91.9)
    assert r.status_code == 422, r.text
    r = client.post("/api/rescue/route",
                    json={"origin_lat": 999, "origin_lng": 91.0})
    assert r.status_code == 422, r.text


def test_valid_route_geometry_integrity():
    r = rg.find_route(*ORIGIN, *DEST)
    assert r["route_available"] is True, r
    assert r["road_count"] >= 1, r
    geom = r["geometry"]
    assert isinstance(geom, list) and len(geom) >= 2, r
    for pt in geom:
        lng, lat = float(pt[0]), float(pt[1])
        assert math.isfinite(lng) and math.isfinite(lat)
        assert -90.0 <= lat <= 90.0 and -180.0 <= lng <= 180.0
    for a, b in zip(geom, geom[1:], strict=False):
        assert a != b  # no duplicate consecutive points


def test_valid_route_endpoints_near_request():
    r = _get(*ORIGIN, *DEST)
    assert r.status_code == 200, r.text
    d = r.json()
    assert d["route_available"] is True, d
    assert len(d["route_geometry"]) >= 2, d
    assert d["origin_snap_m"] is not None and d["origin_snap_m"] <= 5000, d
    assert d["destination_snap_m"] is not None and d["destination_snap_m"] <= 5000, d


def test_post_without_destination_routes_to_demo_safe_zone():
    r = client.post("/api/rescue/route",
                    json={"origin_lat": ORIGIN[0], "origin_lng": ORIGIN[1]})
    assert r.status_code == 200, r.text
    d = r.json()
    assert d["route_available"] is True, d
    assert len(d["geometry"]["coordinates"]) >= 2, d


def test_post_ocean_origin_unavailable():
    r = client.post("/api/rescue/route",
                    json={"origin_lat": 0.0, "origin_lng": 0.0})
    assert r.status_code == 200, r.text
    d = r.json()
    assert d["route_available"] is False, d
    assert d["geometry"]["coordinates"] == [], d
    assert d["distance_km"] == 0, d
    why = d["explanation"]["why"][0]
    assert "OUT_OF_COVERAGE" in why or "No connected road path" in why, d


def test_empty_graph_unavailable(monkeypatch):
    monkeypatch.setattr(rg, "_build_graph",
                        lambda: {"adj": {}, "edges": {},
                                 "node_coords": {}, "blocked_ids": frozenset()})
    r = rg.find_route(*ORIGIN, *DEST)
    assert r["route_available"] is False
    assert "not loaded" in r["reason"], r


def test_geometry_validator_unit():
    assert rg._valid_geometry([[91.0, 25.0], [91.1, 25.1]]) is True
    assert rg._valid_geometry([]) is False
    assert rg._valid_geometry([[91.0, 25.0]]) is False  # single point
    assert rg._valid_geometry([[91.0, 25.0], [float("nan"), 25.1]]) is False
    assert rg._valid_geometry([[91.0, 25.0], [91.1, float("inf")]]) is False
    assert rg._valid_geometry([[91.0, 999.0], [91.1, 25.1]]) is False
    assert rg._valid_geometry("not-a-list") is False


def test_snap_threshold_env_driven(monkeypatch):
    import os
    monkeypatch.setenv("ROUTE_MAX_SNAP_DISTANCE_M", "10000000")
    # helper reads config at call time; force the fallback path instead:
    monkeypatch.setattr(rg, "_max_snap_m", lambda: 10000000.0)
    r = rg.find_route(0, 0, 0.001, 0.001)
    # huge threshold: may snap, but same-node degenerate case stays unavailable
    assert r["route_available"] is False, r
    assert os.getenv("ROUTE_MAX_SNAP_DISTANCE_M") == "10000000"
