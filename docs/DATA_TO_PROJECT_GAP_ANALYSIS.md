# GEO-SENTINEL DATA-TO-PROJECT GAP ANALYSIS

**Status:** AUDIT ONLY. No code, datasets, models, registry, or config touched. `ner_v1` and `seq_real_v2` intact. No Redis. No downloads.
**Method:** read-only code/DB/doc inspection + recomputation from `datasets/` and `backened/data/`. Documentation was never treated as integration — every "used" claim below cites the loading code path. Inference is labeled INFERENCE; gaps in evidence are UNKNOWN.

## 1. Executive Summary

- **Required data we already have:** GSI spatial inventory (865, used), Open-Meteo archive rainfall caches per event (used for all ML rain features), OpenTopodata SRTM point windows (used for terrain), ASF Sentinel-1 metadata (used, metadata-only), Overpass OSM counts + seeded exposure registry (partially used), and the full `datasets/` holding (11 files — **entirely unused**, most of it valuable).
- **Actually being used:** backend `data/raw` + `data/processed` artifacts and live-ish APIs (Open-Meteo archive/forecast code paths exist; default runtime is MOCK). Nothing under `datasets/` is referenced by any script, loader, API, or worker (verified by repo-wide grep — zero hits).
- **Currently unused but valuable:** Reports dated-NER subset (label path), 3 rainfall files (gauge features), 3 SRTM tiles (raster terrain), soil polygons (static soil features), PBF (offline roads), NWIC boundaries (GIS).
- **Biggest bottleneck:** validated dated positives. Today: 10, all demo-seed (not independently validated real events). Upper-bound candidate pool from `datasets/`: **243 NER / 9 Meghalaya** (computed §4, pre-verification).
- **Must collect next:** almost nothing new — verify and clean what we hold (per-row source verification, rainfall QC, soil coding, bounded PBF import, 3 rim SRTM tiles). First genuine external collection: field/media verification of weak-location rows + NRSC hand-extraction (pipeline already ready).
- **Can be postponed:** SAR imagery processing, physical sensors, SMAP credentials, IMD API key, census population, production alerting credentials.

## 2. Current Dataset Usage Matrix

