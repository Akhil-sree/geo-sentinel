# PROJECT_STRUCTURE_AUDIT.md — GEO-SENTINEL (verified 2026-09-18)

## Layout (actual)

```text
D:\sih
├── backened/          FastAPI backend (app/), data pipelines (data/),
│                      training (training/, scripts/), models/, tests/
├── frontend/          React 18 + Leaflet + Vite (builds ✓, 11 vitest ✓)
├── datasets/          read-only sources + training package (untracked by git)
├── reports/           audits + training/gap/leakage reports
├── experiments/       timestamped run records
├── docs/              40+ design/provenance docs
├── docker-compose.yml backend + worker + frontend (+ prod postgres profile)
└── training_report.md top-level gs_v1 summary
```

## Findings

- **Duplicate React trees**: root `package.json` (React 19) vs `frontend/package.json`
  (React 18). Frontend builds from its own manifest — root manifest looks stale.
  P3: remove or document the root manifest to avoid installing the wrong tree.
- **Coexisting model generations** (`models/rf/event_*`, `rf_2026_01`, `ner_ner_v1`,
  `mamba_2026_0x`, `gs_v1`): all load (27/27 joblib OK; legacy mamba `.pt`
  are `{state_dict, seed, dataset}` snapshots that load into `SelectiveSSMCell`
  and forward correctly). Risk: wrong-schema model could be served — mitigated by
  per-version dirs + registry, but no runtime schema assertion on legacy paths. P2.
- **Dev-machine path**: `backened/data/process_gsi.py:26` references
  `C:\Users\akhil\...` with an existence fallback (works, not portable). P3.
- **Absolute paths in MY gs metadata** (`D:\sih\...` artifact paths in
  `models/*/gs_v1/*.metadata.json`, `experiment_gs_v1.json`): metadata-only wart;
  loaders use relative paths. P3 (regenerate with relative paths on next run).
- **Dead/placeholder surface**: `SENTINEL1/2` source dirs empty per README;
  vision `OBSERVATION_MODEL_UNTRAINED` stub is flagged, not silent (checked docstring).
- **No broken imports**: `app.main` imports clean (91 routes); full backend suite green.
- **No hardcoded secrets** found by pattern scan; `.env` files gitignored.
