import { beforeEach, describe, expect, it } from "vitest";
import { act, renderHook } from "@testing-library/react";
import { backendLabel, useApiStatus } from "../store/apiStatus";

describe("useApiStatus (backend outage visibility)", () => {
  beforeEach(() => {
    useApiStatus.getState().reset();
  });

  it("starts unknown (no banner)", () => {
    expect(useApiStatus.getState().backend).toBe("unknown");
  });

  it("network error with no response -> offline", () => {
    act(() => {
      useApiStatus.getState().reportFailure({ url: "/api/zones" });
    });
    expect(useApiStatus.getState().backend).toBe("offline");
    expect(useApiStatus.getState().lastErrorUrl).toBe("/api/zones");
    expect(useApiStatus.getState().lastErrorAt).not.toBeNull();
  });

  it("5xx response -> degraded (reachable but failing)", () => {
    act(() => {
      useApiStatus.getState().reportFailure({ url: "/api/zones", status: 500 });
    });
    expect(useApiStatus.getState().backend).toBe("degraded");
  });

  it("success recovers to online and clears error", () => {
    act(() => {
      useApiStatus.getState().reportFailure({ url: "/api/zones" });
    });
    act(() => {
      useApiStatus.getState().reportSuccess();
    });
    const s = useApiStatus.getState();
    expect(s.backend).toBe("online");
    expect(s.consecutiveFailures).toBe(0);
    expect(s.lastErrorUrl).toBeNull();
  });

  it("counts consecutive failures", () => {
    act(() => {
      useApiStatus.getState().reportFailure({ status: 503 });
      useApiStatus.getState().reportFailure({ status: 503 });
    });
    expect(useApiStatus.getState().consecutiveFailures).toBe(2);
  });

  it("labels every state", () => {
    expect(backendLabel("online")).toBe("BACKEND ONLINE");
    expect(backendLabel("degraded")).toBe("BACKEND DEGRADED");
    expect(backendLabel("offline")).toBe("BACKEND UNAVAILABLE");
    expect(backendLabel("unknown")).toBe("BACKEND STATUS UNKNOWN");
  });

  it("is reactive via hook", () => {
    const { result } = renderHook(() => useApiStatus((s) => s.backend));
    expect(result.current).toBe("unknown");
    act(() => {
      useApiStatus.getState().reportFailure({});
    });
    expect(result.current).toBe("offline");
  });
});
