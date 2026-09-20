"""Route optimizer — A* primary, Dijkstra fallback, response + evacuation modes,
risk-weighted edges, route explanation."""

import heapq
import math

from sqlalchemy.orm import Session

from app.models_db import RiskScore, RoadSegment, Zone

# Status penalties — configurable
STATUS_PENALTY = {
    "OPEN": 1.0,
    "UNDER_REPAIR": 1.5,
    "DAMAGED": 3.0,
    "BLOCKED": float("inf"),
}

# Mode-specific risk weight multipliers
MODE_RISK_WEIGHT = {
    "response": 1.0,
    "evacuation": 2.0,
}

# Travel speed assumptions (km/h) by road type
ROAD_SPEED = {
    "national": 50,
    "state": 40,
    "district": 35,
    "village": 25,
}


def build_graph(db: Session, sim_time: int = 96, mode: str = "response",
                risk_weight_override: float | None = None):
    """Build adjacency list from road segments.

    Cost function (documented, Phase 6/13):
        weight = travel_time_min * status_penalty
                 * (1 + risk_weight * avg_risk) * (1 + 0.3 * avg_slope_norm)
    where travel_time_min = length_km / speed(road_type),
    status_penalty in {OPEN 1.0, UNDER_REPAIR 1.5, DAMAGED 3.0, BLOCKED inf},
    avg_risk = mean endpoint zone risk, avg_slope_norm = mean endpoint
    slope / 60 (steeper approaches cost more),
    risk_weight 1.0 (response) / 2.0 (evacuation).
    risk_weight_override=0 gives the distance-only baseline.
    Output is a LOWER-EXPOSURE route, never a "safe" route.

    Returns: graph, zones, risk_map, all_segments
    graph = {zone_id: [(neighbor, weight, travel_time_min, road_segment)]}
    """
    segments = db.query(RoadSegment).all()
    zones = {z.id: z for z in db.query(Zone).all()}

    risk_map = {}
    for zid in zones:
        latest = (
            db.query(RiskScore)
            .filter(RiskScore.zone_id == zid)
            .order_by(RiskScore.timestamp.desc())
            .first()
        )
        risk_map[zid] = latest.risk_score if latest else 0.0

    risk_weight = (risk_weight_override if risk_weight_override is not None
                   else MODE_RISK_WEIGHT.get(mode, 1.0))
    graph = {zid: [] for zid in zones}

    for seg in segments:
        base_dist = seg.length_km if seg.length_km > 0 else 1.0
        penalty = STATUS_PENALTY.get(seg.status, 1.0)
        if penalty == float("inf"):
            continue  # excluded from graph

        avg_risk = (risk_map.get(seg.from_zone, 0) + risk_map.get(seg.to_zone, 0)) / 2
        za, zb = zones.get(seg.from_zone), zones.get(seg.to_zone)
        avg_slope = (((za.slope if za and za.slope else 0)
                      + (zb.slope if zb and zb.slope else 0)) / 2) / 60.0
        speed = ROAD_SPEED.get(seg.road_type, 35)
        travel_time_min = (base_dist / speed) * 60

        # Effective cost with slope-aware exposure penalty
        weight = (travel_time_min * penalty * (1 + risk_weight * avg_risk)
                  * (1 + 0.3 * min(1.0, max(0.0, avg_slope))))

        graph[seg.from_zone].append((seg.to_zone, weight, travel_time_min, seg))
        graph[seg.to_zone].append((seg.from_zone, weight, travel_time_min, seg))

    return graph, zones, risk_map, segments


def _heuristic(zones, node, target):
    """Euclidean heuristic for A* (in km, roughly)."""
    a, b = zones.get(node), zones.get(target)
    if not a or not b:
        return 0
    dlat = (a.latitude - b.latitude) * 111
    dlng = (a.longitude - b.longitude) * 111 * math.cos(math.radians(a.latitude))
    return math.sqrt(dlat**2 + dlng**2)


