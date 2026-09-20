# DEM PIPELINE (SRTM GL1 30m, OpenTopodata, keyless)

1. `scripts/fetch_dem.py --fetch`: 5×5@30m per centroid → `dem_{zid}.json`.
2. Horn slope/aspect + ruggedness/relief → `TerrainDEM` (migrate v4).
3. `scripts/fetch_demgrid.py`: 9×9@250m per zone (648 pts, 0 missing) →
   `demgrid_{zid}.json`.
4. `/risk/{z}/cell-grid` mode=observed: real per-cell slope/elevation/
   ruggedness through the RF + zone dynamic fusion; sub-zone-blindness
   note published (model limit, not data limit).
5. Deterministic: same grid → same derivatives (tested across 8 zones:
   slopes 0–90°, aspects 0–360°).

Not built: full-raster risk surface, curvature, drainage modeling —
roadmap with the same provenance discipline.
