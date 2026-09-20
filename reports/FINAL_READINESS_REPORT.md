# FINAL_READINESS_REPORT.md — GEO-SENTINEL (2026-09-18, remediated + runtime-verified same day)

## Executive Summary — DEMO READY (not production)

The system works end-to-end as an honest scored-advisory SIH prototype: datasets load, training reproduces,
API serves ML risk with correct `temporal_risk: null` gating, tests pass (**127+1 backend, 19 frontend**,
`tsc` clean, `vite build` ok), and the full compose stack is runtime-verified
(`docker compose build` + `up`, healthy services, 27/27 container API checks,
restart + down/up recovery, shared-DB persistence, browser E2E PASS,
Postgres prod-profile runtime verified). Command-center UI/GIS redesign
landed same day (compact header/nav, amber advisory, data-sources list,
location panel, functional layer control, honest road status markers —
straight-chord fake roads removed). See
`reports/FINAL_RUNTIME_VERIFICATION.md` and
`reports/UI_GIS_REDESIGN_REPORT.md` for the evidence.
It is NOT production and NOT validated early warning. All previously blocking engineering issues are fixed
and regression-tested (P0 shared DB, fabricated AI panel, null crashes, unsafe loads, CORS/auth defaults,
error codes, input bounds, traversal, dep pins); Docker runtime is the remaining verification gap
(daemon down). ML is weak-by-evidence and correctly labeled as such — unchanged by design.

## VERIFIED WORKING (all executed today)

- Backend `/health`, `/api/ready`, `gs_point` (0.6993 HIGH), `gs_tabular` (0.2428 LOW), `gs_sequence` (neutral 0.5, 49 steps), all `temporal_risk: null` — re-verified over live uvicorn HTTP today
- Training `--smoke` reproduces artifacts; `validate_dataset` PASS; leakage PASS_WITH_PARTIAL
- Data integrity re-verified today: tensor (666,73,15) float32 0 NaN/Inf; RF CSV 54 rows {0:36,1:18} 0 NaN 0 dups (per prior audit; datasets untouched)
- 132 passed + 1 skipped backend (incl. 5 road-geometry honesty tests); 24 passed frontend (incl. 5 roads-lib tests); `tsc` clean; `vite build` ok (image builds from source in-Docker)
- gs_* wired to UI (`GsPointPanel`, real API, explicit null states); fabricated AI panel removed; null crashes fixed
- P0 shared DB (compose `sqlite_data` + CWD-independent resolution + regression test); error codes 422/503/404; traversal blocked; `weights_only` everywhere; CORS/auth fail closed in production; deps bounded

## PARTIALLY WORKING

RF (CV-strong, held-out 0.45), Mamba (chance-level, safely unwired), fusion (research-only), API error codes
(200-with-error), frontend (synthetic AI panel, null-crash risk), GIS (visual≠analytical cells), DB (sqlite ok,
compose split-brain), feeds (mock-default honest), deployment (statically sane, runtime unverified).

## FIXED (all re-tested 2026-09-18)

1. ~~Fabricated "AI predicts X% within 6h" panel~~ — removed; temporal shown as Unavailable with reason.
2. ~~Null-crash on `risk_score: null`~~ — null-safe formatters + explicit UI states everywhere.
3. ~~Compose sqlite split-brain~~ — shared `sqlite_data` volume + absolute URL + CWD-independent resolution + regression test.
4. ~~200-with-error quirk~~ — 422/503/404 with structured bodies; OpenAPI `GsOut` nullable contract.
5. ~~Unbounded inputs / unsafe loads / traversal~~ — caps, `weights_only=True` everywhere, allowlisted paths.

## UNVERIFIED (recorded, not claimed)

S3/TLS, multi-user deployment load, live rainfall/satellite feeds.
Browser E2E is now VERIFIED (Playwright/Chromium PASS); Postgres prod runtime
VERIFIED here; container perf measured (gs_point med 12.1 ms, page 23 ms);
Docker VERIFIED (build + up + health + persistence + recovery).

## ML Reality Check

Useful: none for operations. Promising but insufficient: RF static (needs spatial holdout + calibration + larger inventory).
Chance-level: Mamba, HGB. Blocked: SegFormer. Safe to display for demo/research with existing uncalibrated labels;
unsuitable for production or any "early warning" claim. `training_report.md` fusion row (0.6352) is STALE —
current artifact is 0.9176 post label-fix; do not quote the report row.

## Deployment Result

Demo-hostable after setting `CORS_ORIGINS` + `ADMIN_API_KEY`/`API_KEYS` (+ `ENVIRONMENT=production`
fails closed without them). Compose DB sharing fixed; fusion weights reconciled to yaml. Remaining for a
compose E2E stamp: run `docker compose up --build` (daemon was down today) + browser pass.

## Critical Fixes (ordered) — all DONE, see `REMEDIATION_REPORT.md`

1. (P0) Compose DB sharing. 2. (P1) Remove/rewire fabricated AI panel. 3. (P1) Frontend null guards.
4. (P1) `torch.load(weights_only=True)` + CORS + API keys for hosted demo. 5. (P2) 4xx errors, input caps, traversal sanitization, pin deps.
