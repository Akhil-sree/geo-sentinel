# ML FINAL REPORT (ner_v1 baselines)

| Model | Dataset | +/− | Spatial CV | Temporal holdout | Prec/Rec/F1 | Recall 95% CI | LDO-F1 | PR-AUC | Brier | Calibration | Status |
|---|---|---|---|---|---|---|---|---|---|---|---|
| ner_logreg | ner_v1 | 10/20 | GroupKFold-3 F1 0.28 | 2024 test F1 0.33 | 0.50/0.25/0.33 | [0.046, 0.699] | 0.20 | 0.54 | 0.318 | UNCALIBRATED | EXPERIMENTAL, BLOCKED |
| ner_rf | ner_v1 | 10/20 | GroupKFold-3 F1 0.37 | 2024 test F1 0.40 | 1.00/0.25/0.40 | [0.046, 0.699] | 0.32 | 0.56 | 0.216 | UNCALIBRATED | EXPERIMENTAL, BLOCKED |
| ner_gbm | ner_v1 | 10/20 | GroupKFold-3 F1 0.69 | 2024 test F1 0.33 | 0.50/0.25/0.33 | [0.046, 0.699] | 0.55 | 0.53 | 0.333 | UNCALIBRATED | EXPERIMENTAL, BLOCKED |

Gate blocks (each): n=30<50; F1<0.6; recall<0.6 (RF Brier passes; GBM Brier
fails too). Leakage: binding PASS, spatial overlap PARTIAL disclosed.
Calibration: attempted (Platt/isotonic), kept on Brier evidence only — none
qualified at n=30. Class imbalance: 1:2 via matched controls + balanced
weights, no positive inflation. Mamba: not trained on ner_v1 (unjustified at
n=30; documented). Served engine unchanged. Artifacts: `models/ner_ner_v1/`
(+ registry hashes). Verdict: honest weak baselines on a traceable
foundation — scale (inventory with exact dates) is the blocker, not method.
