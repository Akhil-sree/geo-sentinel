import { SEV_COLOR, SEV_LABEL } from "../../lib/severity";

const SLOPE_STATES = [
  { state: "STABLE", color: "#245c45" },
  { state: "STRESSED", color: "#d97706" },
  { state: "DEGRADING", color: "#ea580c" },
  { state: "CRITICAL", color: "#ba1a1a" },
];

export default function MapLegend() {
  return (
    <div className="leaflet-bottom leaflet-left">
      <div className="m-2 rounded bg-white p-2.5 text-[10px] shadow-md w-40">
        <h4 className="mb-1 font-bold text-[#1b1c17]">SLOPE STATE</h4>
        {SLOPE_STATES.map((s) => (
          <div key={s.state} className="flex items-center gap-2 py-0.5">
            <i className="h-2 w-2.5 rounded-full" style={{ background: s.color }} />
            <span className="text-[#1b1c17]">{s.state.charAt(0) + s.state.slice(1).toLowerCase()}</span>
          </div>
        ))}
        <div className="my-1 border-t border-[#e4e3db]" />
        <h4 className="mb-1 font-bold text-[#1b1c17]">SEVERITY</h4>
        {Object.entries(SEV_COLOR).map(([k, c]) => (
          <div key={k} className="flex items-center gap-2 py-0.5">
            <i className="h-2 w-2.5 rounded-full" style={{ background: c }} />
            <span className="text-[#1b1c17]">{SEV_LABEL[k as keyof typeof SEV_COLOR]}</span>
          </div>
        ))}
        <div className="my-1 border-t border-[#e4e3db]" />
        <h4 className="mb-1 font-bold text-[#1b1c17]">RISK FIELD</h4>
        <div className="h-3 w-full rounded" style={{
          background: "linear-gradient(to right, #245c45, #d97706, #ea580c, #ba1a1a, #7f1d1d)",
        }} />
        <div className="flex justify-between text-[7px] text-[#707973] mt-0.5">
          <span>Low</span>
          <span>High</span>
        </div>
        <div className="mt-1 text-[8px] text-[#707973]">zone-level advisory (demo)</div>
      </div>
    </div>
  );
}
