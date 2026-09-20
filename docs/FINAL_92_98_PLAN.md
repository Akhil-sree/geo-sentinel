# FINAL 92→98 PLAN — top bottlenecks, ranked

## Bottleneck 1 — Negatives are too easy (matched calendar windows)
Impact: HIGH (ML validity). Feasibility: HIGH (ERA5 archive works).
Plan: mine HARD negatives — wettest 7d windows 2022–24 per zone with no
recorded event ±30d, labeled with incompleteness caveat → seq_real_v2
(n≈32). Verify: temporal gate + retrained benchmark.

## Bottleneck 2 — Temporal validation n=6 holdout only
Impact: HIGH. Feasibility: HIGH (CPU seconds).
Plan: GroupKFold-3 by district over seq_real_v2 (mean±std, per-fold counts)
+ weighting/focal comparison. Verify: test asserts table shape + counts.

## Bottleneck 3 — Grid risk uses random perturbation
Impact: HIGH (GIS honesty + resolution). Feasibility: MED (648 SRTM lookups).
Plan: 9×9@250m real DEM grids/zone → observed cell static scores + zone
dynamic fusion → endpoint mode=observed (legacy random mode labeled or
removed). Verify: cell test on real grid values.

## Bottleneck 4 — Provenance scattered across endpoints
Impact: MED. Feasibility: HIGH.
Plan: single `risk_provenance` object in pipeline outputs + evidence.
Verify: e2e key assertions.

## Bottleneck 5 — Docker/PG/Redis unverifiable here (daemon down ×4, no creds)
Impact: HIGH but BLOCKED. Plan: retry once; else UNVERIFIED + final_verify.py
as the runnable substitute. No score claimed.

Also: report geo-intelligence (Phase 22), priority reasons (23),
multilingual fallback test (24), PWA scope doc (25), sat-imagery auth
boundary proof (13), failure tests + final_verify.py (21/29), claim audit,
FINAL_MODEL_BENCHMARK.md, final score (30/31).

Estimated evidence-backed ceiling: 94–95 (95 only if grid + CV + hard
negatives all land with clean tests).
