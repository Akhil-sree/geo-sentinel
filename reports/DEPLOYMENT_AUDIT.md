# DEPLOYMENT_AUDIT.md — GEO-SENTINEL (static + partial live, 2026-09-18)

- **Backend boot**: VERIFIED (`/health`, `/ready` 200; TestClient, sqlite demo).
- **Start/health**: `Dockerfile:27` migrate (v1–v9) + uvicorn :8000; image HEALTHCHECK + compose healthcheck on `/health`; worker healthcheck NONE by design (liveness via `/api/worker-status`).
- **Compose (static)**: backend :8000, worker `worker.py`, frontend :80→5173, prod-profile PostGIS 16-3.4 with `POSTGRES_PASSWORD:?` fail-fast + `pgdata`.
- **BLOCKER (P0)**: sqlite split-brain — backend + worker each get a private ephemeral sqlite (relative `DATABASE_URL`, only models/media volumes shared). Worker writes invisible to API in default compose. Fix: shared DB volume or default to prod postgres.
- **Drift (P1)**: live `.env` sets STATIC/DYNAMIC 0.5/0.5, overriding tested yaml 0.4/0.6 via `config.py:32-33` — tested weights not live.
- **Defaults**: `CORS_ORIGINS` commented out → `*`; `ADMIN_API_KEY` commented out → open-demo. Fine for judging, not for hosting.
- **UNVERIFIED**: image build/run (docker client present, build not executed); S3/TLS; worker-vs-Postgres long-run; fresh perf benchmarks. No `D:\`/`C:\`/`/home/developer` absolute paths in compose/Dockerfile (metadata artifact embeds a `D:\` path string only).
- **Frontend serve**: nginx `/api/` + `/media/` → backend:8000, SPA fallback — sane.

## Remediation update (2026-09-18, verified unless noted)

- FIXED (P0): backend + worker share `sqlite_data:/data` with absolute
  `DATABASE_URL=sqlite:////data/geo_sentinel.db`; local relative sqlite URLs
  resolve against `backened/` CWD-independently and the resolved URL is logged
  at startup (`test_db_shared_persistence.py` passes).
- FIXED: live `.env` no longer overrides fusion weights (yaml 0.4/0.6 is the
  single source of truth, as tested).
- `ENVIRONMENT=production` without keys/CORS origins fails closed (verified by
  unit tests; hosting still requires setting real values).
- Live uvicorn boot VERIFIED (`/health`, `/ready`, gs_point over HTTP).

## Runtime verification (2026-09-18, Docker daemon started, all executed)

- VERIFIED: `docker compose config` validates; all 3 images build;
  `up -d` → backend Up **healthy**, worker Up (full cycle OK), frontend Up.
- FIXED: /data volume root-owned (backend crash-loop + worker silent
  rollbacks) — Dockerfile now creates/chowns /data; volume recreated.
- FIXED: `config` failed without POSTGRES_PASSWORD on clean checkout —
  dev default added, prod requirement documented.
- FIXED: worker `_mark_sensor_health` NameError (defined after blocking
  main loop) — moved above guard + regression test.
- FIXED: worker restart exit-loop (own heartbeat seen as peer) — same-host/
  same-pid takeover + graceful `_release()` + regression test; restart and
  full down/up recovery verified, cooldown dedup observed working.
- FIXED: terrain rasters unmounted → gs_point 503 in-container —
  `./datasets:/datasets:ro` added; valid gs_point/tabular/sequence re-verified
  200 with `temporal_risk: null`.
- Networking via compose service names (`backend:8000`); nginx `/api/` proxy
  returns live model JSON; shared `sih_sqlite_data` proven (worker job rows
  served by API; pre-restart rows survive restart).
- Backend suite now 127 passed + 1 skipped; frontend 19/19, tsc clean.
- Browser E2E VERIFIED (Playwright/Chromium PASS); Postgres prod runtime
  VERIFIED here (migrate v1–v9, PostGIS applied, seed, cross-session
  visibility, restart persistence; stale-volume password caveat documented).
- Still UNVERIFIED: S3/TLS, multi-user deployment load, live feeds.
