# Backup & Recovery (honest scope)

No automated backup operator exists in this repo. What exists is a **tested
manual procedure** below. Claims beyond this file are out of scope.

## SQLite (demo / local / compose default)

- Live DB: compose `sqlite:////data/geo_sentinel.db` on the `sqlite_data`
  volume; local default `backened/geo_sentinel.db` (see `app/database.py`).
- Backup: `cd backened && python scripts/backup_sqlite.py backup`
  (online-backup API snapshot + immediate `PRAGMA integrity_check`).
  Verified 2026-09-19 against the dev DB (see test below).
- Restore: stop backend+worker, then
  `python scripts/backup_sqlite.py restore --from <file> --force`,
  restart, check `GET /api/ready` → `{"ready":true}`.
- Suggested frequency for demo ops: daily file copy of the volume off-host.
  RPO ≈ 24h, RTO ≈ 15 min (restart + migrate + seed are idempotent).
- Full reseed from scratch is always possible: Git + `scripts/migrate.py`
  (v1–v9) reconstructs schema + seed zones/events/roads; ingested
  observations re-accumulate via the worker. Uploaded `/media` files are
  NOT in the DB — back up `backened/media` (compose `./backened/media`
  bind) alongside it.

## Postgres/PostGIS (production profile)

- Procedure (manual, standard): `pg_dump -Fc geosentinel > geo.dump`
  (daily via cron/systemd or managed-service automated backups);
  restore with `pg_restore -d geosentinel geo.dump`, then boot the backend
  (migrations are idempotent) and verify `/api/ready` + `/api/metrics`.
- Helper script: `cd backened && python scripts/backup_postgres.py backup`
  (wraps pg_dump -Fc with integrity check via pg_restore -l);
  restore with `python scripts/backup_postgres.py restore --from <file> [--force]`.
  Script tested for syntax and CLI; full dump/restore cycle UNVERIFIED
  (requires live Postgres instance — see docs/POSTGRES_POSTGIS.md).
- Suggested RPO ≤ 24h (or provider PITR), RTO ≈ 30 min.
- UNVERIFIED as an executed dump/restore cycle — the restore *path*
  (migrate → seed → serve) is what compose/prod verification covers.

## What is NOT backed up automatically

- `backened/media` uploads (bind-mount; copy it with the DB backup).
- In-memory state (rate-limit budgets, cooldown memory, metrics) —
  intentionally ephemeral; cooldowns rebuild from the `alerts` table.
- `datasets/` raw caches (re-fetchable via `backened/data/*.py` + scripts).

## Recovery test (SQLite)

```bash
cd backened
python scripts/backup_sqlite.py backup --out "$TEMP/geo-test.db"
# stop backend/worker; simulate loss; restore:
python scripts/backup_sqlite.py restore --from "$TEMP/geo-test.db" --force
python -m uvicorn app.main:app --port 8000  # /api/ready -> ready:true
```

## Recovery test (Postgres) — requires live Postgres

```bash
cd backened
# backup (uses pg_dump -Fc)
python scripts/backup_postgres.py backup --out "$TEMP/geo-test.dump"
# stop backend/worker; simulate loss; restore:
python scripts/backup_postgres.py restore --from "$TEMP/geo-test.dump" --force
python -m uvicorn app.main:app --port 8000  # /api/ready -> ready:true
```
