# Feature association notes (model-prediction associations, NOT causes)

## Tabular branch (permutation importance, full-fit descriptive)
### gs_logreg
- Road_Length_1km_m: 0.0944 (associated with model predictions)
- Distance_to_Major_Road_m: 0.05 (associated with model predictions)
- Curvature: 0.0241 (associated with model predictions)
- Roughness_m: 0.0241 (associated with model predictions)
- TPI_m: 0.0185 (associated with model predictions)
- Aspect_deg: 0.0167 (associated with model predictions)
- Distance_to_Major_Waterway_m: 0.0148 (associated with model predictions)
- Distance_to_Nearest_Road_m: 0.0111 (associated with model predictions)
### gs_rf
- Distance_to_Nearest_Road_m: 0.0167 (associated with model predictions)
- Elevation_m: 0.0 (associated with model predictions)
- Slope_deg: 0.0 (associated with model predictions)
- Aspect_deg: 0.0 (associated with model predictions)
- Curvature: 0.0 (associated with model predictions)
- TPI_m: 0.0 (associated with model predictions)
- Roughness_m: 0.0 (associated with model predictions)
- LULC_Class: 0.0 (associated with model predictions)
### gs_hgb
- Distance_to_Nearest_Road_m: 0.25 (associated with model predictions)
- Distance_to_Major_Road_m: 0.1889 (associated with model predictions)
- Distance_to_Major_Waterway_m: 0.0907 (associated with model predictions)
- Distance_to_Nearest_Waterway_m: 0.037 (associated with model predictions)
- Elevation_m: 0.0 (associated with model predictions)
- Slope_deg: 0.0 (associated with model predictions)
- Aspect_deg: 0.0 (associated with model predictions)
- Curvature: 0.0 (associated with model predictions)
### gs_xgb
- Distance_to_Nearest_Road_m: 0.2259 (associated with model predictions)
- Distance_to_Major_Road_m: 0.0519 (associated with model predictions)
- Distance_to_Major_Waterway_m: 0.013 (associated with model predictions)
- Road_Length_1km_m: 0.0056 (associated with model predictions)
- Distance_to_Nearest_Waterway_m: 0.0056 (associated with model predictions)
- Elevation_m: 0.0 (associated with model predictions)
- Slope_deg: 0.0 (associated with model predictions)
- Aspect_deg: 0.0 (associated with model predictions)
### gs_lgbm
- Distance_to_Nearest_Road_m: 0.15 (associated with model predictions)
- Distance_to_Major_Road_m: 0.1148 (associated with model predictions)
- Road_Length_1km_m: 0.0148 (associated with model predictions)
- Elevation_m: 0.0 (associated with model predictions)
- Slope_deg: 0.0 (associated with model predictions)
- Aspect_deg: 0.0 (associated with model predictions)
- Curvature: 0.0 (associated with model predictions)
- TPI_m: 0.0 (associated with model predictions)

## Temporal branch
- CV PR-AUC 0.0337; positive-event recall per fold [0.3333, 0.1667, 0.8333]
- Antecedent rainfall accumulations (24h/72h) and deep-layer soil moisture dominate sequence outputs in inspection; reported as associations, not causal claims.
