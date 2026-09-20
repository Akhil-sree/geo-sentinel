# GEO-SENTINEL Datasets Folder Utility Audit

**Scope:** `datasets/` only. READ-ONLY audit. Nothing modified, moved, renamed, deleted, or retrained. Legacy `seq_real_v2` untouched. No Redis added.
**Date:** 2026-09-15 (addendum same day: 2 files added to `datasets/` at ~22:31 — `meghalaya.pbf`, `Meghalaya_Soil.geojson` — audited below). **Method:** direct file reads + header/row inspection + coordinate/date math + TIFF tag parse + GeoJSON regex scan + OSM PBF framing/protobuf walk (read-only). No content fabricated; unverifiable items marked UNKNOWN.

## 1. Executive Summary

`datasets/` contains **11 files, 0 subdirectories, 0 archives** (~208 MB total). All 11 are real data (no synthetic/demo, no model artifacts, no caches):

- **2 global landslide inventories** (NASA COOLR-style `Events` + `Reports` tables). Only `Landslide Reports.csv` covers NER/Meghalaya (504 NER rows by division, 38 Meghalaya, all day-dated). `Landslide Events.csv` has **zero** NER-bbox rows (its 176 India rows are a single-day 2023-07-09 Uttarakhand/Himachal manual inventory).
- **3 Meghalaya rainfall files** (2 manual-daily + 1 telemetry-hourly, ~136k rows combined). Real station data, Meghalaya-only, but provenance is UNVERIFIED (WRIS-like schema, no README/URL in folder), filenames overclaim their date ranges, and each needs sentinel/sensor-spike cleaning.
- **1 India-wide state boundary GeoJSON** (36 features, Survey of India via NWIC, EPSG:7755 — reproject before web use). GIS-only.
- **3 SRTM 1-arcsec v3 tiles** (3601×3601 int16, ~30 m, EPSG:4326, verifiable SRTM metadata). Central Meghalaya covered; west edge / east edge / south strip tiles missing.
- **1 OSM PBF extract (`meghalaya.pbf`, 11.3 MB, valid OSM framing, writer `osmium/1.19.1`, 274 OSMData blobs / ~32.5 MB uncompressed, `highway` tags present, `Meghalaya` name hits present).** Road/network data for offline import; original extract source unverified, OSM data vintage unknown (no bbox/timestamp in header).
- **1 Meghalaya soil-type map (`Meghalaya_Soil.geojson`, 24 MultiPolygon/Polygon units S01–S24, USDA taxonomy + drainage/texture/erosion descriptions, vertex bounds 89.82–92.80E × 25.03–26.12N, area sum 22,451 km² ≈ state area).** Static soil polygons, no CRS field (coords are lon/lat degrees), no date, no agency field → provenance UNKNOWN. Soil TYPE, not soil moisture.

**Headline verdicts:** one file can legitimately grow validated dated positives after QC (`Landslide Reports.csv` NER subset); three rainfall files are features/validation-only after cleaning; SRTM + boundaries are GIS/feature-only; the soil map adds static soil-type features (not moisture); the PBF adds offline road/GIS value after import; `Landslide Events.csv` is reference-only for NER. **Do NOT rebuild `ner_v1`** (immutable, gate-bound); any integration goes through a new versioned build with the standard pipeline gates.

## 2. Dataset Inventory

