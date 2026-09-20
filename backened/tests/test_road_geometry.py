"""Road GIS honesty regressions: routes run on the real demo graph, carry no
invented coordinates, fail honestly, and never present centroid chords as
surveyed road geometry.
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from app.database import SessionLocal  # noqa: E402
from app.models_db import RoadSegment, Zone  # noqa: E402
from app.services.route_optimizer import (  # noqa: E402
    build_graph,
    find_safest_route,
)


def _db():
    return SessionLocal()


def test_route_path_uses_only_real_graph_edges():
    db = _db()
    try:
        graph, zones, _, _ = build_graph(db, 96, "response")
        segs = {(s.from_zone, s.to_zone) for s in db.query(RoadSegment).all()}
        segs |= {(b, a) for a, b in segs}
        for src in list(zones)[:3]:
            for tgt in zones:
                if src == tgt:
                    continue
                r = find_safest_route(db, src, tgt, 96, "response")
                if not r.get("route_available"):
                    continue
                path = r["path"]
                for a, b in zip(path, path[1:], strict=False):
                    assert (a, b) in segs, f"invented hop {a}->{b}"
    finally:
        db.close()


def test_route_coords_are_real_zone_positions_only():
    db = _db()
    try:
        zones = {z.id: z for z in db.query(Zone).all()}
        r = find_safest_route(db, "Z1", "Z3", 96, "response")
        assert r["route_available"] is True
        for c in r["route_coords"]:
            z = zones[c["zone_id"]]
            assert c["lat"] == z.latitude and c["lng"] == z.longitude
        for lon, lat in r["geometry"]["coordinates"]:
            assert -180 <= lon <= 180 and -90 <= lat <= 90
        assert r["geometry_kind"] == "schematic-centroid-demo"
    finally:
        db.close()


def test_no_route_is_honest_unavailable():
    db = _db()
    try:
        # Z2's only link is BLOCKED; isolate further if needed — either way,
        # an unavailable route must say so, never draw a fake line.
        r = find_safest_route(db, "ZZ_UNKNOWN", "Z1", 96, "response")
        assert r is None or r.get("route_available") is False
        r2 = find_safest_route(db, "Z1", "Z1", 96, "response")
        assert r2["route_available"] is True and r2["distance_km"] == 0
    finally:
        db.close()


def test_blocked_segments_excluded_from_routes():
    db = _db()
    try:
        blocked = {s.name for s in db.query(RoadSegment).all()
                   if s.status == "BLOCKED"}
        assert blocked, "seed must contain blocked segments for this test"
        r = find_safest_route(db, "Z1", "Z3", 96, "response")
        used = {s["road_name"] for s in r.get("roads_used", [])}
        assert not (used & blocked), f"blocked road routed: {used & blocked}"
    finally:
        db.close()


def test_segment_midpoints_are_valid_and_preserved():
    db = _db()
    try:
        for s in db.query(RoadSegment).all():
            assert -90 <= s.latitude <= 90
            assert -180 <= s.longitude <= 180
            assert s.length_km > 0
            assert s.road_type in ("national", "state", "district", "village")
    finally:
        db.close()
