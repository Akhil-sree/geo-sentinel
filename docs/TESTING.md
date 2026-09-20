# TESTING

Backend (`pytest` 41/41, sqlite/memory + file DB): remediation+fusion (12)
+ `test_pipeline.py` (13) + `test_failures.py` (16: malformed/429/500→STALE,
soil-down→STALE, GPS 422, MIME 415, magic 422, media 409, revoked key 401,
RF-missing/corrupt fallback, worker lock, DEM derive ×8, temporal gate
v1+v2, i18n fallback, geo-match label, priorities reasons + provenance,
observed cell-grid). Gated live test (`LIVE_NET_TEST=1`): real Open-Meteo
rows. Regression gate `scripts/final_verify.py`: 12 checks, 0 FAIL — caught
a real ZoneFeature upsert IntegrityError on fresh DBs (fixed: preloaded-map
upsert + latest-per-zone semantics).

Frontend (vitest 10): format, severity, offline queue, provenance chips
(LIVE/SIMULATED/DEMO/STALE never overclaimed). `tsc --noEmit` clean,
`vite build` passes.

ML: `validate_dataset.py` PASS (7 gates), `process_events.py`
reproducible, ablation measured, ECE/bins stored. Worker: startup loop +
single-instance + cycle-never-crashes (code-path tested via lock test).
Run: backend `pytest -k "not live"`, live opt-in, frontend `npm test -- --run`.