| Dataset | Present? | Actually Used? | Used Where? | ML Feature? | ML Label? | GIS? | Validation? | Runtime? | Quality | Provenance | Leakage Risk | Action |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| `datasets/Landslide Reports.csv` | YES | NO (zero code refs) | — | NO | NO (candidates only) | NO | NO | NO | MIXED (accuracy varies) | NASA COOLR/GLC family, verifiable in-file | MEDIUM (§4) | VALIDATE → USE AS LABEL (dated NER subset, ner_v2 only) |
| `datasets/Landslide Events.csv` | YES | NO | — | NO | NO | NO | Reference | NO | REAL but out-of-region | NASA COOLR-style, verifiable | HIGH if misused | REFERENCE ONLY / DO NOT USE for NER labels |
| `datasets/` telemetry hourly rainfall | YES | NO | — | NO | NO | NO | NO | NO | Needs spike/neg QC | UNKNOWN | MEDIUM-HIGH if uncut | CLEAN → USE AS FEATURE |
| `datasets/` manual daily rainfall 2001–18 | YES | NO | — | NO | NO | NO | NO | NO | Needs −999/extreme QC | UNKNOWN | MEDIUM (acquisition-day) | CLEAN → USE AS FEATURE |
| `datasets/` Khliehriat single-site | YES | NO | — | NO | NO | NO | Spot only | NO | Clean, narrow | UNKNOWN | LOW | REFERENCE ONLY |
| `datasets/` SRTM tiles (3) | YES | NO | — | NO | NO | NO | NO | NO | VERIFIED SRTM v3 | USGS SRTM, verified tags | LOW | INTEGRATE (raster windows) |
| `datasets/state_NWIC.GeoJSON` | YES | NO (seed: "no real boundary polygons yet") | — | NO | NO | NO | NO | NO | 36 UT/state polys, EPSG:7755 | SOI via NWIC, in-file | LOW | GIS ONLY (reproject first) |
| `datasets/Meghalaya_Soil.geojson` | YES | NO | — | NO | NO | NO | NO | NO | 24 units, no date/agency | UNKNOWN | LOW | VALIDATE → USE AS FEATURE (coded) + GIS |
| `datasets/meghalaya.pbf` | YES | NO (`osm_ner_report.manual_pbf: null`) | — | NO | NO | NO | NO | NO | Valid PBF, vintage/bbox unverified | UNKNOWN origin | MEDIUM (road vintage) | VALIDATE → USE AS FEATURE + GIS |
| Backend GSI parquet (865) | YES | YES (`ingest_gsi.py` → `gsi_ner.json` → inventory 861 spatial) | `build_features._spatial_ctx`, `/landslides/gsi` | YES (density/dist) | NO (spatial-only, enforced) | YES | YES (control veto) | YES | REAL, CC0 mirror | bharatlas mirror, recorded | LOW | KEEP |
| Open-Meteo archive caches (`ner_rain_*.json`, 30) | YES | YES (`fetch_rainfall.py` → `build_features`) | All rain/soil ML features | YES | NO | NO | YES (cross-check) | Build-time | REAL blend / MODELED soil | open-meteo, per-file meta | LOW (pre-event clip) | KEEP |
| OpenTopodata SRTM points (`ner_dem_*.json`, 30) | YES | YES (`ingest_dem/fetch_dem` → `_terrain`) | Terrain ML features | YES | NO | Partial (cell-grid) | NO | Build-time | REAL 30 m points | opentopodata, tagged | LOW | KEEP (supersede w/ raster where tiled) |
| ASF S1 metadata (`ner_sar_*.json`, 10 events) | YES | YES (`ingest_sentinel1.py` → `_sar`) | SAR metadata features | PARTIAL (mostly NOT_ACQUIRED) | NO | Scene layer | NO | Build-time | REAL metadata | ASF, no key | LOW | KEEP |
| Overpass OSM counts (`osm_zone_*.json`, 8) | YES | PARTIAL (counts cached; `manual_pbf` null; osmnx NOT_INSTALLED) | Exposure distances via seeded registry tables | PARTIAL (static registry) | NO | YES | NO | YES | COUNTS real; registry DEMO | Overpass, logged | LOW | KEEP + NEED MORE DATA (PBF import) |
| Demo seed (10 events, 8 zones) | YES | YES (ner_v1 positives; zone profiles) | Training + all GIS display | YES (tagged demo) | YES — DEMO, blocks promotion | YES | NO | YES | SYNTHETIC, labeled | seed, honest | LOW (labeled) | KEEP (frozen) / DO NOT USE as validation of real skill |
| Citizen reports / sensors tables+APIs | Infra YES, data NO | Infra USED, no physical devices | `/reports`, `/sensors` endpoints, frontend pages | NO | NO | YES (display) | NO | API live, devices NOT_CONFIGURED | N/A | N/A | LOW | KEEP infra; NEED MORE DATA (devices/field data) |

## 3. Project Requirement Coverage

