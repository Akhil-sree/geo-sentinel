import { describe, expect, it } from "vitest";
import {
  DEFAULT_TILE_URL,
  FALLBACK_TILE_URL,
  resolveTileUrls,
} from "../components/map/BasemapLayer";

describe("resolveTileUrls (basemap portability)", () => {
  it("defaults to Esri with OSM fallback", () => {
    const { primary, fallback } = resolveTileUrls("");
    expect(primary).toBe(DEFAULT_TILE_URL);
    expect(fallback).toBe(FALLBACK_TILE_URL);
  });

  it("honours a configured URL", () => {
    const { primary, fallback } = resolveTileUrls(
      "https://tiles.example.com/{z}/{x}/{y}.png",
    );
    expect(primary).toBe("https://tiles.example.com/{z}/{x}/{y}.png");
    expect(fallback).toBe(FALLBACK_TILE_URL);
  });

  it("avoids a self-fallback loop when already on OSM", () => {
    const { primary, fallback } = resolveTileUrls(FALLBACK_TILE_URL);
    expect(primary).toBe(FALLBACK_TILE_URL);
    expect(fallback).toBe("");
  });

  it("trims whitespace-only env to the default", () => {
    expect(resolveTileUrls("   ").primary).toBe(DEFAULT_TILE_URL);
  });
});
