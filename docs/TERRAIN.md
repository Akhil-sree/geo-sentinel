# TERRAIN

Source: SRTM GL1 30m via OpenTopodata (public; extends `fetch_dem.py` /
`fetch_demgrid.py`, which feed the zone cell-grids). Per event/control:
5x5@30m window → elevation mean/min/max/range, slope mean/max/variance
(Horn-style central differences), ruggedness (std) — identical method for
both classes (`scripts/ingest_dem.py`, cached, 429-backoff). Resolution +
window recorded per feature. Seed zone profiles remain the legacy-RF
authority and the STATIC fallback (tagged, never mixed silently). Full-raster
curvature/drainage products remain roadmap. Official source:
https://earthexplorer.usgs.gov.