| Req | Data needed | Current data available | Current implementation | Quality | Missing | Priority |
|---|---|---|---|---|---|---|
| A. Historical events | Dated NER inventory | 871 (10 demo dated + 861 spatial) + 502 Reports candidates (unused) | `build_inventory.py` + gates | PARTIAL (labels are demo) | Verified real dated positives | REQUIRED (via verification, not new collection) |
| B. Event date/time | Day/hour stamps | Demo ISOs; Reports day-dates (unused) | TEMPORAL/SPATIAL classifier | DEMO live; REAL unused | Verified dates for candidates | REQUIRED |
| C. Lat/lon | Coords | All sources have coords | NER filter + dedup (2 km) | MIXED (≤1 km: 97/477 novel) | QC + field check of weak rows | REQUIRED |
| D. Severity/type | Type/trigger/fatalities | Reports has category/trigger/fatalities (unused); seed has type | Stored, unused in features | UNUSED REAL | Severity-as-label protocol (optional) | OPTIONAL |
| E/F. Pre-event + historical rainfall | Gauge/reanalysis series | OM archive (used) + 3 gauge files (unused) | `fetch_rainfall` + windows | REAL (both) | Gauge QC + vintage pairing | HIGH |
| G. Soil moisture | Observed moisture | NONE observed; ERA5 modeled (used, tagged); sensor API (no devices) | MODELED fallback + SENSOR_* path | PLACEHOLDER | SMAP creds OR field sensors (production) | HIGH (production) / OPTIONAL (demo) |
| H/I. Soil type + drainage | Static soil attrs | Soil polygons (unused) | NONE | UNVERIFIED REAL | Description→code table + source confirm | HIGH |
| J–O. Terrain (elev/slope/aspect/curv/rug/TWI) | DEM | SRTM points (used) + 3 raster tiles (unused) | 8 terrain feats; NO aspect/curvature/TWI yet | REAL, point-limited | Raster pipeline + rim tiles + aspect/curv/TWI | HIGH |
| P/Q/R. Optical / SAR / change detection | Imagery | Metadata only (used); NO imagery anywhere | `ingest_sentinel1`, SATELLITE_DEMO quarantine | METADATA REAL | Imagery pipeline (Copernicus auth + processing) | OPTIONAL (MVP) / HIGH (production) |
| S/T. Roads + distance | Network | OSM counts (partial) + PBF (unused) + 8 demo segments | Registry distances (demo) | DEMO live; REAL unused | Bounded PBF import + vintage tag | HIGH |
| U/V. Villages/population | Exposure | Seeded indicative tables (demo, labeled) | `/risk` exposure readout | DEMO | Census/village polygons (production) | MEDIUM |
| W. Critical infra | Infra registry | Seeded demo table | Emergency pages | DEMO | Authoritative infra list (production) | MEDIUM |
| X. Weather forecast | Forecast API | Open-Meteo forecast adapter (code LIVE-capable, default mock) | `OpenMeteoRainAdapter` (past 7 d + 1 d fcst) | REAL-CAPABLE, default MOCK | Flip RAIN_PROVIDER + verify (no collection) | REQUIRED (config, not data) |
| Y/Z. Sensors + health | Devices | API + tables, zero devices | `sensors.py` full lifecycle | NOT_CONFIGURED | Pilot sensors (production) | OPTIONAL (MVP) |
| AA/AB. Field reports + photos | Citizen data | API + review workflow, no real reports | ReportsPage + media hashes | INFRA READY | Field/citizen collection drive | HIGH (also feeds labels) |
| AC. Emergency routes | Routable graph | Static segments + optimizer (demo) | Route pages | DEMO | PBF-derived graph | MEDIUM |
| AD. Multilingual alerts | Templates | 7 language templates (as/bn/en/garo/hi/kha/mni) | Alert pipeline (Mock providers) | IMPLEMENTED | Real SMS/push creds (production) | MEDIUM |
| AE. Offline sync | Offline-first | Client-ID reports; no full sync protocol verified | Partial | PARTIAL | Sync protocol + cached tiles (production) | MEDIUM |
| AF/AG/AH. Labels / controls / sequences | Validated sets | 10 demo + 20 controls; seq v1/v2 frozen | `build_controls` (defensible) | DEMO-SCALE | 243-candidate verification → ner_v2 | REQUIRED |
| AI. Near-real-time | Live feeds | Scheduler exists (default off), providers mock-default | `scheduler.py` (thread, opt-in) | MOCK default | Enable + monitor (config) | MEDIUM |
| AJ. Explainability | Drivers | drivers_json (XAI module `ml/xai.py`) | Risk APIs return drivers | IMPLEMENTED | Nothing (data-complete) | LOW |
| AK. Provenance | Per-row source | Missingness taxonomy + per-feature provenance JSON | Whole pipeline | IMPLEMENTED | Extend to new sources (same pattern) | REQUIRED (process) |

## 4. ML Dataset Status

**Positive funnel (computed read-only, project 2 km dedup rule):**
`RAW 14,750 → NER 504 → DATED 502 → with coords 502 → NOVEL vs 871-inventory 477 → accuracy ≤5 km 251 → within-file deduped **243**`
Eligible by state: AS 53, NL 52, MN 42, AR 38, SK 24, MZ 19, **ML 9**, TR 6. Strict (≤1 km) subset: 97 NER.
Meghalaya sub-funnel: 38 → novel 17 → eligible 9 (21 overlap existing GSI spatials — expected, not a problem).
**This 243 is an UPPER BOUND:** per-row media-source verification and per-event rainfall-alignment checks are still required; each check can only shrink it. It must never be quoted as "243 validated events."

**Negatives:** `build_controls.py` matched-spatiotemporal (same site, same month-day, non-event year, ±30 d exclusion) — scientifically defensible, scales automatically with new positives. Current 20 controls fit the 10 demo events; ner_v2 re-runs the same script. Status: METHODOLOGY OK, count pending labels.

**Sequences:** `sequences_v1/v2.npz` frozen with seq_real_v2; temporal-model data path proven. New events reuse `fetch_rainfall` + `fetch_satmeta` patterns unchanged.

**Current ML status: BLOCKED. Promotion gate (n≥50 validated dated): FAIL** — today only 10 demo dated positives count as TEMPORAL, and demo cannot satisfy a real-data gate.
**"ML promotion gate is NOT satisfied."**
Path to PASS exists (243 candidates ≥ 50) but requires verification + ner_v2 build + gate re-run. Meghalaya-scoped modeling alone (9 eligible) would NOT pass — NER-scope training with Meghalaya-held-out validation is the defensible design.

