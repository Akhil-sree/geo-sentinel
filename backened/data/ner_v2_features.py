"""ner_v2 feature augmentations: gauge rainfall, SRTM raster terrain, soil
polygons, PBF roads. All functions are pure (artifact in → features out)
so tests never touch the database. Leakage policy: day-precision events use
a conservative prior-day cutoff (nothing from the event calendar day is
used); every value carries provenance; gaps are None + missingness codes.
"""
import csv
import json
import math
import os
import struct

from ner_v2_common import (  # noqa: E402
    DATA_DIR, DATASETS_DIR, PROCESSED_DIR, GAUGE_MISSING,
    HOURLY_SPIKE_MM, DAILY_SPIKE_MM, PROV_GAUGE, PROV_SRTM_RASTER,
    PROV_SOIL_MAP, PROV_ROAD_PBF, ROAD_VINTAGE,
)

# ---------------------------------------------------------------- SRTM raster

TILES = {
    "n25_e090": (90.0, 25.0),
    "n25_e091": (91.0, 25.0),
    "n26_e090": (90.0, 26.0),
}
N = 3601
NODATA = -32767
M_PER_DEG_LAT = 111320.0


def _tile_for(lat: float, lon: float) -> tuple | None:
    for name, (lon0, lat0) in TILES.items():
        if lon0 <= lon < lon0 + 1.0 and lat0 <= lat < lat0 + 1.0:
            return name, lon0, lat0
    return None


def _read_tile(name: str):
    """Read one SRTM tile into a numpy int16 grid (cached). Pure stdlib +
    numpy; no rasterio needed for these uncompressed single-strip tiles."""
    import numpy as np
    cache = _read_tile.__dict__.setdefault("cache", {})
    if name in cache:
        return cache[name]
    path = os.path.join(DATASETS_DIR, f"{name}_1arc_v3.tif")
    with open(path, "rb") as fh:
        data = fh.read()
    ifd = struct.unpack("<I", data[4:8])[0]
    ntags = struct.unpack("<H", data[ifd:ifd + 2])[0]
    offs = None
    off = ifd + 2
    for _ in range(ntags):
        tid, _, cnt, val = struct.unpack("<HHI4s", data[off:off + 12])
        if tid == 273:
            vo = struct.unpack("<I", val)[0]
            offs = struct.unpack("<" + "I" * cnt, data[vo:vo + 4 * cnt])
        off += 12
    rows = []
    for o in offs:
        rows.append(np.frombuffer(data[o:o + 2 * N], dtype="<i2").astype(np.float64))
    grid = np.vstack(rows)  # row 0 = north edge
    grid[grid == NODATA] = math.nan
    cache[name] = grid
    return grid


