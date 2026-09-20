# LABELING PROTOCOL

## Positives (seq + zone-year)
- Seed inventory event (zone, date) → prediction ts = date 12:00 UTC
  (dates lack time; documented approximation). Features strictly ≤ ts.
- GSI slides are NOT positives (no exact dates) — spatial features only.

## Negatives
- Matched: same zone, same month-day, non-event year (background).
- Hard: wettest 7d monsoon window/zone with no RECORDED event ±30d and no
  sample overlap ±8d. Label means "extreme conditions, no RECORDED event"
  — inventory may be incomplete (stated in `neg_reason` per file).

## Forbidden
Duplicating rows, perturbing rows, random labels, future features,
threshold-tuning on holdout, scaler fit outside folds (no fitted scalers
exist — fixed divisors only).

## Audit
Every event: date, zone, window, rainfall window, label rule, confidence
(seed = demo/medium; GSI = catalog/high-spatial, no-temporal).
`validate_dataset.py` + `validate_temporal_dataset.py` enforce mechanically.
