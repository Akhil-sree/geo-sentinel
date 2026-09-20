"""Route optimization endpoints — A* routing for evacuation/response."""

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.database import get_db
from app.models_db import RoadSegment, Zone
from app.services.route_optimizer import find_all_routes_from, find_safest_route

router = APIRouter(tags=["routes"])


class RouteRecalculateRequest(BaseModel):
    source: str
    target: str
    mode: str = "response"
    t: int = 96


@router.get("/routes/optimize")
def optimize_route(
    source: str = Query(..., description="Source zone ID"),
    target: str = Query(..., description="Target zone ID"),
    mode: str = Query("response", description="response or evacuation"),
    t: int = Query(96, ge=24, le=168),
    db: Session = Depends(get_db),
):
    """Find the lower-exposure route between two zones (A*, risk-weighted
    edges). Not a "safe" route — see cost_function and baseline comparison."""
    if mode not in ("response", "evacuation"):
        raise HTTPException(status_code=422,
                            detail="mode must be 'response' or 'evacuation'")
    route = find_safest_route(db, source, target, t, mode)
    if route is None:
        raise HTTPException(status_code=404,
                            detail=f"Unknown zone: {source} or {target}")
    return route


@router.get("/routes/all-from")
def all_routes_from(
    source: str = Query(..., description="Source zone ID"),
    mode: str = Query("response", description="response or evacuation"),
    t: int = Query(96, ge=24, le=168),
    db: Session = Depends(get_db),
):
    """Find safest routes from a zone to all reachable zones."""
    routes = find_all_routes_from(db, source, t, mode)
    zones = {z.id: z for z in db.query(Zone).all()}
    source_zone = zones.get(source)
    if source_zone is None:
        raise HTTPException(status_code=404, detail=f"Unknown zone: {source}")
    return {
        "source": source,
        "source_name": source_zone.name,
        "mode": mode,
        "routes": routes,
        "total": len(routes),
    }


@router.post("/routes/recalculate")
def recalculate_route(req: RouteRecalculateRequest, db: Session = Depends(get_db)):
    """Recalculate route — triggers fresh graph build from current road status."""
    if req.mode not in ("response", "evacuation"):
        raise HTTPException(status_code=422,
                            detail="mode must be 'response' or 'evacuation'")
    route = find_safest_route(db, req.source, req.target, req.t, req.mode)
    if route is None:
        raise HTTPException(status_code=404,
                            detail=f"Unknown zone: {req.source} or {req.target}")
    return route


@router.get("/routes/network")
def route_network(db: Session = Depends(get_db)):
    """Return the full road network graph for frontend rendering."""
    segments = db.query(RoadSegment).all()
    zones = {z.id: z for z in db.query(Zone).all()}

    nodes = [
        {"id": zid, "name": z.name, "lat": z.latitude, "lng": z.longitude, "population": z.population}
        for zid, z in zones.items()
    ]
    edges = [
        {
            "id": seg.id, "name": seg.name,
            "from_zone": seg.from_zone, "to_zone": seg.to_zone,
            "length_km": seg.length_km, "status": seg.status,
            "blockage_reason": seg.blockage_reason, "road_type": seg.road_type,
            "latitude": seg.latitude, "longitude": seg.longitude,
        }
        for seg in segments
    ]
    return {"nodes": nodes, "edges": edges, "total_nodes": len(nodes), "total_edges": len(edges)}


@router.get("/zones/list")
def list_zones_for_routing(db: Session = Depends(get_db)):
    """List all zones for route selection dropdowns."""
    zones = db.query(Zone).all()
    return {
        "zones": [
            {"id": z.id, "name": z.name, "district": z.district, "lat": z.latitude, "lng": z.longitude}
            for z in zones
        ]
    }