def raster_terrain(lat: float, lon: float, win: int = 5) -> tuple[dict, dict, dict]:
    """Elevation/slope/aspect/curvature/ruggedness/relief from the SRTM
    raster where covered. TWI is deliberately NOT computed: it needs
    catchment-scale flow routing, which a 5x5 window cannot provide
    (recorded DATA GAP, not a silent proxy)."""
    import numpy as np
    hit = _tile_for(lat, lon)
    if hit is None:
        miss = {k: "OUT_OF_COVERAGE" for k in
                ("r_elevation_mean", "r_elevation_min", "r_elevation_max",
                 "r_elevation_range", "r_slope_mean", "r_aspect_mean",
                 "r_curvature", "r_ruggedness", "r_relief")}
        return ({k: None for k in miss}, {k: PROV_SRTM_RASTER for k in miss}, miss)
    name, lon0, lat0 = hit
    grid = _read_tile(name)
    px = (lon - lon0) * (N - 1)
    py = (lat0 + 1.0 - lat) * (N - 1)
    cx, cy = int(round(px)), int(round(py))
    h = win // 2
    x0, x1 = max(1, cx - h), min(N - 2, cx + h)
    y0, y1 = max(1, cy - h), min(N - 2, cy + h)
    w = grid[y0:y1 + 1, x0:x1 + 1]
    if np.isnan(w).all():
        miss = {k: "QUALITY_REJECTED" for k in
                ("r_elevation_mean", "r_elevation_min", "r_elevation_max",
                 "r_elevation_range", "r_slope_mean", "r_aspect_mean",
                 "r_curvature", "r_ruggedness", "r_relief")}
        return ({k: None for k in miss}, {k: PROV_SRTM_RASTER for k in miss}, miss)
    cell_lat_m = M_PER_DEG_LAT / 3600.0
    cell_lon_m = M_PER_DEG_LAT * math.cos(math.radians(lat)) / 3600.0
    # Horn (1981) slope/aspect on the center 3x3
    c = grid[cy - 1:cy + 2, cx - 1:cx + 2]
    if np.isnan(c).any():
        c = np.where(np.isnan(c), np.nanmean(w), c)
    dzdx = ((c[0, 2] + 2 * c[1, 2] + c[2, 2]) - (c[0, 0] + 2 * c[1, 0] + c[2, 0])) / (8 * cell_lon_m)
    dzdy = ((c[2, 0] + 2 * c[2, 1] + c[2, 2]) - (c[0, 0] + 2 * c[0, 1] + c[0, 2])) / (8 * cell_lat_m)
    slope_rad = math.atan(math.hypot(dzdx, dzdy))
    aspect = (math.degrees(math.atan2(dzdx, -dzdy)) + 360.0) % 360.0
    # Zevenbergen–Thorne profile curvature on center cell
    z1, z2, z3 = c[0, 0], c[0, 1], c[0, 2]
    z4, z5, z6 = c[1, 0], c[1, 1], c[1, 2]
    z7, z8, z9 = c[2, 0], c[2, 1], c[2, 2]
    L = (cell_lon_m + cell_lat_m) / 2.0
    D = ((z4 + z6) / 2 - z5) / L ** 2
    E = ((z2 + z8) / 2 - z5) / L ** 2
    F = (-z1 + z3 + z7 - z9) / (4 * L ** 2)
    G = (-z4 + z6) / (2 * L)
    H = (z2 - z8) / (2 * L)
    p, q = G, H
    curv = -2 * (D * (q * q + 1) + E * (p * p + 1) - F * p * q) / max(1e-9, (p * p + q * q + 1) ** 1.5)
    feats = {
        "r_elevation_mean": round(float(np.nanmean(w)), 1),
        "r_elevation_min": round(float(np.nanmin(w)), 1),
        "r_elevation_max": round(float(np.nanmax(w)), 1),
        "r_elevation_range": round(float(np.nanmax(w) - np.nanmin(w)), 1),
        "r_slope_mean": round(math.degrees(slope_rad), 2),
        "r_aspect_mean": round(aspect, 1),
        "r_curvature": round(float(curv), 6),
        "r_ruggedness": round(float(np.nanstd(w)), 2),
        "r_relief": round(float(np.nanmax(w) - np.nanmin(w)), 1),
    }
    return (feats, {k: PROV_SRTM_RASTER for k in feats},
            {"raster_tile": name, "raster_window": win})

# ---------------------------------------------------------------- soil


def load_soil_units() -> list[dict]:
    """Soil polygons + deterministic codes. Codes come ONLY from
    data/processed/soil_codes_v2.json (code_soil_map.py); unmapped units
    stay UNKNOWN here too."""
    polys = json.load(open(os.path.join(DATASETS_DIR, "Meghalaya_Soil.geojson"),
                           encoding="utf-8"))["features"]
    codes_path = os.path.join(PROCESSED_DIR, "soil_codes_v2.json")
    codes = {}
    if os.path.exists(codes_path):
        codes = {c["Soil_ID"]: c for c in
                 json.load(open(codes_path, encoding="utf-8"))["codes"]}
    units = []
    for f in polys:
        sid = (f.get("properties") or {}).get("Soil_ID", "UNKNOWN")
        units.append({"Soil_ID": sid, "geometry": f["geometry"],
                      "codes": codes.get(sid, {"drainage": "UNKNOWN",
                                               "texture": "UNKNOWN",
                                               "erosion": "UNKNOWN",
                                               "taxonomy": "UNKNOWN"})})
    return units


def soil_at(units: list[dict], lat: float, lon: float) -> tuple[dict, dict, dict]:
    from shapely.geometry import Point, shape
    pt = Point(lon, lat)
    for u in units:
        try:
            if shape(u["geometry"]).contains(pt):
                c = u["codes"]
                feats = {"soil_drainage": c.get("drainage", "UNKNOWN"),
                         "soil_texture": c.get("texture", "UNKNOWN"),
                         "soil_erosion": c.get("erosion", "UNKNOWN"),
                         "soil_unit": u["Soil_ID"]}
                return (feats, {k: PROV_SOIL_MAP for k in feats},
                        {"soil_match": u["Soil_ID"]})
        except Exception:
            continue
    feats = {"soil_drainage": "UNKNOWN", "soil_texture": "UNKNOWN",
             "soil_erosion": "UNKNOWN", "soil_unit": "UNKNOWN"}
    return (feats, {k: PROV_SOIL_MAP for k in feats}, {"soil_match": None})

# ---------------------------------------------------------------- roads (PBF)


