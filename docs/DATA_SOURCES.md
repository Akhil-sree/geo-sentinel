# DATA SOURCES (authoritative list with access + license)

Official sources only (no third-party mirrors except where noted):

| Source | URL | Access | License / terms | Machine-readable path |
|---|---|---|---|---|
| NASA COOLR / GLC | https://landslides.nasa.gov | Public API (Socrata `data.nasa.gov/resource/dd9e-wu2v.json`) | NASA open data | `scripts/ingest_coolr.py` (paged); `--manual` official CSV fallback. Status here: FAILED (egress 404) — retry with full egress |
| GSI Bhukosh | https://bhukosh.gsi.gov.in/Bhukosh/Public | Registration + login (no public API — never bypassed) | GSI / NGDR terms | Manual downloads → `data/manual/gsi/`; vendored CC0-1.0 bharatlas mirror already in `data/raw/gsi_meghalaya.parquet` |
| NRSC Landslide Atlas (~80k claimed, never assumed) | https://www.isro.gov.in | Manual (PDFs + Bhuvan viewer) | ISRO terms | `data/manual/nrsc/*.csv` hand-extracted rows; actual imported count recorded (currently 0) |
| Open-Meteo archive (ERA5) | https://open-meteo.com/en/docs/historical-weather-api | Public, keyless | Open-Meteo terms | REAL rainfall history per event (`scripts/fetch_rainfall.py`); soil variable serves nulls → coded missing |
| Open-Meteo forecast | https://open-meteo.com/en/docs | Public, keyless | Open-Meteo terms | Live inference path (`app/providers/openmeteo.py`) |
| NASA Earthdata / SMAP L3 | https://earthdata.nasa.gov | AUTH_REQUIRED (`EARTHDATA_USERNAME/PASSWORD`) | Earthdata terms | `scripts/ingest_smap.py` boundary + `data/manual/smap/` |
| USGS EarthExplorer / SRTM 30m | https://earthexplorer.usgs.gov | Public via OpenTopodata | SRTM public | REAL 5x5 windows (`scripts/ingest_dem.py`); extends `fetch_dem.py` |
| Copernicus Data Space / S-1 | https://dataspace.copernicus.eu | Public metadata (ASF search, no key); imagery AUTH_REQUIRED | Copernicus terms | REAL metadata discovery (`scripts/ingest_sentinel1.py`); no imagery processing |
| Geofabrik India OSM | https://download.geofabrik.de/asia/india.html | Public bulk (GB-scale, not auto-fetched) | ODbL | Manual PBF → `data/manual/osm/`; per-zone counts via Overpass (REAL) |
| OSMnx | https://osmnx.readthedocs.io | Optional library (not installed) | MIT | NetworkX graphs only when installed |
| IMD | https://mausam.imd.gov.in | Key/gated (`IMD_API_KEY`) | IMD terms | Adapter stub (`app/providers/imd.py`) |
| OpenWeatherMap | https://openweathermap.org/api | Key (unused) | OWM terms | Not wired — documented only |

Download policy: public → auto-fetch with retry/backoff/resume; auth →
stop at boundary with exact creds documented; manual → validate + record
provenance. Every run records source/url/timestamp/file/size/checksum/count.
One failed source never crashes the pipeline.
