"""Rescue route endpoint — real road-network A* routing from road_graph service."""

import logging as _log

from fastapi import APIRouter, Query
from pydantic import BaseModel, Field

from app.services.road_graph import find_route, get_blocked_road_ids

router = APIRouter(tags=["rescue"])

# Documented emergency-road speed used for ETA derivation (distance / speed).
EMERGENCY_SPEED_KMH = 40.0

ALGORITHM = "A* (distance-optimal)"


class RescueRouteRequest(BaseModel):
    origin_lat: float = Field(ge=-90, le=90)
    origin_lng: float = Field(ge=-180, le=180)
    destination_lat: float | None = Field(default=None, ge=-90, le=90)
    destination_lng: float | None = Field(default=None, ge=-180, le=180)


SAFE_ZONES = [
    {
        "id": "sz-1",
        "name": "Shillong Relief Camp",
        "lat": 25.62,
        "lng": 91.88,
        "type": "stable_area",
        "district": "East Khasi Hills",
        "description": "Primary relief camp with medical and shelter facilities",
        "is_demo": True,
        "demo_label": "DEMO SAFE ZONE",
    },
    {
        "id": "sz-2",
        "name": "Tura Valley Safe Area",
        "lat": 25.52,
        "lng": 90.22,
        "type": "stable_area",
        "district": "West Garo Hills",
        "description": "Open valley area with low landslide risk",
        "is_demo": True,
        "demo_label": "DEMO SAFE ZONE",
    },
    {
        "id": "sz-3",
        "name": "Williamnagar Open Ground",
        "lat": 25.59,
        "lng": 90.48,
        "type": "stable_area",
        "district": "East Garo Hills",
        "description": "Open ground suitable for emergency staging",
        "is_demo": True,
        "demo_label": "DEMO SAFE ZONE",
    },
    {
        "id": "sz-4",
        "name": "Jowai Community Center",
        "lat": 25.44,
        "lng": 92.22,
        "type": "stable_area",
        "district": "Jaintia Hills",
        "description": "Reinforced community center for emergency shelter",
        "is_demo": True,
        "demo_label": "DEMO SAFE ZONE",
    },
    {
        "id": "sz-5",
        "name": "Nongstoin Hillside Clearing",
        "lat": 25.53,
        "lng": 91.25,
        "type": "stable_area",
        "district": "West Khasi Hills",
        "description": "Hillside clearing with safe drainage patterns",
        "is_demo": True,
        "demo_label": "DEMO SAFE ZONE",
    },
    {
        "id": "sz-6",
        "name": "Sohra Evacuation Centre",
        "lat": 25.27,
        "lng": 91.73,
        "type": "stable_area",
        "district": "East Khasi Hills",
        "description": "Demonstration evacuation point near Sohra town",
        "is_demo": True,
        "demo_label": "DEMO SAFE ZONE",
    },
    {
        "id": "sz-7",
        "name": "Mawsynram Relief Centre",
        "lat": 25.32,
        "lng": 91.60,
        "type": "stable_area",
        "district": "East Khasi Hills",
        "description": "Demonstration relief point near Mawsynram town",
        "is_demo": True,
        "demo_label": "DEMO SAFE ZONE",
    },
    {
        "id": "sz-8",
        "name": "Baghmara Emergency Shelter",
        "lat": 25.21,
        "lng": 90.64,
        "type": "stable_area",
        "district": "South Garo Hills",
        "description": "Demonstration emergency shelter near Baghmara town",
        "is_demo": True,
        "demo_label": "DEMO SAFE ZONE",
    },
]


def _route_response(result, origin=None, destination=None, options=None):
    try:
        from app.observability import record_route
        record_route(bool(result.get("route_available")))
    except Exception as e:
        _log.getLogger("geo-sentinel").debug("Route recording failed: %s", e)
    distance_km = round(result["distance_m"] / 1000.0, 2) if result["route_available"] else 0
    eta_min = round(distance_km / EMERGENCY_SPEED_KMH * 60) if result["route_available"] else 0

    explanation = {}
    if result["route_available"]:
        why = [f"{ALGORITHM} road-network search over OSM geometry"]
        why.append(f"Route found across {result['road_count']} road segment(s)")
        tradeoffs = []
        if result["blocked_avoided"]:
            avoided_names = [b["name"] or f"Road {b['road_id']}" for b in result["blocked_avoided"]]
            why.append(
                f"Routed around {len(result['blocked_avoided'])} blocked road(s): "
                + ", ".join(avoided_names)
            )
            tradeoffs.append("Blocked roads avoided — rerouted via open roads")
        else:
            why.append("No blocked segments on this corridor")
        explanation = {"why": why, "tradeoffs": tradeoffs}
    else:
        explanation = {
            "why": [result.get("reason", "No route found")],
            "tradeoffs": ["Consider alternative transport or road clearing"],
        }

    resp = {
        "status": "ok",
        "route_available": result["route_available"],
        "origin": origin,
        "destination": destination,
        "algorithm": ALGORITHM if result["route_available"] else None,
        "geometry": {
            "type": "LineString",
            "coordinates": result["geometry"],
        },
        # Alias for map clients: the exact backend route path as
        # [[lat, lng], ...]. Same list object as geometry.coordinates,
        # reordered for Leaflet — never a straight line or fallback.
        "route_geometry": [[c[1], c[0]] for c in result["geometry"]],
        "distance_km": distance_km,
        "eta_min": eta_min,
        "eta_basis": (
            f"distance / {EMERGENCY_SPEED_KMH:g} km/h emergency-road speed (planning assumption)"
            if result["route_available"] else None
        ),
        "segments": result["segments"],
        "roads_used": result["segments"],
        "blocked_avoided": result["blocked_avoided"],
        "roads_avoided": result["blocked_avoided"],
        "road_count": result["road_count"],
        "exposure": {
            "weighted": False,
            "note": (
                "Distance-optimal route; hazard-exposure weighting is not applied "
                "in this demo. Uncalibrated advisory only — not a probability."
            ),
        },
        "origin_snap_m": result.get("origin_snap_m"),
        "destination_snap_m": result.get("destination_snap_m"),
        "explanation": explanation,
        "demo_labels": _demo_labels(result),
    }
    if options is not None:
        resp["options"] = options
    return resp


