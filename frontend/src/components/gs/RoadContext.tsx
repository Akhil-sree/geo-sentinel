import { useNearestRoad } from "../map/RoadNetworkLayer";

/** Infrastructure exposure context for a location — real OSM geometry + honest distance.
 *  Shows road class, distance, surface, and proximity-based exposure context. */
export default function RoadContext({
  lat,
  lng,
}: {
  lat: number;
  lng: number;
}) {
  const { nearestRoad, loading } = useNearestRoad(lat, lng);

  if (loading) return null;

  const CATEGORY_LABEL: Record<string, string> = {
    major: "Major road", secondary: "Secondary road",
    local: "Local road", minor: "Minor access",
  };

  const CATEGORY_ICON: Record<string, string> = {
    major: "━━", secondary: "──", local: "┄┄", minor: "··",
  };

  return (
    <div data-testid="road-context">
      <div className="gs-label mb-2">Infrastructure Exposure</div>

      {nearestRoad && !nearestRoad.error ? (
        <div className="space-y-2">
          {/* Nearest road */}
          <div className="flex items-start gap-3">
            <div className="shrink-0 mt-0.5">
              <span className="text-[14px] font-bold" style={{ color: '#075240' }}>
                {CATEGORY_ICON[nearestRoad.category || ""] || "──"}
              </span>
            </div>
            <div className="min-w-0 flex-1">
              <p className="text-[13px] font-semibold text-gs-text truncate">
                {nearestRoad.name}
                {nearestRoad.ref ? ` (${nearestRoad.ref})` : ""}
              </p>
              <p className="text-[11px] text-gs-text-secondary mt-0.5">
                {CATEGORY_LABEL[nearestRoad.category || ""] || nearestRoad.highway}
              </p>
            </div>
          </div>

          {/* Metrics grid */}
          <div className="grid grid-cols-2 gap-2">
            <div className="rounded-md px-2 py-1.5" style={{ background: 'rgba(237,233,224,0.5)' }}>
              <div className="text-[9px] font-bold uppercase tracking-wide text-gs-text-secondary">Distance</div>
              <div className="text-[14px] font-bold tabular-nums text-gs-text">
                {nearestRoad.distance_m != null
                  ? nearestRoad.distance_m < 1000
                    ? `${nearestRoad.distance_m} m`
                    : `${(nearestRoad.distance_m / 1000).toFixed(1)} km`
                  : "—"}
              </div>
            </div>
            <div className="rounded-md px-2 py-1.5" style={{ background: 'rgba(237,233,224,0.5)' }}>
              <div className="text-[9px] font-bold uppercase tracking-wide text-gs-text-secondary">Surface</div>
              <div className="text-[13px] font-semibold text-gs-text">
                {nearestRoad.surface && nearestRoad.surface !== "Not available"
                  ? nearestRoad.surface
                  : "OSM data"}
              </div>
            </div>
          </div>

          {/* Proximity context */}
          <div className="text-[10px] text-gs-text-secondary" style={{ fontStyle: 'italic' }}>
            Proximity-based road context · Not a risk assessment
          </div>
        </div>
      ) : (
        <div className="rounded-md px-3 py-2" style={{ background: 'rgba(237,233,224,0.5)' }}>
          <p className="text-[13px] font-medium text-gs-text-secondary">
            Road route unavailable
          </p>
          <p className="text-[10px] text-gs-text-secondary/60 mt-0.5">
            No OSM road geometry found near this location
          </p>
        </div>
      )}
    </div>
  );
}
