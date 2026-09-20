"""API error-contract regressions (P1): unknown zones -> 404, never 200 error-dicts.

Semantics enforced:
  200 = success (empty states like `state: empty` / [] stay 200 for VALID zones)
  404 = unknown zone / resource
  422 = schema validation failure
  503 = unavailable dependency (missing roads file, untrained model)
"""
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)

BAD = "ZZ_NO_SUCH_ZONE"

ZONE_ENDPOINTS = [
    "/api/risk/{z}/history",
    "/api/risk/{z}/rainfall",
    "/api/risk/{z}/soil-moisture",
    "/api/risk/{z}/explanation",
    "/api/risk/{z}/satellite",
    "/api/risk/{z}/rainfall-windows",
    "/api/risk/{z}/slope-state",
    "/api/risk/{z}/trajectory",
    "/api/risk/{z}/evidence",
    "/api/risk/{z}/cell-grid?mode=demo",
    "/api/risk/{z}/cell-grid/temporal?mode=demo",
    "/api/risk/{z}/forecast",
]


def test_unknown_zone_is_404_everywhere():
    for tpl in ZONE_ENDPOINTS:
        r = client.get(tpl.format(z=BAD))
        assert r.status_code == 404, (tpl, r.status_code, r.text[:200])
        assert "zone not found" in r.json()["detail"], (tpl, r.text[:200])


def test_valid_zone_keeps_success_shapes():
    assert client.get("/api/risk/Z1/history").status_code == 200
    r = client.get("/api/risk/Z1/rainfall")
    assert r.status_code == 200 and r.json()["state"] in ("ok", "empty")
    r = client.get("/api/risk/Z1/trajectory")
    assert r.status_code == 200
    assert client.get("/api/risk/Z1/evidence").status_code == 200
    assert client.get("/api/risk/Z1/slope-state").status_code == 200


def test_routes_unknown_zone_404():
    r = client.get("/api/routes/optimize",
                   params={"source": BAD, "target": "Z1"})
    assert r.status_code == 404, r.text
    r = client.get("/api/routes/all-from", params={"source": BAD})
    assert r.status_code == 404, r.text
    r = client.post("/api/routes/recalculate",
                    json={"source": BAD, "target": "Z1"})
    assert r.status_code == 404, r.text


def test_routes_valid_pair_still_200():
    r = client.get("/api/routes/optimize",
                   params={"source": "Z1", "target": "Z3"})
    assert r.status_code == 200, r.text


def test_invalid_query_is_422_not_200_error():
    r = client.get("/api/risk/gs_point", params={"lat": 999, "lon": 999})
    assert r.status_code == 422, r.text
    r = client.get("/api/rescue/route",
                   params={"danger_lat": 999, "danger_lng": 0,
                           "safe_lat": 0, "safe_lng": 0})
    assert r.status_code == 422, r.text
    r = client.get("/api/roads/nearest",
                   params={"lat": 999, "lng": 0})
    assert r.status_code == 422, r.text


def test_roads_endpoints_healthy_shapes():
    r = client.get("/api/roads/geojson")
    assert r.status_code == 200, r.text
    assert r.json()["type"] == "FeatureCollection"
    r = client.get("/api/roads/nearest",
                   params={"lat": 25.3, "lng": 91.7})
    assert r.status_code == 200, r.text
    assert "distance_m" in r.json(), r.text[:200]
