import { useState, useRef, useCallback } from "react";
import { fmtPctOpt } from "../../lib/format";

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
      <div className="absolute inset-0" style={{
        background: `
          radial-gradient(ellipse at 30% 40%, rgba(${isAfter ? "180,40,40" : "60,80,60"},${0.3 + intensity * 0.4}) 0%, transparent 60%),
          radial-gradient(ellipse at 70% 60%, rgba(${isAfter ? "200,60,30" : "80,100,80"},${0.2 + intensity * 0.3}) 0%, transparent 50%),
          radial-gradient(ellipse at 50% 80%, rgba(${isAfter ? "160,30,30" : "50,70,50"},${0.25 + intensity * 0.35}) 0%, transparent 45%),
          linear-gradient(135deg, #1a1a2e ${isAfter ? "0%" : "20%"}, #16213e 50%, #0f3460 100%)
        `,
      }} />
      <div className="absolute inset-0 opacity-30" style={{
        backgroundImage: `
          repeating-linear-gradient(${45 + (isAfter ? 10 : 0)}deg, transparent, transparent 2px, rgba(255,255,255,0.03) 2px, rgba(255,255,255,0.03) 4px),
          repeating-linear-gradient(-${30 + (isAfter ? 5 : 0)}deg, transparent, transparent 3px, rgba(0,0,0,0.05) 3px, rgba(0,0,0,0.05) 6px)
        `,
      }} />
      {isAfter && changeScore > 0.3 && (
        <div className="absolute inset-0" style={{
          background: `radial-gradient(circle at ${40 + changeScore * 20}% ${50 + changeScore * 10}%, rgba(255,80,40,${changeScore * 0.4}) 0%, transparent 40%)`,
        }} />
      )}
      <div className="absolute top-1 left-1 rounded bg-black/70 px-1.5 py-0.5 text-[8px] font-semibold text-white backdrop-blur-sm">
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

  const changeColor = changeScore > 0.5 ? "#B51D24" : changeScore > 0.3 ? "#E4570A" : "#C98208";
  const changeLabel = changeScore > 0.5 ? "High" : changeScore > 0.3 ? "Moderate" : "Low";

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
    <div className="rounded-card p-4" style={{
      background: 'rgba(255, 255, 255, 0.55)',
      backdropFilter: 'blur(4px)',
      WebkitBackdropFilter: 'blur(4px)',
      border: '1px solid rgba(255, 255, 255, 0.30)',
      boxShadow: '0 2px 10px rgba(15, 35, 27, 0.04)',
    }}>
      <div className="mb-3 flex items-center justify-between">
        <div className="flex items-center gap-2.5">
          <p className="text-[14px] font-semibold text-gs-text">Satellite change detection</p>
          <span className="rounded bg-risk-stressed/10 px-2 py-0.5 text-[11px] font-medium text-risk-stressed">
            Sentinel-1
          </span>
        </div>
        <div className="flex items-center gap-2">
          <span className="text-[12px] text-gs-text-secondary">Change:</span>
          <span className="rounded px-2 py-0.5 text-[12px] font-semibold text-white" style={{ backgroundColor: changeColor }}>
            {changeLabel}
          </span>
        </div>
      </div>

      {/* Split comparison view */}
      <div
        ref={containerRef}
        className="relative mb-3 h-36 cursor-col-resize overflow-hidden rounded-card border border-gs-border"
        onMouseDown={handleMouseDown}
        onMouseMove={handleMouseMove}
        onMouseUp={handleMouseUp}
        onMouseLeave={handleMouseUp}
        onTouchMove={handleTouchMove}
        onTouchEnd={handleMouseUp}
      >
        <div className="absolute inset-0">
          <SARImage label="Previous" date={previousDate} changeScore={changeScore} isAfter={false} />
        </div>

        <div className="absolute inset-0" style={{ clipPath: `inset(0 0 0 ${sliderPos}%)` }}>
          <SARImage label="Current" date={acquisitionDate} changeScore={changeScore} isAfter={true} />
        </div>

        <div className="absolute top-0 bottom-0 w-0.5 bg-white/90 shadow-lg" style={{ left: `${sliderPos}%` }}>
          <div className="absolute -left-2.5 top-1/2 flex h-6 w-5 -translate-y-1/2 items-center justify-center rounded-sm bg-white shadow-lg border border-gs-border">
            <span className="text-[8px] text-gs-text-secondary">◀▶</span>
          </div>
        </div>

        {changeScore > 0.3 && (
          <div className="absolute inset-0 pointer-events-none">
            <div className="absolute rounded-full border-2 border-dashed border-risk-critical/40 animate-pulse"
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
        <div className="absolute top-1 right-1 rounded bg-black/70 px-1.5 py-0.5 text-[8px] font-bold text-amber-300 backdrop-blur-sm">
          SIMULATED PREVIEW — not real imagery
        </div>
      </div>

      {/* Change score bar */}
      <div className="mb-2.5">
        <div className="flex justify-between text-[12px] mb-1.5">
          <span className="font-medium text-gs-text-secondary">Surface change index</span>
          <span className="font-semibold" style={{ color: changeColor }}>{fmtPctOpt(changeScore, 1)}</span>
        </div>
        <div className="h-2 w-full rounded-full bg-gs-border overflow-hidden">
          <div className="h-full rounded-full transition-all duration-700" style={{
            width: `${changeScore * 100}%`,
            background: `linear-gradient(90deg, #236B4A, #C98208, ${changeColor})`,
          }} />
        </div>
      </div>

      {/* Details */}
      <div className="flex items-center justify-between text-[12px] text-gs-text-secondary">
        <span>Pre: {previousDate}</span>
        <span>Post: {acquisitionDate}</span>
      </div>

      <p className="mt-2.5 text-[12px] italic leading-relaxed text-risk-stressed">{honestyNote}</p>
    </div>
  );
}
