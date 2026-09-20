# MODEL REGISTRY (ner era)

JSON registry (`models/registry.json`) via `app/ml/registry.py`: every entry
carries dataset_version, feature_version, seed, artifact hash, metrics,
calibration status, validation method, promotion_status. Gate
(n≥50, F1≥0.6, recall≥0.6, Brier≤0.25, leakage-passed, spatial GroupKFold):
`evaluate_promotion()` records BLOCKED reasons, never auto-promotes; only
human-flipped PROMOTED entries enter inference (`production_model()`).
ner_v1 entries: `ner_logreg/ner_rf/ner_gbm @ ner_v1_v1` — all EXPERIMENTAL +
BLOCKED (see `scripts/register_model.py --model ner_rf --version ner_v1_v1`).
Legacy entries (events_v2, seq_real_*) untouched. Promotion path: larger
inventory → rerun pipeline → gate PASS → human review → PROMOTED → risk
engine reads `production_model()` (wiring exists; no code change needed).
