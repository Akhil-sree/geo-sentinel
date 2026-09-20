import { describe, expect, it, beforeEach } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import { loadDragPos, clampDragPos } from "../hooks/useDraggable";
import LayerControl, { DEFAULT_LAYERS, DEFAULT_ROAD_FILTERS } from "../components/map/LayerControl";
import MapLegend from "../components/map/MapLegend";

beforeEach(() => {
  localStorage.clear();
});

describe("drag position helpers", () => {
  it("loadDragPos returns null when absent, round-trips valid positions", () => {
    expect(loadDragPos("x")).toBeNull();
    localStorage.setItem("gs-overlay-pos:x", JSON.stringify({ x: 120, y: 40 }));
    expect(loadDragPos("x")).toEqual({ x: 120, y: 40 });
  });
  it("loadDragPos rejects corrupt/non-finite entries", () => {
    localStorage.setItem("gs-overlay-pos:bad", "not-json");
    expect(loadDragPos("bad")).toBeNull();
    localStorage.setItem("gs-overlay-pos:nan", JSON.stringify({ x: NaN, y: 1 }));
    expect(loadDragPos("nan")).toBeNull();
    localStorage.setItem("gs-overlay-pos:str", JSON.stringify({ x: "10", y: 5 }));
    expect(loadDragPos("str")).toBeNull();
  });
  it("clampDragPos keeps panels inside the map", () => {
    expect(clampDragPos(-20, -5, 180, 200, 800, 600)).toEqual({ x: 0, y: 0 });
    expect(clampDragPos(700, 500, 180, 200, 800, 600)).toEqual({ x: 620, y: 400 });
    expect(clampDragPos(100, 100, 180, 200, 800, 600)).toEqual({ x: 100, y: 100 });
  });
});

describe("draggable overlays", () => {
  it("Map Layers has a drag handle and still collapses on click", () => {
    const { container } = render(
      <LayerControl layers={DEFAULT_LAYERS} onToggle={() => {}} roadFilters={DEFAULT_ROAD_FILTERS} onRoadFilterToggle={() => {}} />
    );
    const handle = container.querySelector('[title="Drag to move · double-click to reset"]');
    expect(handle).toBeTruthy();
    expect(screen.getByText("Risk zones")).toBeTruthy();
    fireEvent.click(screen.getByText("Map Layers"));
    expect(screen.queryByText("Risk zones")).toBeNull(); // click (no drag) still toggles
  });
  it("Legend has a drag handle and still collapses on click", () => {
    const { container } = render(<MapLegend />);
    expect(container.querySelector('[title="Drag to move · double-click to reset"]')).toBeTruthy();
    expect(screen.getByText(/Rescue route/)).toBeTruthy();
    fireEvent.click(screen.getByText("Legend"));
    expect(screen.queryByText(/Rescue route/)).toBeNull();
  });
});
