# SATELLITE (Sentinel-1)

Provider: ASF Search API (public metadata, verified 200, no key) —
`scripts/ingest_sentinel1.py` discovers pre/nearest/post scenes per event
(±60d, IW) into `sat_scenes` + `data/raw/ner_sar_*.json` (10/10 events with
candidates). Stored: scene_id, acquisition_time, orbit, polarization,
processing_status=METADATA_ONLY. Features are acquisition-date metadata, not
magnitudes. Imagery download/processing stays AUTH_REQUIRED (Copernicus
creds) — claimed nowhere. Production risk quarantines SAR to neutral 0.15
(`SATELLITE_LIVE=false` default). Demo `POST /api/satellite/change`
unchanged. Official source: https://dataspace.copernicus.eu.
Known gap: same-orbit pre/post pairs rare in ±60d windows → `sar_same_orbit`
all-missing in ner_v1 (excluded from inputs, honestly).
