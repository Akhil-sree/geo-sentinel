"""Unit tests for the fusion engine and escalation rule — the highest-risk
pure logic in the system."""
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from app.ml.fusion import fuse, classify, escalation_rule
from app.config import THRESHOLDS

def test_class_boundaries():
    assert classify(0.10) == "LOW"
    assert classify(0.30) == "MODERATE"
    assert classify(0.60) == "HIGH"
    assert classify(0.90) == "VERY_HIGH"

def test_fusion_weighted_average():
    r = fuse(0.8, 0.6, 0, 0, 0.3)          # no escalation conditions
    assert abs(r["risk_score"] - 0.7) < 1e-6
    assert r["escalated"] is False

def test_escalation_fires_on_r72():
    fired, reasons, boost = escalation_rule(0.60, 40, 260, 0.40)
    assert fired and any("72h" in x for x in reasons)
    r = fuse(0.60, 0.30, 40, 260, 0.40)
    assert r["escalated"] and r["risk_score"] > 0.45

def test_escalation_requires_static_gate():
    # low static susceptibility → no escalation even in extreme rain
    fired, _, _ = escalation_rule(0.20, 150, 400, 0.70)
    assert fired is False

def test_severity_never_decreases_with_escalation():
    base = fuse(0.5, 0.2, 10, 50, 0.3)
    esc = fuse(0.5, 0.2, 150, 300, 0.70)
    order = ["LOW", "MODERATE", "HIGH", "VERY_HIGH"]
    assert order.index(esc["severity"]) >= order.index(base["severity"])

def test_score_clamped_to_one():
    r = fuse(1.0, 1.0, 999, 999, 1.0)
    assert r["risk_score"] <=1.0
