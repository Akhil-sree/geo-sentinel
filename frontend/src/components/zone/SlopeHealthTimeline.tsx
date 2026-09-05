import { useEffect, useState } from "react";
import { getRiskTrajectory } from "../../api/risk";
import type { TrajectoryPoint } from "../../types/risk";

const STATE_COLORS: Record<string, string> = {
  STABLE: "#245c45",
  STRESSED: "#d97706",
  DEGRADING: "#ea580c",
  CRITICAL: "#ba1a1a",
};

export default function SlopeHealthTimeline({ zoneId }: { zoneId: string }) {
  const [points, setPoints] = useState<TrajectoryPoint[]>([]);
  const [animStep, setAnimStep] = useState(-1);

  useEffect(() => {
    getRiskTrajectory(zoneId)
      .then((r) => {
        const trajectory = r.trajectory;
        setPoints(trajectory);
        setAnimStep(-1);
        trajectory.forEach((_, i) => {
          setTimeout(() => setAnimStep(i), i * 120);
        });
      })
      .catch(() => {});
  }, [zoneId]);

  if (points.length === 0) return null;

  const displayPoints = points.filter((_, i) =>
    i === 0 || i === points.length - 1 || i % Math.max(1, Math.floor(points.length / 6)) === 0
  );

  return (
    <div className="rounded bg-white p-2 shadow-sm">
      <p className="mb-1.5 text-[10px] font-bold text-[#1b1c17]">
        SLOPE DIGITAL HEALTH
      </p>
      <p className="mb-2 text-[8px] text-[#707973]">
        State progression over observation window
      </p>

      <div className="flex items-center gap-0.5 overflow-x-auto pb-1">
        {displayPoints.map((p, i) => {
          const isActive = i <= animStep;
          const color = STATE_COLORS[p.slope_state] ?? "#707973";
          const time = new Date(p.timestamp).getHours() + "h";

          return (
            <div key={i} className="flex flex-col items-center min-w-[40px]">
              <span className={`text-[8px] font-bold ${isActive ? "animate-count" : "opacity-30"}`}
                style={{ color: isActive ? color : "#ccc" }}>
                {p.slope_state_label ?? p.slope_state}
              </span>
              <div className={`my-1 h-2 w-8 rounded-full ${isActive ? "" : "opacity-30"}`}
                style={{ backgroundColor: isActive ? color : "#e4e3db" }} />
              <span className="text-[7px] text-[#707973]">{time}</span>
              {i < displayPoints.length - 1 && (
                <div className="absolute" style={{ display: "none" }}>→</div>
              )}
            </div>
          );
        })}
      </div>

      {/* Final state highlight */}
      {points.length > 0 && (
        <div className="mt-2 flex items-center gap-2 rounded border p-1.5"
          style={{ borderColor: STATE_COLORS[points[points.length - 1].slope_state] + "40" }}>
          <span className="text-[8px] font-bold text-[#707973]">NOW:</span>
          <span className="rounded px-1.5 py-0.5 text-[9px] font-bold text-white"
            style={{ backgroundColor: STATE_COLORS[points[points.length - 1].slope_state] }}>
            {points[points.length - 1].slope_state_label ?? points[points.length - 1].slope_state}
          </span>
          <span className="text-[9px] font-bold" style={{ color: STATE_COLORS[points[points.length - 1].slope_state] }}>
            {(points[points.length - 1].risk_score * 100).toFixed(0)}%
          </span>
        </div>
      )}
    </div>
  );
}
