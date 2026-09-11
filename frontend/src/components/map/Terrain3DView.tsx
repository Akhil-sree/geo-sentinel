import { useEffect, useRef, useState } from "react";
import * as Cesium from "cesium";
import "cesium/Build/Cesium/Widgets/widgets.css";
import { SEV_COLOR, SEV_FILL_OPACITY } from "../../lib/severity";
import { zonePolygonCoords } from "../../lib/geo";
import { TerrariumTerrainProvider } from "../../lib/terrain";
import type { Zone } from "../../api/zones";
import type { ZoneRisk } from "../../types/risk";
import type { RoadSegment } from "../../api/dashboard";

// Open DEM 3D terrain: Cesium globe + AWS Terrain Tiles (Terrarium, open DEMs)
// + Esri World Imagery (same satellite source as the 2D map). No API keys.

// Matches RiskMap CENTER [25.45, 91.1] (Meghalaya).
const MEGHALAYA = { lat: 25.45, lng: 91.1 };

/** Slope-state fill opacity mirrors ZonePolygon (2D visual language). */
const STATE_OPACITY: Record<string, number> = {
  STABLE: 0.15,
  STRESSED: 0.3,
  DEGRADING: 0.45,
  CRITICAL: 0.6,
};

const EXAGGERATIONS = [1.0, 1.5, 2.0] as const;

function riskStyle(risk: ZoneRisk | undefined): { color: string; opacity: number } {
  if (!risk) return { color: "#707973", opacity: 0.15 };
  const color = risk.slope_state_color ?? SEV_COLOR[risk.severity] ?? "#707973";
  const opacity = risk.slope_state
    ? STATE_OPACITY[risk.slope_state] ?? SEV_FILL_OPACITY[risk.severity]
    : SEV_FILL_OPACITY[risk.severity];
  return { color, opacity };
}

interface Terrain3DViewProps {
  zones: Zone[];
  risks: ZoneRisk[];
  roads: RoadSegment[];
  selectedId: string | null;
  onSelect: (id: string) => void;
  onBackTo2D: () => void;
}

