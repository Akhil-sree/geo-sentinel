# ML METHODOLOGY (ner_v1)

Order: LogisticRegression → RandomForest → GradientBoosting
(`scripts/train_models.py --dataset ner_v1 --seed 42`).
No positive inflation; `class_weight=balanced` documented.
Validation: spatial GroupKFold-3 by district + temporal holdout (2024 test).
Calibration: Platt/isotonic attempted, kept only on Brier evidence — at n=30
nothing qualified → all UNCALIBRATED (risk scores, not probabilities).
Mamba deliberately NOT trained on ner_v1: n=30 matched controls do not
justify a temporal SSM (existing Mamba work stays EXPERIMENTAL on seq data).
Results (honest, weak): LogReg CV-F1 0.28 / holdout 0.33; RF 0.37 / 0.40;
GBM 0.69 / 0.33. Gate: all BLOCKED (n<50, F1<0.6) — see ML_FINAL_REPORT.md.
Served risk engine unchanged (rf_2026_01 + heuristic + fusion_v1); ner models
are EXPERIMENTAL registry entries until a human promotes them.
