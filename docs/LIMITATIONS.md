# LIMITATIONS (binding — capabilities stop here)

- ML n ≤ 32: all models DEMO/EXPERIMENTAL, gate BLOCKED, risk UNCALIBRATED.
- CV and holdout disagree (published side by side, never averaged).
- Seed init scheme moves CV F1 (0.222 vs 0.489 measured) — standardized on
  per-fold reseed + torch-first imports; residual run variance possible.
- Soil is MODELED reanalysis, never sensors. Satellite is metadata-only
  (imagery 403-gated) + quarantined DEMO path. DEM derivatives are
  zonal/windowed, not full-raster risk. Static RF has no sub-zone
  discrimination (measured on observed cells).
- Alerts are MOCK (no creds). Auth is key-roles (no JWT). Offline is
  field-report scope. i18n reviewed en/hi only. Docker/PG runtime VERIFIED
  2026-09-15 (fresh-boot v1–v6, E2E, outage recovery); S3/TLS still
  unverified. SQLite remains demo storage. Torch DLLs fragile on Windows
  (OSError fallback coded + tested order-sensitivity).
