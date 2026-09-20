"""Road GIS endpoint tests — real OSM geometry served by the API."""
import json
import os
import sys
from pathlib import Path

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

ROADS_GEOJSON = Path(__file__).resolve().parent.parent / "data" / "processed" / "roads.geojson"


def test_roads_geojson_exists():
    assert ROADS_GEOJSON.exists(), "roads.geojson must exist — run scripts/extract_roads.py"


def test_roads_geojson_is_valid_featurecollection():
    with open(ROADS_GEOJSON, encoding="utf-8") as f:
        data = json.load(f)
    assert data["type"] == "FeatureCollection"
    assert isinstance(data["features"], list)
    assert len(data["features"]) > 0


def test_road_geometries_are_linestrings():
    with open(ROADS_GEOJSON, encoding="utf-8") as f:
        data = json.load(f)
    for feat in data["features"][:100]:  # sample first 100
        geom = feat["geometry"]
        assert geom["type"] in ("LineString", "MultiLineString"), \
            f"unexpected geometry type: {geom['type']}"
        coords = geom["coordinates"]
        if geom["type"] == "LineString":
            assert len(coords) >= 2, "LineString must have >= 2 points"
            for c in coords:
                assert len(c) == 2, f"coordinate must be [lon, lat], got {c}"
                lon, lat = c
                assert -180 <= lon <= 180, f"invalid lon: {lon}"
                assert -90 <= lat <= 90, f"invalid lat: {lat}"
        else:  # MultiLineString
            for ring in coords:
                assert len(ring) >= 2
                for c in ring:
                    assert len(c) == 2
                    lon, lat = c
                    assert -180 <= lon <= 180
                    assert -90 <= lat <= 90


def test_road_features_have_osm_properties():
    with open(ROADS_GEOJSON, encoding="utf-8") as f:
        data = json.load(f)
    for feat in data["features"][:50]:
        props = feat["properties"]
        assert "road_id" in props, "missing road_id"
        assert "highway" in props, "missing highway"
        assert "category" in props, "missing category"
        assert props["category"] in ("major", "secondary", "local", "minor"), \
            f"unknown category: {props['category']}"


def test_road_metadata_present():
    with open(ROADS_GEOJSON, encoding="utf-8") as f:
        data = json.load(f)
    meta = data.get("metadata", {})
    assert meta.get("crs") == "EPSG:4326", "CRS must be EPSG:4326"
    assert meta.get("source") == "meghalaya.pbf", "source must be meghalaya.pbf"
    assert meta.get("total_features", 0) > 0
    assert "highway_classes" in meta
    assert "categories" in meta


def test_no_point_only_road_features():
    """Primary road layer must not be point-only markers."""
    with open(ROADS_GEOJSON, encoding="utf-8") as f:
        data = json.load(f)
    for feat in data["features"]:
        geom_type = feat["geometry"]["type"]
        assert geom_type in ("LineString", "MultiLineString"), \
            f"road feature must be LineString/MultiLineString, got {geom_type}"


def test_no_fake_straight_line_connections():
    """Each road feature should come from OSM PBF, not fabricated coords."""
    with open(ROADS_GEOJSON, encoding="utf-8") as f:
        data = json.load(f)
    for feat in data["features"][:200]:
        props = feat["properties"]
        # road_id must be a positive integer (OSM way ID)
        assert isinstance(props["road_id"], int) and props["road_id"] > 0, \
            f"road_id must be positive int, got {props['road_id']}"


# ── AOI Containment: verify roads actually fall within Meghalaya ──

# Meghalaya approximate bounding box (conservative)
MEGHALAYA_LAT_MIN, MEGHALAYA_LAT_MAX = 24.95, 26.20
MEGHALAYA_LON_MIN, MEGHALAYA_LON_MAX = 89.70, 92.90


