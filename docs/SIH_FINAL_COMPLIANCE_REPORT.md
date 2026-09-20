# GEO-SENTINEL SIH FINAL COMPLIANCE REPORT

> Positioning: GEO-SENTINEL provides an integrated AI-assisted landslide
> risk-advisory and emergency-response platform covering rainfall, terrain,
> soil moisture, historical landslides, GIS exposure analysis, alerts, field
> reporting and operational decision support. Risk outputs are UNCALIBRATED
> RISK SCORES (not probabilities); demo/modeled sources are always labeled.

## 1. Executive Summary

The complete SIH chain is implemented end-to-end: ingestion → validation →
features → AI risk → spatial risk → forecast scenarios → exposure →
prioritization → alerts → multilingual warnings → field reports → offline
sync → routing → monitoring → audit. Real provider paths exist where
credentials allow (Open-Meteo keyless live); credential-gated paths
(IMD/SMAP-observed/Sentinel imagery/Twilio/FCM/SMTP) expose honest
NOT_CONFIGURED/AUTH_REQUIRED states instead of fake success. All ML models
remain DEMO/EXPERIMENTAL under promotion gates (n≥50, F1≥0.60) — the served
risk is labeled accordingly.

## 2. Problem Statement

NER India: landslides, flash floods, road blockages, slope failures from
heavy rainfall, fragile terrain, hill cutting. Required: AI early warning,
rainfall/soil/satellite/terrain/history inputs, high-risk zones, real-time
monitoring, admin/community alerts, GIS, road/village/infra exposure,
weather-linked forecasting, prioritization, geo-tagged field reports,
multilingual + offline, IMD/satellite/sensor integrations, SMS/app warnings,
cloud deployment, sync, explainability, reliability.

## 3. Solution Architecture

Frontend (React/Leaflet + shell-cache SW) → FastAPI (`/api`) → worker
(15-min periodic: ingest → sensor-health → autoeval) → SQLite (demo) /
PostgreSQL+PostGIS (prod profile) → migrations v1–v8. Risk = static RF +
temporal heuristic fused by expert weights + escalation rule, UNCALIBRATED.
Satellite quarantined from risk. Sensors mirror into zone observations with
SENSOR_* source tags.

## 4. Requirement A-X mapping