| File | Type | Size | Rows/Features | Source | Geographic Coverage | Temporal Coverage | Category | Utility | ML Use | Leakage Risk |
|---|---|---|---|---|---|---|---|---|---|---|
| `Landslide Events.csv` | CSV, 24 cols | 27,723,092 B (~26.4 MB), SHA256 `83826B3E…` | 40,154 rows | NASA COOLR-style Events table (verifiable: `Citation`→NASA GSFC, `Method`=Manual, `Imagery Type`=PlanetScope, `Name of Information Source`=International Disasters Charter etc.) | GLOBAL (22 country values); India=176 rows, all Uttarakhand/Himachal; NER bbox=0, Meghalaya bbox=0 | 2023–2024 mostly; day-level `Event Date` (+`Event Time (approximate)` mostly `unknown`/blank); 16 empty dates → EXACT_DATE (day precision) | A (inventory) | ★★ REFERENCE | NOT_SUITABLE_FOR_TRAINING (for NER) | LOW for NER (unused); MEDIUM-HIGH if used naively (`Satellite Imagery Date After Event` is post-event by definition) |
| `Landslide Reports.csv` | CSV, 32 cols | 10,497,833 B (~10 MB), SHA256 `E5948A01…` | 14,750 rows | NASA COOLR/GLC-style Reports table (verifiable: `Imported Event Source Catalog` GLC/SMMML, news+science sources, `Location Accuracy` scheme) | GLOBAL (157 countries); India=1,741; NER-by-division=504 (MN102 AS94 NL91 AR74 SK56 MZ41 ML38 TR8); Meghalaya bbox≈65, division=38 | Day-level `Event Date`; 1,637 empty (11%) → EXACT_DATE for dated rows, NO_DATE for rest | A (inventory) | ★★★★ HIGH VALUE | USEFUL_AFTER_CLEANING (dated NER subset only) | MEDIUM (location uncertainty + media-report bias; LOW once strict pre-event feature cutoff + dedup applied) |
| `rainfall_manual_daily_meghalaya_ml_1991_2020.csv` | CSV, 20 cols | 5,596,227 B (~5.3 MB), SHA256 `22E011EE…` | 35,052 rows, 40 stations | UNVERIFIED — WRIS-like schema (`State/District LGD Code`, `Basin/Tributary`, `Agency`=Meghalaya; probable India-WRIS/Meghalaya WR origin, **cannot verify**, no README/URL) | MEGHALAYA_ONLY (stn lats 22.03–27.23, lons 89.93–92.37; 2 outlier coords are entry errors, see §9) | Filename claims 1991–2020; **actual 2001-01-01–2018-12-31**; daily `Data Acquisition Time` 10:00 → EXACT_DATE (day) | B (rainfall) | ★★★★ HIGH VALUE | USEFUL_FOR_FEATURES_ONLY (+ validation) | LOW with strict pre-event cutoff; MEDIUM if 10:00 acquisition day misaligned to event hour |
| `rainfall_manual_daily_meghalaya_ml_2021_2025.csv` | CSV, 20 cols | 53,344 B, SHA256 `FFB438F5…` | 324 rows, **1 station** (Khliehriat ORG, E. Jaintia Hills) | UNVERIFIED, same WRIS-like schema family | MEGHALAYA_ONLY (single point 25.3572, 92.37) | Filename claims 2021–2025; **actual 2021-04-01–2022-08-31**; daily 09:00 → EXACT_DATE (day) | B | ★★ REFERENCE (single-site) | USEFUL_FOR_FEATURES_ONLY (that site) / AUXILIARY | LOW |
| `rainfall_tel_hr_meghalaya_ml_2021_2025.csv` | CSV, 20 cols | 16,119,614 B (~15.4 MB), SHA256 `CB0365CD…` | 101,196 rows, 30 telemetry/AWS stations | UNVERIFIED, same schema family (`Telemetry Hourly Rainfall (mm)`) | MEGHALAYA_ONLY (lats 25.07–26.06, lons 89.95–92.62) | **Actual 2023-01-01–2025-12-31** (filename range holds); hourly → EXACT_DATE (hour precision) | B | ★★★★ HIGH VALUE | USEFUL_FOR_FEATURES_ONLY (only sub-daily source in folder) | LOW with cutoff; **MEDIUM-HIGH if post-event hours leak in** (file extends to 2025-12-31 — exclude ≥ event time) |
| `state_NWIC.GeoJSON` | GeoJSON FeatureCollection, 36 features | 49,664,202 B (~47.4 MB), SHA256 `2CE4F888…` | 36 state/UT polygons | Survey of India via NWIC (inside properties: `src_agency`="Survey of India (SOI)", `ds_name`=" Administrative Boundary") — VERIFIED in-file | INDIA_WIDE (36 = 28 states + 8 UTs; includes ML/MN/MZ/NL/AR/AS/SK/TR) | NO_DATE (admin boundary snapshot, no timestamp in file) | P (GIS display) | ★★★ SUPPORTING | NOT_SUITABLE_FOR_TRAINING | LOW (static geometry; note CRS) |
| `n25_e090_1arc_v3.tif` | GeoTIFF, 3601×3601 int16, 1 band | 25,964,800 B, SHA256 `34AF4344…` | 12.97M px | USGS SRTM 1-arcsec v3 (VERIFIED: embedded DTED/SRTM tags, WGS84/EGM96 GeoKeys) | Tile 90–91E × 25–26N (W. Meghalaya / Garo + Ri-Bhoi part) | NO_DATE (SRTM Feb-2000 mission; static DEM) | D (DEM/terrain) | ★★★★ HIGH VALUE | USEFUL_FOR_FEATURES_ONLY | LOW (static pre-event terrain) |
| `n25_e091_1arc_v3.tif` | GeoTIFF, same spec | 25,964,800 B, SHA256 `7FB88ECC…` | 12.97M px | USGS SRTM v3, VERIFIED same | Tile 91–92E × 25–26N (central Meghalaya: Khasi Hills) | NO_DATE | D | ★★★★ HIGH VALUE | USEFUL_FOR_FEATURES_ONLY | LOW |
| `n26_e090_1arc_v3.tif` | GeoTIFF, same spec | 25,964,800 B, SHA256 `E2630CCA…` | 12.97M px | USGS SRTM v3, VERIFIED same | Tile 90–91E × 26–27N (N. of Meghalaya into Assam; covers Ri-Bhoi north) | NO_DATE | D | ★★★ SUPPORTING (mostly off-state, buffers northern events) | USEFUL_FOR_FEATURES_ONLY | LOW |
| `meghalaya.pbf` | OSM PBF (protobuf, osmium/1.19.1 writer) | 11,306,427 B, SHA256 `041995C6…` | 274 OSMData blobs (~32.5 MB uncompressed); feature counts NOT enumerated (no osmium tooling; framing walk only) | UNKNOWN origin extract (writer tag is the clip tool, not the source; no URL/manifest; OSM contributors implied, cannot verify vintage) | MEGHALAYA (provisional: filename + 112 `Meghalaya` tag hits; geometric bounds NOT enumerated — verify on import) | NO_DATE, vintage UNKNOWN (no bbox/timestamp in OSMHeader) | H (roads) + P (GIS) | ★★★ SUPPORTING | USEFUL_FOR_FEATURES_ONLY (after import: road distance/density) | MEDIUM (present-day roads vs historical events — see §15) |
| `Meghalaya_Soil.geojson` | GeoJSON FeatureCollection, 24 soil polygons | 3,873,692 B, SHA256 `C87E9ADE…` | 24 features (22 MultiPolygon + 2 Polygon), props: OBJECTID/Soil_ID/Soil_Description/Soil_Taxonomy/Area_sqkm | UNKNOWN (no agency/URL/date in file or folder; USDA-taxonomy survey-unit style, unattributed per audit rules) | MEGHALAYA_ONLY (vertices 89.82–92.80E × 25.03–26.12N; area sum 22,451 km² ≈ state area 22,429 km²) | NO_DATE (static survey snapshot, no timestamp) | F (soils, closest fit) + P + O | ★★★ SUPPORTING | USEFUL_FOR_FEATURES_ONLY (static soil attributes per event) | LOW (static survey surface) |

