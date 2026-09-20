"""Real road-network graph built from roads.geojson for A* routing
with actual road geometry (not zone-to-zone schematic)."""

import heapq
import math
from collections import defaultdict
from functools import lru_cache
from pathlib import Path

ROADS_GEOJSON_PATH = (
    Path(__file__).resolve().parent.parent.parent / "data" / "processed" / "roads.geojson"
)

_BLOCKED_ROADS = [
    {"coord": [91.64, 25.30], "reason": "landslide - demo scenario"},
    {"coord": [91.95, 25.38], "reason": "landslide - demo scenario"},
    {"coord": [91.58, 25.57], "reason": "landslide - demo scenario"},
]

_ENDPOINT_TOLERANCE_M = 50.0
_FLOAT_TOL = 1e-5


def _max_snap_m():
    """Snap threshold, env-driven (app.config) with safe fallback for
    bare imports (tests importing this module without full app config)."""
    try:
        from app.config import ROUTE_MAX_SNAP_DISTANCE_M
        return float(ROUTE_MAX_SNAP_DISTANCE_M)
    except Exception:
        return 5000.0


def _valid_latlng(lat, lng):
    try:
        la, ln = float(lat), float(lng)
    except (TypeError, ValueError):
        return False
    import math as _m
    if not (_m.isfinite(la) and _m.isfinite(ln)):
        return False
    return -90.0 <= la <= 90.0 and -180.0 <= ln <= 180.0


def _valid_geometry(geom):
    """A routable LineString needs >= 2 finite, in-range, distinct points."""
    import math as _m
    if not isinstance(geom, list) or len(geom) < 2:
        return False
    for pt in geom:
        try:
            lng, lat = float(pt[0]), float(pt[1])
        except (TypeError, ValueError, IndexError):
            return False
        if not (_m.isfinite(lng) and _m.isfinite(lat)):
            return False
        if not (-90.0 <= lat <= 90.0 and -180.0 <= lng <= 180.0):
            return False
    return True


def _unavailable(reason):
    return {
        "route_available": False,
        "reason": reason,
        "geometry": [],
        "distance_m": 0,
        "segments": [],
        "blocked_avoided": [],
        "road_count": 0,
    }


def _haversine_m(lat1, lon1, lat2, lon2):
    R = 6371000.0
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = (
        math.sin(dlat / 2) ** 2
        + math.cos(math.radians(lat1))
        * math.cos(math.radians(lat2))
        * math.sin(dlon / 2) ** 2
    )
    return R * 2 * math.asin(math.sqrt(a))


@lru_cache(maxsize=1)
def _load_roads():
    if not ROADS_GEOJSON_PATH.exists():
        return []
    import json
    with open(ROADS_GEOJSON_PATH, encoding="utf-8") as f:
        data = json.load(f)
    return data.get("features", [])


def _find_nearest_road_id(coord):
    roads = _load_roads()
    best_id = None
    best_dist = float("inf")
    clng, clat = coord
    for feat in roads:
        props = feat["properties"]
        coords = feat["geometry"]["coordinates"]
        for c in coords:
            d = _haversine_m(clat, clng, c[1], c[0])
            if d < best_dist:
                best_dist = d
                best_id = props.get("road_id")
    return best_id