@router.get("/rescue/route")
def get_rescue_route(
    danger_lat: float = Query(..., ge=-90, le=90, description="Latitude of danger/origin point"),
    danger_lng: float = Query(..., ge=-180, le=180, description="Longitude of danger/origin point"),
    safe_lat: float = Query(..., ge=-90, le=90, description="Latitude of safe destination"),
    safe_lng: float = Query(..., ge=-180, le=180, description="Longitude of safe destination"),
):
    """Find a rescue route from a danger point to a safe point using real road geometry.

    Returns route with actual road coordinates (never straight lines),
    distance, segment details, and any blocked roads avoided.
    """
    result = find_route(danger_lat, danger_lng, safe_lat, safe_lng)
    return _route_response(
        result,
        origin={"lat": danger_lat, "lng": danger_lng},
        destination={"lat": safe_lat, "lng": safe_lng},
    )


@router.post("/rescue/route")
def post_rescue_route(body: RescueRouteRequest):
    """Find a rescue route. Without a destination, routes to the nearest
    reachable demo safe zone (shortest available road route)."""
    if body.destination_lat is not None and body.destination_lng is not None:
        result = find_route(body.origin_lat, body.origin_lng, body.destination_lat, body.destination_lng)
        return _route_response(
            result,
            origin={"lat": body.origin_lat, "lng": body.origin_lng},
            destination={"lat": body.destination_lat, "lng": body.destination_lng},
        )

    best = None
    best_zone = None
    ranked = []
    for zone in SAFE_ZONES:
        result = find_route(body.origin_lat, body.origin_lng, zone["lat"], zone["lng"])
        if result["route_available"]:
            ranked.append((result["distance_m"], result, zone))
    ranked.sort(key=lambda t: t[0])
    if ranked:
        best = ranked[0][1]
        z = ranked[0][2]
        best_zone = {"type": "safe_zone", "id": z["id"], "name": z["name"],
                     "lat": z["lat"], "lng": z["lng"], "is_demo": z["is_demo"]}
    if best is None:
        return _route_response(
            {
                "route_available": False,
                "reason": "No connected road path from this location to any safe zone in the mapped network",
                "geometry": [],
                "distance_m": 0,
                "segments": [],
                "blocked_avoided": [],
                "road_count": 0,
            },
            origin={"type": "risk_zone", "lat": body.origin_lat, "lng": body.origin_lng},
            destination=None,
        )
    options = [
        {"type": "safe_zone", "id": z["id"], "name": z["name"], "lat": z["lat"], "lng": z["lng"],
         "is_demo": z["is_demo"], "distance_km": round(r["distance_m"] / 1000.0, 2),
         "eta_min": round(r["distance_m"] / 1000.0 / EMERGENCY_SPEED_KMH * 60)}
        for _, r, z in ranked[1:4]
    ]
    return _route_response(
        best,
        origin={"type": "risk_zone", "lat": body.origin_lat, "lng": body.origin_lng},
        destination=best_zone,
        options=options,
    )


@router.get("/rescue/blocked-roads")
def get_rescue_blocked_roads():
    """Return blocked OSM road ids for map highlighting."""
    ids = get_blocked_road_ids()
    return {
        "blocked_road_ids": ids,
        "total": len(ids),
        "reason": "landslide",
    }


@router.get("/rescue/safe-zones")
def get_safe_zones():
    """Return safe zones for the Meghalaya region."""
    return {"safe_zones": SAFE_ZONES}


def _demo_labels(result):
    """Generate status labels for the response."""
    labels = ["Road network sourced from OSM data"]
    if result["blocked_avoided"]:
        for b in result["blocked_avoided"]:
            name = b["name"] or f"Road {b['road_id']}"
            labels.append(
                f"BLOCKED: {name} — {b['reason']}"
            )
    return labels
