# FRONTEND_AUDIT.md — GEO-SENTINEL (verified 2026-09-18)

- **Tests**: 11/11 vitest pass (re-run today, 57 s). Routes: 12 (`/`, `/zone/:zoneId`, reports, alerts, roads, weather, emergency, insights, about, sensors, satellite, health, data).
- **API wiring**: relative `/api` base (`client.ts:3-6`) + dev proxy to :8000; no `VITE_API_URL` — same-origin deploy only.
- **Honest mocks**: SendButton labeled "Dispatch (mock)"; satellite demo quarantined.
- **BROKEN (user-visible fabrication)**: `GovernmentIntelligencePanel.tsx:31-47,87-95` — synthetic sparkline + "AI predicts X% probability of slope movement within 6h" with no backend forecast. Backend explicitly says confidence is uncalibrated, not a probability (`sim.py:214-224`). P1: remove or rewire to measured values.
- **BROKEN (latent crash)**: frontend `risk_score: number` + unguarded `.toFixed()` (`AreaRiskPanel:128`, `ScoreCards:24`, `ZonePolygon:110`, `RiskMap:300`) vs backend `risk_score: null` out-of-coverage. P1 null guards.
- **PARTIAL**: `RiskMap:111-117` heat spread uses `Math.random()` (non-reproducible); unknown zones teleport to map center (`310-311`); hotspot dots are hash-derived (`geo.ts:22-54`), not detections; hex visual (4 km) ≠ backend cells (3.5 km); `ScoreCards:34-35` labels uncalibrated mean "model probability".
- **GIS**: consistent `[lat,lng]` for Leaflet; backend `geometry.coordinates` are GeoJSON `[lon,lat]` — correct today (geometry never rendered) but a trap for first `L.polyline(geometry.coordinates)` use. No CRS code anywhere (assumed WGS84/3857). No lat/lon inversion found.

## Remediation update (2026-09-18, verified)

- FIXED: fabricated "AI predicts X% within 6h" + synthetic sparkline removed
  from `GovernmentIntelligencePanel`; temporal shown as Unavailable with reason.
- FIXED: `HotspotRankingPanel.tsx` (hardcoded invented ranking, "Live signal",
  same 6h claim, no backend use) deleted; unmounted from CommandCenter. Real
  hotspot ranking remains via the backend-driven GovernmentIntelligencePanel.
- FIXED: null-crash — `fmtNum/fmtPctOpt/fmtMmOpt` + `gsDisplayState`
  (AVAILABLE/UNAVAILABLE/PROCESSING/ERROR) applied across AreaRiskPanel,
  ScoreCards ("model probability" relabeled uncalibrated), ZonePolygon,
  RiskMap, ThreatMarker, MapHoverCard.
- WIRED: `src/api/gs.ts` + `GsPointPanel` call real `GET /risk/gs_point` in
  the zone tab (null states explicit). Heat spread deterministic (no
  `Math.random`); unknown zones skipped, not teleported.
- 19/19 vitest pass (8 new), `tsc` clean, `vite build` ok.
