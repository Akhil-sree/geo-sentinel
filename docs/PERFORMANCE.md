# PERFORMANCE (measured 2026-09-15, Windows/SQLite/TestClient, 3 warm runs each)

| Operation | min | mean | Note |
|---|---|---|---|
| GET /api/risk/map t=48 | 1441ms | 1516ms | includes per-zone RiskScore writes; first call slowest |
| GET /api/risk/Z1/evidence | 1791ms | 1854ms | includes full pipeline run (t=168 default) |
| GET /api/risk/Z1/cell-grid (observed) | 1958ms | 2002ms | was ~5600ms; batched RF predict (identical outputs, verified deterministic) + warm pipeline |
| GET /api/risk/emergency-priorities | 1644ms | 1709ms | full pipeline + exposure scoring |
| GET /api/routes/optimize Z1→Z3 | 154ms | 184ms | A* over road network |
| GET /api/data-status | 17ms | 34ms | |
| GET /health | 7ms | 8ms | |

Bottleneck: sim pipeline re-runs + writes history per request (by design
for the demo scrubber). Production path: precompute on worker cadence and
serve cached scores (roadmap — not implemented, not claimed). No numbers
here are estimated; rerun via TestClient timing snippet before citing.
Cell-grid optimization (2026-09-15): per-cell `predict_proba` in a Python
loop → single batched call; outputs byte-identical (deterministic check
across runs + legacy mode smoke-tested).

## LIVE POSTGRES STACK (2026-09-15, real HTTP vs container backend)

| Operation | latency | Note |
|---|---|---|
| GET /api/risk/map t=48 | 736ms | 8 zones, Postgres |
| GET /api/risk/Z1/cell-grid (observed) | 698ms | 49 cells, postgis backend |
| GET /api/risk/Z1/evidence | 581ms | full pipeline on PG |
