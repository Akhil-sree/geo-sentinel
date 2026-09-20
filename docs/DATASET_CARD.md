# DATASET CARD

## events_v2 (static ML)
- 24 zone-years (8 zones × 2022–24), 10 pos / 14 neg, terrain6, district groups.
- Labels: 1 if ≥1 seed-inventory event in zone-year. `data/process_events.py`.

## events_v3 (static ML, feature-enriched)
- SAME 24 samples + 2 REAL GSI features (slide count ≤15km, nearest-slide
  distance). CV F1 drops vs v2 for all models (0.375 across) — features kept
  as GIS signal, not an ML upgrade. Registered, BLOCKED.

## seq_real_v1 (temporal ML)
- 24 ERA5 sequences (10 pos + 14 matched negatives), 168h pre-event, 48×7.

## seq_real_v2 (temporal ML, current)
- 32 sequences (+8 hard peak-rain no-event negatives, ±30d exclusion,
  incompleteness caveat). Gates PASS. Mamba v04: F1 0.444, recall 1.0.

## gsi_slides_meghalaya (GIS + features)
- 865 REAL GSI catalog slides (CC0-1.0), coords verified in-bbox, 219 with
  years (≤2019), 646 year-unknown. Year resolution → NO temporal use
  (documented boundary). Served at `/api/landslides/gsi`.

## Scale statement
Largest ML n = 32. Promotion gate (n≥50) blocks everything by design.
No duplicates, no perturbations, no synthetic positives — ever.
