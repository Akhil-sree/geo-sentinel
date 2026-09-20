import { useApiStatus, backendLabel } from "../../store/apiStatus";

/**
 * Global system-failure banner. Rendered once in App so that a dead backend
 * can never be mistaken for "zero risks / no alerts / empty lists".
 * Hidden when the backend is online or its state is still unknown.
 */
export default function BackendStatusBanner() {
  const backend = useApiStatus((s) => s.backend);
  const lastErrorUrl = useApiStatus((s) => s.lastErrorUrl);
  const lastErrorAt = useApiStatus((s) => s.lastErrorAt);

  if (backend === "online" || backend === "unknown") return null;

  const offline = backend === "offline";
  return (
    <div
      role="alert"
      data-testid="backend-status-banner"
      style={{
        background: offline ? "#7f1d1d" : "#78350f",
        color: "white",
        padding: "8px 16px",
        fontSize: 13,
        fontWeight: 600,
        display: "flex",
        gap: 12,
        alignItems: "center",
        justifyContent: "center",
      }}
    >
      <span>
        {backendLabel(backend)} — data shown may be stale or empty. Check that
        the backend is running
        {lastErrorUrl ? ` (last failure: ${lastErrorUrl}` : ""}
        {lastErrorAt ? ` at ${lastErrorAt}` : ""}
        {lastErrorUrl ? ")" : ""}.
      </span>
    </div>
  );
}