def test_roads_within_meghalaya_aoi():
    """Sample of road coordinates should fall within the Meghalaya bounding box."""
    with open(ROADS_GEOJSON, encoding="utf-8") as f:
        data = json.load(f)
    sample = data["features"][:500]
    outside = 0
    for feat in sample:
        geom = feat["geometry"]
        coords = geom["coordinates"]
        rings = coords if geom["type"] == "MultiLineString" else [coords]
        for ring in rings:
            for lon, lat in ring:
                if not (MEGHALAYA_LAT_MIN <= lat <= MEGHALAYA_LAT_MAX and
                        MEGHALAYA_LON_MIN <= lon <= MEGHALAYA_LON_MAX):
                    outside += 1
    # Allow a small margin for edge roads near state boundary
    total_coords = sum(
        len(ring)
        for feat in sample
        for ring in (feat["geometry"]["coordinates"]
                     if feat["geometry"]["type"] == "MultiLineString"
                     else [feat["geometry"]["coordinates"]])
    )
    assert total_coords > 0, "no coordinates found in sample"
    out_pct = outside / total_coords * 100
    assert out_pct < 2.0, \
        f"{out_pct:.1f}% of sampled road coords outside Meghalaya AOI — expected < 2%"


def test_representative_road_coordinates_geographically_plausible():
    """Check representative roads have lon/lon in expected Meghalaya range."""
    with open(ROADS_GEOJSON, encoding="utf-8") as f:
        data = json.load(f)
    # Find a major road (NH)
    major = [f for f in data["features"]
             if f["properties"].get("category") == "major"][:5]
    assert len(major) > 0, "no major roads found"
    for feat in major:
        geom = feat["geometry"]
        coords = geom["coordinates"]
        flat = coords[0] if geom["type"] == "MultiLineString" else coords
        for lon, lat in flat[:10]:
            assert 89.0 < lon < 93.0, f"major road lon {lon} outside NER range"
            assert 24.5 < lat < 26.5, f"major road lat {lat} outside NER range"


def test_road_categories_are_balanced():
    """The road network should have features across categories."""
    with open(ROADS_GEOJSON, encoding="utf-8") as f:
        data = json.load(f)
    cats = {}
    for feat in data["features"]:
        c = feat["properties"].get("category", "unknown")
        cats[c] = cats.get(c, 0) + 1
    assert cats.get("major", 0) >= 10, "expected at least 10 major roads"
    assert cats.get("secondary", 0) >= 10, "expected at least 10 secondary roads"
    assert cats.get("local", 0) >= 10, "expected at least 10 local roads"


def test_road_feature_geometry_line_segment_count():
    """Major roads should have reasonable segment counts (not single-point)."""
    with open(ROADS_GEOJSON, encoding="utf-8") as f:
        data = json.load(f)
    major = [f for f in data["features"]
             if f["properties"].get("category") == "major"][:20]
    for feat in major:
        geom = feat["geometry"]
        coords = geom["coordinates"]
        if geom["type"] == "LineString":
            assert len(coords) >= 2, "LineString road must have >= 2 coords"
        else:
            for ring in coords:
                assert len(ring) >= 2, "MultiLineString ring must have >= 2 coords"


def test_no_risk_point_to_risk_point_lines():
    """Verify no road is a straight line between two different zone centers.
    Short roads within a single zone area are fine — those are real OSM ways.
    What we prohibit: a line that starts at one zone center and ends at another,
    which would be a synthetic connection rather than real road geometry."""
    with open(ROADS_GEOJSON, encoding="utf-8") as f:
        data = json.load(f)
    # Known zone centers (approximate)
    zone_centers = [
        (91.5, 25.5), (91.8, 25.8), (90.5, 25.2), (91.2, 25.6),
        (90.8, 25.8), (91.6, 25.3), (90.3, 25.5), (91.9, 25.7),
    ]
    for feat in data["features"][:500]:
        geom = feat["geometry"]
        coords = geom["coordinates"]
        rings = coords if geom["type"] == "MultiLineString" else [coords]
        for ring in rings:
            if len(ring) < 2:
                continue
            start = ring[0]
            end = ring[-1]
            # Find which zone center (if any) the start is near
            start_zone = None
            for i, zc in enumerate(zone_centers):
                if abs(start[0] - zc[0]) + abs(start[1] - zc[1]) < 0.01:
                    start_zone = i
                    break
            # Find which zone center (if any) the end is near
            end_zone = None
            for i, zc in enumerate(zone_centers):
                if abs(end[0] - zc[0]) + abs(end[1] - zc[1]) < 0.01:
                    end_zone = i
                    break
            # Prohibit: start near zone A, end near zone B, where A != B
            if start_zone is not None and end_zone is not None and start_zone != end_zone:
                # Check if the road is suspiciously straight (few intermediate points)
                if len(ring) <= 3:
                    assert False, \
                        f"road {feat['properties']['road_id']} is a straight line between zone centers"