## 5. Feature Availability Matrix

| Feature | Data available? | Quality | Integrated? | Needed? | Source |
|---|---|---|---|---|---|
| Rain 1–12h | YES (telemetry file, unused) | Spike QC needed, UNKNOWN prov | NO | YES | Gauge files → ner_v2 |
| Rain 24h–30d/ant/trend/anomaly | YES (manual file + OM archive) | −999 QC needed / REAL | OM YES, gauge NO | YES | Both (gauge primary where near) |
| Soil moisture | NO observed (MODELED used) | Tagged proxy | PARTIAL | Production YES / demo OPTIONAL | SMAP creds or sensors |
| Elevation/slope/ruggedness | YES | REAL points used | YES | YES | Keep; upgrade to raster |
| Aspect/curvature/TWI | NO (seed roadmap) | — | NO | YES | SRTM tiles (free, present) |
| Soil drainage/texture/erosion | YES (polygons, unused) | UNVERIFIED, needs coding | NO | YES | Soil file → coded join |
| Road distance/density | PARTIAL (counts; demo registry) | DEMO live | PARTIAL | YES | PBF import |
| Population/villages/infra | DEMO tables only | Indicative, labeled | YES (display) | Production YES | Census/authoritative lists |
| SAR metadata | YES (10 events) | REAL metadata | YES | Keep | ASF (no key) |
| SAR/optical change | NO imagery | — | NO | OPTIONAL (MVP) | Copernicus (auth) |
| Hist density / nearest slide | YES (GSI) | REAL | YES | YES | Keep; extend w/ verified Reports |
| Forecast rain | Code-ready, mock-default | REAL-capable | NO (config) | YES | RAIN_PROVIDER=openmeteo |

## 6. Live Integration Matrix

| Source | Real? | Runtime status | Credentials | Needed? |
|---|---|---|---|---|
| Open-Meteo forecast+soil (keyless) | YES (capable) | MOCK default → STALE/LIVE only if `RAIN_PROVIDER=openmeteo` | None | YES — flip + verify |
| IMD | Code stub (`RealIMDAdapter`) | NOT_INTEGRATED | `IMD_API_BASE/KEY` empty → AUTH_REQUIRED | OPTIONAL (gauge files + OM cover demo) |
| OpenWeatherMap | Documented only | NOT_INTEGRATED | Key unused | NOT NEEDED (redundant) |
| SMAP L3 | NO | AUTH_REQUIRED, modeled fallback active | `EARTHDATA_*` empty | Production HIGH / demo NOT NEEDED |
| Sentinel-1 imagery | NO (metadata only) | SATELLITE_DEMO quarantined, neutral 0.15 | `COPERNICUS_*` empty | MVP NOT NEEDED / production HIGH |
| Sensors | NO devices (API ready) | NOT_CONFIGURED | N/A | Production MEDIUM |
| SMS (Twilio/MSG91) / Push (FCM) / Email | Providers coded | MOCK default | All keys empty | Production MEDIUM / demo NOT NEEDED |
| Worker/scheduler | Real thread scheduler | OFF default (`SCHEDULER_ENABLED`) | N/A | Enable for demo ops |
| PostGIS | Module present; `app/geo_sentinel.db` SQLite file in repo | SQLite fallback ACTIVE; live PostGIS UNVERIFIED | DB URL | Production MEDIUM |

## 7. MISSING DATA

**CRITICAL** (blocks ner_v2/gate): per-row verification of the 243 candidates (media-source check + ≤5 km confirmation + rain-alignment feasibility) — a task, not a download; rainfall provenance confirmation (WRIS export log/department record).
**HIGH:** rim SRTM tiles (e089/e092/n24, free USGS); soil description→code table + source confirmation; PBF bounds/vintage verification on import; NRSC hand-extracted rows (pipeline slot ready, count 0); citizen/field reports (labels + AA/AB).
**MEDIUM:** census village/population polygons; authoritative infra list; IMD access; scheduler enablement + RAIN_PROVIDER flip verification; offline tile cache.
**LOW:** severity-as-label protocol; aspect/curvature/TWI (derivable, just work).
**NOT NEEDED:** second DEM; second road dataset; `Events.csv` as labels; Landsat/Sentinel-2 processing for MVP; OpenWeatherMap; OSMnx library; physical sensors for MVP; SMAP/Copernicus/SMS creds for demo.

## 8. DATA COLLECTION ROADMAP

