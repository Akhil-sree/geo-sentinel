"""PostGIS-backed spatial queries with explicit backend routing.

postgresql backend → real ST_DWithin on geography columns (created by
migration v6). sqlite backend → same-shape results via haversine on the
canonical float lat/lng columns. No silent behavior change: every result
carries `spatial_backend` ("postgis" | "haversine").
"""
from app.geo.postgis import ensure_postgis, is_postgis, reports_within_km, roads_within_km, zones_within_km

__all__ = ["is_postgis", "ensure_postgis", "zones_within_km",
           "roads_within_km", "reports_within_km"]