| Requirement | Implementation | API | Database | Frontend | Test | Evidence | Status |
|---|---|---|---|---|---|---|---|
| Requirement A: AI early warning | RF + heuristic-temporal fusion + Mamba experimental, versioned, gated | GET /api/models, GET /admin/model/metrics, GET /model/reliability | models/registry.json, RiskScore (rf/mamba/fusion versions) | SystemHealthPage versions card, AboutPage honesty | test_pipeline registry/fusion tests | Registry 13 entries, zero promoted | PARTIALLY IMPLEMENTED |
| Requirement B: Rainfall monitoring | MockIMD + OpenMeteoRain (keyless live) + windows 1/3/6/12/24/72h/7d, intensity, antecedent, forecast flag | GET /api/risk/{z}/rainfall, GET /api/risk/{z}/rainfall-windows | rainfall_observations (source/quality) | WeatherForecastPage, rainfall charts | ingestion + windows tests | openmeteo.py:88-143, features.py WINDOWS | IMPLEMENTED + VERIFIED |
| Requirement C: Soil moisture | SMAP mock + OpenMeteo MODELED + SENSOR in-situ ingestion (POST), outlier/dup handling, never modeled-as-observed | POST /api/sensors/soil-moisture, POST /api/sensors/readings, GET /api/sensors | sensors, sensor_readings, soil_moisture_observations | SensorsPage registry + health | test_sih_chain sensors (5) | app/api/sensors.py | IMPLEMENTED + VERIFIED |
| Requirement D: Satellite imagery | Sentinel-1 metadata + demonstrable delta change-detection, quarantined DEMO, credential-gated OBSERVED | GET /api/satellite/status, GET /api/satellite/scenes, POST /api/satellite/change, GET /api/satellite/features/{z} | sat_scenes, satellite_features | SatellitePage boundary card | test_sih_chain satellite (3) | app/api/satellite.py, sim.py:152-157 | DEMO/MOCK |
| Requirement E: Terrain/slope | STATIC profiles + SRTM observed point+grid, slope/aspect/ruggedness/relief + ESTIMATED curvature proxy + resolution metadata | _dem_block in evidence, GET /api/gis/provenance, GET /api/risk/{z}/cell-grid | terrain_dem, zones | TerrainFacts, CellRiskGrid | DEM derive tests | risk.py _dem_block, data/raw/dem*.json | PARTIALLY IMPLEMENTED |
| Requirement F: Historical landslides | Temporal (dated, trainable) vs spatial (display-only) split, provenance per record | GET /api/landslides, GET /api/landslides/gsi, GET /api/landslides/inventory | landslide_events, spatial_inventory | SatellitePage inventory card, EventInventory | inventory test | risk.py landslide_inventory | IMPLEMENTED + VERIFIED |
| Requirement G: High-risk zones | Zone + 9x9 cell grid + hotspots from actual pipeline outputs | GET /api/risk/map, GET /api/risk/{z}/cell-grid, GET /api/risk/hotspots | risk_scores, zone_features | RiskMap heat/polygons, HotspotRankingPanel | e2e + cell-grid tests | sim.run_pipeline | IMPLEMENTED + VERIFIED |
| Requirement H: Near-real-time monitoring | 15-min worker: ingest → sensor-health → autoeval; heartbeat lock; graceful SIGTERM; freshness tiers | GET /api/jobs, GET /api/worker-status | ingestion_runs | DataFreshnessBar, health page | lock/idempotency tests | worker.py, runner.py | IMPLEMENTED + VERIFIED |
| Requirement I: Alert lifecycle | DETECT→EVALUATE→GATE→DEDUP→COOLDOWN→DISPATCH→ESCALATE→ACK→RESOLVE→AUDIT | POST /api/alerts/evaluate, POST /api/alerts/send, POST /api/alerts/{id}/ack|resolve, GET /api/alerts | alerts, audit_logs | AlertConsole, SendButton, AlertLog | cooldown/escalation/idem tests | api/alerts.py, sms.py:261-455 | IMPLEMENTED + VERIFIED |
| Requirement J: GIS decision support | Leaflet 2D (heat, roads, polygons, hotspots, reports, routes); 3D Cesium where present in tree | /api/risk/*, /api/routes/*, /api/exposure/* | zones, roads, villages, infrastructure | RiskMap + intelligence panels | routing e2e | RiskMap.tsx:417-480 | IMPLEMENTED + VERIFIED |
| Requirement K: Roads/villages/infra | 8 road segments + 8 villages + 8 infra (STATIC indicative) + urgency composite + A* lower-exposure routing + baseline compare | GET /api/roads, GET /api/exposure/villages, GET /api/risk/emergency-priorities, GET /api/routes/optimize | road_segments, villages, infrastructure, emergency_tasks | RoadConnectivityPanel, EvacuationRoutePanel, SensorsPage | routing + exposure tests | route_optimizer.py, seed VILLAGES/INFRASTRUCTURE | IMPLEMENTED + VERIFIED |
| Requirement L: Weather-linked forecasting | Dynamic risk + synthetic forecast/what-if with Observed/Forecast/Modeled/Scenario labels | GET /api/risk/{z}/forecast, POST /api/risk/simulation, rainfall-windows forecast_note | rainfall_observations (forecast_days=1 when openmeteo) | WeatherForecastPanel, RainfallScenarioControl | e2e windows check | risk.py:1418-1523 | PARTIALLY IMPLEMENTED |
| Requirement M: Emergency prioritization | urgency=0.40·risk+0.25·pop+0.20·road+0.15·sar, CRITICAL/HIGH/MEDIUM/LOW + reasons + evac status | GET /api/risk/emergency-priorities | zones, roads, villages | EmergencyPrioritiesPanel, EmergencyTasksPanel | priorities reasons test | risk.py:1564-1643 | IMPLEMENTED + VERIFIED |
| Requirement N: Field reporting | GPS+photo/video, MIME+magic+size+sha256 dedup, idempotent sync, moderation chain, GIS markers | POST /api/reports, POST /api/reports/{id}/media, POST /api/reports/{id}/sync, POST /api/admin/moderate/{id} | citizen_reports, media_hashes | ReportModal, PhotoCapture, GpsCapture, ReportList | 409/415/422/201 tests | api/reports.py | IMPLEMENTED + VERIFIED |
| Requirement O: Multilingual | EN/HI served; as/mni drafts UNREVIEWED (fallback EN); never machine-translated; UI EN/AS/MN | GET /api/alerts/languages | alerts/templates/*.json + lang_status.json | TopBar EN/AS/MN selector | i18n fallback test | templates/, translations.ts | PARTIALLY IMPLEMENTED |
| Requirement P: Offline/low-network | IndexedDB queue + retry + SYNCING states + SW shell + critical-GET cache (zones/alerts/tasks, labeled STALE by age) | POST /api/reports/{id}/sync (idempotent) | client_id dedup | useReportQueue, OfflineToggle, sw.js gs-field-v2 | offline queue + sync-state tests (11 frontend) | offline.ts, sw.js | PARTIALLY IMPLEMENTED |
| Requirement Q: IMD/weather API | WeatherProvider switch: mock | openmeteo (live) | imd adapter (needs IMD_API_BASE) | provider_states, /api/data-status | WEATHER_PROVIDER in config | data-status providers_selected | PARTIALLY IMPLEMENTED |
| Requirement R: Satellite integration | Sentinel-1 boundary: config → auth → discovery → metadata → processing-status → feature interface + REAL ASF per-event discovery into sat_scenes | /api/satellite/* | sat_scenes, satellite_features | SatellitePage | status honesty test | providers/sentinel1.py + api/satellite.py + scripts/ingest_sentinel1.py | PARTIALLY IMPLEMENTED |
| Requirement S: Sensor integration | Registry + ingestion + validation + rate-limit + dup/outlier + staleness + health | POST /api/sensors/*, GET /api/sensors, GET /api/sensors/{id}/readings | sensors, sensor_readings | SensorsPage ONLINE/STALE/OFFLINE | 5 sensor tests | api/sensors.py, worker _mark_sensor_health | IMPLEMENTED + VERIFIED |
| Requirement T: SMS/app warnings | Mock SMS/email/push default; Twilio/MSG91 stubs; FCM credential-gated; SMTP if creds; UI says DEMO DELIVERY | delivery block in /api/data-status | alerts (provider/status) | SendButton, AlertLog | delivery-label tests | providers/sms.py, alerts/sms.py, notify/push.py | DEMO/MOCK |
| Requirement U: Cloud/deployment | Compose backend+worker+frontend, prod Postgres/PostGIS profile, non-root, healthchecks, migrate v1–v8, env-driven config | /health, /api/ready, /api/metrics | schema_versions, migrate.py | — | final_verify docker-config | docker-compose.yml, Dockerfiles | PARTIALLY IMPLEMENTED |
| Requirement V: Offline sync | client_id + timestamps + sync_status + retry_count + idempotency keys; dup/conflict/partial-failure handling | POST /api/reports/{id}/sync | citizen_reports.id (client-generated) | queueSize/flushQueue + describeSync | sync + dedup tests | reports.py:126-133,406-441 | IMPLEMENTED + VERIFIED |
| Requirement W: Explainability | WHY per zone: drivers (rain/72h/slope/soil/history/exposure) + model versions + freshness + methodology + UNCALIBRATED label | GET /api/risk/{z}/explanation, GET /api/risk/{z}/evidence | risk_scores.drivers_json | DriverBars, GovernmentIntelligencePanel | XAI tests | ml/xai.py, sim.py:189-205 | IMPLEMENTED + VERIFIED |
| Requirement X: Reliability | Timeout+retry+STALE+last-good everywhere; honest /health /ready /metrics; worker never-crash; DB-down honesty | /health, /api/ready, /api/metrics, /api/data-status, /api/model/monitor | ingestion_runs, audit_logs | DataFreshnessBar, SystemHealthPage | failure-recovery tests (20) | ingest/base.py, runner.py, worker.py | IMPLEMENTED + VERIFIED |

## 5. Data Sources

Rainfall: MockIMD synthetic default; Open-Meteo keyless live opt-in
(precipitation observed blend, 10-min cache, 429/malformed→STALE).
Soil: SMAP mock proxy; Open-Meteo ERA5-Land MODELED (tagged); SENSOR
in-situ via POST (SENSOR_* source). Satellite: mock SAR quarantined +
ASF metadata catalog (no imagery; 403 boundary). Terrain: STATIC seeds +
SRTM 30m observed point+grids. History: 10 demo dated events + 865 GSI
(display/spatial-only). Sensors: new registry (this release).

## 6. AI/ML

Static LogReg F1 0.526 / GBM 0.50 / RF 0.375 (GroupKFold-3, n=24, BLOCKED);
served static rf_2026_01 (n=8, F1-macro 0.2222, DEMO); temporal heuristic
served (F1 0.000/recall 0.000, PR-AUC 0.700); Mamba v03 F1 0.50 / v04 0.444
(recall 1.0), CV 0.489±0.126, LZO recall 1.0 — EXPERIMENTAL, gate BLOCKED.
Stacking REJECTED (F1 0.0). Production confidence UNCALIBRATED mean.
Correct label: AI-assisted risk estimation / experimental forecasting demo.

## 7. GIS

Zones + observed 9×9@250m cell grids + hotspots + trajectory + evidence
bundles; PostGIS-or-haversine backend with identical shapes; urgency
composite + A* lower-exposure routing with baseline compare. Example chain:
Z1 Sohra → HIGH → Z1–Z2 Link BLOCKED → CRITICAL tier + reasons → route vs
baseline. Content is demo seeds — mechanism real, geographies indicative.

## 8. Remote Sensing

Metadata-only Sentinel-1 (10 ASF records) + mock SAR quarantined (neutral
0.15). New: provider-state boundary, scene catalog endpoint, demonstrable
delta change-detection (POST /api/satellite/change, stored MODELED/DEMO).
No imagery pipeline — EXTERNAL DEPENDENCY (credentials).

## 9. Sensors

New: registry + ingestion + validation + health (this release). Soil default
remains modeled proxy; any POSTed in-situ reading overrides the proxy for
its zone with SENSOR_* tags. No physical sensors are claimed.

## 10. Weather

Provider switch WEATHER_PROVIDER=mock|openmeteo|imd. Live = Open-Meteo only
(keyless). IMD adapter exists, needs IMD_API_BASE (EXTERNAL DEPENDENCY).
Forecast horizon = Open-Meteo forecast_days=1 when live, else Scenario.

## 11. Alerts

Full lifecycle VERIFIED in code + tests; delivery MOCK (SMS/email/push
logged only). FCM adapter credential-gated (NOT_CONFIGURED without key).
No storm: cooldown 360m + hourly severity-bucket dedup + escalation-only
resend.

## 12. Emergency Response

Priorities + evac accessibility + tasks + slope-aware routing. Weights are
config (unvalidated) — reasons attached to every priority for audit.

## 13. Field Reports

GPS (accuracy warning >500m) + photo/video (MIME+magic+8/25MB+sha256) +
idempotent sync + geo-match (haversine/PostGIS, "not verification") +
moderation PENDING→VERIFIED→USED_FOR_TRAINING. On-map markers.

## 14. Offline

Field-report scope: IndexedDB queue, auto-flush on online, retry counts,
OFFLINE/SYNCING/SYNCED/FAILED states, SW shell + critical-GET cache. Maps
and API data stay online. Not a full PWA (labeled).

## 15. Multilingual

Alerts EN/HI served; as/mni drafts exist but UNSERVED (pending native
review); UI EN/AS/MN (~70 keys, MN partial). Policy: never machine-translate
safety-critical text.

## 16. Security

Role keys (admin>operator>viewer, 401/403 tested), in-memory 60/min limits,
CORS open-demo labeled, hardening headers + request IDs, SecretBox
(ENC:/FERNET_KEY), upload validation, non-root containers, audit logs. Gaps:
no JWT, CORS *, single-worker limits, SQLite demo default.

## 17. Infrastructure

Compose demo default (mock providers, SATELLITE/MAMBA false) + prod profile
(postgis:16-3.4, pgdata, migrate v1–v9 on boot). Redis explicitly absent by
design. Docker VERIFIED this release: backend image builds, container boots
(migrate v1–v9 incl. seed backfill), /health 200 + all new endpoints 200;
fixed pre-existing non-root sqlite ownership bug (chown /app). Prod Postgres
profile RE-VERIFIED 2026-09-15: PG 16.4 + PostGIS 3.4 live, migrate v1–v9,
geog columns + GIST, API 200s, geo-match `spatial_backend: postgis`
(6.04/10.13/26.68 km) — see POSTGRES_POSTGIS.md re-verification note.
Worker-against-PG long-run + outage re-run remain prior-evidence only.

## 18. Reliability

Retry-3 with backoff, fail→STALE never mock-filled, idempotent stores +
trim, worker heartbeat lock + stale-takeover + never-crash + graceful
SIGTERM, sensor-health aging, /health /ready /metrics /jobs /worker-status /
model/monitor. Failure matrix covered by 20 failure tests.

## 19. Testing

Backend 84 passed + 1 gated live (`pytest -k "not live"`); frontend 11
vitest + tsc clean + vite build ok. New: tests/test_sih_chain.py (15:
sensors 5, satellite 3, inventory/exposure/langs/models/metrics, E2E chain).
Regression gate: scripts/final_verify.py (now incl. sensors+exposure,
satellite-boundary, sih-e2e-chain, sih-coverage).

## 20. Performance

Prior claims (map ~1.4s SQLite, cell-grid ~2s, PG faster) unchanged; new
endpoints are single-query reads (no N+1: sensor list one scan, exposure two
scans). No fresh benchmarks run this release — re-run PERFORMANCE.md
procedure before quoting.

## 21. Limitations

ML n≤32 BLOCKED; risk UNCALIBRATED; default data synthetic/modeled;
satellite metadata-only; delivery MOCK; offline reports-only; EN/HI alerts;
sensors registry empty until POSTed; S3/TLS/JWT/native-app absent; sub-zone
blindness measured; prod Postgres-profile RE-VERIFIED 2026-09-15 (PG 16.4 +
PostGIS 3.4, migrate v1–v9, postgis geo-match live); worker-against-PG
long-run + outage re-run remain prior-evidence only.

## 22. External dependencies

IMD_API_BASE (weather), SMAP/SMAP-observed (soil), COPERNICUS_USER +
SATELLITE_LIVE (imagery), TWILIO/MSG91/SMTP/FCM creds (delivery), real
landslide inventory, DEM raster pipeline, S3/TLS/JWT. All fail honest
(NOT_CONFIGURED/AUTH_REQUIRED/STALE/MOCK).

## 23. Future work

Curated inventory (spatial train/val/test + calibration), IMD/SMAP keys +
field sensors, Sentinel-1 imagery pipeline, Mamba promotion, live delivery
runs, full PWA, prod PG+S3+TLS+JWT+CI, calibrated probabilities.

## 24. Final compliance matrix

See §4 (+ §26 NER addendum). Counts: IMPLEMENTED + VERIFIED: 14 · PARTIALLY IMPLEMENTED: 8 ·
DEMO/MOCK: 2 · EXTERNAL DEPENDENCY: 0 (folded into DEMO/MOCK + PARTIAL) ·
NOT IMPLEMENTED: 0 (sensor gap closed; 3D terrain absent — no Cesium in tree, not claimed).

## 25. Demo workflow

Heavy rain (scrub t→168) → windows react → Z1 HIGH → cells/hotspots →
Z1–Z2 BLOCKED → CRITICAL + reasons → lower-exposure route vs baseline →
evaluate → cooldown blocks dup → escalate → EN/HI mock dispatch → POST
sensor reading (zone soil goes SENSOR) → satellite delta candidate →
field report + photo → geo-match → VERIFIED → ack → resolve → audit trail →
/metrics + data-status + languages + models all honest.

## 26. NER data-pipeline addendum (2026-09-15)

Reproducible NER training pipeline built (`docs/DATA_PIPELINE.md`):
- Inventory: 871 NER (10 demo exact-date TEMPORAL + 861 GSI SPATIAL) with
  NER filter, date classes, dedup, provenance (`ner_inventory`, migration v9).
- REAL per-sample features: Open-Meteo archive rain (30/30), SRTM 5x5 terrain
  (30/30, parity both classes), ASF Sentinel-1 metadata (10/10), Overpass OSM
  roads (8/8 zones). SMAP AUTH_REQUIRED, COOLR egress-FAILED, NRSC manual-only.
- Dataset `ner_v1` (n=30, 10+/20−, splits 15/3/12, checksum-versioned) with
  leakage gates PASS_WITH_PARTIAL (temporal direction + split integrity
  binding-PASS; district overlap disclosed PARTIAL; future-inventory features
  excluded; measurement parity fixed after catching two real biases).
- Models `ner_logreg/rf/gbm` registered EXPERIMENTAL, gate-BLOCKED (honest
  weak: CV-F1 0.28/0.37/0.69, holdout 0.33/0.40/0.33); Mamba skipped on ner_v1
  by documented justification. Served engine unchanged.
- New APIs: `/api/datasets`, `/datasets/{id}`, `/landslides/temporal`,
  `/landslides/spatial`, `/data-quality`, `/models/{id}`,
  `/features/{sample_id}`, `/rainfall/history`, `/soil/history`,
  `/terrain/features`; new `/data` dashboard page (Data & Model Health).
- Requirement deltas: R (satellite) DEMO/MOCK → PARTIALLY IMPLEMENTED (real
  metadata discovery, imagery still AUTH_REQUIRED); F strengthened (exact
  NER inventory + quality report); A/W strengthened (versioned training path
  + per-sample provenance). Counts now: IMPLEMENTED + VERIFIED: 14 ·
  PARTIALLY IMPLEMENTED: 8 · DEMO/MOCK: 2 · NOT IMPLEMENTED: 0.
- Full evidence: `docs/NER_DATASET_FINAL_REPORT.md`, `docs/ML_FINAL_REPORT.md`,
  `scripts/final_dataset_audit.py` (Status: PARTIAL — pipeline complete and
  honest; scale + credentials remain the blockers).
