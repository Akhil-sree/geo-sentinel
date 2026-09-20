"""Rate-limit store + spoof-safe client-IP regressions."""
import os

from fastapi.testclient import TestClient

from app import auth
from app.auth import (InMemoryRateLimitStore, RateLimitStore,
                      get_rate_limit_store, resolve_client_ip,
                      set_rate_limit_store)
from app.main import app

client = TestClient(app)


def test_in_memory_budget_and_reset():
    store = InMemoryRateLimitStore()
    assert isinstance(store, RateLimitStore)
    for _ in range(3):
        assert store.allow("k", 3, 60) is True
    assert store.allow("k", 3, 60) is False
    store.reset()
    assert store.allow("k", 3, 60) is True


def test_rate_limit_raises_429_at_budget():
    store = InMemoryRateLimitStore()
    old = get_rate_limit_store()
    set_rate_limit_store(store)
    try:
        from fastapi import HTTPException
        import pytest
        for _ in range(2):
            auth.rate_limit("burst-key", limit=2)
        with pytest.raises(HTTPException) as ei:
            auth.rate_limit("burst-key", limit=2)
        assert ei.value.status_code == 429
    finally:
        set_rate_limit_store(old)


def test_custom_store_installable():
    class AllowAll(RateLimitStore):
        def allow(self, key, limit, window_s):
            return True

        def reset(self):
            pass

    old = get_rate_limit_store()
    set_rate_limit_store(AllowAll())
    try:
        auth.rate_limit("anything", limit=1)  # must not raise
        assert isinstance(get_rate_limit_store(), AllowAll)
    finally:
        set_rate_limit_store(old)


def test_resolve_client_ip_ignores_spoofed_xff_by_default(monkeypatch):
    monkeypatch.delenv("TRUSTED_PROXIES", raising=False)
    assert resolve_client_ip("1.2.3.4", "9.9.9.9") == "1.2.3.4"
    assert resolve_client_ip(None, "9.9.9.9") == "local"


def test_resolve_client_ip_honours_trusted_proxy(monkeypatch):
    monkeypatch.setenv("TRUSTED_PROXIES", "10.0.0.1")
    assert resolve_client_ip("10.0.0.1", "9.9.9.9, 10.0.0.1") == "9.9.9.9"
    # untrusted peer with same header stays on peer IP
    assert resolve_client_ip("1.2.3.4", "9.9.9.9") == "1.2.3.4"


def test_client_ip_helper_survives_none_request():
    assert auth._client_ip(None) == "local"