No archives, PDFs, images, NetCDF, SQLite, or model files exist in `datasets/`. Total files: 11. Total datasets identified: 11 (8 logical datasets: 2 inventories, 1 rainfall family, 1 boundary, 1 DEM set, 1 OSM extract, 1 soil map).

## 3. Critical Datasets

None of the 11 files is plug-and-play CRITICAL for the frozen pipeline (★★★★★ requires directly usable, provenance-clean, gate-passing training data — nothing here meets that without QC). The closest, pending QC, are in §4.

## 4. Potentially Useful Datasets

1. **`Landslide Reports.csv` — dated NER subset (502 dated rows; 38 Meghalaya, all dated).** Only path in this folder to legitimately grow dated positives. Requires: (a) dedup against existing 871 inventory (spatial ≤1 km + date ±1 d + division match), (b) location-accuracy filter (only 1/38 Meghalaya rows is `Known exactly`; decide 1 km vs 5 km cutoff in labeling protocol), (c) media-source verification per row, (d) pre-event-only feature alignment through existing gates. Expected yield is a fraction of 502, not 502.
2. **Telemetry hourly rainfall (101k rows, 30 stns).** Only sub-daily source → enables true 1h/3h/6h/12h pre-event features. Requires spike QC (85 rows >500 mm/hr, max 3849 — cap/flag), −493.5 negatives handling, station mapping to events.
3. **Manual daily rainfall 2001–2018 (35k rows, 40 stns).** Long baseline for 24h/48h/72h/7d antecedent features + ERA5 cross-check. Requires −999→NaN conversion (629 rows), >500 mm/day review (663 rows, max 9990.5 implausible), filename-range correction, 2 bad station coords quarantine.
4. **3 SRTM tiles.** Replace/augment point-sample terrain (current `demgrid_*` 9×9@250m) with real 30 m raster derivatives. Requires rim tiles for full state (see §11/§19).
5. **`Meghalaya_Soil.geojson` — static soil-type join.** 24 survey units with drainage (excessively drained → Aquic/Haplaquepts), texture (fine/coarse-loamy), erosion hazard, stoniness in free-text descriptions + USDA taxonomy codes. Requires parsing descriptions into coded attributes (soil_drainage_class, texture_class, erosion_hazard) + point-in-polygon join per event. Static → no temporal alignment needed.
6. **`meghalaya.pbf` — offline road network.** Requires import (osmium/osmosis → PostGIS per existing OSM pipeline) + coverage verification (bounds check on import) + vintage tagging. Recomputes road_dist_km/road density from full geometry instead of Overpass counts.

