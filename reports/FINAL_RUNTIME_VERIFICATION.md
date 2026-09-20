# FINAL_RUNTIME_VERIFICATION.md — GEO-SENTINEL (2026-09-18)

Runtime proof that the existing implementation starts, communicates, fails
gracefully, and survives restart. Nothing was mocked to make this pass; every
number below was executed today. Scientific limitations are unchanged
(RF experimental, Mamba chance-level/unwired, fusion experimental, SegFormer
blocked).

## Environment

- OS: Windows 11 Home Single Language; Python 3.11.9 (`backened/.venv`,
  `pip check` clean; global env has unrelated third-party conflicts only);
  Node v24.18.0, npm 12.0.1; Docker client 29.6.2 + Compose v5.3.1;
  Docker Desktop daemon started during this session (was down).
- No GPU (torch CPU). Ports 8000/5173 free. No system browser — Playwright
  1.63.0 + Chromium installed into an isolated temp venv (project envs
  untouched) → Browser E2E EXECUTED, PASS (see below).

## Startup procedure (verified, twice from clean state)

```bash
docker compose build
docker compose up -d
docker compose ps            # backend healthy, worker up, frontend up
curl /health /api/ready      # 200
```

Backend entrypoint `scripts/migrate.py` (v1–v9) then uvicorn :8000; worker
`python worker.py`; frontend nginx :80→host 5173 with `/api/` + `/media/`
proxied to `http://backend:8000` (service-name networking, verified live).

## Services (final `docker compose ps`)

- sih-backend-1 — Up, **healthy**, 0.0.0.0:8000
- sih-worker-1 — Up (full cycle: ingestion OK, sensors OK, autoeval 8 zones)
- sih-frontend-1 — Up, 0.0.0.0:5173, serves 200, `/api/` proxy live

## Ports

8000 (backend), 5173 (frontend). No collisions detected. Not yet env-parameterized
(acceptable: documented compose defaults; no silent changes made).

## Database

- Compose backend + worker share `sih_sqlite_data:/data` with
  `DATABASE_URL=sqlite:////data/geo_sentinel.db` (both log the identical URL).
