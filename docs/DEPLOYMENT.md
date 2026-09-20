# DEPLOYMENT

Services: backend (FastAPI, migrate-on-boot → uvicorn), worker
(`worker.py` loop, heartbeat single-instance lock), frontend (nginx).
`docker-compose.yml`: healthchecks + `unless-stopped` on all three;
`--profile prod` adds postgis/postgres (booted + E2E-verified 2026-09-15
against PostgreSQL 16.4 + PostGIS 3.4; no redis service by design).

Verified 2026-09-15: `scripts/migrate.py` v1→v6 on SQLite AND fresh
PostgreSQL (8 zones seeded, postgis 10 statements); backend + worker +
frontend + postgres stack healthy; full PG E2E (ingest→risk→GIS→alert
lifecycle→report→restart-persistence) plus DB-outage and worker-stop
recovery. `docker compose build` WORKS (fixed nonexistent
psycopg2-binary>=3.1.0 pin → ==2.9.9). UNVERIFIED: S3/TLS runtimes.
Production needs: `DATABASE_URL` → Postgres, `CORS_ORIGINS`,
`API_KEYS`, `FERNET_KEY`, provider credentials (rate limiting stays in-memory single-worker)
limits, S3 signed URLs for media (code comments mark the seam).

Readiness: `/health` (liveness), `/ready` (DB check), `/data-status`,
`/worker-status`, `/jobs`, `/model/monitor`. No "healthy" lies: monitor
flags missing predictions/observations as WARNING.
