import { SEV_COLOR, SEV_LABEL } from "../../lib/severity";

export default function MapLegend() {
  return (
    <div className="leaflet-bottom leaflet-left">
      <div className="m-2 rounded bg-white p-2.5 text-[10px] shadow-md w-32">
        <h4 className="mb-1.5 font-bold text-[#1b1c17]">RISK LEVEL</h4>
        {Object.entries(SEV_COLOR).map(([k, c]) => (
          <div key={k} className="flex items-center gap-2 py-0.5">
            <i className="h-2 w-2.5 rounded-full" style={{ background: c }} />
            <span className="text-[#1b1c17]">{SEV_LABEL[k as keyof typeof SEV_COLOR]}</span>
          </div>
        ))}
        <div className="mt-1 text-[9px] text-[#707973]">zone-level advisory (demo)</div>
      </div>
    </div>
  );
}
