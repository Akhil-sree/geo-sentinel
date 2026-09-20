# FULL_PROJECT_AUDIT.md — GEO-SENTINEL (execution audit, 2026-09-18; remediated same day)

Skeptical rule applied: only live-executed results count as VERIFIED. Everything else is marked PARTIAL/UNVERIFIED/BLOCKED.

## Overall: GREEN — honest demo-ready prototype, runtime-verified (not production: ML evidence insufficient by design)

Backend boots (live uvicorn verified), all gs endpoints respond with corrected 422/503 semantics,
training reproduces, tests pass (**127+1 backend, 19 frontend**; `tsc` clean; `vite build` ok).
ML is weak-by-evidence (n=18 positives, Mamba chance-level, held-out recall 0.45), correctly gated out of live risk.
No hardcoded secrets found. Former deployment blockers fixed and re-tested: shared compose DB,
production-closed CORS/auth, fabricated AI panel removed, null crashes fixed, safe model loading,
bounded inputs, traversal blocked (see `REMEDIATION_REPORT.md`). Remaining gap: Docker runtime
unverified (daemon down) + no browser E2E.

## Subsystem status

| Subsystem | Status | One-line evidence |
|---|---|---|
| Dataset | PARTIAL | Files exist, hashes readable, 0 NaN, 0 dups; but n=18 pos, pseudo-negatives, soil cols all-None |
| Preprocessing | PASS | Scaler train-only per-fold; 73→49 strictly-before-event cutoff, 666 kept / 0 dropped |
| RF | PARTIAL | Loads (14 feats), inference live; CV ROC 0.944 vs held-out recall 0.45 — optimistic gap disclosed |
| Mamba | PARTIAL | Pipeline runs, chance-level (ROC 0.52, PR 0.047), correctly unwired (`temporal_risk: null`) |
| SegFormer | BLOCKED | `BLOCKED.md` + `SEGFORMER_STATUS=BLOCKED`; 49/49 patches constant-0, 0 masks; no fake output |
| Fusion | PARTIAL | Research LR trains (ROC 0.92 on OOF); live path = static+heuristic fuse, gs_fusion not served |
| Backend | PASS | `/health` + `/api/ready` 200 via TestClient; startup clean |
| API | PASS | gs_point/tabular/sequence 200 valid; errors return 422/503/404; inputs bounded; OpenAPI GsOut nullable |
| Frontend | PASS | 19/19 tests pass; fabricated panel removed; null-safe states; gs_* wired via GsPointPanel |
| GIS | PARTIAL | Leaflet consistent [lat,lng]; frontend hex ≠ backend cells; GeoJSON geometry trap documented |
| Database | PASS | SQLite shared (compose volume + CWD-independent resolution + regression test); PostGIS add-on only |
| External feeds | PARTIAL | Mock defaults honest; live Open-Meteo gated; satellite quarantined from risk |
| Security | PASS | No live secrets; CORS/auth fail closed in production; `weights_only` everywhere; traversal blocked; inputs bounded |
| Docker | PASS | All 3 images build; compose up healthy; restart + down/up recovery verified (see FINAL_RUNTIME_VERIFICATION.md) |
| Deployment | PASS | Demo-hostable; compose + Postgres-prod runtimes verified; S3/TLS + load still unverified |
| Testing | PASS | 132 passed + 1 skipped backend; 24 passed frontend — both re-run today |
| End-to-end | PASS | Container API→ML→risk chain (27/27) + browser E2E PASS (map→panel, 16/16 API 200, zero console/page errors) |

## Reproduction notes (all executed 2026-09-18)

- `pytest -q` → 132 passed, 1 skipped. Frontend `npm test -- --run` → 24 passed. `tsc --noEmit` clean, `vite build` ok.
- `training.train_all --smoke` → RF CV ROC 0.944 / Mamba 0.447 / fusion 0.921 / held-out 0.4545 (reproduces artifacts).
- `validate_dataset.py` → PASS (events_v2, n=24). `run_leakage_checks.py` → PASS_WITH_PARTIAL (spatial overlap disclosed).
- Tensor `(666,73,15)` float32, 0 NaN/Inf. RF CSV `(54,18)`, labels {0:36, 1:18}, 0 NaN, 0 dups.
- Model loads: `gs_rf.joblib` (RandomForest, 14 feats) OK; `gs_fusion.joblib` (LogReg) OK.
