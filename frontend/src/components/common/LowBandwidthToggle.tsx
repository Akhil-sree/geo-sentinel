import { useUIStore } from "../../store/uiStore";

export default function LowBandwidthToggle() {
  const lowBandwidth = useUIStore((s) => s.lowBandwidth);
  const toggle = useUIStore((s) => s.toggleLowBandwidth);

  return (
    <button
      onClick={toggle}
      className={`flex items-center gap-1.5 rounded-full px-2.5 py-1 text-[9px] font-bold transition-colors ${
        lowBandwidth
          ? "bg-[#d97706]/15 text-[#92400e] ring-1 ring-[#d97706]/30"
          : "bg-[#f0eee6] text-[#707973] hover:bg-[#e4e3db]"
      }`}
      title={lowBandwidth ? "Low bandwidth mode ON — tap to disable" : "Enable low bandwidth mode for remote areas"}
    >
      <span className="text-[10px]">{lowBandwidth ? "\u26A1" : "\u2B50"}</span>
      {lowBandwidth ? "LOW BW" : "FULL BW"}
    </button>
  );
}
