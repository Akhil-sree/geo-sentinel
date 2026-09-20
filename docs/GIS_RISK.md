# GIS RISK

Layers (all with provenance): 8 risk zones + 865 REAL GSI slides
(`/api/landslides/gsi`) + observed DEM cells + roads + exposure +
field reports + routes + drilldown (risk/rain/soil/slope/history/roads/
alerts/freshness/DEM). Thresholds centralized (`risk_thresholds.yaml`;
LOW/MODERATE/HIGH/VERY_HIGH).

Grid story (honest): observed cells vary in real terrain (slopes
0.5–11.8°) but the zone-scale RF assigns one leaf (static 0.5115) —
published in `resolution_note`. Cell→zone aggregation therefore currently
adds no discrimination; the endpoint exists as the honest harness a
retrained fine-scale model will plug into. No fake red grids: legacy
noise mode is opt-in and labeled.
