# CONTROL SAMPLE METHODOLOGY (ner_v1, `scripts/build_controls.py`)

Strategy: matched spatiotemporal controls. For each TEMPORAL event (same
site lat/lon, same month-day, non-event years ±1–3, ±30d exclusion against
any same-site event, complete-archive cutoff). Deterministic, no random
points, no positive inflation. Current: 20 controls linked to all 10 events
(862–871), years 2020–23 + 2025, splits train 10 / val 2 / test 8 (controls
follow their linked event's split).

## Contamination checks (measured, ner_v1)
- Unrealistic environments: none — controls share event sites by design, so
  terrain is identical; discrimination must come from weather, not geography.
- Known-record contamination: ±30d exclusion vs same-site events; GSI
  spatial catalog is undated and cannot contaminate temporal labels (excluded
  from inputs as future-inventory).
- Spatial duplicates: sample_id unique across splits (leakage gate).
- Temporal validity: all windows end ≤ control date (same pre-event clip);
  2025 controls are observable history, window-disjoint from test events.
- Future knowledge: none — dates are calendar arithmetic; selection uses no
  rainfall, model, or outcome data.
- Target-derived features: none (leakage gate `no_label_feature` PASS).

## Limitations
- Same-site matching means terrain cannot discriminate (by design); at n=30
  the weather signal is weak (holdout F1 ≤ 0.40).
- Controls are NO_RECORDED_LANDSLIDE (absence of record), never proven absence.
- Data expansion re-probe 2026-09-15: COOLR bulk still egress-404; viewer is a
  JS shell (manual download only). Verdict: additional NER dated-event data
  unavailable through current access boundary. Import framework
  (`ingest_coolr --manual`, `data/manual/{gsi,nrsc,smap,osm}/`) stands ready.
