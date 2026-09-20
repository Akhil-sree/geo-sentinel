# DOCKER

Compose: backend + worker + frontend + postgres(postgis) under `--profile
prod`; default profile runs the SQLite demo stack. No Redis by design
(explicitly out of scope — removed 2026-09-15).

- Backend Dockerfile: non-root `appuser`, healthcheck, migrate-on-boot.
- Postgres: `postgis/postgis:16-3.4`, required `POSTGRES_PASSWORD` (no
  default — compose config fails loudly without it, verified), pgdata volume.
- Runtime VERIFIED 2026-09-15: full stack booted (`--profile prod` +
  temporary PG-DATABASE_URL override, deleted after): backend healthy,
  frontend HTTP 200, postgres healthy, worker running (its inherited :8000
  healthcheck disabled in compose — worker serves no HTTP; liveness =
  /api/worker-status job rows). Previously UNVERIFIED (daemon down ×5).