def _build_graph_raw():
    """Build the raw graph dict from ALL road vertices (not just endpoints).

    Each coordinate in a road feature becomes a node. Consecutive coordinates
    within the same road are connected by edges. Nearby coordinates across
    different roads are merged into shared nodes (intersection points).
    """
    roads = _load_roads()
    if not roads:
        return None

    blocked_ids = set()
    for br in _BLOCKED_ROADS:
        rid = _find_nearest_road_id(br["coord"])
        if rid is not None:
            blocked_ids.add(rid)

    # Phase 1: collect ALL vertices from ALL roads
    raw_pts = []  # [(lng, lat), ...]
    road_sequences = []  # [(start_idx, end_idx, feat_index)]

    for fi, feat in enumerate(roads):
        coords = feat["geometry"]["coordinates"]
        if len(coords) < 2:
            continue
        start_idx = len(raw_pts)
        for c in coords:
            raw_pts.append((c[0], c[1]))
        end_idx = len(raw_pts) - 1
        road_sequences.append((start_idx, end_idx, fi))

    n_raw = len(raw_pts)
    if n_raw == 0:
        return None

    # Phase 2: grid-based spatial hashing for vertex merging
    # Grid cell ~50m
    _GRID_SIZE = 200.0 / 111000.0  # ~0.0018 degrees

    grid = {}
    for i, (lng, lat) in enumerate(raw_pts):
        gx = int(math.floor(lng / _GRID_SIZE))
        gy = int(math.floor(lat / _GRID_SIZE))
        key = (gx, gy)
        if key not in grid:
            grid[key] = []
        grid[key].append(i)

    # Phase 3: union-find to merge nearby vertices
    parent = list(range(n_raw))

    def find(x):
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    def union(x, y):
        rx, ry = find(x), find(y)
        if rx != ry:
            parent[rx] = ry

    _MERGE_TOLERANCE_M = 200.0
    checked = set()
    for (gx, gy), cell_indices in grid.items():
        for dx in (-1, 0, 1):
            for dy in (-1, 0, 1):
                neighbor_key = (gx + dx, gy + dy)
                if neighbor_key not in grid:
                    continue
                for i in cell_indices:
                    for j in grid[neighbor_key]:
                        if i >= j:
                            continue
                        pair_key = (i, j)
                        if pair_key in checked:
                            continue
                        checked.add(pair_key)
                        lng_i, lat_i = raw_pts[i]
                        lng_j, lat_j = raw_pts[j]
                        if _haversine_m(lat_i, lng_i, lat_j, lng_j) <= _MERGE_TOLERANCE_M:
                            union(i, j)

    # Phase 4: build canonical node IDs
    canonical_of = {}
    node_counter = 0
    node_coords = {}

    for i in range(n_raw):
        root = find(i)
        if root not in canonical_of:
            canonical_of[root] = node_counter
            node_coords[node_counter] = list(raw_pts[root])
            node_counter += 1

    # Phase 5: build adjacency from ALL consecutive vertex pairs within each road
    adj = defaultdict(list)
    edge_data = {}
    edge_counter = 0

    for start_idx, _end_idx, fi in road_sequences:
        feat = roads[fi]
        props = feat["properties"]
        road_id = props.get("road_id")
        is_blocked = road_id in blocked_ids
        coords = feat["geometry"]["coordinates"]

        # Create edges between consecutive vertices in this road
        for k in range(len(coords) - 1):
            idx_from = start_idx + k
            idx_to = start_idx + k + 1
            ca = canonical_of[find(idx_from)]
            cb = canonical_of[find(idx_to)]
            if ca == cb:
                continue

            seg_len = _haversine_m(
                coords[k][1], coords[k][0], coords[k + 1][1], coords[k + 1][0]
            )
            if seg_len < 1.0:
                continue  # skip sub-meter edges

            edge_id = edge_counter
            edge_counter += 1

            # For multi-vertex roads, each segment gets the same road metadata
            edge_data[edge_id] = {
                "edge_id": edge_id,
                "road_id": road_id,
                "geometry": [coords[k], coords[k + 1]],
                "length_m": seg_len,
                "category": props.get("category", ""),
                "highway": props.get("highway", ""),
                "name": props.get("name") or "",
                "ref": props.get("ref") or "",
                "status": "BLOCKED" if is_blocked else "OPEN",
                "blockage_reason": "landslide - demo scenario" if is_blocked else "",
            }

            if not is_blocked:
                adj[ca].append((cb, edge_id, seg_len))
                adj[cb].append((ca, edge_id, seg_len))

    return {
        "adj": dict(adj),
        "edges": edge_data,
        "node_coords": node_coords,
        "blocked_ids": frozenset(blocked_ids),
    }


@lru_cache(maxsize=1)
def _build_graph():
    result = _build_graph_raw()
    if result is None:
        return {"adj": {}, "edges": {}, "node_coords": {}, "blocked_ids": frozenset()}
    return result


def get_blocked_road_ids():
    """Return sorted list of blocked OSM road_ids (demo scenario)."""
    return sorted(_build_graph().get("blocked_ids", frozenset()))


def _find_nearest_node(node_coords, lat, lng, adj=None):
    # ponytail: skip isolated (degree-0) nodes when adj given — routing
    # through them is impossible; fall back to any node if none connected.
    best_node = None
    best_d = float("inf")
    for nid, (nlng, nlat) in node_coords.items():
        if adj is not None and not adj.get(nid):
            continue
        d = _haversine_m(lat, lng, nlat, nlng)
        if d < best_d:
            best_d = d
            best_node = nid
    if best_node is None and adj is not None:
        return _find_nearest_node(node_coords, lat, lng)
    return best_node, best_d