export default function Terrain3DView({
  zones,
  risks,
  roads,
  selectedId,
  onSelect,
  onBackTo2D,
}: Terrain3DViewProps) {
  const containerRef = useRef<HTMLDivElement | null>(null);
  const viewerRef = useRef<Cesium.Viewer | null>(null);
  const onSelectRef = useRef(onSelect);
  onSelectRef.current = onSelect;
  const [status, setStatus] = useState<"loading" | "ready" | "error">("loading");
  const [terrainMissing, setTerrainMissing] = useState(false);
  const [showReadyBadge, setShowReadyBadge] = useState(false);
  const [exaggeration, setExaggeration] = useState<number>(1.0);

  // Init once per mount; destroy on unmount (no duplicate viewers, no leaks).
  useEffect(() => {
    let cancelled = false;
    let viewer: Cesium.Viewer | null = null;

    try {
      (window as unknown as Record<string, unknown>).CESIUM_BASE_URL = "/cesium/";

      viewer = new Cesium.Viewer(containerRef.current as HTMLDivElement, {
        animation: false,
        baseLayerPicker: false,
        fullscreenButton: false,
        geocoder: false,
        homeButton: false,
        infoBox: false,
        sceneModePicker: false,
        selectionIndicator: false,
        timeline: false,
        navigationHelpButton: false,
        baseLayer: false, // imagery added explicitly below (same source as 2D)
      });
      // Keep default camera controls (orbit / tilt / zoom / touch / pinch).
      viewer.scene.screenSpaceCameraController.enableCollisionDetection = false;
      if (cancelled) {
        viewer.destroy();
        return () => {};
      }
      viewerRef.current = viewer;

      // Open DEM terrain (progressive streaming). Failures fall back to the
      // ellipsoid globe — the app keeps working, badge informs the user.
      viewer.terrainProvider = new TerrariumTerrainProvider(() => {
        if (!cancelled) setTerrainMissing(true);
      });

      // Satellite imagery draped on the DEM (same Esri source as the 2D map).
      viewer.imageryLayers.addImageryProvider(
        new Cesium.UrlTemplateImageryProvider({
          url: "https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}",
          credit: "Esri World Imagery",
        })
      );

      setStatus("ready");
      setShowReadyBadge(true);
      window.setTimeout(() => {
        if (!cancelled) setShowReadyBadge(false);
      }, 3000);
      flyTo(viewer, selectedIdRef.current, zonesRef.current, false);

      // Click a risk polygon -> shared selected-zone state (same panel as 2D).
      viewer.screenSpaceEventHandler.setInputAction((movement: { position: Cesium.Cartesian2 }) => {
        const picked = viewer?.scene.pick(movement.position) as unknown as
          | { id?: { id?: string } }
          | undefined;
        const id = picked?.id?.id;
        if (id && typeof id === "string" && id.startsWith("gs-zone-")) {
          onSelectRef.current(id.replace("gs-zone-", ""));
        }
      }, Cesium.ScreenSpaceEventType.LEFT_CLICK);
    } catch {
      if (!cancelled) setStatus("error");
    }

    return () => {
      cancelled = true;
      viewerRef.current = null;
      if (viewer && !viewer.isDestroyed()) viewer.destroy();
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // Visual-only terrain exaggeration (never touches risk calculations).
  useEffect(() => {
    const viewer = viewerRef.current;
    if (viewer && !viewer.isDestroyed()) viewer.scene.verticalExaggeration = exaggeration;
  }, [exaggeration, status]);

  // Latest props for callbacks/effects that must not recreate the viewer.
  const zonesRef = useRef(zones);
  zonesRef.current = zones;
  const risksRef = useRef(risks);
  risksRef.current = risks;
  const roadsRef = useRef(roads);
  roadsRef.current = roads;
  const selectedIdRef = useRef(selectedId);
  selectedIdRef.current = selectedId;

  // Rebuild risk overlays when data/selection changes (viewer persists).
  // Future GIS layers (SAR, rainfall/soil rasters, DEM slope, drainage, roads,
  // evacuation routes) plug in here as additional entities/data sources.
  useEffect(() => {
    const viewer = viewerRef.current;
    if (!viewer || viewer.isDestroyed() || status !== "ready") return;
    viewer.entities.removeAll();
    const riskByZone = new Map(risks.map((r) => [r.zone_id, r]));
    const zoneById = new Map(zones.map((z) => [z.id, z]));

    for (const z of zones) {
      const risk = riskByZone.get(z.id);
      const { color, opacity } = riskStyle(risk);
      const isSelected = z.id === selectedId;
      const ring = zonePolygonCoords(z).flatMap(([lat, lng]) => [lng, lat]);
      const cesiumColor = Cesium.Color.fromCssColorString(color);
      viewer.entities.add(
        new Cesium.Entity({
          id: `gs-zone-${z.id}`,
          name: z.name,
          polygon: new Cesium.PolygonGraphics({
            hierarchy: new Cesium.PolygonHierarchy(
              Cesium.Cartesian3.fromDegreesArray(ring)
            ),
            material: cesiumColor.withAlpha(isSelected ? Math.min(1, opacity + 0.25) : opacity),
            outline: true,
            outlineColor: isSelected
              ? Cesium.Color.WHITE
              : cesiumColor.withAlpha(1),
            outlineWidth: isSelected ? 3 : risk?.escalated ? 2.5 : 1,
            // Clamp to the DEM surface (correct mechanism for terrain providers).
            heightReference: Cesium.HeightReference.CLAMP_TO_GROUND,
            classificationType: Cesium.ClassificationType.BOTH,
          }),
        })
      );
      // Selected-zone outline drawn as a clamped polyline (always visible).
      if (isSelected) {
        const loop = [...ring, ring[0], ring[1]];
        viewer.entities.add(
          new Cesium.Entity({
            id: `gs-zone-outline-${z.id}`,
            polyline: new Cesium.PolylineGraphics({
              positions: Cesium.Cartesian3.fromDegreesArray(loop),
              width: 3,
              material: Cesium.Color.WHITE,
              clampToGround: true,
            }),
          })
        );
      }
      viewer.entities.add(
        new Cesium.Entity({
          id: `gs-label-${z.id}`,
          position: Cesium.Cartesian3.fromDegrees(z.lng, z.lat, (z.elevation ?? 500) + 900),
          label: new Cesium.LabelGraphics({
            text: z.name,
            font: "bold 12px sans-serif",
            fillColor: Cesium.Color.WHITE,
            outlineColor: Cesium.Color.BLACK,
            outlineWidth: 2,
            style: Cesium.LabelStyle.FILL_AND_OUTLINE,
            disableDepthTestDistance: 50000,
          }),
        })
      );
      if (risk?.slope_state === "CRITICAL" || risk?.severity === "VERY_HIGH") {
        viewer.entities.add(
          new Cesium.Entity({
            id: `gs-marker-${z.id}`,
            position: Cesium.Cartesian3.fromDegrees(z.lng, z.lat, (z.elevation ?? 500) + 600),
            point: new Cesium.PointGraphics({
              pixelSize: isSelected ? 14 : 10,
              color: Cesium.Color.fromCssColorString("#ba1a1a").withAlpha(0.9),
              outlineColor: Cesium.Color.WHITE,
              outlineWidth: 2,
              disableDepthTestDistance: 50000,
            }),
          })
        );
      }
    }

    for (const r of roads) {
      if (r.status === "OPEN") continue;
      const from = zoneById.get(r.from_zone);
      const to = zoneById.get(r.to_zone);
      if (!from || !to) continue;
      const color =
        r.status === "BLOCKED" ? "#ba1a1a" : r.status === "DAMAGED" ? "#ea580c" : "#d97706";
      viewer.entities.add(
        new Cesium.Entity({
          id: `gs-road-${from.id}-${to.id}`,
          polyline: new Cesium.PolylineGraphics({
            positions: Cesium.Cartesian3.fromDegreesArray([from.lng, from.lat, to.lng, to.lat]),
            width: r.status === "BLOCKED" ? 4 : 2.5,
            material: Cesium.Color.fromCssColorString(color).withAlpha(0.85),
            clampToGround: true,
          }),
        })
      );
    }
  }, [status, zones, risks, roads, selectedId]);

  // Selected zone changes (e.g. picked in 2D first) -> fly 3D camera to it.
  useEffect(() => {
    const viewer = viewerRef.current;
    if (!viewer || viewer.isDestroyed() || status !== "ready") return;
    flyTo(viewer, selectedId, zones, true);
  }, [status, selectedId, zones]);

  return (
    <div className="relative h-full w-full">
      <div ref={containerRef} className="absolute inset-0" />

      {status === "loading" && (
        <div className="pointer-events-none absolute top-4 left-4 z-[1000] rounded-lg bg-black/70 px-3 py-2 text-[11px] font-bold text-white backdrop-blur-sm">
          Loading 3D terrain…
        </div>
      )}
      {status === "ready" && showReadyBadge && !terrainMissing && (
        <div className="pointer-events-none absolute top-4 left-4 z-[1000] rounded-lg bg-black/70 px-3 py-2 text-[11px] font-bold text-white backdrop-blur-sm">
          3D Terrain Ready
        </div>
      )}
      {status === "ready" && terrainMissing && (
        <div className="pointer-events-none absolute top-4 left-4 z-[1000] rounded-lg bg-black/70 px-3 py-2 text-[11px] font-bold text-white backdrop-blur-sm">
          3D elevation data unavailable
        </div>
      )}
      {status === "error" && (
        <div className="absolute top-4 left-4 z-[1000] max-w-[320px] rounded-lg bg-black/75 px-3 py-2 text-[11px] font-bold text-white backdrop-blur-sm">
          <p>3D terrain unavailable</p>
          <button
            onClick={onBackTo2D}
            className="mt-2 rounded bg-white/15 px-2 py-1 hover:bg-white/25"
          >
            Back to 2D
          </button>
        </div>
      )}

      {status === "ready" && (
        <div className="absolute bottom-4 left-4 z-[1000] flex flex-col gap-1.5">
          <div className="pointer-events-none rounded-lg bg-black/70 px-2.5 py-1 text-[9px] font-bold tracking-wide text-white/85 backdrop-blur-sm">
            REAL ELEVATION · DEM: open (SRTM/ETOPO)
          </div>
          <div className="flex items-center gap-1 rounded-lg bg-black/70 px-2 py-1 backdrop-blur-sm">
            <span className="mr-1 text-[9px] font-bold text-white/70">EXAGGERATION</span>
            {EXAGGERATIONS.map((v) => (
              <button
                key={v}
                onClick={() => setExaggeration(v)}
                className={`rounded px-1.5 py-0.5 text-[9px] font-bold transition-colors ${
                  exaggeration === v ? "bg-white text-black" : "text-white/70 hover:bg-white/15"
                }`}
              >
                {v.toFixed(1)}x
              </button>
            ))}
          </div>
        </div>
      )}

      <button
        onClick={onBackTo2D}
        className="absolute top-4 right-4 z-[1000] flex items-center gap-1.5 rounded-lg border border-white/20 bg-black/70 px-3 py-2 text-[10px] font-bold text-white shadow-lg backdrop-blur-sm transition hover:bg-black/90"
      >
        ▣ 2D VIEW
      </button>
    </div>
  );
}

function flyTo(
  viewer: Cesium.Viewer,
  selectedId: string | null,
  zones: Zone[],
  animate: boolean
) {
  if (viewer.isDestroyed()) return;
  const zone = selectedId ? zones.find((z) => z.id === selectedId) : null;
  const target = zone ?? MEGHALAYA;
  viewer.camera.flyTo({
    destination: Cesium.Cartesian3.fromDegrees(
      target.lng,
      target.lat,
      zone ? 12000 : 90000
    ),
    orientation: {
      heading: Cesium.Math.toRadians(20),
      pitch: Cesium.Math.toRadians(-45),
      roll: 0,
    },
    duration: animate && zone ? 1.5 : 0,
  });
}
