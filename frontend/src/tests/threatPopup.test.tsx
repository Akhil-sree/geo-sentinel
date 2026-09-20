import { describe, expect, it } from "vitest";
import { render } from "@testing-library/react";
import { ThreatPopupContent } from "../components/map/ThreatMarker";
import type { ThreatZone } from "../components/map/RiskMap";

const base: ThreatZone = {
  id: 1,
  zoneId: "Z1",
  name: "Sohra",
  district: "East Khasi Hills",
  lat: 25.27,
  lng: 91.73,
  risk: "high",
  score: 0.72,
  rainfall: "120mm",
  soilMoisture: "Saturated",
  slopeStress: "High",
  trend: "escalating",
};

describe("ThreatPopupContent (XSS regression)", () => {
  it("renders zone fields as text", () => {
    const { getByText } = render(<ThreatPopupContent zone={base} />);
    expect(getByText("Sohra").textContent).toBe("Sohra");
    expect(getByText("72%").textContent).toContain("72%");
  });

  it.each([
    `<script>alert(1)</script>`,
    `<img src=x onerror=alert(1)>`,
    `"><svg/onload=alert(1)>`,
  ])("neutralises malicious payload %q", (payload) => {
    const evil: ThreatZone = {
      ...base,
      name: payload,
      district: payload,
      rainfall: payload,
      soilMoisture: payload,
      slopeStress: payload,
    };
    const { container } = render(<ThreatPopupContent zone={evil} />);
    expect(container.querySelector("script")).toBeNull();
    expect(container.querySelector("img")).toBeNull();
    expect(container.querySelector("svg")).toBeNull();
    expect(container.querySelector("[onerror]")).toBeNull();
    // payload is visible as inert text, not parsed markup
    expect(container.textContent).toContain(payload);
  });

  it("handles null score without crashing", () => {
    const { container } = render(
      <ThreatPopupContent zone={{ ...base, score: null }} />,
    );
    expect(container.textContent).toContain("—");
  });
});