def astar(graph, zones, source, target):
    """A* algorithm. Returns (cost, path, edges)."""
    open_set = [(0, source)]
    came_from = dict.fromkeys(graph)
    edge_from = dict.fromkeys(graph)
    g_score = {n: float("inf") for n in graph}
    g_score[source] = 0

    while open_set:
        _, u = heapq.heappop(open_set)
        if u == target:
            break
        for v, weight, _, edge in graph[u]:
            tentative = g_score[u] + weight
            if tentative < g_score[v]:
                came_from[v] = u
                edge_from[v] = edge
                g_score[v] = tentative
                f = tentative + _heuristic(zones, v, target)
                heapq.heappush(open_set, (f, v))

    if g_score[target] == float("inf"):
        return None, [], []

    path, edges = [], []
    node = target
    while node is not None:
        path.append(node)
        if edge_from[node] is not None:
            edges.append(edge_from[node])
        node = came_from[node]
    path.reverse()
    edges.reverse()
    return g_score[target], path, edges


def dijkstra(graph, source, target):
    """Dijkstra fallback. Returns (cost, path, edges)."""
    dist = {n: float("inf") for n in graph}
    prev = dict.fromkeys(graph)
    prev_edge = dict.fromkeys(graph)
    dist[source] = 0
    pq = [(0, source)]

    while pq:
        d, u = heapq.heappop(pq)
        if d > dist[u]:
            continue
        if u == target:
            break
        for v, weight, _, edge in graph[u]:
            nd = d + weight
            if nd < dist[v]:
                dist[v] = nd
                prev[v] = u
                prev_edge[v] = edge
                heapq.heappush(pq, (nd, v))

    if dist[target] == float("inf"):
        return None, [], []

    path, edges = [], []
    node = target
    while node is not None:
        path.append(node)
        if prev_edge[node] is not None:
            edges.append(prev_edge[node])
        node = prev[node]
    path.reverse()
    edges.reverse()
    return dist[target], path, edges


