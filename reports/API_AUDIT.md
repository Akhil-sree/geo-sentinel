# API_AUDIT.md — GEO-SENTINEL (live TestClient verification, 2026-09-18)

## VERIFIED WORKING

| Endpoint | Valid | Invalid | Note |
|---|---|---|---|
| `GET /health` | 200 `{"status":"ok"}` | — | |
| `GET /api/ready` | 200 `{"ready":true,"database":"ok"}` | — | |
| `GET /api/risk/gs_point?lat=25.3&lon=91.7` | 200 risk_score 0.6993 HIGH, `temporal_risk: null` | lat=999 → 200 `{"error":...,"risk_level":"UNKNOWN"}` | Out-of-range returns 200-with-error, not 4xx |
| `POST /api/risk/gs_tabular` | 200 risk_score 0.2428 LOW, `temporal_risk: null` | `{}` → 200 `{"error":...}`; `assess_tabular({})` raises ValueError server-side, caught to 200-error | Missing-field returns 200-with-error, not 422 |
| `POST /api/risk/gs_sequence` (49×15) | 200 neutral static 0.5, `temporal_risk: null`, `sequence_steps: 49` | `[]` → 200-error; `{}` → 422 missing field; 5000-step seq → 200 (no size cap — DoS surface) | Temporal branch deliberately unwired |
| `GET /api/data-status`, `/api/model/reliability` | 200 | — | Honest DEMO/degraded labels |
| Malformed JSON body | — | 422 `json_invalid` | Correct |

## Contract notes

- gs_* schema is dict/list-based: feature-order bugs impossible by construction (schema-ordered vectoring).
- Actual 14-feature schema differs from older docs (`Distance_to_Major_Road_m`, `Road_Length_1km_m`, …) — use `gs_rf.metadata.json:features`, not guessed names.
- gs_* is unconsumed by frontend (0 hits) — wiring it directly would crash on `risk_score: null` (out-of-coverage) since frontend calls `.toFixed()` unguarded.
- Perf: 5× gs_point in 0.15 s in-process; sequence latency ~0.0 s (neutral path, no model compute).

## Remediation update (2026-09-18, verified)

- Invalid inputs now return **422** (`gs_point` OOR, `gs_tabular {}`,
  `gs_sequence []`/wrong-width/>1000 rows) with structured
  `{"error","risk_level":"UNKNOWN"}`; missing artifact → **503**;
  `cell-grid` unknown zone → **404**, untrained RF → **503**.
- Input bounds: gs lat ∈ [-90,90], lon ∈ [-180,180]; sequence 1–1000 rows;
  features ≤128 keys; history `limit` ≤2000; `ReportIn` coord/string/accuracy
  bounds (non-numeric accuracy is 422, not 500).
- OpenAPI `GsOut` response models document `risk_score`/`temporal_risk` as
  nullable. Live uvicorn re-verified: `gs_point` HIGH 0.6993,
  `temporal_risk: null`. Backend suite: 125 passed + 1 skipped.
