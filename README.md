# geo-sentinel

## 3D Terrain Architecture

2D:
Leaflet + existing GIS layers (Esri World Imagery, hillshade, risk polygons)

3D:
CesiumJS
+
Open DEM terrain (no Google Maps API, no API key)
+
GEO-SENTINEL risk overlays (same zones, same selection state)

Data:
AWS Terrain Tiles (Terrarium PNG, `elevation-tiles-prod`), backed by openly
available global DEMs (SRTM / ETOPO1 / NED / ALS). Verified sample: Sohra
(Cherrapunji) decodes to ~1405 m — real Meghalaya plateau elevation.
Imagery draped on the DEM is Esri World Imagery (same source as the 2D map).

How it works:
- `frontend/src/lib/terrain.ts` — minimal Cesium `TerrainProvider` that streams
  Terrarium tiles progressively (`{z}/{x}/{y}.png`, 65x65 heightmap per tile,
  levels 0-15) and decodes `R*256 + G + B/256 - 32768` to meters. Tile failures
  resolve to parent/ellipsoid so the app never crashes.
- `frontend/src/components/map/Terrain3DView.tsx` — Cesium Viewer (created once
  per mount, destroyed on unmount), risk polygons clamped with
  `CLAMP_TO_GROUND`, shared `uiStore.selectZone()` selection, Meghalaya start
  camera (25.45, 91.1, 90 km, heading 20 deg, pitch -45 deg), 12 km selected-zone
  fly-to, visual-only exaggeration toggle (1.0x / 1.5x / 2.0x, default 1.0x).
- `frontend/scripts/copy-cesium.mjs` — copies Cesium Workers/Assets/Widgets to
  `public/cesium` on `predev`/`prebuild` (git-ignored).
- `frontend/scripts/verify-terrain.mjs` — proves the DEM is real: fetches the
  Sohra tile and asserts plateau elevation (run: `node scripts/verify-terrain.mjs`).

No Google Maps API required. No `VITE_GOOGLE_MAPS_API_KEY`.
If elevation tiles are unreachable, the viewer falls back to the ellipsoid globe
with a non-blocking "3D elevation data unavailable" badge; the 2D map is unaffected.