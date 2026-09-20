# ARCHITECTURE

## Data flow

```
providers (mock | openmeteo | sentinel-mock)
  → IngestionAdapter.fetch/validate/normalize/store (retry+backoff, STALE never mocked)
  → observations (rainfall / soil / sar, source+quality tagged, idempotent)
  → trim (validity windows) → ZoneFeature snapshot
  → sim.run_pipeline(t): RF static + heuristic temporal + fusion_v1 + XAI
  → RiskScore history → worker auto-evaluate → alerts (cooldown/escalation/ack/resolve/audit)
```

Live and simulated paths share the adapter contract; `provider_states()`
reports LIVE/SIMULATED/STALE with `is_live` flags the UI renders verbatim.

## ML flow

`data/process_events.py` → `events_v2` (n=24) → `validate_dataset.py` gate →
`train_rf.main_event` (LogReg/RF/GBM, GroupKFold by district, Platt/isotonic
bake-off, ECE, reliability bins) → `registry.json` (artifact hash, promotion
gate) → `ablation.py` (stacking rejected at n=24; expert fusion stays, labeled
unvalidated). Mamba: `sequences.py` → `train_mamba.py` → EXPERIMENTAL
checkpoint (SIMULATED task only). Nothing auto-promotes.

## Worker flow

`worker.py` loop (heartbeat single-instance lock) → `run_ingestion`
(job_id/timing/trim) → `auto_evaluate_alerts` (HIGH+, cooldown 360m,
escalation-only resend, hourly idempotency key) → dispatch (SMS/email,
MOCK labeled) → audit.

## Risk calculation

`risk = 0.4·static + 0.6·dynamic + escalation_boost` (config, `fusion_v1`);
uncalibrated score + `probability_status`. Routing cost adds slope exposure.

## Notes

- `app/routers/` is legacy dead code (unmounted duplicates of `app/api/`);
  kept, not imported. `app.notify` likewise superseded by `app/alerts/`.
- SQLite demo storage, labeled. Postgres/PostGIS: compose `--profile prod` (no Redis — out of scope)
  (runtime-unverified — daemon down).
- JWT: roadmap. Auth = role API keys (server-side), Fernet SecretBox.
