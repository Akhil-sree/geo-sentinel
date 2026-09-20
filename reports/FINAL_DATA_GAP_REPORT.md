# FINAL_DATA_GAP_REPORT.md — GEO-SENTINEL

## Available and successfully used

- 18 COOLR high-confidence Meghalaya points → RF + Mamba supervision
- 54-row RF table (14 features) → baselines (event-grouped CV)
- 666×73×15 ERA5 sequences → temporal model (chance-level, honestly reported)
- 3 SRTM tiles → terrain features + 600×600 susceptibility grid
- Gauge CSVs (QC-gated) → agreement baselines; OSM PBF → road features;
  soil polygons → categorical codes; boundary → GIS reference

## Available but limited

- 20 lower-confidence COOLR events (held-out pool; 9/20 outside SRTM coverage)
- Hourly gauges 2023–2025 (spike-laden; needs gate, overlaps no labels)
- LULC codes without codebook (opaque categories)
- Jan-2020 ECMWF grids (schema samples, not a feed)

## Missing but important

| Dataset | Why | Model | Resolution | Source | Priority |
|---|---|---|---|---|---|
| Pixel landslide masks | SegFormer has zero supervision | SegFormer | ≤10 m, event-aligned | annotate S2/Landsat for the 18 events | ESSENTIAL for segmentation |
| Valid optical imagery | current patches are constant fill | SegFormer | 10–30 m, pre/post-event | re-download HLS/S2 (no fabricated crops) | ESSENTIAL |
| Sentinel-1 SAR scenes | SAR branch is vapor; soil-moisture proxy only | Mamba/fusion | IW GRD, pre/post pairs | ASF / Copernicus | ESSENTIAL for detection |
| SRTM lon 92–93 tile | 9/20 held-out + E. Jaintia out of coverage | RF/GIS | 30 m (n25_e092, n26_e092) | USGS LP DAAC | ESSENTIAL (free) |
| LULC raster + legend | codes uninterpretable, irreproducible | RF | 30 m NRSC/Bhuvan 2015-16 | NRSC | HIGH |
| Live rain + ERA5 feed | Jan-2020 samples ≠ operations; no refresh/latency | warning | hourly rain, daily ERA5 | IMD + ECMWF open data | HIGH for ops |
| Confirmed negatives | pseudo-absence caps all claims | all | field/GIS verified | GSI/state surveys | HIGH for research |
| Numeric geology | GSI map is a reference JPEG | RF | polygons, Meghalaya | GSI (georeference) | OPTIONAL prototype |
| OSM waterway layer | distance feats exist without the layer | RF | vectors | Geofabrik extract | OPTIONAL |

Priority order for impact: ground-truth quality (masks/negatives) → SAR →
SRTM gap + LULC (cheap) → live feed (ops) → spatial generalization data.