## 5. Supporting Datasets

- **`state_NWIC.GeoJSON`** — GIS display + spatial joins (district/state assignment, in-state checks). Reproject EPSG:7755→4326 first. Not training data.
- **Single-station manual file (Khliehriat, 324 rows)** — site-specific validation/reference for E. Jaintia Hills; too narrow for general features.
- **`Landslide Events.csv`** — global reference for methods (manual PlanetScope digitization pattern) and non-NER context; zero NER training value.

## 6. Unsuitable Datasets

- **`Landslide Events.csv` for any NER/Meghalaya ML use:** 0 rows in NER bbox; all 176 India rows are one 2023-07-09 Uttarakhand/Himachal bulk-mapped set. Using it would inject out-of-region positives — violates REAL DATA > SYNTHETIC DATA discipline in the other direction (real data, wrong population). ★ UNSUITABLE for NER training; REFERENCE only.
- **Year-only / undated rows anywhere as temporal labels:** 1,637 undated `Reports` rows + all `Events` Myanmar/Vietnam bulk rows must never become dated positives.
- **`Satellite Imagery Date After Event` as a predictor:** post-event by construction. Metadata-only use (provenance), never a feature.
- **Raw rainfall extremes as-is:** 9990.5 mm/day, 3849 mm/hr, −999.0/−493.5 values are QC failures, not observations. Unsuitable until cleaned.

## 7. Unknown/Unverified Datasets

