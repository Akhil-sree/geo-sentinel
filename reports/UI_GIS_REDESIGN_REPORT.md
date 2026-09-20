# UI_GIS_REDESIGN_REPORT.md — GEO-SENTINEL command-center redesign (2026-09-18)

Visual + GIS presentation upgrade. No architecture rewrite, no ML change, no
contract break (one additive `geometry_kind` field). All verified below.

## UI changes

- **Header**: two tall rows → compact 72px bar (identity + centered brand +
  demo badge + real IST clock + static status dot) + slim 40px nav. Removed
  "Power to Empower" slogan and the ping animation. All 12 routes preserved.
- **Alert banner**: giant red block → 37px amber advisory bar with the REAL
  escalated count ("8 locations require attention"); red reserved for critical.
- **Data status**: repetitive badges → compact DATA SOURCES list with dot
  semantics (LIVE green / SIMULATED amber / MODELED slate / DEMO gray +
  "NOT USED" for SAR, which is excluded from risk). Same honest backend data.
- **Right panel**: AreaRiskPanel rewritten around the selected location —
  name/district, severity pill, 40px MODEL-GENERATED RISK SCORE x/1.00 with
  "advisory indicator, not a probability", and indicator bars built ONLY from
  backend fields (TERRAIN ← static_score, RAINFALL 72h ← rainfall_72h against
  the real 220 mm escalation threshold, SOIL ← soil_moisture, SAR ← explicit
  "Unavailable · demo, excluded from risk"). Nulls render as "—".
- **Report action**: oversized button → compact "+ Report a Landslide"
  secondary action; workflow untouched.
- **Bottom strip**: new operational bar with live values (last-update time,
  monitored-zone count, active-advisory count, demo mode).
- **Legend**: large 4-section card → compact collapsible (risk levels + risk
  zones + road status point). **Layer control**: new, functional checkboxes
  for the 6 layers that actually exist (zones, hotspots, threats, roads,
  heat, reports). No rivers/terrain/admin toggles — those sources don't exist.
- **Markers**: hotspot dots ~60% smaller with thin halos; threat markers
  smaller; pulse animation reserved for the SELECTED marker only.
- **2D/3D**: kept as-is (already honestly labeled "visual tilt only").
- **Responsive**: sidebar becomes an overlay drawer ≤860px (map stays
  visible); zero horizontal overflow at 800px (verified); focus-visible
  outlines added for keyboard navigation.
- Removed the dark vignette overlay (visual noise).

## GIS changes

**Are roads actual road geometry?** Zone-to-zone road LINE geometry does not
exist in this project (verified): the OSM PBF feeds only ML node features,
`roads_v2.json` holds unordered thinned points, and the 8 seeded segments
carry real midpoints + lengths but no polylines. Reconstructing routes from
unordered points would fabricate geography — refused per GIS-correctness rule.

**What was done instead (all honest):**
- REMOVED the only fake-road rendering: `RoadNetworkLayer` straight
  centroid-to-centroid chords (deleted `L.polyline` — the sole such call in
  the frontend).
- Road layer now renders STATUS MARKERS at the 8 REAL segment midpoints,
  sized by the REAL road class (national/state/district/village) and colored
  by REAL status (OPEN/BLOCKED/DAMAGED/UNDER_REPAIR), with tooltips
  (name, zones, class, length, status, blockage reason, demo-network note).
  Markers use a dedicated SVG renderer (map is canvas-preferred) and support
  route highlight by segment id/name.
- **Point-to-road snapping**: new `lib/roads.ts` (`haversineKm`,
  `snapToRoad` → `{original, snapped, segment_id, segment_name,
  road_distance_m}`, null on failure). Original coordinates always preserved;
  snapped point is always a real midpoint, never an interpolation.
- **Route display**: evacuation panel stays text (names/distances/statuses);
  map highlights used segments' real markers; no connecting lines anywhere.
  Backend adds additive `geometry_kind: "schematic-centroid-demo"`
  (or `"unavailable-no-passable-route"`) so no future renderer mistakes
  centroid chords for surveyed geometry. Route failure already returned
  `route_available: false` + reason — kept and tested.
- **Selected-location road context**: new `RoadContext` card in the zone tab
  ("Nearest road: Sohra-Mawsynram Link · 6.0 km …" or "Road route
  unavailable").
- **Leaflet control fix**: layer/legend panels inside the map container now
  use `L.DomEvent.disableClickPropagation/scrollPropagation` (checkbox clicks
  were swallowed by map drag handling — found by E2E, fixed, re-verified).
- **Layer overlap fix**: layer panel moved below the 2D/3D controls
  (z-index swallow — found by E2E, fixed, re-verified).
- Coordinate order audited: Leaflet `[lat,lng]` everywhere; backend GeoJSON
  `[lon,lat]`DJ only in the (unrendered) schematic geometry, as documented;
  selection flies to real zone coordinates.

**Can any straight-line fake road remain?** No: repo-wide, the only
`L.polyline` was removed; backend geometry is labeled schematic and unrendered;
E2E asserts 8 road markers vs 0 road paths in the live DOM.

## Files changed

- Backend: `app/services/route_optimizer.py` (+`geometry_kind`, honesty
  comment), `tests/test_road_geometry.py` (new, 5 tests).
- Frontend: `lib/roads.ts` + `tests/roads.test.ts` (new),
  `components/map/{RoadNetworkLayer (rewrite),LayerControl (new),MapLegend
  (rewrite),RiskMap,HotspotMarker,ThreatMarker,SimulationOverlay}`,
  `components/layout/{TopBar (rewrite),DataFreshnessBar}`,
  `components/area/AreaRiskPanel (rewrite)`,
  `components/gs/RoadContext (new)`, `components/intelligence/
  {CriticalSlopeCard,EmergencyPrioritiesPanel,SeveritySummaryPanel,
  WeatherOverviewPanel,CellRiskGrid,SoilMoistureDetail}`,
  `pages/CommandCenter`, `index.css` (drawer + focus).
- No Docker/backend-config/API-contract changes (additive field only).

## Tests (actual results, 2026-09-18)

- Backend: **132 passed, 1 skipped** (127 + 5 road-geometry).
- Frontend: **24 passed** (19 + 5 roads lib). `tsc` clean. `vite build` ok.
- Docker: images rebuilt, `down` + `up` recovery verified, all healthy.
- API: 27/27 container checks pass (re-run after changes).
- Browser E2E: original map workflow PASS (re-run) + redesign acceptance
  **23/23 PASS** (header/nav sizes, advisory content, strip, 6 layers, no
  fake layers, roads toggle, 8 markers vs 0 paths, GsPointPanel AVAILABLE,
  RoadContext, legend collapse, 800px overflow, geometry_kind, zero
  console/page errors).

## Remaining limitations

- No surveyed road LINE geometry exists: routes remain schematic at the
  graph level (honestly labeled). Real OSM edge import (osmium/osmnx,
  currently NOT_INSTALLED) is the documented next step, not this change.
- Zone polygons remain schematic 4 km hexagons (no district-boundary source
  in repo); legend presents them as risk zones, not boundaries.
- Heat overlay uses deterministic hash spread (documented demo visual).
- Basemap tiles need external network (Esri); offline tiles out of scope.
