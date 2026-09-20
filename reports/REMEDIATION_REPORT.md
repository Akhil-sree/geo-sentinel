# REMEDIATION_REPORT.md — GEO-SENTINEL (2026-09-18)

Remediation of the YELLOW prototype state described in `FULL_PROJECT_AUDIT.md`
/ `FINAL_READINESS_REPORT.md` (both 2026-09-18). Every claim below was
executed today; nothing is asserted from code-reading alone.

## Executive Summary

All confirmed P0/P1/P2 engineering issues are fixed and regression-tested.
Backend suite went 105 → **127 passed + 1 skipped** (125 + 2 worker-runtime regressions); frontend 11 → **19
passed**; `tsc` clean; `vite build` ok; live uvicorn boot verified
(`/health`, `/ready`, real `gs_point` over HTTP). Overall moves from YELLOW
to **YELLOW-GREEN: honest demo-ready prototype** — still not production (ML
evidence unchanged by design; Docker runtime unverified — daemon down).

## Before (baseline, reproduced)

- `pytest`: 105 passed, 1 skipped. Frontend vitest: 11 passed.
- `gs_point?lat=999` → 200-with-error; `gs_tabular {}` → 200-with-error;
  `gs_sequence []` → 200-with-error; 5000-step sequence accepted (no cap).
- Compose backend + worker each used private `sqlite:///./geo_sentinel.db`
  (relative, CWD-dependent, no shared volume) — worker writes invisible to API.
- Frontend `GovernmentIntelligencePanel` rendered hash-seeded "AI predicts X%
  probability of slope movement within 6h" with no backend forecast; unguarded
  `.toFixed()` on `risk_score` in 4+ components (backend can return null).
- `torch.load` without `weights_only` in 3 files; `CORS *` default with no
  production guard; open-demo auth with no production guard.
- Traversal-capable reads: `GET /datasets/{version}` → metadata path,
  `_observed_cells(zone_id)` → `data/raw` path.
- `ReportIn.accuracy: str` → `float(str)` 500 on non-numeric input.
- `Pillow/scipy/cryptography` unpinned; frontend gs_* endpoints unconsumed.
- Live `backened/.env` overrode fusion weights 0.5/0.5 vs tested yaml 0.4/0.6.

## After (verified behavior)

- Invalid gs inputs → **422** with structured `{"error", "risk_level":
  "UNKNOWN"}`; missing model artifact → **503**; unknown zone → **404**;
  untrained RF → **503**. No stack traces / paths leak (`str(e)[:200/500]`).
- Compose backend + worker share `sqlite_data:/data` with absolute
  `DATABASE_URL=sqlite:////data/geo_sentinel.db`; local relative sqlite URLs
  resolve against `backened/` independent of CWD (`resolve_database_url`,
  logged at startup). Regression test: worker-session write → API-session read.
- Fabricated panel removed: no "6h probability" text anywhere in the UI;
  temporal shown as **Unavailable** with the validated reason. Null scores
  render as "—"/explicit states, never 0/NaN/crash.
- All `torch.load` use `weights_only=True` (verified: gs folds load, legacy
  wrapper loads, repo-wide grep clean). Production CORS fails closed;
  production auth fails closed (401) without keys; dev/demo workflow unchanged.
- Traversal blocked by filename allowlist + normpath containment + DB-version
  allowlist; regression tests for `../`, absolute, and encoded inputs.
- `ReportIn` bounds coords/strings; `accuracy: float` → non-numeric is 422.
- Deps bounded (`Pillow>=10,<13`, `scipy>=1.11,<1.18`,
  `cryptography>=41,<51`); `python:3.11-slim` keeps minor pin (patch floats for
  security updates); npm `package-lock.json` remains the exact pin.
- gs_* wired to the UI: `GsPointPanel` (real `GET /risk/gs_point`) in the zone
  tab with AVAILABLE/UNAVAILABLE/PROCESSING/ERROR states. OpenAPI `GsOut`
  documents `risk_score`/`temporal_risk` as nullable.
- Map: deterministic heat spread (no `Math.random`), unknown zones skipped
  (no teleport), null-safe popups/tooltips, `Math.round` NaN-proof.
- Fusion-weight drift removed (live `.env` no longer overrides yaml).

## P0 Fixes

1. SQLite split-brain — shared `sqlite_data` volume + absolute compose
   `DATABASE_URL` + CWD-independent `resolve_database_url()` + startup URL log
   + `test_db_shared_persistence.py` (4 tests).

## P1 Fixes

1. Fabricated "AI predicts X% within 6h" + synthetic sparkline removed from
   `GovernmentIntelligencePanel`; replaced with measured risk score +
   explicit temporal-unavailable note. A second fully-hardcoded fabrication
   (`HotspotRankingPanel`: static invented zones/percentages, "Live signal",
   same 6h claim, zero backend connection — missed by the prior audit, found
   by remediation grep) was **deleted**; the backend-driven
   `GovernmentIntelligencePanel` already covers real hotspot ranking.
2. Null safety: `fmtNum/fmtPctOpt/fmtMmOpt/nullState` + `gsDisplayState`;
   applied in AreaRiskPanel, ScoreCards, ZonePolygon, RiskMap, ThreatMarker,
   MapHoverCard, GovernmentIntelligencePanel (+ `gs.test.ts`, 8 tests).
