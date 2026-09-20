"""RF input-validation regressions (P1): NaN/Inf/wrong-type/out-of-range
zone features must raise ValueError, never silently score."""
from types import SimpleNamespace

import pytest

from app.ml.rf_model import RFModel, _to_features


def _zone(**kw):
    base = dict(slope=30, elevation=1000, ruggedness=0.7,
                road_proximity=0.6, drainage_proximity=0.6,
                settlement_density=0.5, sar_change_score=0.2)
    base.update(kw)
    return SimpleNamespace(**base)


def test_valid_zone_converts():
    feats = _to_features(_zone())
    assert len(feats) == 7
    assert all(isinstance(v, float) for v in feats)


def test_nan_inf_rejected():
    for bad in (float("nan"), float("inf"), float("-inf")):
        with pytest.raises(ValueError):
            _to_features(_zone(slope=bad))
        with pytest.raises(ValueError):
            _to_features(_zone(sar_change_score=bad))


def test_non_numeric_rejected():
    with pytest.raises(ValueError):
        _to_features(_zone(slope="steep"))
    with pytest.raises(ValueError):
        _to_features(_zone(slope=None))


def test_out_of_range_rejected():
    with pytest.raises(ValueError):
        _to_features(_zone(slope=-1))
    with pytest.raises(ValueError):
        _to_features(_zone(slope=91))
    with pytest.raises(ValueError):
        _to_features(_zone(sar_change_score=1.5))
    with pytest.raises(ValueError):
        _to_features(_zone(ruggedness=-0.1))


def test_predict_missing_model_raises_not_fabricates():
    rf = RFModel(model_dir="/nonexistent", version="nope")
    assert rf.available() is False
    with pytest.raises(RuntimeError):
        rf.predict(_zone())


def test_predict_invalid_features_raise():
    rf = RFModel()
    if not rf.available():
        pytest.skip("RF artifact absent")
    with pytest.raises(ValueError):
        rf.predict(_zone(slope=float("nan")))