- **All 3 rainfall files: SOURCE = UNKNOWN (UNVERIFIED).** Schema strongly resembles India-WRIS (LGD codes, basin/tributary columns, ORG/AWS station naming, Meghalaya agency) but there is no README, URL, export manifest, or checksum in `datasets/`, and filenames misstate ranges. Treat as *unverified observed* data: usable for features/validation after QC, but provenance must be confirmed (WRIS portal export log / department letter) before any training-label dependency.
- **`Meghalaya_Soil.geojson`: SOURCE = UNKNOWN.** No agency, URL, survey year, or citation in file or folder. Property schema (Soil_ID S01–S24, USDA Soil_Taxonomy, Area_sqkm) is a standard soil-survey-unit pattern but unattributed per audit rules — do not cite a source. Static polygon geometry is verifiable (bounds + area sum match the state); authorship is not.
- **`meghalaya.pbf`: SOURCE = UNKNOWN (origin extract unverified).** Framing/protobuf walk confirms a well-formed OSM PBF (OsmSchema-V0.6 + DenseNodes, writer `osmium/1.19.1` — that is the clipping tool, not the data source). No bbox/timestamp in OSMHeader, so data vintage is UNKNOWN; Meghalaya coverage is filename + tag-hit evidence only until a bounded import verifies it.

## 8. Landslide Inventory Analysis

- **Exact-date (day-precision) events:** `Events`: 40,138/40,154 dated (all bulk-inventory dates like `29/04/24, 5:30 am` — the `5:30 am` is a load timestamp, treat as DAY precision). `Reports`: 13,113/14,750 dated; NER dated = 502; Meghalaya dated = 38/38. **New candidate dated positives live only here.**
- **Month-level:** none labeled as such; do not infer.
- **Year-only:** none in these two files (year-only records live in the existing backend GSI parquet — 217 YEAR_ONLY — not in `datasets/`).
- **Spatial-only:** 1,637 undated `Reports` rows + 16 undated `Events` rows → GIS density / control-exclusion use only, never labels.
- **Synthetic/demo:** none in `datasets/` (the 10 demo exact-date events live in backend `ner_inventory_v1.json`, not here).
- **Meghalaya location quality (Reports, n=38):** Known exactly 1, within 1 km 10, within 5 km 11, within 10 km 3, within 25 km 4, within 50 km 4, not known 5. A ≤5 km cutoff keeps 22/38; ≤1 km keeps 11/38.
- **Duplicates:** no exact key dupes within either file (unique Event-ID+latlon+date keys); top repeated latlon in Reports is a Colombia cluster (109×), irrelevant to NER. Cross-file/backend dedup is still mandatory (§16).

## 9. Rainfall Analysis

- **Coverage:** manual 2001–2018 (40 stns, daily 10:00), Khliehriat 2021-04–2022-08 (1 stn, daily 09:00), telemetry 2023–2025 (30 stns, hourly). Combined spans 2001–2025 with gaps (2019–2020 daily missing except none; 2022 H2 sparse).
- **Data-quality findings:** −999.0 missing-marker in manual file (629 rows, e.g. Rymphum Seed Farm Jan-2006 run); 663 daily rows >500 mm (max 9990.5 — non-physical, quarantine); 27 hourly negatives (min −493.5); 85 hourly rows >500 mm/hr (max 3849.0 — sensor spikes, e.g. Aradonga 2024-08-22 burst, Rerapara 1029.5). Zero-value rows: 0 in all files (zeros appear absent — confirm whether dry days were omitted vs zero-filled before use as antecedent features).
- **Coordinate errors:** `Umiam Stage I` lat 22.03 (outside Meghalaya — suspect entry), `Williamnagar` lat 27.23 (north of state). Quarantine both stations' coords; values usable only after relocating.
- **Usable features (after QC):** daily → 24h/48h/72h/7d/14d/30d sums, antecedent_7d, intensity, trend, anomaly-vs-climatology; hourly → 1h/3h/6h/12h rolling sums + peak rates. Station assignment: nearest-station with max-distance cap + elevation check; record per-sample station id + distance in provenance (existing `nerfeat_v1` pattern supports this).
- **Not usable:** rainfall as labels; post-event hours; −999 as zeros.

## 10. Soil Moisture Analysis

