import { useEffect, useState } from "react";
import Card from "../components/common/Card";
import { getSensors, getExposure } from "../api/ops";

export default function SensorsPage() {
  const [sensors, setSensors] = useState<any[]>([]);
  const [exposure, setExposure] = useState<any>(null);
  useEffect(() => {
    getSensors().then((d) => setSensors(d.sensors ?? [])).catch(() => {});
    getExposure().then(setExposure).catch(() => {});
  }, []);
  return (
    <main className="overflow-y-auto bg-gs-bg p-6">
      <h1 className="mb-4 text-[18px] font-semibold text-gs-text">Sensors & Exposure</h1>
      <div className="grid gap-4 md:grid-cols-2">
        <Card title="Sensor registry — ONLINE / STALE / OFFLINE">
          {sensors.length === 0 && (
            <p className="text-[12px] text-gs-text-secondary">
              No sensors registered yet. POST /api/sensors/readings to ingest IoT readings
              (soil-moisture, rainfall, tilt, pore-pressure). Modeled fallback in use.
            </p>
          )}
          {sensors.map((s) => (
            <div key={s.sensor_id} className="flex justify-between border-b border-gs-border py-1.5 text-[12px]">
              <span>{s.sensor_id} · {s.type} · {s.zone_id}</span>
              <b className={s.health === "ONLINE" ? "text-forest" : "text-risk-high"}>{s.health}</b>
            </div>
          ))}
        </Card>
        <Card title="Villages & infrastructure — STATIC indicative registry">
          <p className="mb-2 text-[11px] text-gs-text-secondary">{exposure?.status}</p>
          {(exposure?.villages ?? []).map((v: any) => (
            <div key={v.name} className="flex justify-between py-1 text-[12px]">
              <span>{v.name} ({v.zone_id}) · pop {v.population}</span>
              <span>{v.criticality}</span>
            </div>
          ))}
          <h4 className="mt-3 text-[11px] font-semibold">Infrastructure</h4>
          {(exposure?.infrastructure ?? []).map((i: any) => (
            <div key={i.name} className="flex justify-between py-1 text-[12px]">
              <span>{i.name} · {i.kind} ({i.zone_id})</span>
              <span>{i.criticality}</span>
            </div>
          ))}
        </Card>
      </div>
    </main>
  );
}