**PHASE 1 — Verify what we hold (no new collection, unblocks everything):**
1. Verify 243 candidates (source check, accuracy confirmation, rain-window feasibility) → validated list.
2. Rainfall QC (−999→NaN, spike caps, dry-day policy) + gauge-vs-ERA5 agreement report.
3. Soil code table (drainage/texture/erosion from S01–S24) + point-in-polygon check.
4. PBF bounded import + vintage tag + road-feature recompute; fetch 3 rim SRTM tiles (only download in this phase; free, USGS).
**PHASE 2 — Build ner_v2:** inventory merge (dedup vs 871) → controls re-run → gauge-augmented features → leakage gates → train (LogReg/RF/GBM) → promotion check vs n≥50.
**PHASE 3 — Targeted collection:** field/media re-verification of weak-location rows; NRSC hand extraction; citizen-report drive in 8 zones; rainfall provenance letter.
**PHASE 4 — Production hardening:** SMAP/Copernicus creds + imagery pipeline; pilot sensors; census + infra lists; IMD key; real SMS/push creds; PostGIS cutover; offline tiles.

## 9. MINIMUM VIABLE DATASET

Labels: ≥50 verified dated NER positives (from the 243) + matched controls (auto, ~2/event) + 861 GSI spatials for density/veto. Features: OM archive rain + gauge-augmented windows, SRTM raster terrain (+aspect/curv/TWI), coded soil join, PBF road distances, ASF metadata. GIS: NWIC + zones + soil units. Live: RAIN_PROVIDER=openmeteo verified + scheduler on. That demonstrates full loop: monitor → predict → GIS → alert → prioritize.

## 10. PRODUCTION DATASET

Section 9 + observed soil moisture (SMAP/sensors), S1 imagery change pipeline, census exposure, authoritative infra, IMD redundancy, routable PBF graph, multilingual real-channel alerting, PostGIS, offline tile/sync pack, and a re-verification cadence for inventory drift.

## 11. REDUNDANT / UNNECESSARY DATA

Second DEM; second commercial road dataset; `Landslide Events.csv` for NER; any undated/year-only rows as labels; post-event imagery dates as predictors; raw un-QC gauge extremes; OpenWeatherMap; OSMnx; Landsat/S2 for MVP; synthetic positives/negatives of any kind; anything written into ner_v1/seq_real_v2.

## 12. FINAL ANSWER

### WE ALREADY HAVE
GSI 865 spatial inventory (used); Open-Meteo archive rain caches (used); SRTM point windows (used); ASF S1 metadata (used); OSM counts + exposure tables (partially used); full demo loop (seed, GIS, alerts infra, 7-language templates, XAI drivers, provenance/missingness system).

### WE HAVE BUT NEED TO CLEAN/VALIDATE
Reports 243 candidates (verify); 3 rainfall files (QC + provenance); soil polygons (code + confirm); PBF (bounded import + vintage); 3-tile SRTM set (add rim tiles).

### WE HAVE BUT SHOULD USE ONLY FOR GIS/DISPLAY
NWIC boundaries; soil units as map layer; undated inventory rows; demo zones/segments (labeled).

### WE STILL NEED
Verified dated positives (task, §8-P1); rim SRTM tiles; NRSC rows; field/citizen reports; (production only: SMAP/sensors/S1-imagery/census/infra/IMD/real alert creds/PostGIS).

### WE DO NOT NEED
Second DEM/roads; Events-as-labels; optical/S2 for MVP; OWM; OSMnx; synthetic data; any ner_v1/seq_real_v2 edits.

### BIGGEST BOTTLENECK
Validated dated positives: 10 demo today vs n≥50 gate. The 243-candidate pool is the only legitimate path, and every candidate still needs per-row verification.

### NEXT 5 DATA TASKS
1. Verify the 243 NER candidates (source + location + rain feasibility) → validated list for ner_v2.
2. QC gauge rainfall (−999/spikes/dry-day policy) + gauge-vs-ERA5 agreement; confirm WRIS provenance.
3. Code soil units to drainage/texture/erosion + join check; confirm soil source.
4. Bounded, vintage-tagged PBF import; recompute road features; fetch 3 rim SRTM tiles.
5. Build ner_v2 (labels + controls + gauge features + gates) and re-check n≥50; keep models BLOCKED until PASS.

---

AUDIT STATUS:
READ-ONLY COMPLETE

FILES MODIFIED:
Only docs/DATA_TO_PROJECT_GAP_ANALYSIS.md

DATASETS MODIFIED:
NONE

MODELS RETRAINED:
NONE

ner_v1 MODIFIED:
NO

seq_real_v2 MODIFIED:
NO
