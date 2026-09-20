"""Road GIS endpoints — real OSM road geometry from PBF extraction."""
import json
import math
from pathlib import Path
from functools import lru_cache
from fastapi import APIRouter, HTTPException, Query
from typing import Optional

router = APIRouter(tags=["roads-gis"])

ROADS_GEOJSON_PATH = Path(__file__).resolve().parent.parent.parent / "data" / "processed" / "roads.geojson"


@lru_cache(maxsize=1)
def _load_roads():
    if not ROADS_GEOJSON_PATH.exists():
        return None
    with open(ROADS_GEOJSON_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def _haversine_m(lat1, lon1, lat2, lon2):
    R = 6371000
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = math.sin(dlat / 2) ** 2 + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon / 2) ** 2
    return R * 2 * math.asin(math.sqrt(a))


def _point_to_segment_distance(px, py, ax, ay, bx, by):
    """Distance from point (px,py) to line segment (ax,ay)-(bx,by) in degrees, approx meters."""
    dx = bx - ax
    dy = by - ay
    if dx == 0 and dy == 0:
        return _haversine_m(py, px, ay, ax)
    t = max(0, min(1, ((px - ax) * dx + (py - ay) * dy) / (dx * dx + dy * dy)))
    proj_x = ax + t * dx
    proj_y = ay + t * dy
    return _haversine_m(py, px, proj_y, proj_x)


@router.get("/roads/geojson")
def get_roads_geojson(
    category: Optional[str] = Query(None, description="Filter: major, secondary, local, minor"),
    limit: int = Query(0, ge=0, description="0 = all features"),
):
    """Return real OSM road geometry as GeoJSON FeatureCollection."""
    data = _load_roads()
    if data is None:
        raise HTTPException(
            status_code=503,
            detail="roads.geojson not available — run scripts/extract_roads.py")

    features = data["features"]
    if category:
        features = [f for f in features if f["properties"].get("category") == category]

    if limit > 0:
        features = features[:limit]

    return {
        "type": "FeatureCollection",
        "features": features,
        "metadata": data.get("metadata", {}),
    }


@router.get("/roads/nearest")
def find_nearest_road(
    lat: float = Query(..., ge=-90, le=90, description="Latitude"),
    lng: float = Query(..., ge=-180, le=180, description="Longitude"),
    category: Optional[str] = Query(None, description="Filter category"),
):
    """Find the nearest real road to a point. Returns road info + distance."""
    data = _load_roads()
    if data is None:
        raise HTTPException(
            status_code=503,
            detail="roads.geojson not available — run scripts/extract_roads.py")

    features = data["features"]
    if category:
        features = [f for f in features if f["properties"].get("category") == category]

    best_dist = float("inf")
    best_feature = None
    best_point = None

    for feat in features:
        geom = feat["geometry"]
        coords = geom["coordinates"]
        for i in range(len(coords) - 1):
            ax, ay = coords[i]
            bx, by = coords[i + 1]
            dist = _point_to_segment_distance(lng, lat, ax, ay, bx, by)
            if dist < best_dist:
                best_dist = dist
                best_feature = feat
                # Closest point on segment
                dx = bx - ax
                dy = by - ay
                seg_len_sq = dx * dx + dy * dy
                if seg_len_sq < 1e-12:
                    best_point = [ax, ay]
                else:
                    t = max(0, min(1, ((lng - ax) * dx + (lat - ay) * dy) / seg_len_sq))
                    best_point = [ax + t * dx, ay + t * dy]

    if best_feature is None:
        raise HTTPException(status_code=503, detail="No roads found")

    props = best_feature["properties"]
    return {
        "road_id": props.get("road_id"),
        "name": props.get("name") or "Unnamed road",
        "ref": props.get("ref") or "",
        "highway": props.get("highway", ""),
        "category": props.get("category", ""),
        "surface": props.get("surface") or "Not available",
        "distance_m": round(best_dist),
        "nearest_point": {"lng": best_point[0], "lat": best_point[1]} if best_point else None,
    }


@router.get("/roads/stats")
def get_road_stats():
    """Summary statistics for the road network."""
    data = _load_roads()
    if data is None:
        return {"error": "roads.geojson not found"}

    meta = data.get("metadata", {})
    return {
        "total_roads": meta.get("total_features", len(data.get("features", []))),
        "highway_classes": meta.get("highway_classes", {}),
        "categories": meta.get("categories", {}),
        "source": meta.get("source", "unknown"),
        "crs": meta.get("crs", "EPSG:4326"),
        "aoi": meta.get("aoi", {}),
    }