No soil-moisture dataset exists in `datasets/`. The gap for observed/modelled moisture stands (same as backend: soil 100% NOT_AVAILABLE in ner_v1). NEW: `Meghalaya_Soil.geojson` is a soil-TYPE map, not moisture — it does not fill the moisture gap, but it adds static soil covariates: drainage class (e.g. excessively drained Kandiudults vs Aquic/Haplaquepts valley units), texture (fine vs coarse-loamy), erosion hazard + stoniness from descriptions, USDA taxonomy per unit. These are legitimate static predictors (drainage strongly conditions landslide susceptibility) joinable by point-in-polygon with zero temporal leakage. Requires description→code parsing + provenance confirmation before training use.

## 11. DEM/Terrain Analysis

- **Verified SRTM 1-arcsec v3** (int16, 3601², pixel 1/3600°, scale verified in tags, tiepoints: e090→90E/26N etc., GeoKeys: EPSG 4326 + WGS84 + EGM96 geoid 9102, nodata −32767). Sampled elevations sane (e.g. n25_e091 max ~1916 m; n26_e090 max ~2603 m in Bhutan direction).
- **Coverage vs Meghalaya (24.9–26.15N × 89.8–92.8E):** have e090+e091 @ n25 and e090 @ n26. Missing: e089 (89–90E, west Garo tip), e092 (92–93E, east Jaintia edge to 92.8), n24 row (24–25N, south Garo band). Net: central ~80% of state covered; edges incomplete.
- **Derivable features:** elevation (mean/min/max/range), slope, aspect, curvature, ruggedness/TRI, TWI, distance-to-ridge/channel approximations. This replaces point-sample terrain with true raster windows — strictly complementary to existing `demgrid_*` points.
- **Leakage:** LOW — SRTM is a static year-2000 surface, pre-event for all modern labels by decades.

## 12. Satellite/SAR Analysis

No satellite imagery or SAR products in `datasets/`. The only SAR-adjacent columns are the `Satellite Imagery Date Before/After Event` strings in `Events` — metadata, and the After-date is post-event by definition. No change/deformation feature can be extracted from this folder. Backend SAR status (metadata-only, NOT_ACQUIRED) is unaffected.

## 13. Road/GIS Analysis

- NEW: **`meghalaya.pbf`** is a valid OSM extract (274 OSMData blobs, `highway` tags confirmed present) — the offline counterpart to the existing Overpass-counts path (`scripts/ingest_osm.py` already defines the `data/manual/osm/*.pbf` drop-box; this file belongs there conceptually but lives in `datasets/` — do NOT move it, reference by path). Needs: import with osmium/osmosis, bounds verification, vintage tagging, then road_dist_km / road-density recomputation with full geometry. Leakage note: present-day OSM roads postdate older events — record extract vintage and treat pre-existing-road assumption explicitly (§15).
- No village or infrastructure dataset in `datasets/`. Village/infra distance features keep their current sources.
- `state_NWIC.GeoJSON` (36 features, SOI via NWIC, EPSG:7755 projected metres) is the GIS workhorse here: state masking, Meghalaya clipping, event-in-state checks, map display. Reproject to EPSG:4326 for web/PostGIS-4326 joins; validate geometries on load (large 49.6 MB file — simplify copy for rendering, keep full-res for joins).
- NEW: **`Meghalaya_Soil.geojson`** doubles as a GIS layer (24 soil units, full-state coverage verified by area sum) for map display alongside risk zones.

## 14. Potential ML Features

| Source file | Features actually extractable | Notes |
|---|---|---|
| Telemetry hourly (after spike QC) | rain_1h/3h/6h/12h sums, peak rate, wet-hour count | Only sub-daily source; 2023+ events only |
| Manual daily (after −999→NaN) | rain_24h/48h/72h/7d/14d/30d, antecedent_7d, intensity, trend, anomaly | 2001–2018 events; cross-check vs ERA5 |
| Khliehriat single-site | Same daily set for that site | Validation spot only |
| SRTM tiles | elevation_*, slope_*, aspect, curvature, ruggedness, TWI | Per-event 5×5 or larger windows; record tile IDs |
| NWIC boundaries | in-state flag, district/state id, hist_density denominator area | Join keys, not predictors per se |
| Reports inventory | hist_density_15km, nearest_spatial_km inputs (as backend already does with GSI) | After merge/dedup, spatial-only use |
| Meghalaya soil polygons (after description→code parse + point-in-polygon) | soil_drainage_class, soil_texture_class, soil_erosion_hazard, soil_taxonomy_unit | Static per-event join; no temporal alignment needed |
| meghalaya.pbf (after import + vintage tag) | road_dist_km (recomputed), road_density, road_class | Full-geometry upgrade of existing Overpass-count path |

