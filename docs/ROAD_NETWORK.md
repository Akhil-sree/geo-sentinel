# ROAD NETWORK

Existing routing PRESERVED and documented: A* primary (`astar()`), Dijkstra
fallback (`dijkstra()`), `find_safest_route()` —
cost = travel_time × status_penalty × (1 + risk_weight × avg_risk) ×
(1 + 0.3 × slope_norm); response/evacuation weight presets; distance-only
baseline for comparison (`backened/app/services/route_optimizer.py`).
Weights are config (`risk_thresholds.yaml`), documented as unvalidated.
OSM real-data layer (new): per-zone highway-way counts + classes via Overpass
(8/8 zones cached in `data/raw/osm_zone_*.json`, REAL geometry counts);
Geofabrik India PBF manual drop supported (`data/manual/osm/`); OSMnx
optional (not installed — NetworkX graphs only when present). Full-graph
OSM routing (OSMnx over manual PBF) is the documented next step; current
emergency routing runs on the curated segment graph. Sources:
https://download.geofabrik.de/asia/india.html, https://osmnx.readthedocs.io.