def load_road_nodes() -> dict:
    """Decoded highway nodes from data/processed/roads_v2.json
    (import_pbf_roads.py). Empty dict when the import has not run."""
    p = os.path.join(PROCESSED_DIR, "roads_v2.json")
    if not os.path.exists(p):
        return {"meta": {"status": "NOT_IMPORTED"}, "nodes": []}
    return json.load(open(p, encoding="utf-8"))


def _road_index(roads: dict, cell: float = 0.02):
    """Coarse grid index over thinned highway nodes (cached). Density uses
    the recorded thinning factor so counts estimate true density."""
    key = ("grid", cell)
    cache = _road_index.__dict__
    if key in cache:
        return cache[key]
    grid: dict = {}
    for n in roads.get("nodes", []):
        k = (round(n["lat"] / cell), round(n["lon"] / cell))
        grid.setdefault(k, []).append(n)
    cache[key] = (grid, cell)
    return grid, cell


def road_features(roads: dict, lat: float, lon: float) -> tuple[dict, dict, dict]:
    nodes = roads.get("nodes", [])
    if not nodes:
        miss = {k: "NOT_AVAILABLE" for k in ("road_dist_km", "road_density_5km")}
        return ({k: None for k in miss}, {k: PROV_ROAD_PBF for k in miss}, miss)
    grid, cell = _road_index(roads)
    ck = (round(lat / cell), round(lon / cell))
    best, cnt = None, 0
    ring = 0
    # expanding-ring search: nearest node + 5 km count without full scans
    while True:
        found = False
        for dx in range(-ring, ring + 1):
            for dy in range(-ring, ring + 1):
                if ring and abs(dx) < ring and abs(dy) < ring:
                    continue
                for n in grid.get((ck[0] + dx, ck[1] + dy), []):
                    d = math.dist((lat, lon), (n["lat"], n["lon"])) * 111.0
                    if best is None or d < best:
                        best = d
                    if d <= 5.0:
                        cnt += 1
                    found = True
        # cell ~2.2 km; stop once the ring exceeds best distance + margin
        if best is not None and (ring + 1) * cell * 111.0 > best + cell * 111.0:
            break
        ring += 1
        if ring > 40 or (ring > 6 and not found and best is not None):
            break
    factor = 1.0
    try:
        factor = float((roads.get("thinning") or {}).get("factor", 1.0))
    except (TypeError, ValueError):
        pass
    feats = {"road_dist_km": round(best, 2) if best is not None else None,
             "road_density_5km": int(round(cnt * factor))}
    prov = {k: PROV_ROAD_PBF for k in feats}
    miss = {"road_data_vintage": ROAD_VINTAGE,
            "road_basis": roads.get("status", "UNKNOWN"),
            "road_thinning_factor": factor}
    return (feats, prov, miss)

# ---------------------------------------------------------------- gauges


def _ok_hourly() -> list[dict]:
    """All QC-passing hourly gauge readings, loaded once (cached)."""
    cache = _ok_hourly.__dict__
    if "vals" in cache:
        return cache["vals"]
    vals = list(_iter_ok_hourly())
    cache["vals"] = vals
    return vals


def _ok_daily() -> list[dict]:
    cache = _ok_daily.__dict__
    if "vals" in cache:
        return cache["vals"]
    vals = list(_iter_ok_daily())
    cache["vals"] = vals
    return vals


def _iter_ok_hourly():
    path = os.path.join(DATASETS_DIR, "rainfall_tel_hr_meghalaya_ml_2021_2025.csv")
    seen = set()
    with open(path, encoding="utf-8-sig", newline="") as fh:
        for r in csv.DictReader(fh):
            try:
                import datetime as _dt
                t = _dt.datetime.strptime(r["Data Acquisition Time"].strip(), "%d-%m-%Y %H:%M")
                v = float(r["Telemetry Hourly Rainfall (mm)"].strip())
                la, lo = float(r["Latitude"]), float(r["Longitude"])
            except (ValueError, AttributeError, KeyError, TypeError):
                continue
            if v in GAUGE_MISSING or v < 0 or v > HOURLY_SPIKE_MM:
                continue
            key = (r["Station"].strip(), t)
            if key in seen:  # duplicate timestamp: first wins, never double-count
                continue
            seen.add(key)
            yield {"station": r["Station"].strip(), "t": t, "v": v, "lat": la, "lon": lo}


