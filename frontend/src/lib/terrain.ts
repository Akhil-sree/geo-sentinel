import * as Cesium from "cesium";

// Open DEM terrain for the 3D view. No API key, no Google services.
//
// Source: AWS Terrain Tiles (Terrarium PNG encoding), backed by openly
// available global DEMs (SRTM, ETOPO1, NED, ALS...). Same XYZ slippy grid as
// the 2D map, so Cesium tile (x, y, level) maps 1:1 to the tile URL.
// Docs: https://registry.opendata.aws/terrain-tiles/
export const TERRARIUM_URL = "https://s3.amazonaws.com/elevation-tiles-prod/terrarium";
export const TERRAIN_CREDIT = "Terrain: AWS Terrain Tiles (SRTM/ETOPO open DEM)";
export const MAX_TERRAIN_LEVEL = 15;
const SAMPLES = 65; // heightmap grid per tile (matches Cesium's default)

export function terrariumTileUrl(x: number, y: number, level: number): string {
  return `${TERRARIUM_URL}/${level}/${x}/${y}.png`;
}

/** Terrarium decoding: height = R * 256 + G + B / 256 - 32768 (meters). */
export function decodeTerrariumPixel(r: number, g: number, b: number): number {
  return r * 256 + g + b / 256 - 32768;
}

async function fetchHeights(x: number, y: number, level: number): Promise<Float32Array> {
  const res = await fetch(terrariumTileUrl(x, y, level), { mode: "cors" });
  if (!res.ok) throw new Error(`terrain tile ${level}/${x}/${y}: HTTP ${res.status}`);
  const blob = await res.blob();
  const bitmap = await createImageBitmap(blob);
  try {
    const canvas = document.createElement("canvas");
    canvas.width = SAMPLES;
    canvas.height = SAMPLES;
    const ctx = canvas.getContext("2d", { willReadFrequently: true });
    if (!ctx) throw new Error("2d canvas unavailable");
    ctx.drawImage(bitmap, 0, 0, SAMPLES, SAMPLES);
    // Image row 0 = north; Cesium heightmap row 0 = north. Direct copy.
    const pixels = ctx.getImageData(0, 0, SAMPLES, SAMPLES).data;
    const heights = new Float32Array(SAMPLES * SAMPLES);
    for (let i = 0; i < SAMPLES * SAMPLES; i++) {
      heights[i] = decodeTerrariumPixel(pixels[i * 4], pixels[i * 4 + 1], pixels[i * 4 + 2]);
    }
    return heights;
  } finally {
    bitmap.close();
  }
}

/**
 * Minimal Cesium TerrainProvider streaming open DEM tiles progressively.
 * Tile fetch failures resolve to undefined (Cesium renders parent/ellipsoid
 * there) and are reported via onTileError for a non-blocking status badge.
 */
export class TerrariumTerrainProvider {
  readonly tilingScheme = new Cesium.WebMercatorTilingScheme();
  readonly errorEvent = new Cesium.Event();
  readonly credit = new Cesium.Credit(TERRAIN_CREDIT);
  readonly hasWaterMask = false;
  readonly hasVertexNormals = false;
  readonly availability: Cesium.TileAvailability | undefined = undefined;
  private readonly levelZeroError: number;

  constructor(private readonly onTileError?: () => void) {
    this.levelZeroError = Cesium.TerrainProvider.getEstimatedLevelZeroGeometricErrorForAHeightmap(
      this.tilingScheme.ellipsoid,
      SAMPLES,
      this.tilingScheme.getNumberOfXTilesAtLevel(0)
    );
  }

  getLevelMaximumGeometricError(level: number): number {
    return this.levelZeroError / (1 << level);
  }

  getTileDataAvailable(_x: number, _y: number, level: number): boolean {
    return level <= MAX_TERRAIN_LEVEL;
  }

  loadTileDataAvailability(_x: number, _y: number, _level: number): Promise<void> | undefined {
    return undefined; // no availability metadata; every tile URL is addressable
  }

  requestTileGeometry(
    x: number,
    y: number,
    level: number
  ): Promise<Cesium.TerrainData> | undefined {
    if (level > MAX_TERRAIN_LEVEL) return undefined;
    return fetchHeights(x, y, level)
      .then(
        (heights) =>
          new Cesium.HeightmapTerrainData({
            buffer: heights,
            width: SAMPLES,
            height: SAMPLES,
            childTileMask: 15,
          })
      )
      .catch((e: unknown) => {
        this.onTileError?.();
        this.errorEvent.raiseEvent(e);
        return undefined as unknown as Cesium.TerrainData;
      });
  }
}
