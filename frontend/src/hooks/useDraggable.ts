import { useCallback, useEffect, useRef, useState } from "react";

export interface DragPos {
  x: number;
  y: number;
}

const DRAG_THRESHOLD_PX = 4;

function storageKey(id: string): string {
  return `gs-overlay-pos:${id}`;
}

/** Load a persisted position; null when absent/invalid. Pure — unit-tested. */
export function loadDragPos(id: string): DragPos | null {
  try {
    const raw = localStorage.getItem(storageKey(id));
    if (!raw) return null;
    const p = JSON.parse(raw);
    if (typeof p?.x === "number" && typeof p?.y === "number"
        && Number.isFinite(p.x) && Number.isFinite(p.y)) {
      return { x: p.x, y: p.y };
    }
  } catch {
    /* corrupted entry — fall through to default */
  }
  return null;
}

/** Clamp a position so the element stays inside its container. Pure — unit-tested. */
export function clampDragPos(
  x: number, y: number,
  elW: number, elH: number,
  boxW: number, boxH: number,
): DragPos {
  return {
    x: Math.min(Math.max(0, x), Math.max(0, boxW - elW)),
    y: Math.min(Math.max(0, y), Math.max(0, boxH - elH)),
  };
}

/**
 * Makes a map overlay draggable by its header handle.
 * - Click (no move) still works — e.g. collapse toggles.
 * - Position persists per `id` in localStorage; double-click handle resets.
 * - Element must be absolutely positioned inside a positioned container.
 */
export function useDraggable(id: string) {
  const ref = useRef<HTMLDivElement>(null);
  const [pos, setPos] = useState<DragPos | null>(null);
  const drag = useRef<{
    startX: number; startY: number;
    baseX: number; baseY: number;
    active: boolean;
  } | null>(null);

  useEffect(() => {
    setPos(loadDragPos(id));
  }, [id]);

  const reset = useCallback(() => {
    try {
      localStorage.removeItem(storageKey(id));
    } catch {
      /* storage unavailable — layout just resets for this session */
    }
    setPos(null);
  }, [id]);

  const onHandlePointerDown = useCallback((e: React.PointerEvent) => {
    const el = ref.current;
    if (!el || e.button !== 0) return;
    // Anchor to current layout position on first drag (offsetParent = map wrapper).
    const base = pos ?? { x: el.offsetLeft, y: el.offsetTop };
    drag.current = { startX: e.clientX, startY: e.clientY, baseX: base.x, baseY: base.y, active: false };
    (e.target as HTMLElement).setPointerCapture?.(e.pointerId);
  }, [pos]);

  const onHandlePointerMove = useCallback((e: React.PointerEvent) => {
    const d = drag.current;
    const el = ref.current;
    if (!d || !el) return;
    const dx = e.clientX - d.startX;
    const dy = e.clientY - d.startY;
    if (!d.active && Math.hypot(dx, dy) < DRAG_THRESHOLD_PX) return;
    d.active = true;
    const box = el.offsetParent as HTMLElement | null;
    const next = clampDragPos(
      d.baseX + dx, d.baseY + dy,
      el.offsetWidth, el.offsetHeight,
      box?.clientWidth ?? window.innerWidth,
      box?.clientHeight ?? window.innerHeight,
    );
    setPos(next);
  }, []);

  const endDrag = useCallback(() => {
    const d = drag.current;
    drag.current = null;
    if (!d?.active) return; // plain click — leave toggle behavior alone
    const el = ref.current;
    if (!el) return;
    try {
      localStorage.setItem(storageKey(id),
        JSON.stringify({ x: el.offsetLeft, y: el.offsetTop }));
    } catch {
      /* storage unavailable — position lasts for this session only */
    }
  }, [id]);

  const handleProps = {
    onPointerDown: onHandlePointerDown,
    onPointerMove: onHandlePointerMove,
    onPointerUp: endDrag,
    onPointerCancel: endDrag,
    onDoubleClick: reset,
    title: "Drag to move · double-click to reset",
    style: { cursor: "grab", touchAction: "none" as const },
  };

  // Explicit left/top only after user moves the panel; otherwise CSS defaults apply.
  const style: React.CSSProperties = pos
    ? { left: pos.x, top: pos.y, right: "auto", bottom: "auto" }
    : {};

  return { ref, style, handleProps, reset };
}