def _iter_ok_daily():
    for fname, col in (("rainfall_manual_daily_meghalaya_ml_1991_2020.csv",
                        "Manual Daily Rainfall (mm)"),
                       ("rainfall_manual_daily_meghalaya_ml_2021_2025.csv",
                        "Manual Daily Rainfall (mm)")):
        path = os.path.join(DATASETS_DIR, fname)
        seen = set()
        with open(path, encoding="utf-8-sig", newline="") as fh:
            for r in csv.DictReader(fh):
                try:
                    import datetime as _dt
                    t = _dt.datetime.strptime(r["Data Acquisition Time"].strip(), "%d-%m-%Y %H:%M")
                    v = float(r[col].strip())
                    la, lo = float(r["Latitude"]), float(r["Longitude"])
                except (ValueError, AttributeError, KeyError, TypeError):
                    continue
                if v in GAUGE_MISSING or v < 0 or v > DAILY_SPIKE_MM:
                    continue
                key = (r["Station"].strip(), t)
                if key in seen:
                    continue
                seen.add(key)
                yield {"station": r["Station"].strip(), "t": t, "v": v,
                       "lat": la, "lon": lo, "file": fname}


def gauge_features(lat: float, lon: float, event_day: str,
                   max_dist_km: float = 60.0) -> tuple[dict, dict, dict]:
    """Pre-event gauge features for a DAY-precision event. Leakage rule:
    only measurements strictly before the event calendar day are used
    (conservative prior-day cutoff — same-day 09:00/10:00 acquisitions may
    already contain post-event rain). Returns features + provenance +
    missingness/method notes."""
    import datetime as _dt
    from ner_common import haversine_km
    day = _dt.date.fromisoformat(event_day)
    feats: dict = {}
    prov: dict = {}
    miss: dict = {"gauge_cutoff": "strictly before event calendar day (day-precision events)",
                  "gauge_provenance": PROV_GAUGE}
    # nearest hourly station in span
    hourly = [x for x in _ok_hourly() if x["t"].date() < day]
    if hourly:
        from collections import defaultdict
        by_st: dict = defaultdict(list)
        for x in hourly:
            by_st[x["station"]].append(x)
        cand = [(haversine_km(lat, lon, v[0]["lat"], v[0]["lon"]), st)
                for st, v in by_st.items()]
        dist, st = min(cand, key=lambda t: t[0])
        if dist <= max_dist_km:
            vals = sorted(by_st[st], key=lambda x: x["t"])
            last24 = [x["v"] for x in vals if (day - x["t"].date()).days <= 1]
            last72 = [x["v"] for x in vals if (day - x["t"].date()).days <= 3]
            feats["g_rain_24h"] = round(sum(last24), 2) if last24 else None
            feats["g_rain_72h"] = round(sum(last72), 2) if last72 else None
            feats["g_rain_max1h"] = round(max(last24), 2) if last24 else None
            feats["g_station_dist_km"] = round(dist, 1)
            for k in ("g_rain_24h", "g_rain_72h", "g_rain_max1h", "g_station_dist_km"):
                prov[k] = PROV_GAUGE
            miss["g_station"] = st
            for k in ("g_rain_24h", "g_rain_72h", "g_rain_max1h"):
                if feats[k] is None:
                    miss[k] = "NOT_AVAILABLE"
        else:
            miss.update({k: "OUT_OF_COVERAGE" for k in
                         ("g_rain_24h", "g_rain_72h", "g_rain_max1h")})
    else:
        miss.update({k: "NOT_AVAILABLE" for k in
                     ("g_rain_24h", "g_rain_72h", "g_rain_max1h")})
    # daily antecedent (acquisition day must be < event day)
    daily = [x for x in _ok_daily() if x["t"].date() < day]
    if daily:
        from collections import defaultdict
        by_st2: dict = defaultdict(list)
        for x in daily:
            by_st2[x["station"]].append(x)
        cand2 = [(haversine_km(lat, lon, v[0]["lat"], v[0]["lon"]), st)
                 for st, v in by_st2.items()]
        dist2, st2 = min(cand2, key=lambda t: t[0])
        if dist2 <= max_dist_km:
            vals2 = sorted(by_st2[st2], key=lambda x: x["t"])
            recent = [(day - x["t"].date()).days for x in vals2]
            w7 = [x["v"] for x, d in zip(vals2, recent) if d <= 7]
            w30 = [x["v"] for x, d in zip(vals2, recent) if d <= 30]
            # no readings in window → None (never a fabricated zero)
            feats["g_rain_7d"] = round(sum(w7), 2) if w7 else None
            feats["g_rain_30d"] = round(sum(w30), 2) if w30 else None
            prov["g_rain_7d"] = prov["g_rain_30d"] = PROV_GAUGE
            miss["g_station_daily"] = st2
            if not w7:
                miss["g_rain_7d"] = "NOT_AVAILABLE"
            if not w30:
                miss["g_rain_30d"] = "NOT_AVAILABLE"
        else:
            miss.update({k: "OUT_OF_COVERAGE" for k in ("g_rain_7d", "g_rain_30d")})
    else:
        miss.update({k: "NOT_AVAILABLE" for k in ("g_rain_7d", "g_rain_30d")})
    return feats, prov, miss
