import { useState } from "react";
import { TileLayer } from "react-leaflet";

/**
 * Configurable basemap with graceful degradation (P2):
 * - primary URL from VITE_TILE_URL (default: Esri World Imagery)
 * - on tile errors, falls back once to OSM standard tiles
 * - if the fallback also fails, shows a BASEMAP UNAVAILABLE chip instead
 *   of leaving a silently blank map. GIS overlays keep working.
 * No offline tile bundle exists — offline mode covers report queueing only.
 */

export const DEFAULT_TILE_URL =
  "https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}";
export const FALLBACK_TILE_URL = "https://tile.openstreetmap.org/{z}/{x}/{y}.png";

export function resolveTileUrls(envUrl?: string): { primary: string; fallback: string } {
  const primary = (envUrl ?? "").trim() || DEFAULT_TILE_URL;
  // Avoid a pointless fallback loop when the user already points at OSM.
  const fallback = primary === FALLBACK_TILE_URL ? "" : FALLBACK_TILE_URL;
  return { primary, fallback };
}

export function tileEnvUrl(): string {
  return (import.meta.env.VITE_TILE_URL as string | undefined) ?? "";
}

export default function BasemapLayer() {
  const { primary, fallback } = resolveTileUrls(tileEnvUrl());
  const [url, setUrl] = useState(primary);
  const [dead, setDead] = useState(false);
  const usingFallback = fallback !== "" && url === fallback;

  return (
    <>
      {!dead && (
        <TileLayer
          attribution='Tiles &copy; Esri &mdash; Source: Esri, Maxar, Earthstar Geographics | &copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>'
          url={url}
          eventHandlers={{
            tileerror: () => {
              if (!usingFallback && fallback !== "") setUrl(fallback);
              else setDead(true);
            },
          }}
        />
      )}
      {dead && (
        <div
          data-testid="basemap-unavailable"
          style={{
            position: "absolute",
            top: 12,
            left: "50%",
            transform: "translateX(-50%)",
            zIndex: 500,
            background: "#78350f",
            color: "white",
            padding: "6px 14px",
            borderRadius: 6,
            fontSize: 12,
            fontWeight: 600,
          }}
        >
          BASEMAP UNAVAILABLE — check network or set VITE_TILE_URL. GIS overlays still work.
        </div>
      )}
    </>
  );
}