3. `torch.load(weights_only=True)` in `gs_inference.py`, `mamba_model.py`,
   `benchmark_real.py` + repo-wide regression test.
4. CORS: `_cors_origins()` — `*` allowed in dev only, production fails closed.
5. Auth: `guard`/`require_role` fail closed (401) in production without keys.

## P2 Fixes

1. HTTP semantics: gs ValueError→422, OSError→503; cell-grid 404/503;
   `GsOut` response models; OpenAPI nullable contract.
2. Input bounds: gs lat/lon ranges, sequence 1–1000 rows, features ≤128 keys,
   `limit` params ≤2000, `ReportIn` coord/string/accuracy bounds.
3. Path traversal: allowlisted + contained `_read_json_under`, version regex,
   `_observed_cells` zone allowlist.
4. Deps pinned (above); fusion-weight env drift removed.

## Tests Added

- `backened/tests/test_db_shared_persistence.py` — 4 (P0 shared persistence).
- `backened/tests/test_hardening.py` — 16 (422s, 503, CORS, auth,
  traversal, ReportIn, weights_only, known-coordinate GIS).
- `frontend/src/tests/gs.test.ts` — 8 (gsDisplayState, null-safe formatters).
- Updated `test_gs_integration.py` OOR assertion to the corrected 422 contract.

## Tests Passed

- Backend: **127 passed, 1 skipped** (was 105 + 1). Frontend: 19 passed. Full compose runtime verified — see `FINAL_RUNTIME_VERIFICATION.md` (6 more runtime bugs found and fixed there: /data ownership, compose POSTGRES_PASSWORD gate, worker NameError, worker restart exit-loop, unmounted terrain rasters, 12 unguarded components).
- Frontend: **19 passed** (was 11), 5 files.
- `tsc --noEmit`: clean. `vite build`: ok (19.4 s).
- Live uvicorn boot: `/health` 200, `/ready` 200, real `gs_point`
  HIGH 0.6993 `temporal_risk: null` over HTTP.

## Tests Failed

- 0 backend, 0 frontend. (One frontend test initially caught a real NaN gap
  in `gsDisplayState`; fixed the source, not the test.)

## Unverified

- Docker image build/run + compose boot (daemon down: Docker Desktop Linux
  engine unreachable) — compose file statically reviewed only.
- Browser live run (no browser in this environment) — chain verified to the
  HTTP boundary via uvicorn + TestClient; panel states covered by vitest.
- S3/TLS, Postgres long-run worker behavior, live rainfall/satellite feeds.
- Fresh wall-clock perf beyond local: gs_point ~32 ms mean in-process,
  16 concurrent assessments consistent in 3.9 s (LOCAL VERIFIED).

## ML Status

- RF = experimental (CV-strong, held-out recall ~0.45, background-sampling bias
  disclosed; limitations intact, no retraining, no metric optimization).
- Mamba = chance-level / operationally unwired (`temporal_risk: null` on all
  gs outputs; 73→49 strictly-before-event cutoff untouched).
- Fusion = experimental research artifact (label/order fix intact;
  `test_fusion_label_order_invariant` still passes; not served live).
- SegFormer = BLOCKED (no masks; `train_all --segformer` refuses; no fake output).
- Datasets untouched: Mamba tensor re-verified (666, 73, 15) float32 0 NaN/Inf
  today. No leakage protections changed; `test_training_leakage.py` passes.

## Deployment Status

- LOCAL VERIFIED (uvicorn boot + full suites + build).
- DEMO READY (honest scored-advisory prototype; run `ENVIRONMENT=development`,
  set `CORS_ORIGINS` + `ADMIN_API_KEY`/`API_KEYS` when hosting).
- DEPLOYMENT READY: NO — compose runtime not executed (daemon down).
- PRODUCTION READY: NO — ML evidence insufficient by design; see ML Status.

## Files changed (remediation only)

Backend: `app/database.py`, `app/main.py`, `app/config.py`, `app/auth.py`,
`app/api/gs.py`, `app/api/datasets.py`, `app/api/risk.py`, `app/api/reports.py`,
`app/schemas.py`, `app/ml/gs_inference.py`, `app/ml/mamba_model.py`,
`app/ml/benchmark_real.py`, `requirements.txt`, `.env`, `.env.example`,
`tests/test_hardening.py` (new), `tests/test_db_shared_persistence.py` (new),
`tests/test_gs_integration.py` (1 assertion updated to corrected contract).
Frontend: `lib/format.ts`, `api/gs.ts` (new), `components/gs/GsPointPanel.tsx`
(new), `pages/CommandCenter.tsx`, `components/intelligence/
GovernmentIntelligencePanel.tsx`, `components/area/AreaRiskPanel.tsx`,
`components/zone/ScoreCards.tsx`, `components/map/{RiskMap,ZonePolygon,
ThreatMarker,MapHoverCard}.tsx`, `tests/gs.test.ts` (new),
`components/intelligence/HotspotRankingPanel.tsx` (deleted: hardcoded fabrication).
Root: `docker-compose.yml`, `.env.example`, `README.md`.
Note: the working tree already differed from HEAD (126 files) before this
remediation; the list above is the remediation subset only.
