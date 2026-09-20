"""Lightweight production-grade observability (P3, no extra stack).

- JSON structured logs: one line per request (request_id, method, path,
  status, latency_ms) plus dependency-failure lines from this module.
- In-memory request metrics merged into GET /api/metrics:
  requests_total, request_errors_total, avg_latency_ms, per-prefix
  breakdown, route_requests/route_failures, ml_inference count+latency,
  provider_failures_total.
- Counters reset on process restart (documented; use an external scraper
  for durable history).
"""
import json
import logging
import threading
import time
from collections import defaultdict

_log = logging.getLogger("geo-sentinel")


class JsonFormatter(logging.Formatter):
    def format(self, record):
        payload = {
            "ts": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(record.created)),
            "level": record.levelname,
            "logger": record.name,
            "msg": record.getMessage(),
        }
        for attr in ("request_id", "method", "path", "status", "latency_ms",
                     "component", "detail"):
            if hasattr(record, attr):
                payload[attr] = getattr(record, attr)
        return json.dumps(payload)


def setup_json_logging(level=logging.INFO):
    """Idempotent: attach a JSON stdout handler once (uvicorn already logs
    its own access lines; these are the application-structured lines)."""
    root = logging.getLogger("geo-sentinel")
    for h in root.handlers:
        if isinstance(h, logging.StreamHandler) and isinstance(h.formatter, JsonFormatter):
            return
    handler = logging.StreamHandler()
    handler.setFormatter(JsonFormatter())
    root.addHandler(handler)
    root.setLevel(level)


_lock = threading.Lock()
_metrics = {
    "requests_total": 0,
    "request_errors_total": 0,   # status >= 500 (or unhandled)
    "latency_ms_total": 0.0,
    "by_prefix": defaultdict(lambda: {"requests": 0, "errors": 0, "latency_ms_total": 0.0}),
    "route_requests": 0,
    "route_failures": 0,         # route_available == False
    "ml_inferences": 0,
    "ml_latency_ms_total": 0.0,
    "provider_failures_total": 0,
}


def _prefix(path: str) -> str:
    for p in ("/api/rescue", "/api/risk", "/api/routes", "/api/roads",
              "/api/reports", "/api/alerts", "/api/sensors", "/api/satellite",
              "/api/model", "/api/admin", "/api/worker", "/api/metrics",
              "/api/data-status", "/api/ready", "/health", "/media"):
        if path.startswith(p):
            return p
    return "other"


def record_request(path: str, status: int, latency_ms: float) -> None:
    with _lock:
        _metrics["requests_total"] += 1
        _metrics["latency_ms_total"] += latency_ms
        cell = _metrics["by_prefix"][_prefix(path)]
        cell["requests"] += 1
        cell["latency_ms_total"] += latency_ms
        if status >= 500:
            _metrics["request_errors_total"] += 1
            cell["errors"] += 1


def record_route(available: bool) -> None:
    with _lock:
        _metrics["route_requests"] += 1
        if not available:
            _metrics["route_failures"] += 1


def record_ml_inference(latency_ms: float) -> None:
    with _lock:
        _metrics["ml_inferences"] += 1
        _metrics["ml_latency_ms_total"] += latency_ms


def record_provider_failure(source: str) -> None:
    with _lock:
        _metrics["provider_failures_total"] += 1
    _log.warning("provider failure", extra={"component": "ingest", "detail": source})


def snapshot() -> dict:
    with _lock:
        total = _metrics["requests_total"]
        out = {
            "requests_total": total,
            "request_errors_total": _metrics["request_errors_total"],
            "avg_latency_ms": round(_metrics["latency_ms_total"] / total, 2) if total else 0.0,
            "route_requests": _metrics["route_requests"],
            "route_failures": _metrics["route_failures"],
            "ml_inferences": _metrics["ml_inferences"],
            "ml_avg_latency_ms": (round(_metrics["ml_latency_ms_total"] / _metrics["ml_inferences"], 2)
                                  if _metrics["ml_inferences"] else 0.0),
            "provider_failures_total": _metrics["provider_failures_total"],
            "by_prefix": {k: {"requests": v["requests"], "errors": v["errors"],
                              "avg_latency_ms": round(v["latency_ms_total"] / v["requests"], 2)
                              if v["requests"] else 0.0}
                          for k, v in _metrics["by_prefix"].items()},
            "note": "in-memory since process start (resets on restart)",
        }
    return out


def reset_metrics() -> None:
    with _lock:
        _metrics["requests_total"] = 0
        _metrics["request_errors_total"] = 0
        _metrics["latency_ms_total"] = 0.0
        _metrics["by_prefix"].clear()
        _metrics["route_requests"] = 0
        _metrics["route_failures"] = 0
        _metrics["ml_inferences"] = 0
        _metrics["ml_latency_ms_total"] = 0.0
        _metrics["provider_failures_total"] = 0
