# Data source register (Phase 2)

| Source | URL | License | Status | Used for |
|---|---|---|---|---|
| Seed demo inventory (10 events 2022–2024) | in-repo `app/seed.py` | demo synthetic | ACTIVE (SIMULATED) | `events_v2` labels (n=24) |
| Open-Meteo precipitation + soil reanalysis | https://open-meteo.com | CC-BY 4.0 (provider) | LIVE when `RAIN_PROVIDER=openmeteo`, verified 2026-09-14 | features only |
| NASA Global Landslide Catalog export | https://data.nasa.gov/dataset/global-landslide-catalog-export-f07b6 | public, cite Kirschbaum et al. 2010/2015 | ATTEMPTED 2026-09-15, UNRETRIEVABLE from this environment | none yet (roadmap) |
| GSI landslide inventory via bharatlas | https://bharatlas.com/view/gsi_landslide_inventory (parquet mirror) | CC0-1.0 | RETRIEVED 2026-09-15, 30,842 rows | Meghalaya subset (865) → GIS layer + events_v3 spatial features |
| NRSC landslide inventory/hazard zones (Meghalaya) | https://bhuvan-app1.nrsc.gov.in (landslide inventory) | government, terms apply | IDENTIFIED, not bulk-downloadable (PDF/map portal) | roadmap |

## GLC retrieval attempt log (2026-09-15, honest record)

1. Legacy CSV `data.nasa.gov/docs/legacy/..._rows.csv` → TCP connect timeout (WinError 10060).
2. `catalog.data.gov/.../resource/e9aad2b3...` → HTTP 404.
3. Socrata catalog API `api.us.socrata.com` → OK (found `dd9e-wu2v`, `rthp-tcrg`).
4. `data.nasa.gov/resource/dd9e-wu2v.json` → TCP connect timeout from backend host.
5. Same URL via alternate fetch path → 404. `rthp-tcrg` → 404.

Conclusion: GLC bulk data is legitimate and public but not retrievable from
this environment (host-level timeouts). NOT fabricated locally in its place.
Dataset stays n=24; limitation documented. Retry from an environment with
full egress, then run `data/process_events.py`-equivalent for GLC
(spatial filter Meghalaya bbox 24.5–26.5N 89.5–93.0E → zone assignment →
`events_v3`).

## Why more years cannot inflate events_v2

Features are static terrain: same zone in two years has identical X. Adding
earlier years would create identical-feature rows with different labels
(noise, not signal) — or duplicates (forbidden). Real growth requires new
*zones/events with distinct features* (authoritative inventory) or
time-varying features (rainfall history per event — needs dated observed
rainfall, roadmap).
