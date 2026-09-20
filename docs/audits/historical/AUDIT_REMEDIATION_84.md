# AUDIT ITERATION 1 (2026-09-19)

Previous score: 61/100
New score: 84/100
Delta: +23

Portability: 11 -> 13 (+2)
Reliability: 8 -> 13 (+5)
Fault Tolerance: 6 -> 8 (+2)
Reproducibility: 7 -> 9 (+2)
Scalability: 4 -> 6 (+2)
Security: 7 -> 9 (+2)
Observability: 3 -> 5 (+2)
Testability: 7 -> 9 (+2)
Data Pipeline: 3 -> 4 (+1)
ML System: 3 -> 4 (+1)
GIS/Routing: 2 -> 4 (+2)

## Fixed

1. P0 routing false-positive: `ROUTE_MAX_SNAP_DISTANCE_M` (5000m default,
   `app/config.py` + `.env.example`), coverage gate + geometry-integrity
   gate in `road_graph.find_route`, lat/lng 422 bounds on rescue +
   roads/nearest, `tests/test_routing_safety.py` (13 tests). Ocean coords
   now `route_available:false` + OUT_OF_COVERAGE (verified live, incl.
   inside compose).
2. P0 stored XSS: `ThreatMarker` popup reimplemented as React JSX
   (`ThreatPopupContent`); `dangerouslySetInnerHTML` eliminated from src
   (grep-verified); `threatPopup.test.tsx` (5 tests incl. 3 payloads).
3. P1 silent outages: `store/apiStatus.ts` + axios interceptor (network
   error -> offline, 5xx -> degraded, 404 ignored) + global
   `BackendStatusBanner` in `App`; 10 + 3 frontend tests.
4. P1 error contracts: `_require_zone` 404 helper across 11 risk endpoints
   + routes 404s + roads 503s; `tests/test_error_contracts.py` (6 tests).
   All 155 pre-existing backend tests still pass unmodified.
5. P1 RF validation: finite/numeric/range checks in `_to_features`
   (`test_rf_validation.py`, 6 tests); missing model still RuntimeError.
6. P1/P2 config: `VITE_API_BASE_URL` + `VITE_TILE_URL` in client code,
   documented `frontend/.env.example`; `GSI_PARQUET` env replaces
   hardcoded Temp path; `BasemapLayer` with OSM fallback + UNAVAILABLE
   chip (`basemap.test.ts`, 4 tests).
7. Media: traversal/executable/allowlist regression tests
   (`test_media_security.py`, 5 tests); public-read documented as demo
   design in `docs/SECURITY.md` (S3/signed-URL production path noted).
8. Rate limiting: `RateLimitStore` abstraction + spoof-safe
   `resolve_client_ip` (`TRUSTED_PROXIES`); wired into 4 API modules;
   `test_ratelimit_store.py` (6 tests).
9. Observability: `app/observability.py` (JSON logs, request/route/ML/
   provider counters) wired into middleware, rescue, gs, ingest;
   `/api/metrics` extended; `test_observability.py` (5 tests).
10. Backup: `scripts/backup_sqlite.py` (verified backup+integrity) +
    `docs/BACKUP_RECOVERY.md` (RPO/RTO, Postgres procedure, honesty scope).
11. P3 bundle: manualChunks (vendor/leaflet/charts) + lazy page routes;
    no chunk warning; build 5.5s.
12. Docs: README counts de-staled; backend `.env.example` gains
    `ROUTE_MAX_SNAP_DISTANCE_M`, `TRUSTED_PROXIES`; `docs/SECURITY.md`
    documents media/rate-limit/routing/contracts/observability deltas.

## Verified this iteration (executable evidence)

- Backend: 196 passed + 1 skipped (was 155+1; +41 new, 0 modified old)
- Frontend: 62 passed / 12 files (was 43/8); `tsc --noEmit` clean
- Build ok; `final_verify.py` 20/20 (0 FAIL)
- Docker: backend+frontend images build; compose up healthy;
  API smoke (ready/evidence/route-31seg/metrics/404s/ocean-False);
  backend restart recovery; nginx proxy (:5173/api/*) verified;
  Postgres 16.4 + PostGIS 3.4 prod path: migrate v1-v9, seed 8 zones,
  API + write + restart-persistence verified; stack torn down (0 running)
- SQLite backup script executed (backup ok + integrity_check)

## Still failing / residual (honest, mostly declared scope)

1. Per-component empty states still silent (global banner mitigates).
2. Single-process state (cooldown/rate-limit/metrics) — Redis explicitly
   out of scope; abstraction + docs provided instead.
3. Offline maps: declared out (reports queue only).
4. Cloud (AWS/Render/Railway): UNVERIFIED — no account/harness here;
   config is env-portable and compose-verified.
5. Browser E2E: UNVERIFIED — playwright browsers uninstallable in this
   env (`npx playwright install` needs @playwright/test + download);
   nginx-proxy + API + unit/integration layers verified instead.
6. Dataset scale / RF strength (n=24/30, F1-macro 0.22): research scope,
   honestly gated BLOCKED + labeled uncalibrated; leakage PASS_WITH_PARTIAL.

## New regressions

- None. One self-inflicted test flake (media dedup across runs) fixed by
  unique PNG bytes per test run.
