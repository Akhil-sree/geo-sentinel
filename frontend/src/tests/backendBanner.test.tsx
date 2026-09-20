import { afterEach, describe, expect, it } from "vitest";
import { act, cleanup, render } from "@testing-library/react";
import BackendStatusBanner from "../components/layout/BackendStatusBanner";
import { useApiStatus } from "../store/apiStatus";

afterEach(() => {
  cleanup();
  useApiStatus.getState().reset();
});

describe("BackendStatusBanner", () => {
  it("renders nothing when online or unknown", () => {
    act(() => useApiStatus.getState().reset());
    const { container, rerender } = render(<BackendStatusBanner />);
    expect(container.firstChild).toBeNull();
    act(() => useApiStatus.getState().reportSuccess());
    rerender(<BackendStatusBanner />);
    expect(container.firstChild).toBeNull();
  });

  it("renders BACKEND UNAVAILABLE alert on outage", () => {
    act(() => {
      useApiStatus.getState().reportFailure({ url: "/api/zones" });
    });
    const { getByTestId } = render(<BackendStatusBanner />);
    const banner = getByTestId("backend-status-banner");
    expect(banner.getAttribute("role")).toBe("alert");
    expect(banner.textContent).toContain("BACKEND UNAVAILABLE");
    expect(banner.textContent).toContain("/api/zones");
  });

  it("renders BACKEND DEGRADED on 5xx", () => {
    act(() => {
      useApiStatus.getState().reportFailure({ url: "/api/risk/map", status: 500 });
    });
    const { getByTestId } = render(<BackendStatusBanner />);
    expect(getByTestId("backend-status-banner").textContent).toContain(
      "BACKEND DEGRADED",
    );
  });
});
