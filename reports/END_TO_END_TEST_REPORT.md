# END_TO_END_TEST_REPORT.md — GEO-SENTINEL (2026-09-18)

```text
User → Frontend → API → ML → Risk → Frontend/GIS : PARTIALLY VERIFIED
```

## Chain (each link executed or statically traced)

1. Datasets exist + readable: VERIFIED (`GEO_SENTINEL_TRAINING_PACKAGE`, tensor 666×73×15, RF CSV 54 rows).
2. Validation gates: VERIFIED (`validate_dataset` PASS; leakage PASS_WITH_PARTIAL).
3. Training reproduces: VERIFIED (`--smoke`: RF 0.944 / Mamba 0.447 / fusion 0.921 / held-out 0.4545).
4. Model loads: VERIFIED (RF 14 feats, fusion LR; Mamba checkpoints present, correctly unused live).
5. Inference: VERIFIED (`assess_point` HIGH 0.6993; `assess_tabular` LOW 0.2428; `assess_sequence` neutral 0.5; all `temporal_risk: null`).
6. API: VERIFIED (`/health`, `/ready`, gs_point/tabular/sequence 200; error paths return 200-with-error).
7. Frontend render + map: UNVERIFIED live (tests 11/11 pass; browser run not executed in this audit).
8. GIS correspondence: PARTIAL (visual hex ≠ analytical cells; hotspot dots derived, not detections).

## Breaks found

- Browser→backend→map loop not run live — chain verified up to API boundary via TestClient only.
- Error-code quirk: invalid inputs return 200-with-error (gs_point OOR, tabular empty, sequence empty) instead of 4xx — clients must parse `error` field.
- Wiring gs_* into current frontend would crash on `null` risk_score (no guards).

## SIH demo verdict

Demonstrable honestly as a scored-advisory prototype (map → zone → evidence → risk → alerts-mock → reports). NOT demonstrable as validated early warning. Requires narration of SIMULATED/STATIC/uncalibrated labels the system already exposes.

## Remediation re-test (2026-09-18, verified)

```text
User → Frontend → API → ML → Risk → Frontend/GIS : VERIFIED to HTTP boundary
```

- Live uvicorn: `/health` 200, `/ready` 200, `gs_point(25.30,91.70)` → HIGH
  0.6993, `temporal_risk: null` over real HTTP.
- Error paths over HTTP/TestClient: OOR coords → 422, empty tabular/sequence
  → 422, oversize sequence → 422, missing artifact → 503, unknown zone → 404.
- Frontend `GsPointPanel` calls the real endpoint with explicit
  AVAILABLE/UNAVAILABLE/PROCESSING/ERROR states (vitest-covered); browser live
  run still UNVERIFIED (no browser here).
- Persistence: worker-session write → API-session read passes; startup logs
  the resolved absolute DB URL.

## Runtime verification re-test (2026-09-18, compose, all executed)

```text
User → nginx :5173 → /api/ → backend:8000 → ML → Risk → JSON → UI panel : VERIFIED (browser)
```

- 27/27 container API checks pass (valid/invalid/traversal/leak/CORS/feeds/
  reliability/worker-status; FAILURES: none) + valid gs_tabular (MODERATE
  0.2928) + gs_sequence 49×15 HIGH, all `temporal_risk: null`.
- Restart + full down/up recovery verified; worker full cycle green twice.
- Frontend bundle rebuilt from current source, served 200, fabrication strings
  absent from the bundle; panel states vitest-covered.
- Browser click→panel flow VERIFIED 2026-09-18 (Playwright/Chromium PASS —
  see FINAL_RUNTIME_VERIFICATION.md), re-verified after the UI/GIS redesign
  plus a 23/23 redesign acceptance run (see UI_GIS_REDESIGN_REPORT.md).
