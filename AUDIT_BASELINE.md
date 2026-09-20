# GEO-SENTINEL AUDIT BASELINE (pre-remediation)

Date: 2026-09-19
Git commit: 7740059 (working tree has pre-existing uncommitted changes vs HEAD)
Environment: Windows 11, Python 3.11.9, Node v24.18.0, Docker 29.6.2
Baseline score: 61/100 (Portability 11, Reliability 8, Fault Tolerance 6,
Reproducibility 7, Scalability 4, Security 7, Observability 3, Testability 7,
Data Pipeline 3, ML 3, GIS/Routing 2)

## Verified test results (this session, pre-fix)

- Backend: 155 passed, 1 skipped / 156 collected (`backened/ pytest`, ~30s)
- Frontend: 43 passed / 8 files (`frontend/ vitest run`)
- TypeScript: `tsc --noEmit` clean
- Frontend build: ok (11.2s; 1 MB chunk-size warning)
- `docker compose config`: parses; daemon reachable (build/up not yet run)
- `scripts/final_verify.py`: 20/20 non-fail (0 FAIL; live-rainfall UNVERIFIED)
- Live smoke (uvicorn :1809x): /health ok; /api/ready ready:true;
  /api/data-status honest DEMO/EXPIRED; gs_point lat=999 -> 422;
  /api/risk/NOPE/evidence -> 200 {"error":"zone not found"};
  rescue (0,0)->(0.001,0.001) -> route_available:true, 0 segments,
  single-point LineString, distance 0.0 (P0 CONFIRMED)

## Confirmed findings to fix

P0-1: out-of-coverage rescue false-positive + degenerate geometry
P0-2: ThreatMarker.tsx:180 dangerouslySetInnerHTML with backend fields
P1-3: 68 silent `.catch(()=>{})` in frontend/src
P1-4: unknown-zone returns 200 error-dict (cell-grid=404, gs=422/503 are OK)
P1-5: RF `_to_features` (rf_model.py:48-68) has no NaN/Inf/range checks
P1-6: frontend/.env.example empty; baseURL fixed to "/api"
P2-7: data/process_gsi.py:26-27 hardcoded C:\ Temp path (+ D:\ strings in
  generated metadata JSONs — artifacts only, code path is the fix target)
P2-8: RiskMap Esri-only tiles, no VITE_TILE_URL, no basemap-failure state
P3-9: 1 MB bundle warning; P3-10: no JSON logs/metrics beyond row counts
Plus: in-memory rate-limit/cooldown, no backup docs, /media public-by-default
undocumented, README test counts stale (132 vs 155; 19 vs 43).

## Remediation rules in force

Root-cause fixes only; regression test per fix; no fabricated claims;
UNVERIFIED stays UNVERIFIED unless actually executed.
