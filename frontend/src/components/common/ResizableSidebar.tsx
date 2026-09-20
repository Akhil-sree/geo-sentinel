import { useRef, useEffect } from "react";

const WIDTH_KEY = "geo-sentinel-sidebar-width";
const MIN_WIDTH = 260;
const MAX_WIDTH = 580;
const DEFAULT_WIDTH = 300;

function clampWidth(w: number): number {
  return Math.max(MIN_WIDTH, Math.min(MAX_WIDTH, w));
}

function loadSavedWidth(): number {
  try {
    const s = localStorage.getItem(WIDTH_KEY);
    if (s) {
      const w = parseInt(s, 10);
      if (!isNaN(w)) return clampWidth(w);
    }
  } catch {}
  return DEFAULT_WIDTH;
}

export default function ResizableSidebar({ children }: { children: React.ReactNode }) {
  const asideRef = useRef<HTMLElement>(null);
  const handleRef = useRef<HTMLDivElement>(null);
  const isResizing = useRef(false);

  useEffect(() => {
    const el = asideRef.current as HTMLElement;
    const handle = handleRef.current;
    if (!el || !handle) return;

    const parent = el.parentElement as HTMLElement;
    el.style.width = loadSavedWidth() + "px";

    function onMouseDown(e: MouseEvent) {
      e.preventDefault();
      isResizing.current = true;
      document.body.style.cursor = "col-resize";
      document.body.style.userSelect = "none";
      document.addEventListener("mousemove", onMouseMove);
      document.addEventListener("mouseup", onMouseUp);
    }

    function onMouseMove(e: MouseEvent) {
      if (!isResizing.current) return;
      const newWidth = parent.getBoundingClientRect().right - e.clientX;
      el.style.width = clampWidth(newWidth) + "px";
    }

    function onMouseUp() {
      if (!isResizing.current) return;
      isResizing.current = false;
      document.body.style.cursor = "";
      document.body.style.userSelect = "";
      document.removeEventListener("mousemove", onMouseMove);
      document.removeEventListener("mouseup", onMouseUp);
      localStorage.setItem(WIDTH_KEY, el.style.width);
    }

    function onTouchStart(e: TouchEvent) {
      e.preventDefault();
      isResizing.current = true;
      document.body.style.cursor = "col-resize";
      document.body.style.userSelect = "none";
      document.addEventListener("touchmove", onTouchMove, { passive: false });
      document.addEventListener("touchend", onTouchEnd);
    }

    function onTouchMove(e: TouchEvent) {
      if (!isResizing.current) return;
      e.preventDefault();
      const newWidth = parent.getBoundingClientRect().right - e.touches[0].clientX;
      el.style.width = clampWidth(newWidth) + "px";
    }

    function onTouchEnd() {
      if (!isResizing.current) return;
      isResizing.current = false;
      document.body.style.cursor = "";
      document.body.style.userSelect = "";
      document.removeEventListener("touchmove", onTouchMove);
      document.removeEventListener("touchend", onTouchEnd);
      localStorage.setItem(WIDTH_KEY, el.style.width);
    }

    handle.addEventListener("mousedown", onMouseDown);
    handle.addEventListener("touchstart", onTouchStart);

    return () => {
      handle.removeEventListener("mousedown", onMouseDown);
      handle.removeEventListener("touchstart", onTouchStart);
      document.removeEventListener("mousemove", onMouseMove);
      document.removeEventListener("mouseup", onMouseUp);
      document.removeEventListener("touchmove", onTouchMove);
      document.removeEventListener("touchend", onTouchEnd);
      document.body.style.cursor = "";
      document.body.style.userSelect = "";
    };
  }, []);

  return (
    <aside
      ref={asideRef}
      className="gs-sidebar relative flex flex-col overflow-hidden"
      style={{
        width: DEFAULT_WIDTH, minWidth: MIN_WIDTH, maxWidth: MAX_WIDTH, flexShrink: 0,
        background: '#FFFFFF',
        borderLeft: '1px solid #E5E7EB',
        boxShadow: '-1px 0 0 rgba(0, 0, 0, 0.06)',
      }}
    >
      <div
        id="resize-handle"
        ref={handleRef}
        role="separator"
        aria-orientation="vertical"
        aria-label="Resize risk intelligence panel"
        className="absolute left-0 top-0 bottom-0 z-50 flex items-center justify-center"
        style={{ width: 8, cursor: "col-resize", touchAction: "none" }}
      />
      {children}
    </aside>
  );
}