Soil moisture, SAR, village/infra, and forecast features do not come from this folder.

## 15. Leakage Risks

| Risk | Level | Why |
|---|---|---|
| Post-event satellite date as feature | HIGH | `Satellite Imagery Date After Event` is observed after the landslide by construction |
| Telemetry hours ≥ event time in windows | MEDIUM-HIGH | File runs to 2025-12-31; any rolling sum crossing event hour leaks observed rain |
| Daily 10:00 acquisition vs event hour | MEDIUM | Same-day gauge reading can include post-event rain; use prior-day-10:00 cutoff for intraday events |
| Location-uncertain positives | MEDIUM | 16/38 Meghalaya rows ≥10 km/unknown; mislocated positives corrupt feature alignment silently |
| Media-report selection bias | MEDIUM | Reports favors fatal/newsworthy/accessible slides; negatives from same distribution needed (existing matched-control design handles this — keep it) |
| Bulk-inventory single-day positives (Events India set) | HIGH if used | 176 same-day points are one mapping campaign, not 176 independent triggers |
| SRTM static surface | LOW | Year-2000 DEM predates all candidate labels |
| NWIC boundaries | LOW | Static admin geometry |
| −999/zero handling | MEDIUM | Treating −999 or missing dry-days as 0 fabricates antecedent dryness/wetness |
| Present-day OSM roads vs historical events | MEDIUM | PBF vintage unknown; roads built after an event make road-proximity look predictive — tag vintage, sensitivity-check old events |
| Soil survey units as features | LOW | Static pre-existing surface; no temporal component |
| PBF coverage assumption | MEDIUM | Bounds not enumerated (no osmium tooling here) — a non-Meghalaya clip would silently misjoin; verify bounds on import |

Mitigation is the existing gate chain (provenance → alignment → leakage check → version); nothing here bypasses it.

## 16. Dataset Overlap

- **Reports NER (504) vs backend GSI parquet (865 Meghalaya spatial + 219 year-known):** complementary sources (media/global catalog vs Bhukosh), same geography → dedup required (spatial ≤1 km + temporal ±1 d where both dated; spatial-only GSI rows can only veto controls, never confirm dates). Expected outcome: modest net new dated positives (order tens, not hundreds — Meghalaya ≤38 pre-QC).
- **Rainfall files vs backend Open-Meteo ERA5 features:** complementary (gauge-observed vs reanalysis). Use gauges as primary where station exists + ERA5 as fallback; log per-sample source; cross-validate the two where both cover an event (disagreement analysis is itself a data-quality signal).
- **SRTM tiles vs backend `demgrid_*` 9×9@250m points + `ner_dem_*` per-sample JSONs:** same source family (SRTM 30 m), different extraction. Raster windows supersede point samples for covered events; keep point path for off-tile events until rim tiles arrive.
- **NWIC vs backend zone registry/static GIS:** overlay, not replace — zone polygons stay authoritative for operations; NWIC is the state-mask/reference layer.
- **meghalaya.pbf vs backend OSM path (Overpass counts + empty `data/manual/osm/` drop-box):** same source family (OSM), complementary form (full offline geometry vs API counts). Scientifically appropriate to import: it upgrades road_dist_km from counts to measured distances. Verify bounds + tag vintage on import.
- **Meghalaya soil map vs backend:** no overlap — backend has no soil-type layer (soil features are 100% missing). Complementary by definition; description→code parsing must be versioned and reviewable.
- **No overlap:** SAR imagery, villages, forecast — folder adds nothing there.

## 17. Recommended Dataset Pipeline