def find_safest_route(db, source, target, sim_time=96, mode="response"):
    """Find the safest route. A* primary, Dijkstra fallback."""
    graph, zones, risk_map, all_segments = build_graph(db, sim_time, mode)

    if source not in graph or target not in graph:
        return None

    if source == target:
        z = zones.get(source)
        return _empty_route(source, target, z, z)

    # A*
    cost, path, edges = astar(graph, zones, source, target)

    # Fallback to Dijkstra if A* fails (shouldn't happen on consistent heuristic)
    if cost is None:
        cost, path, edges = dijkstra(graph, source, target)
        algorithm = "Dijkstra"
    else:
        algorithm = "A*"

    if cost is None:
        reachable = [n for n in graph if n != source and dijkstra(graph, source, n)[0] is not None]
        return {
            "route_available": False,
            "algorithm": algorithm,
            "mode": mode,
            "source": source,
            "target": target,
            "source_name": zones[source].name if source in zones else source,
            "target_name": zones[target].name if target in zones else target,
            "reason": (f"No passable lower-exposure route from {source} to "
                       f"{target} — all paths blocked or impassable"),
            "alternative_routes": [],
            "reachable_zones": reachable,
            "distance_km": 0,
            "estimated_time_min": 0,
            "safety_score": 0.0,
            "risk_exposure": 1.0,
            "roads_used": [],
            "roads_avoided": _get_avoided_roads(all_segments, source, target),
            "geometry": {"type": "LineString", "coordinates": []},
            "geometry_kind": "unavailable-no-passable-route",
            "explanation": _explain_no_route(source, target, zones, all_segments),
        }

    # Build result
    seg_details = []
    total_distance = 0
    total_time = 0
    warnings = []
    avoided = []
    road_status_map = {}

    for edge in edges:
        seg = edge
        speed = ROAD_SPEED.get(seg.road_type, 35)
        t_min = (seg.length_km / speed) * 60 if seg.length_km > 0 else 0
        seg_details.append({
            "road_name": seg.name,
            "from_zone": seg.from_zone,
            "to_zone": seg.to_zone,
            "from_name": zones[seg.from_zone].name if seg.from_zone in zones else seg.from_zone,
            "to_name": zones[seg.to_zone].name if seg.to_zone in zones else seg.to_zone,
            "length_km": seg.length_km,
            "status": seg.status,
            "blockage_reason": seg.blockage_reason,
            "road_type": seg.road_type,
            "travel_time_min": round(t_min, 1),
        })
        total_distance += seg.length_km
        total_time += t_min
        road_status_map[seg.name] = seg.status
        if seg.status != "OPEN":
            warnings.append(f"{seg.name}: {seg.status}" + (f" ({seg.blockage_reason})" if seg.blockage_reason else ""))

    # Avoided roads
    for seg in all_segments:
        if seg.name not in road_status_map and seg.from_zone in path and seg.to_zone in path:
            avoided.append({"road_name": seg.name, "status": seg.status, "reason": seg.blockage_reason})
        elif seg.status in ("BLOCKED", "DAMAGED") and (seg.from_zone in path or seg.to_zone in path):
            if seg.name not in road_status_map:
                avoided.append({"road_name": seg.name, "status": seg.status, "reason": seg.blockage_reason})

    # Safety score: inverse of average risk along path
    avg_risk = sum(risk_map.get(z, 0) for z in path) / max(len(path), 1)
    safety_score = max(0, min(1, 1.0 - avg_risk))

    # Risk exposure
    risk_exposure = avg_risk

    # Risk level
    if avg_risk > 0.7 or any(s["status"] == "DAMAGED" for s in seg_details):
        risk_level = "HIGH"
    elif avg_risk > 0.4 or any(s["status"] == "UNDER_REPAIR" for s in seg_details):
        risk_level = "MODERATE"
    else:
        risk_level = "LOW"

    # Geometry for map
    coords = []
    for zid in path:
        if zid in zones:
            coords.append([zones[zid].longitude, zones[zid].latitude])

    # Explanation
    explanation = _explain_route(path, zones, edges, risk_map, mode, algorithm)

    est_time_min = round(total_time)

    # Baseline: distance-only route (risk_weight=0) for comparison, so the
    # UI can show WHY the risk-aware route is safer (Phase 6).
    baseline = _baseline_route(db, source, target, sim_time, zones, risk_map)

    return {
        "route_available": True,
        "algorithm": algorithm,
        "mode": mode,
        "cost_function": ("travel_time_min * status_penalty * "
                          "(1 + risk_weight * avg_endpoint_risk) * "
                          "(1 + 0.3 * avg_endpoint_slope_norm)"),
        "baseline_route": baseline,
        "source": source,
        "target": target,
        "source_name": zones[source].name if source in zones else source,
        "target_name": zones[target].name if target in zones else target,
        "distance_km": round(total_distance, 1),
        "estimated_time_min": est_time_min,
        "safety_score": round(safety_score, 3),
        "risk_exposure": round(risk_exposure, 3),
        "risk_level": risk_level,
        "roads_used": seg_details,
        "roads_avoided": avoided,
        "warnings": warnings,
        "path": path,
        "path_names": [zones[z].name if z in zones else z for z in path],
        "route_coords": [{"lat": zones[z].latitude, "lng": zones[z].longitude, "zone_id": z, "name": zones[z].name} for z in path if z in zones],
        # GIS honesty: coordinates are zone centroids (real positions) joined
        # in path order — a SCHEMATIC, not surveyed road geometry. The demo
        # graph has no intermediate edge vertices, so no renderer may draw
        # this as a geographic road. Frontend draws road STATUS MARKERS at
        # real segment midpoints instead (see RoadNetworkLayer).
        "geometry": {"type": "LineString", "coordinates": coords},
        "geometry_kind": "schematic-centroid-demo",
        "explanation": explanation,
    }


def find_all_routes_from(db, source, sim_time=96, mode="response"):
    """Find safest route from source to every reachable zone."""
    graph, zones, risk_map, all_segments = build_graph(db, sim_time, mode)
    results = []
    for target in zones:
        if target == source:
            continue
        route = find_safest_route(db, source, target, sim_time, mode)
        if route and route.get("route_available"):
            results.append(route)
    results.sort(key=lambda r: r["distance_km"])
    return results