- CWD-independence proven from 3 working directories (same absolute file).
- Worker-write → API-read proven twice: locally (regression test) and in
  compose (`/api/worker-status` serves the worker container's ingestion job row).
- Restart persistence proven: pre-restart job row readable after
  `docker compose restart backend worker`.
- Postgres prod profile: VERIFIED HERE (see Postgres section below).

## Models

- gs_terrain + gs_rf (14 features) load in-container; gs_point valid →
  HIGH 0.6993, gs_tabular valid → MODERATE 0.2928, gs_sequence 49×15 → HIGH
  with `temporal_risk: null` everywhere.
- All `torch.load` use `weights_only=True` (gs folds verified loadable as raw
  state dicts; legacy wrapper `{state_dict,seed,dataset}` loads safely; legacy
  dims mismatch the current cell — correctly NOT forced into production).
- Missing-artifact path demonstrated live: before the datasets mount,
  gs_point returned structured 503 MODEL_UNAVAILABLE (no traceback/path leak).

## API (27/27 checks pass against the container, plus valid tabular)

Valid, invalid (lat ±bounds, lon bounds, NaN, empty/oversize/wrong-width/
wrong-type/missing sequence, empty/partial/missing tabular, malformed JSON),
traversal (`../`, encoded), leak-token scan, CORS dev preflight, feed honesty,
model reliability, worker-status. Full list in the verification script output
(summary: FAILURES: none).

## Frontend

- Clean `npm ci` + 19/19 vitest + `tsc` clean + `vite build` ok; image builds
  from source in-Docker (`npm ci` + build) and serves the current bundle.
- Real-API path proven: browser-equivalent `GET :5173/api/risk/gs_point` →
  live model JSON through nginx; `GsPointPanel` calls the same endpoint with
  AVAILABLE/UNAVAILABLE/PROCESSING/ERROR states (vitest-covered).
- Misleading-UI sweep: zero "AI predicts / 6h probability / Live signal"
  strings in src and in the built bundle; vision panel keeps its
  "Not a trained landslide detector" badge; SAR keeps "SIMULATED PREVIEW";
  scenario results show the backend WHAT-IF warning; "(SMAP)" title removed
  (source is modeled/proxy per backend label).
- Null-safety extended to 10 more components this session
  (ObservationIntelligence, WeatherForecast, CriticalSlope, EmergencyPriorities,
  SeveritySummary, WeatherOverview, CellRiskGrid, SoilMoisture, SimulationOverlay,
  EvacuationRoute, RainfallScenario, SARComparison, RiskHeader).

## Docker

- VERIFIED: `config` validates, all 3 images build, `up` healthy, networking
  via service names, shared sqlite volume, datasets read-only mount,
  restart + full down/up recovery, healthchecks green.

## Browser E2E — PASS (Playwright + headless Chromium, 2026-09-18)

- Map container present; 40 interactive shapes; satellite basemap tiles render
  (screenshot verified: popup, legend, DATA STATUS DEMO/SIMULATED chips).
- Zone click → side panel + `GsPointPanel` `data-state="AVAILABLE"`:
  "MODEL ASSESSMENT · SOHRA (CHERRAPUNJI) | Current risk · HIGH | 0.70 |
  Risk score (uncalibrated model output … not a probability) |
  Temporal prediction: unavailable | Temporal model is not currently
  validated for operational prediction."
- Real network call observed: `GET /api/risk/gs_point?lat=25.3&lon=91.7` →
  200 `{"risk_score":0.6993,"risk_level":"HIGH","temporal_risk":null,…}`.
  16/16 observed API calls returned 200 (zones, risk/map, evidence,
  forecast, cell-grid, trajectory, history, rainfall, soil-moisture…).
- Console errors (non-tile): none. Page errors: none.
- Screenshots: `e2e_map.png`, `e2e_zone.png` (temp dir, not committed).

## Security (re-verified live)

- Traversal blocked (404s), error bodies leak-free, CORS dev-open (`*`) with
  production fail-closed proven IN-CONTAINER (`_cors_origins() == []`,
  `guard` → 401 without keys under `ENVIRONMENT=production`).
- `.env`/DB files gitignored; compose/container logs secret-free.
- Auth: dev open-demo preserved; mutating endpoints keep existing key gates.

## Live feeds

- `/api/data-status` = DEMO_MODE; rainfall/soil/satellite all `is_live: false`
  (labeled SIMULATED). Startup never depends on external services (worker
  cycle OK offline). Classification: rainfall MOCK/SIMULATED, soil MODELED
  proxy, satellite DEMO, terrain STATIC+SRTM-observed cells.

## Tests (final, all re-run after every fix)

- Backend: **132 passed, 1 skipped, 0 failed** (127 + 5 road-geometry honesty
  tests; 1 pre-existing test updated to corrected contracts — assertions
  kept, not weakened).
- Frontend: **24 passed, 0 failed** (19 + 5 roads-lib tests); `tsc` clean;
  `vite build` ok.
- Perf: in-process gs_point ~32 ms mean; 16 concurrent consistent in ~3.9 s;
  in-container gs_point med 12.1 ms (n=10, min 7.3 / max 37.4),
  `/health` 8.3 ms, frontend page 23.0 ms. LOCAL + CONTAINER PERFORMANCE
  VERIFIED; multi-user/deployment-load performance UNVERIFIED.

## Postgres prod-profile runtime — VERIFIED HERE (2026-09-18)

- `docker compose --profile prod up -d postgres` → postgis/postgis:16-3.4
  Up healthy (5432 container-internal only, not published to host).
- One-off backend container against it: `scripts/migrate.py` applied v1–v9
  (v6: "postgis enabled, 10 statements" — extension really applied);
  schema version 9; 8 zones seeded (idempotent seed).
- Worker-write → API-read across two sessions: True.
- Restart persistence: after `restart postgres`, 8 zones + postgis ext +
  schema v9 all survive via `sih_pgdata`.
- Caveat found: a stale `sih_pgdata` from 2026-09-15 (unknown password)
  blocked auth — Postgres ignores POSTGRES_PASSWORD on existing data.
  Reset the dev volume and re-verified clean. Operational note: prod
  password rotation requires documented procedure, not just env change.
- Prod container stopped afterwards to restore the default sqlite stack
  (volume kept). Default stack re-verified healthy after.

## Runtime bugs found AND fixed this session

1. **/data volume root-owned** → backend crash-loop + silent worker rollbacks.
   Fix: Dockerfile creates/chowns /data; recreated volume. Verified healthy.
2. **compose required POSTGRES_PASSWORD even without prod profile** (`config`
   failed on clean checkout). Fix: dev default + documented prod requirement.
3. **Worker `_mark_sensor_health` defined after blocking `__main__` loop** →
   every cycle NameError. Fix: moved above guard + regression test.
4. **Worker restart exit-loop** (own pre-restart heartbeat seen as live peer).
   Fix: same-host+same-pid takeover + graceful `_release()` + regression test.
5. **Terrain rasters unmounted in compose** → gs_point 503 in-container.
   Fix: `./datasets:/datasets:ro` for backend+worker; re-verified 200s.
6. **12 components with unguarded `.toFixed()` on API numbers** → fixed with
   null-safe formatters; **"(SMAP)" title** removed (source is modeled).

## Known limitations (unchanged, must be narrated in demo)

- RF experimental (held-out recall ~0.45, background-sampling bias).
- Mamba chance-level, `temporal_risk: null` by design.
- Fusion experimental, not served. SegFormer blocked (no masks).
- Postgres prod runtime, S3/TLS, live feeds: not executed here.
- Ports hardcoded in compose (documented, not yet env-parameterized).

## Unverified items

- S3/TLS; multi-user deployment load; live rainfall/satellite feeds.

## Service-worker staleness fix (2026-09-18, after a blank-white-screen report)

- Symptom: app rendered fine in automation but a real browser showed blank
  white. Root cause: `public/sw.js` cached `/` + `/index.html` cache-first,
  so after a frontend redeploy the old shell referenced deleted hashed
  bundles. Fix: network-first shell navigations, purge old `gs-field-*`
  caches on activate, same-origin-only caching (`gs-field-v3`).
- Verified live: new `sw.js` served, SW-controlled reload renders fully
  (root children, map, no page errors). Field-report offline queue behavior
  unchanged. Users stuck on the old worker recover via one normal reload
  (update installs via byte change) or DevTools → Application → clear site
  data in stubborn cases.

## Exact reproduction commands

```bash
# backend (intended venv, clean requirements)
cd backened && .venv\Scripts\python.exe -m pytest tests/ -q
# frontend (clean install per lockfile)
cd frontend && npm ci && npm test -- --run && npx tsc --noEmit && npm run build
# full stack (Docker Desktop running)
docker compose build && docker compose up -d && docker compose ps
python C:\Users\akhil\AppData\Local\Temp\opencode\api_verify.py
```
