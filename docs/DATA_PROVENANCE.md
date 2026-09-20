# DATA PROVENANCE

Every observation carries source + quality; every surface shows it.

| Layer | Source | Status | Freshness rule |
|---|---|---|---|
| Rainfall mock | synthetic monsoon (`IMD_MOCK`) | SIMULATED, deterministic seed | snapshot replace per run |
| Rainfall live | Open-Meteo hourly precipitation | LIVE after first OK run (verified 2026-09-14: 1328 rows, ~1.6s/call) | STALE if fetch fails; 10-min cache; 10-day trim |
| Soil mock | rain-derived proxy (`SMAP_MOCK`) | SIMULATED/`MODELED_PROXY`, seeded | snapshot replace |
| Soil live | Open-Meteo ERA5-Land reanalysis | LIVE **MODELED** (`OPENMETEO_MODELED`) — never observed/SMAP | same as rain |
| Satellite | deterministic mock acquisitions | `SATELLITE_DEMO`, quarantined (neutral 0.15 in risk) | scene-status layer; no imagery |
| Terrain | 8 manual zone profiles (seed v1) | STATIC + `/gis/provenance` meta | aspect/curvature: roadmap |
| History | 10 demo events → `events_v2` (24 zone-years) + `seq_real_v1` (24 ERA5 sequences) + `seq_real_v2` (+8 hard peak-rain no-event windows = 32) | STATIC seed + OBSERVED ERA5 rain / MODELED soil, versioned npz+CSV+JSON, dual gates PASS | GLC bulk: attempted, unretrievable here (see `data/metadata/SOURCES.md`) |
| DEM grid | 9×9@250m SRTM cells/zone (648 points, 0 missing) | OBSERVED (`demgrid_*.json`), `/risk/{z}/cell-grid` mode=observed + sub-zone-blindness note | legacy noise mode retained, labeled |
| Satellite scenes | 10 S1 acquisitions via ASF (±15d/event) | OBSERVED metadata (`sat_scenes`), no imagery (403 auth boundary proven), no risk use |

Idempotency: exact (zone, timestamp, source) dedup; mock snapshots replace;
`/jobs` ledger records trims. UI: `DataFreshnessBar` reads `/data-status`
(`is_live` flags) with legacy fallback; SAR widget carries a SIMULATED
PREVIEW banner.