```
RAW (datasets/ file, checksum + mtime logged, read-only)
→ VALIDATION (schema, ranges, −999/spike rules, coord sanity, filename-vs-actual-range check)
→ NORMALIZATION (units mm, UTC+5:30→UTC handling, EPSG:7755→4326, day/hour binning)
→ DEDUP (within-file keys, then vs 871-record inventory + GSI parquet)
→ PROVENANCE (per-row source tag; rainfall origin confirmed or stays UNVERIFIED;
               per-sample station/tile ids + distances recorded)
→ FEATURE ALIGNMENT (strict pre-event cutoff: hourly < event time;
                     daily ≤ prior 10:00 acquisition; static DEM/NWIC unrestricted)
→ LEAKAGE CHECK (existing run_leakage_checks.py gates + new rainfall-cutoff assertion)
→ VERSION (new immutable version, e.g. ner_v2 tables; ner_v1 + seq_real_v2 untouched)
→ TRAINING (gates must still PASS; promotion gate n≥50 still applies)
```

## 18. Recommended Next Actions

**MUST USE (after QC, via new version — not in ner_v1):**
- `Reports` dated NER/Meghalaya subset → candidate dated positives through dedup + accuracy filter + source verification.
- Telemetry hourly → 1–12h pre-event features for 2023+ events.
- SRTM 3 tiles → raster terrain windows for covered events.

**SHOULD USE:**
- Manual daily 2001–2018 → antecedent features + ERA5 cross-check.
- NWIC boundaries → state masking, map display, join keys (reprojected).
- Meghalaya soil polygons → coded static soil features (drainage/texture/erosion) + GIS layer.
- meghalaya.pbf → bounded, vintage-tagged import; recompute road distance/density.

**OPTIONAL:**
- Khliehriat single-site file → E. Jaintia Hills validation spot.
- `Events` file → methods reference only.

**DO NOT USE:**
- `Events` India bulk set as NER positives; any undated/year-only row as a temporal label; post-event satellite dates or post-event rainfall hours as predictors; raw −999/spike values; rainfall-derived soil-moisture invention; anything written back into `ner_v1` or `seq_real_v2`.

## 19. Data Gaps

1. Rim SRTM tiles (e089, e092, n24 row) for full Meghalaya + NER-state tiles if scope widens.
2. Rainfall provenance confirmation (WRIS export log/department record) + 2019–2020 daily gap + dry-day zero policy.
3. Soil moisture observed data (soil-TYPE map now present; moisture still missing), SAR imagery (no file here), villages/infra (no file here), forecast archives (no file here).
4. Location-accuracy upgrade for the 16/38 weak Meghalaya rows (field/GIS verification) — biggest lever on converting candidates to validated positives.
5. OSM PBF bounds verification + vintage tagging on import; soil-map source confirmation + description→code table review.

## 20. Final Conclusion

`datasets/` is a real, useful, mid-value holding: it cannot rescue the n=30 scale problem by itself, but it contains the only legitimate dated-positive growth path in reach (tens of NER events after QC, ≤38 in Meghalaya pre-QC), the only sub-daily rainfall in the project, a long daily baseline, verifiable SRTM terrain, an authoritative boundary layer, a full-state soil-type map (static features, not moisture), and an offline OSM road extract. Everything else it tempts (bulk out-of-region positives, post-event predictors, filename-claimed ranges, raw sensor spikes, unversioned road vintage) must stay out of the training path. Integrate through the existing gates into a new version — never by editing history.

---

*Audit artifacts (read-only): row/header scans, SHA256 hashes (§2), TIFF tag dumps (§11), PBF framing walk (275 blobs, osmium/1.19.1 writer, DenseNodes, highway/Meghalaya tag hits), soil-polygon scan (24 units, state-matching bounds + area sum), and backend cross-checks (`ner_inventory_v1.json` n=871 = 644 UNKNOWN + 217 YEAR_ONLY + 10 demo EXACT_DATE; `ner_training_ner_v1.csv` n=30) support every count above. Provenance marked UNKNOWN wherever the folder itself provides no verifiable trail.*
