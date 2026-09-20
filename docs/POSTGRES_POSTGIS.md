# POSTGRESQL + POSTGIS

Backend selection is explicit: `backend_name()` (sqlite|postgresql),
logged at boot, no silent fallback (pg URL that can't connect raises —
tested parsing; no substitution code exists).

- Canonical storage stays float lat/lng (every backend).
- Migration v6 (pg-only, sqlite-skips-explicitly): `CREATE EXTENSION
  postgis`, `geog geography(Point,4326)` on zones/reports/roads + GIST.
- `app/geo/postgis.py`: ST_DWithin queries on pg, haversine fallback on
  sqlite, identical shapes + `spatial_backend` label. Wired into report
  geo-match nearby-roads.
- Runtime VERIFIED 2026-09-15 against real PostGIS (see below).
  Previous server-less verification (sqlite live + pg SQL-compile) retained
  as the offline fallback story.

## LIVE RUNTIME EVIDENCE (2026-09-15, Docker)

- Server: PostgreSQL 16.4 + PostGIS 3.4 (`postgis/postgis:16-3.4`),
  `SELECT PostGIS_Version()` → `3.4 USE_GEOS=1 USE_PROJ=1 USE_STATS=1`.
- Fresh-boot migrate v1→v6: `reference data ensured (8 zones)`,
  `postgis enabled (10 statements)`; `zones.geog geography(Point,4326)` +
  `ix_zones_geog` GIST confirmed via `\d zones`.
- Real spatial SQL: KNN `ORDER BY geog <->` (Z2 12km / Z3 41km / Z4 50km
  from Z1); report geo-match returns `spatial_backend: postgis` with
  measured road distances (6.04 / 10.13 / 26.68 km) — the pg path now
  selects `ST_Distance` (meters→km) instead of nulls (bug found live,
  fixed, re-verified).
- Full E2E on Postgres: ingestion (1344 rain / 40 soil / 8 sar),
  risk map (8 zones), evidence, cell-grid (49, observed-DEM), routes,
  alert evaluate→send→cooldown(429)→ack→lifecycle→resolve (RESOLVED),
  field report create→dedup→moderate→restart-persistence.
- Failure: postgres stopped → `/ready` = `{"ready":false,
  "database":"unavailable"}`, risk endpoints 500 with empty body (no
  leak); restart → `ready:true`, 8 zones, report persisted.
- Worker stop → backend reads unaffected; worker restart resumes.
- Live HTTP timings (PG): map ~0.7s, cell-grid ~0.7s, evidence ~0.6s —
  faster than SQLite/TestClient warm numbers.
- Two real bugs found ONLY by this runtime: (1) requirements pinned
  `psycopg2-binary>=3.1.0`, which does not exist → Docker build failed
  (fixed to `==2.9.9`); (2) seed single-commit insert order (no
  relationship()s → UoW unordered; SQLite never enforces) → fresh-PG
  migrate crashed on emergency_tasks FK (fixed: flush zones first +
  regression test `test_seed_flushes_zones_before_dependents`).

## RE-VERIFICATION (2026-09-15, this session, independent run)

- Fresh `postgis/postgis:16-3.4` container: PostgreSQL 16.4 +
  `PostGIS 3.4 USE_GEOS=1 USE_PROJ=1 USE_STATS=1` (live `SELECT`).
- `migrate.py` v1→v9 clean: all ledgers stamped, `postgis enabled
  (10 statements)`; `zones.geog`, `road_segments.geog`,
  `citizen_reports.geog` + `ix_zones_geog` / `ix_roads_geog` /
  `ix_reports_geog` confirmed in `information_schema` / `pg_indexes`.
- Backend image booted with `DATABASE_URL=postgresql+psycopg2://…`:
  `database backend=postgresql`, `/health`, `/data-status`, `/risk/map`,
  `/risk/emergency-priorities` all 200.
- Report create (201) → geo-match returns `spatial_backend: postgis`,
  zone Z1 + the same measured road distances (6.04 / 10.13 / 26.68 km).
- New dataset endpoints live against PG: `/api/datasets` 200 (empty on a
  fresh deploy — honest, training rows are operator-built, not seeded).
- Prod profile is therefore TESTED, not just documented. Remaining
  untested: worker-against-PG long-run, PG outage/recovery re-run
  (prior evidence in §LIVE RUNTIME EVIDENCE stands).
