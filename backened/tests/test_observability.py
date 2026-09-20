"""Observability regressions: JSON request logs, request metrics, route/ML
counters exposed via /api/metrics."""
import json
import logging

from fastapi.testclient import TestClient

from app.main import app
from app.observability import (
    JsonFormatter,
    record_ml_inference,
    record_provider_failure,
    record_request,
    record_route,
    reset_metrics,
    snapshot,
)

client = TestClient(app)


def test_json_formatter_shape():
    fmt = JsonFormatter()
    rec = logging.LogRecord("geo-sentinel", logging.INFO, __file__, 1,
                            "hello %s", ("world",), None)
    rec.request_id = "abc"
    rec.status = 200
    line = fmt.format(rec)
    payload = json.loads(line)
    assert payload["msg"] == "hello world"
    assert payload["request_id"] == "abc"
    assert payload["status"] == 200
    assert payload["level"] == "INFO"


def test_request_counters():
    reset_metrics()
    record_request("/api/risk/map", 200, 12.5)
    record_request("/api/risk/map", 500, 3.0)
    snap = snapshot()
    assert snap["requests_total"] == 2
    assert snap["request_errors_total"] == 1
    assert snap["by_prefix"]["/api/risk"]["requests"] == 2
    assert snap["by_prefix"]["/api/risk"]["errors"] == 1
    reset_metrics()


def test_route_and_ml_counters():
    reset_metrics()
    record_route(True)
    record_route(False)
    record_ml_inference(4.0)
    record_provider_failure("openmeteo")
    snap = snapshot()
    assert snap["route_requests"] == 2
    assert snap["route_failures"] == 1
    assert snap["ml_inferences"] == 1
    assert snap["ml_avg_latency_ms"] == 4.0
    assert snap["provider_failures_total"] == 1
    reset_metrics()


def test_middleware_records_requests_and_request_id():
    reset_metrics()
    r = client.get("/health")
    assert r.status_code == 200
    assert "X-Request-ID" in r.headers
    snap = client.get("/api/metrics").json()
    assert snap["requests"]["requests_total"] >= 1
    assert "by_prefix" in snap["requests"]
    reset_metrics()


def test_rescue_marks_route_metrics():
    reset_metrics()
    client.get("/api/rescue/route",
               params={"danger_lat": 25.30, "danger_lng": 91.58,
                       "safe_lat": 25.62, "safe_lng": 91.90})
    snap = snapshot()
    assert snap["route_requests"] >= 1
    reset_metrics()
