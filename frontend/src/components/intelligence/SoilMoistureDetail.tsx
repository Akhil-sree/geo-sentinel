import { useEffect, useState } from "react";
import { getSoilMoisture } from "../../api/risk";
import { useUIStore } from "../../store/uiStore";
import { fmtPctOpt } from "../../lib/format";
import Spinner from "../common/Spinner";
import { LineChart, Line, XAxis, YAxis, Tooltip, ResponsiveContainer, ReferenceLine } from "recharts";
import type { SoilMoistureObservation } from "../../types/risk";

export default function SoilMoistureDetail() {
  const simTime = useUIStore((s) => s.simTime);
  const selectedZoneId = useUIStore((s) => s.selectedZoneId);
  const [observations, setObservations] = useState<SoilMoistureObservation[]>([]);
  const [label, setLabel] = useState("");
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (!selectedZoneId) { setObservations([]); return; }
    setLoading(true);
    getSoilMoisture(selectedZoneId)
      .then((data) => {
        setObservations(data.observations || []);
        setLabel(data.label || "");
      })
      .catch(() => setObservations([]))
      .finally(() => setLoading(false));
  }, [selectedZoneId, simTime]);

  if (!selectedZoneId) return null;

  if (loading) {
    return (
      <div className="rounded-card p-4" style={{ background: 'rgba(229, 233, 224, 0.45)', backdropFilter: 'blur(8px)', border: '1px solid rgba(255,255,255,0.18)' }}>
        <div className="flex items-center gap-2 text-[14px] text-gs-text-secondary"><Spinner /> Loading soil moisture...</div>
      </div>
    );
  }

  if (!observations.length) return null;

  const vals = observations.map((o) => o.soil_moisture).filter((v): v is number => typeof v === "number");
  const latest = observations[observations.length - 1];
  const avg = vals.length ? vals.reduce((s, v) => s + v, 0) / vals.length : null;
  const max = vals.length ? Math.max(...vals) : null;

  const chartData = observations.map((o) => ({
    time: new Date(o.timestamp).toLocaleTimeString("en-IN", { hour: "2-digit", minute: "2-digit" }),
    moisture: typeof o.soil_moisture === "number" ? +(o.soil_moisture * 100).toFixed(1) : null,
  }));

  return (
    <div className="rounded-card p-4" style={{ background: 'rgba(229, 233, 224, 0.45)', backdropFilter: 'blur(8px)', border: '1px solid rgba(255,255,255,0.18)' }}>
      <h3 className="text-[15px] font-bold text-gs-text mb-1">Soil Moisture</h3>
      <p className="text-[11px] text-gs-text-secondary mb-3 italic">{label}</p>

      {/* Current value */}
      <div className="grid grid-cols-3 gap-2 mb-3">
        <div className="text-center rounded-lg p-2" style={{ background: 'rgba(255,255,255,0.4)' }}>
          <div className="text-[18px] font-bold text-forest">{fmtPctOpt(latest.soil_moisture)}</div>
          <div className="text-[10px] text-gs-text-secondary">Current</div>
        </div>
        <div className="text-center rounded-lg p-2" style={{ background: 'rgba(255,255,255,0.4)' }}>
          <div className="text-[18px] font-bold text-gs-text">{fmtPctOpt(avg)}</div>
          <div className="text-[10px] text-gs-text-secondary">Average</div>
        </div>
        <div className="text-center rounded-lg p-2" style={{ background: 'rgba(255,255,255,0.4)' }}>
          <div className="text-[18px] font-bold text-red-700">{fmtPctOpt(max)}</div>
          <div className="text-[10px] text-gs-text-secondary">Peak</div>
        </div>
      </div>

      {/* Chart */}
      <div className="rounded-lg p-2" style={{ background: 'rgba(255,255,255,0.3)' }}>
        <ResponsiveContainer width="100%" height={120}>
          <LineChart data={chartData}>
            <XAxis dataKey="time" tick={{ fontSize: 9 }} interval="preserveStartEnd" />
            <YAxis domain={[0, 100]} tick={{ fontSize: 9 }} width={30} />
            <Tooltip
              contentStyle={{ background: 'rgba(255,255,255,0.9)', border: '1px solid #ccc', borderRadius: 8, fontSize: 11 }}
              formatter={(v: number) => [`${v}%`, "Moisture"]}
            />
            <ReferenceLine y={70} stroke="#ba1a1a" strokeDasharray="3 3" label={{ value: "Saturation", fontSize: 9, fill: "#ba1a1a" }} />
            <ReferenceLine y={40} stroke="#d97706" strokeDasharray="3 3" />
            <Line type="monotone" dataKey="moisture" stroke="#2563EB" strokeWidth={2} dot={false} />
          </LineChart>
        </ResponsiveContainer>
      </div>

      {/* Saturation warning */}
      {typeof latest.soil_moisture === "number" && latest.soil_moisture > 0.7 && (
        <div className="mt-2 rounded-lg p-2 text-[11px] font-medium text-red-700" style={{ background: 'rgba(186, 26, 26, 0.08)' }}>
          Soil moisture approaching saturation — increased landslide risk
        </div>
      )}
    </div>
  );
}
