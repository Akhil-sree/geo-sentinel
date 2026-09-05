import { useState, useRef, useCallback } from "react";

interface SARComparisonProps {
  acquisitionDate: string;
  previousDate: string;
  changeScore: number;
  honestyNote: string;
}

function SARImage({ label, date, changeScore, isAfter }: { label: string; date: string; changeScore: number; isAfter: boolean }) {
  const intensity = isAfter ? Math.min(1, changeScore * 1.5) : 0.3;
  return (
    <div className="relative h-full w-full overflow-hidden">
      {/* Simulated SAR imagery with noise pattern */}
      <div className="absolute inset-0" style={{
        background: `
          radial-gradient(ellipse at 30% 40%, rgba(${isAfter ? "180,40,40" : "60,80,60"},${0.3 + intensity * 0.4}) 0%, transparent 60%),
          radial-gradient(ellipse at 70% 60%, rgba(${isAfter ? "200,60,30" : "80,100,80"},${0.2 + intensity * 0.3}) 0%, transparent 50%),
          radial-gradient(ellipse at 50% 80%, rgba(${isAfter ? "160,30,30" : "50,70,50"},${0.25 + intensity * 0.35}) 0%, transparent 45%),
          linear-gradient(135deg, #1a1a2e ${isAfter ? "0%" : "20%"}, #16213e 50%, #0f3460 100%)
        `,
      }} />
      {/* Terrain texture overlay */}
      <div className="absolute inset-0 opacity-30" style={{
        backgroundImage: `
          repeating-linear-gradient(${45 + (isAfter ? 10 : 0)}deg, transparent, transparent 2px, rgba(255,255,255,0.03) 2px, rgba(255,255,255,0.03) 4px),
          repeating-linear-gradient(-${30 + (isAfter ? 5 : 0)}deg, transparent, transparent 3px, rgba(0,0,0,0.05) 3px, rgba(0,0,0,0.05) 6px)
        `,
      }} />
      {/* Brightness variation for realism */}
      {isAfter && changeScore > 0.3 && (
        <div className="absolute inset-0" style={{
          background: `radial-gradient(circle at ${40 + changeScore * 20}% ${50 + changeScore * 10}%, rgba(255,80,40,${changeScore * 0.4}) 0%, transparent 40%)`,
        }} />
      )}
      {/* Label */}
      <div className="absolute top-1 left-1 rounded bg-black/70 px-1.5 py-0.5 text-[8px] font-bold text-white backdrop-blur-sm">
        {label}
      </div>
      <div className="absolute bottom-1 right-1 rounded bg-black/70 px-1.5 py-0.5 text-[7px] text-white/80 backdrop-blur-sm">
        {date}
      </div>
    </div>
  );
}

export default function SARComparison({ acquisitionDate, previousDate, changeScore, honestyNote }: SARComparisonProps) {
  const [sliderPos, setSliderPos] = useState(50);
  const containerRef = useRef<HTMLDivElement>(null);
  const isDragging = useRef(false);

  const changeColor = changeScore > 0.5 ? "#ba1a1a" : changeScore > 0.3 ? "#ea580c" : "#d97706";
  const changeLabel = changeScore > 0.5 ? "HIGH CHANGE" : changeScore > 0.3 ? "MODERATE" : "LOW";

  const handleMove = useCallback((clientX: number) => {
    if (!containerRef.current) return;
    const rect = containerRef.current.getBoundingClientRect();
    const x = ((clientX - rect.left) / rect.width) * 100;
    setSliderPos(Math.max(5, Math.min(95, x)));
  }, []);

  const handleMouseDown = () => { isDragging.current = true; };
  const handleMouseMove = (e: React.MouseEvent) => { if (isDragging.current) handleMove(e.clientX); };
  const handleMouseUp = () => { isDragging.current = false; };
  const handleTouchMove = (e: React.TouchEvent) => { handleMove(e.touches[0].clientX); };

  return (
    <div className="rounded-lg border border-[#e4e3db] bg-white p-2.5 shadow-sm">
      <div className="mb-2 flex items-center justify-between">
        <div className="flex items-center gap-2">
          <p className="text-[10px] font-bold text-[#1b1c17]">SAR CHANGE DETECTION</p>
          <span className="rounded bg-[#d97706]/10 px-1.5 py-0.5 text-[7px] font-bold text-[#92400e]">
            SENTINEL-1
          </span>
        </div>
        <div className="flex items-center gap-1.5">
          <span className="text-[8px] text-[#707973]">Change:</span>
          <span className="rounded px-1.5 py-0.5 text-[8px] font-bold text-white" style={{ backgroundColor: changeColor }}>
            {changeLabel}
          </span>
        </div>
      </div>

      {/* Split comparison view */}
      <div
        ref={containerRef}
        className="relative mb-2 h-32 cursor-col-resize overflow-hidden rounded-md border border-[#d9e2d9]"
        onMouseDown={handleMouseDown}
        onMouseMove={handleMouseMove}
        onMouseUp={handleMouseUp}
        onMouseLeave={handleMouseUp}
        onTouchMove={handleTouchMove}
        onTouchEnd={handleMouseUp}
      >
        {/* Previous (left) */}
        <div className="absolute inset-0">
          <SARImage label="PREVIOUS" date={previousDate} changeScore={changeScore} isAfter={false} />
        </div>

        {/* Current (right, clipped) */}
        <div className="absolute inset-0" style={{ clipPath: `inset(0 0 0 ${sliderPos}%)` }}>
          <SARImage label="CURRENT" date={acquisitionDate} changeScore={changeScore} isAfter={true} />
        </div>

        {/* Slider handle */}
        <div className="absolute top-0 bottom-0 w-0.5 bg-white/90 shadow-lg" style={{ left: `${sliderPos}%` }}>
          <div className="absolute -left-2 top-1/2 flex h-5 w-4 -translate-y-1/2 items-center justify-center rounded-sm bg-white shadow-lg border border-gray-200">
            <span className="text-[6px] text-gray-400">◀▶</span>
          </div>
        </div>

        {/* Change hotspot indicators */}
        {changeScore > 0.3 && (
          <div className="absolute inset-0 pointer-events-none">
            <div className="absolute rounded-full border-2 border-dashed border-red-400/60 animate-pulse"
              style={{
                left: `${40 + changeScore * 10}%`,
                top: `${35 + changeScore * 5}%`,
                width: `${30 + changeScore * 20}px`,
                height: `${30 + changeScore * 20}px`,
                transform: "translate(-50%, -50%)",
              }}
            />
          </div>
        )}
      </div>

      {/* Change score bar */}
      <div className="mb-1.5">
        <div className="flex justify-between text-[8px] mb-0.5">
          <span className="font-semibold text-[#404943]">Surface Change Index</span>
          <span className="font-bold" style={{ color: changeColor }}>{(changeScore * 100).toFixed(1)}%</span>
        </div>
        <div className="h-2 w-full rounded-full bg-gray-100 overflow-hidden">
          <div className="h-full rounded-full transition-all duration-700" style={{
            width: `${changeScore * 100}%`,
            background: `linear-gradient(90deg, #245c45, #d97706, ${changeColor})`,
          }} />
        </div>
      </div>

      {/* Details */}
      <div className="flex items-center justify-between text-[8px] text-[#707973]">
        <span>Pre: {previousDate}</span>
        <span>Post: {acquisitionDate}</span>
      </div>

      <p className="mt-1.5 text-[7px] italic leading-relaxed text-[#92400e]">{honestyNote}</p>
    </div>
  );
}