def find_route(origin_lat, origin_lng, dest_lat, dest_lng):
    """Find a real road-route between two lat/lng points.

    Returns dict with: route_available, geometry (LineString coords),
    distance_m, segments, blocked_avoided, road_count.
    """
    g = _build_graph()
    adj = g["adj"]
    edges = g["edges"]
    node_coords = g["node_coords"]

    if not adj:
        return _unavailable("Road network data not loaded")

    if not _valid_latlng(origin_lat, origin_lng):
        return _unavailable("INVALID_ORIGIN (latitude -90..90, longitude -180..180, finite)")
    if not _valid_latlng(dest_lat, dest_lng):
        return _unavailable("INVALID_DESTINATION (latitude -90..90, longitude -180..180, finite)")

    origin_node, od = _find_nearest_node(node_coords, origin_lat, origin_lng, adj)
    dest_node, dd = _find_nearest_node(node_coords, dest_lat, dest_lng, adj)

    if origin_node is None or dest_node is None:
        return _unavailable("Could not snap points to road network")

    # Coverage gate: a snap farther than the threshold means the request
    # point is outside the mapped network — never fabricate a route for it.
    max_snap = _max_snap_m()
    if od > max_snap:
        return _unavailable(
            f"ORIGIN_OUT_OF_COVERAGE (nearest road {round(od)} m away, limit {max_snap:g} m)")
    if dd > max_snap:
        return _unavailable(
            f"DESTINATION_OUT_OF_COVERAGE (nearest road {round(dd)} m away, limit {max_snap:g} m)")

    if origin_node == dest_node:
        # Same snapped node: no road travel exists. A single-point
        # LineString is invalid GeoJSON, so this is explicitly unavailable
        # rather than a zero-length "route".
        return _unavailable("SAME_ORIGIN_DESTINATION (origin and destination snap to the same road node)")

    # A* search — only traverses OPEN roads
    open_set = [(0.0, origin_node)]
    came_from_node = {}
    came_from_edge = {}
    g_score = defaultdict(lambda: float("inf"))
    g_score[origin_node] = 0.0
    closed = set()

    def h(node):
        nlon, nlat = node_coords[node]
        return _haversine_m(dest_lat, dest_lng, nlat, nlon)

    while open_set:
        fval, u = heapq.heappop(open_set)
        if u in closed:
            continue
        if u == dest_node:
            break
        closed.add(u)
        for v, eid, w in adj.get(u, []):
            if v in closed:
                continue
            ng = g_score[u] + w
            if ng < g_score[v]:
                g_score[v] = ng
                came_from_node[v] = u
                came_from_edge[v] = eid
                heapq.heappush(open_set, (ng + h(v), v))

    if g_score[dest_node] == float("inf"):
        return _unavailable("No passable route found — all paths may be blocked")

    # Reconstruct path
    path_nodes = []
    path_edges = []
    cur = dest_node
    while cur != origin_node:
        path_nodes.append(cur)
        path_edges.append(came_from_edge[cur])
        cur = came_from_node[cur]
    path_nodes.append(origin_node)
    path_nodes.reverse()
    path_edges.reverse()

    # Build geometry and segments from path edges
    raw_geometry = []
    segments = []
    total_distance = 0.0

    for i, nid in enumerate(path_nodes):
        nlon, nlat = node_coords[nid]
        raw_geometry.append([nlon, nlat])

        if i < len(path_edges):
            eid = path_edges[i]
            edge = edges[eid]
            coords = edge["geometry"]

            # Edge geometry stored as [start, end] in original direction.
            # Determine traversal direction by checking which endpoint matches
            # the current node or next node.
            if len(coords) >= 2:
                next_nid = path_nodes[i + 1] if i + 1 < len(path_nodes) else None
                cur_lon, cur_lat = node_coords[nid]
                next_lon, next_lat = node_coords[next_nid] if next_nid is not None else (None, None)

                # Check if we're going forward or backward through edge geometry
                dist_start_cur = abs(cur_lon - coords[0][0]) + abs(cur_lat - coords[0][1])
                dist_start_next = abs(next_lon - coords[0][0]) + abs(next_lat - coords[0][1]) if next_lon else float("inf")
                dist_end_cur = abs(cur_lon - coords[-1][0]) + abs(cur_lat - coords[-1][1])
                dist_end_next = abs(next_lon - coords[-1][0]) + abs(next_lat - coords[-1][1]) if next_lon else float("inf")

                # If current node is near start and next node is near end => forward
                # If current node is near end and next node is near start => backward
                if dist_end_cur < dist_start_cur and dist_start_next < dist_end_next or dist_start_next > dist_end_next and dist_start_cur > dist_end_cur:
                    edge_coords = list(reversed(coords))
                else:
                    edge_coords = coords

                # Append road geometry (skip duplicate first point)
                start_idx = 1 if (
                    raw_geometry
                    and abs(raw_geometry[-1][0] - edge_coords[0][0]) < _FLOAT_TOL
                    and abs(raw_geometry[-1][1] - edge_coords[0][1]) < _FLOAT_TOL
                ) else 0
                raw_geometry.extend(edge_coords[start_idx:])

            total_distance += edge["length_m"]
            segments.append({
                "road_id": edge["road_id"],
                "name": edge["name"] or edge["ref"] or f"Road {edge['road_id']}",
                "category": edge["category"],
                "highway": edge["highway"],
                "length_m": round(edge["length_m"]),
                "status": edge["status"],
            })

    # Deduplicate geometry: remove consecutive near-identical points,
    # then smooth out zigzags (if point B goes backward relative to A->C,
    # skip B unless it's a genuine longer detour).
    deduped = []
    for pt in raw_geometry:
        if not deduped or abs(deduped[-1][0] - pt[0]) > _FLOAT_TOL or abs(deduped[-1][1] - pt[1]) > _FLOAT_TOL:
            deduped.append(pt)

    # Smooth zigzags: if deduped[i] reverses direction from deduped[i-2]->deduped[i-1],
    # and deduped[i-2]->deduped[i] is shorter than deduped[i-2]->deduped[i-1]->deduped[i],
    # skip deduped[i-1].
    geometry = []
    for pt in deduped:
        if len(geometry) < 2:
            geometry.append(pt)
            continue
        dx_prev = geometry[-1][0] - geometry[-2][0]
        dy_prev = geometry[-1][1] - geometry[-2][1]
        dx_cur = pt[0] - geometry[-1][0]
        dy_cur = pt[1] - geometry[-1][1]
        # If both axes reverse direction, this is a zigzag — remove middle point
        if (dx_prev * dx_cur < 0 and dy_prev * dy_cur < 0
                and abs(dx_cur) < abs(dx_prev) * 2 and abs(dy_cur) < abs(dy_prev) * 2):
            geometry.pop()
        # Skip if identical to tail (pop may have exposed an equal point)
        if (abs(geometry[-1][0] - pt[0]) <= _FLOAT_TOL
                and abs(geometry[-1][1] - pt[1]) <= _FLOAT_TOL):
            continue
        geometry.append(pt)

    # Find blocked roads that are near the route path (avoided roads)
    path_node_set = set(path_nodes)
    blocked_avoided = []
    for _eid, edge in edges.items():
        if edge["status"] != "BLOCKED":
            continue
        # Check if any endpoint of this blocked road is on the path
        # (the endpoints were snapped to canonical nodes during graph build)
        # We check proximity: if a blocked road endpoint is close to any path node
        coords = edge["geometry"]
        if len(coords) < 2:
            continue
        blng, blat = coords[0][0], coords[0][1]
        for pnid in path_node_set:
            pnlon, pnlat = node_coords[pnid]
            if _haversine_m(blat, blng, pnlat, pnlon) < _ENDPOINT_TOLERANCE_M:
                blocked_avoided.append({
                    "road_id": edge["road_id"],
                    "name": edge["name"],
                    "reason": edge["blockage_reason"],
                })
                break

    # Integrity gate: a route with no traversed segments or a degenerate
    # geometry (< 2 valid positions) is not a route — refuse it instead of
    # serving a single-point/empty LineString to the map.
    if not path_edges or not _valid_geometry(geometry):
        return _unavailable("INVALID_ROUTE_GEOMETRY (computed path failed integrity validation)")

    return {
        "route_available": True,
        "geometry": geometry,
        "distance_m": round(total_distance),
        "segments": segments,
        "blocked_avoided": blocked_avoided,
        "road_count": len(segments),
        "origin_snap_m": round(od),
        "destination_snap_m": round(dd),
    }