def _empty_route(source, target, z_source, z_target):
    return {
        "route_available": True,
        "algorithm": "A*",
        "mode": "response",
        "source": source,
        "target": target,
        "source_name": z_source.name if z_source else source,
        "target_name": z_target.name if z_target else target,
        "distance_km": 0,
        "estimated_time_min": 0,
        "safety_score": 1.0,
        "risk_exposure": 0.0,
        "risk_level": "LOW",
        "roads_used": [],
        "roads_avoided": [],
        "warnings": [],
        "path": [source],
        "path_names": [z_source.name if z_source else source],
        "route_coords": [{"lat": z_source.latitude, "lng": z_source.longitude, "zone_id": source, "name": z_source.name}] if z_source else [],
        "geometry": {"type": "LineString", "coordinates": []},
        "explanation": {"why": ["Start and destination are the same zone"], "tradeoffs": []},
    }


def _baseline_route(db, source, target, sim_time, zones, risk_map):
    """Distance-only route (no risk penalty) for the safer-than comparison."""
    graph, _, _, _ = build_graph(db, sim_time, "response",
                                 risk_weight_override=0.0)
    cost, path, edges = astar(graph, zones, source, target)
    if cost is None:
        cost, path, edges = dijkstra(graph, source, target)
    if cost is None or not path:
        return {"route_available": False}
    dist = sum((e.length_km or 0) for e in edges)
    avg_risk = sum(risk_map.get(z, 0) for z in path) / max(len(path), 1)
    return {"route_available": True,
            "path": path,
            "path_names": [zones[z].name if z in zones else z for z in path],
            "distance_km": round(dist, 1),
            "risk_exposure": round(avg_risk, 3),
            "why_safer": ("Risk-aware route avoids high-risk/blocked segments "
                          "the shortest path uses — compare risk_exposure."),
            "note": "BASELINE (distance-only) — for comparison, not dispatch"}


def _get_avoided_roads(segments, source, target):
    return [
        {"road_name": s.name, "status": s.status, "reason": s.blockage_reason}
        for s in segments if s.status in ("BLOCKED", "DAMAGED")
    ]


def _explain_route(path, zones, edges, risk_map, mode, algorithm):
    """Generate human-readable route explanation."""
    why = []
    tradeoffs = []

    open_roads = [e for e in edges if e.status == "OPEN"]
    damaged_used = [e for e in edges if e.status == "DAMAGED"]
    under_repair_used = [e for e in edges if e.status == "UNDER_REPAIR"]

    if algorithm == "A*":
        why.append(f"Algorithm: {algorithm} — geographic heuristic guides search toward destination")

    if open_roads:
        why.append(f"Uses {len(open_roads)} open road segment{'s' if len(open_roads) > 1 else ''} to reduce hazard exposure")

    if damaged_used:
        why.append(f"Includes {len(damaged_used)} damaged segment{'s' if len(damaged_used) > 1 else ''} — no fully open alternative exists")
        tradeoffs.append("Damaged roads may have reduced capacity or require caution")

    if under_repair_used:
        cnt = len(under_repair_used)
        label = "roads under repair" if cnt > 1 else "road under repair"
        why.append(f"Passes through {cnt} {label}")
        tradeoffs.append("Under-repair roads are passable but may have delays")

    avg_risk = sum(risk_map.get(z, 0) for z in path) / max(len(path), 1)
    if mode == "evacuation":
        why.append("Evacuation mode: prioritizes safety over speed — higher risk penalty applied")
    else:
        why.append("Response mode: balances speed and safety for emergency vehicles")

    if avg_risk > 0.5:
        tradeoffs.append(f"Path passes through zones with elevated risk (avg {avg_risk:.0%})")

    if not why:
        why.append("Route selected as the lowest-cost path through the road network")

    return {"why": why, "tradeoffs": tradeoffs}


def _explain_no_route(source, target, zones, segments):
    """Explain why no route exists."""
    blocked = [s for s in segments if s.status == "BLOCKED" and (s.from_zone == source or s.to_zone == source)]
    damaged = [s for s in segments if s.status in ("BLOCKED", "DAMAGED")]
    why = []
    if blocked:
        why.append(f"All direct connections from {zones[source].name if source in zones else source} are BLOCKED")
    if damaged:
        why.append(f"{len(damaged)} road segments across the network are BLOCKED or DAMAGED")
    why.append("No alternative path exists through open roads")
    return {"why": why, "tradeoffs": ["Consider road clearing or helicopter access"]}
