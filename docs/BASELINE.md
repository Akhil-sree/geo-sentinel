# GEO-SENTINEL BASELINE (pre-remediation, verified 2026-09-14)

Source of truth: code + test evidence. README claims were cross-checked;
fabrications found are listed under "Honesty gaps".

## Tests (ran, passing)

- Backend: 12/12 (`backened/tests/`: test_remediation.py, test_fusion.py)
- Frontend: 6/6 vitest (`frontend/src/tests/`)
- TypeScript: clean (`tsc --noEmit`)
- Production build: passes (`npm run build`)
- Docker: daemon unavailable on this machine — compose NOT verified

## Model metrics (measured, from artifacts)

- Production static RF `rf_2026_01`: n=8 zone labels, spatial GroupKFold-3,
  cv_accuracy 0.50, F1-macro 0.2222, precision-macro 0.1667 — weak, disclosed,
  NOT operationally suitable.
- Temporal: untrained Mamba excluded from risk path (`MAMBA_LIVE=false`,
  no weights); labeled heuristic fallback (`mock_heuristic`).
- Confidence: uncalibrated mean(static, dynamic) — not a probability.
- XAI: RF-importance-weighted heuristic, not SHAP.

## Data sources (code-verified)

| Source | State |
|---|---|
| Rainfall | Mock IMD synthetic monsoon persisted? NO — adapters had no `store()`; ingestion was a no-op. Open-Meteo live path existed but UNVERIFIED, also unpersisted. Mock zone ids (MZ-*) did not match Zones table (Z1..Z8). |
| Soil moisture | Mock rain-derived proxy, unseeded `random` (non-repeatable). Open-Meteo soil labeled live but is modeled reanalysis. |
| Satellite | Deterministic? No — unseeded random mock, quarantined from risk (neutral 0.15). No scene-metadata layer. |
| Terrain | 8 hardcoded profiles, no provenance metadata. |
| History | 10 static demo events; RF trained on 8 zone labels. |

## Honesty gaps found (fixed in remediation)

1. `GET /api/admin/model/metrics` returned HARDCODED roc_auc 0.84 / pr_auc 0.71 /
   f1 0.66 and baselines — measured nowhere. Removed; now serves registry truth.
2. `xai.py` docstring claimed "SHAP-lite". Renamed to importance-weighted.
3. Frontend tooltips implied live NASA SMAP volumetric data; map HUD said "Live".
4. Ingestion `store()` was `...` (no-op) on every adapter — nothing persisted.

## Architecture (preserved)

FastAPI + SQLite demo / Postgres-ready · React + Leaflet GIS · RF +
heuristic-temporal fusion · 15-min worker · cooldown/dedup/escalation alerts
(mock SMS) · field reports + moderation/training gate · offline report queue.

## Scores (pre-remediation estimate)

Overall 74 · Problem coverage 68 · AI/ML 62 · GIS 70 · Real-Time 45 ·
Early Warning 65 · Security 55 · Deployment 65 · Testing 70 ·
Differentiation 78.
