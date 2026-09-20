#!/usr/bin/env python3
"""Extract real OSM road geometry from meghalaya.pbf → roads.geojson

Reads the project PBF, extracts highway ways with node coordinates,
filters to Meghalaya AOI, validates geometry, and outputs a clean GeoJSON
FeatureCollection with LineString/MultiLineString geometries.

Usage:
    python scripts/extract_roads.py
    python scripts/extract_roads.py --input ../datasets/meghalaya.pbf --output data/processed/roads.geojson
"""
import json
import math
import argparse
import sys
from datetime import datetime, timezone
from pathlib import Path

try:
    import osmium
except ImportError:
    print("ERROR: osmium not installed. Run: pip install osmium", file=sys.stderr)
    sys.exit(1)


# Meghalaya bounding box (matches roads_v2.json bbox_nodes)
AOI_BBOX = {
    "min_lon": 89.8001,
    "min_lat": 25.0,
    "max_lon": 92.85,
    "max_lat": 26.1999,
}

# Road classes to extract (OSM highway tags)
ROAD_CLASSES = {
    "motorway", "trunk", "primary", "secondary", "tertiary",
    "unclassified", "residential", "service", "track",
    "motorway_link", "trunk_link", "primary_link", "secondary_link",
    "tertiary_link", "living_street", "road",
}

# Visualization categories (used by frontend)
ROAD_CATEGORY = {
    "motorway": "major",
    "trunk": "major",
    "primary": "major",
    "secondary": "secondary",
    "tertiary": "secondary",
    "unclassified": "local",
    "residential": "local",
    "service": "minor",
    "track": "minor",
    "motorway_link": "major",
    "trunk_link": "major",
    "primary_link": "major",
    "secondary_link": "secondary",
    "tertiary_link": "secondary",
    "living_street": "local",
    "road": "local",
}

# Simplification: thin points beyond this spacing (degrees)
SIMPLIFY_THRESHOLD = 0.0005  # ~55m


def in_bbox(lon, lat):
    return (AOI_BBOX["min_lon"] <= lon <= AOI_BBOX["max_lon"] and
            AOI_BBOX["min_lat"] <= lat <= AOI_BBOX["max_lat"])


def simplify_linestring(coords, threshold=SIMPLIFY_THRESHOLD):
    """Douglas-Peucker-lite: skip points that are within threshold of a straight line."""
    if len(coords) <= 2:
        return coords
    result = [coords[0]]
    for i in range(1, len(coords) - 1):
        prev, curr, nxt = result[-1], coords[i], coords[i + 1]
        # Check if curr deviates significantly from prev→nxt line
        dx = nxt[0] - prev[0]
        dy = nxt[1] - prev[1]
        if abs(dx) < 1e-12 and abs(dy) < 1e-12:
            continue
        t = max(0, min(1, ((curr[0] - prev[0]) * dx + (curr[1] - prev[1]) * dy) / (dx * dx + dy * dy)))
        proj_x = prev[0] + t * dx
        proj_y = prev[1] + t * dy
        dist = math.sqrt((curr[0] - proj_x) ** 2 + (curr[1] - proj_y) ** 2)
        if dist > threshold:
            result.append(curr)
    result.append(coords[-1])
    return result


class RoadExtractor(osmium.SimpleHandler):
    """Walk PBF nodes and ways to extract road geometry."""

    def __init__(self):
        super().__init__()
        self.nodes = {}  # node_id -> (lon, lat)
        self.ways = []   # list of (way_id, tags, [node_ids])
        self.way_count = 0
        self.filtered_count = 0

    def node(self, n):
        if in_bbox(n.location.lon, n.location.lat):
            self.nodes[n.id] = (n.location.lon, n.location.lat)

    def way(self, w):
        highway = w.tags.get("highway", "")
        if highway not in ROAD_CLASSES:
            return
        self.way_count += 1
        node_ids = [n.ref for n in w.nodes]
        self.ways.append((w.id, dict(w.tags), node_ids))


def extract(input_path, output_path):
    print(f"Reading PBF: {input_path}")
    handler = RoadExtractor()
    handler.apply_file(str(input_path), locations=True)

    print(f"  Nodes in AOI: {len(handler.nodes):,}")
    print(f"  Highway ways found: {handler.way_count:,}")

    features = []
    skipped = 0
    for way_id, tags, node_ids in handler.ways:
        coords = []
        for nid in node_ids:
            if nid in handler.nodes:
                lon, lat = handler.nodes[nid]
                coords.append((lon, lat))

        # Need at least 2 points for a LineString
        if len(coords) < 2:
            skipped += 1
            continue

        # Simplify
        coords = simplify_linestring(coords)
        if len(coords) < 2:
            skipped += 1
            continue

        highway = tags.get("highway", "road")
        category = ROAD_CATEGORY.get(highway, "local")

        feature = {
            "type": "Feature",
            "geometry": {
                "type": "LineString",
                "coordinates": [[round(c, 6) for c in pt] for pt in coords],
            },
            "properties": {
                "road_id": way_id,
                "highway": highway,
                "category": category,
                "name": tags.get("name", ""),
                "ref": tags.get("ref", ""),
                "surface": tags.get("surface", ""),
                "oneway": tags.get("oneway", ""),
                "bridge": tags.get("bridge", ""),
                "tunnel": tags.get("tunnel", ""),
                "maxspeed": tags.get("maxspeed", ""),
                "lanes": tags.get("lanes", ""),
            },
        }
        features.append(feature)

    print(f"  Ways with valid geometry: {len(features):,}")
    print(f"  Ways skipped (insufficient nodes): {skipped:,}")

    # Class statistics
    from collections import Counter
    class_counts = Counter(f["properties"]["highway"] for f in features)
    cat_counts = Counter(f["properties"]["category"] for f in features)
    print(f"  By class: {dict(class_counts.most_common())}")
    print(f"  By category: {dict(cat_counts.most_common())}")

    geojson = {
        "type": "FeatureCollection",
        "features": features,
        "metadata": {
            "source": "meghalaya.pbf",
            "extraction_date": datetime.now(timezone.utc).isoformat(),
            "aoi": AOI_BBOX,
            "crs": "EPSG:4326",
            "total_features": len(features),
            "highway_classes": dict(class_counts),
            "categories": dict(cat_counts),
            "simplification_threshold": SIMPLIFY_THRESHOLD,
            "extraction_method": "osmium-simplehandler",
        },
    }

    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)
    with open(output, "w", encoding="utf-8") as f:
        json.dump(geojson, f, separators=(",", ":"))

    size_kb = output.stat().st_size / 1024
    print(f"\nOutput: {output} ({size_kb:.0f} KB)")
    print(f"Total features: {len(features)}")
    return geojson


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Extract OSM roads from PBF")
    parser.add_argument("--input", default=str(Path(__file__).resolve().parent.parent.parent / "datasets" / "meghalaya.pbf"))
    parser.add_argument("--output", default=str(Path(__file__).resolve().parent.parent / "data" / "processed" / "roads.geojson"))
    args = parser.parse_args()
    extract(args.input, args.output)
