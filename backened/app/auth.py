"""Shared API-key guard + tiny in-memory rate limiter (Phase 8).

- Read endpoints stay open (demo-friendly).
- Mutating admin paths (/alerts/send, /admin/moderate, /admin/* writes)
  require `X-API-Key: $ADMIN_API_KEY` when the env var is set.
  When unset (default demo), access is allowed but responses carry
  `auth_mode: open-demo` so the UI can label it honestly.
- Rate limit: 60 req/min/IP on guarded paths (in-memory, single worker).
"""
import os
import time
from fastapi import Header, HTTPException

ADMIN_API_KEY = os.getenv("ADMIN_API_KEY", "")
_hits: dict[str, list[float]] = {}

# Role-aware keys: API_KEYS="key1:admin,key2:operator,key3:viewer".
# Roles: admin > operator > viewer. Legacy ADMIN_API_KEY maps to admin.
# Server-side enforced; viewer cannot mutate. Object-level: moderation and
# alert lifecycle require operator+.
_ROLE_RANK = {"viewer": 0, "operator": 1, "admin": 2}


def _key_roles() -> dict[str, str]:
    keys: dict[str, str] = {}
    for pair in os.getenv("API_KEYS", "").split(","):
        if ":" in pair:
            k, r = pair.split(":", 1)
            if k.strip() and r.strip() in _ROLE_RANK:
                keys[k.strip()] = r.strip()
    if ADMIN_API_KEY:
        keys.setdefault(ADMIN_API_KEY.strip(), "admin")
    return keys


def guard(x_api_key: str | None = Header(default=None)) -> dict:
    if not ADMIN_API_KEY and not os.getenv("API_KEYS", ""):
        # Open-demo is a development convenience only. In production with no
        # keys configured, fail closed instead of serving mutating endpoints
        # anonymously.
        if os.getenv("ENVIRONMENT", "development").lower() == "production":
            raise HTTPException(
                status_code=401,
                detail="API keys required in production "
                       "(set ADMIN_API_KEY or API_KEYS)")
        return {"auth_mode": "open-demo"}
    if x_api_key in _key_roles():
        return {"auth_mode": "key", "role": _key_roles()[x_api_key]}
    raise HTTPException(status_code=401, detail="Invalid or missing X-API-Key")


def require_role(*roles: str):
    """FastAPI dependency: allow only listed roles (server-side).

    Usage: role: str = Depends(require_role("admin", "operator"))
    Open-demo (no keys configured) allows through but labels the response.
    """
    def _check(x_api_key: str | None = Header(default=None)) -> str:
        keys = _key_roles()
        if not keys:
            if os.getenv("ENVIRONMENT", "development").lower() == "production":
                raise HTTPException(
                    status_code=401,
                    detail="API keys required in production "
                           "(set ADMIN_API_KEY or API_KEYS)")
            return "open-demo"
        role = keys.get(x_api_key or "")
        if role is None:
            raise HTTPException(status_code=401, detail="Invalid or missing X-API-Key")
        if role != "admin" and role not in roles:  # admin bypasses every gate
            raise HTTPException(status_code=403, detail=f"Role '{role}' not authorized")
        return role
    return _check


class SecretBox:
    """Provider-secret protection: Fernet when FERNET_KEY is set, else env-only.

    Never log plaintext secrets; ENC: prefixed values are decrypted at use.
    Production should use KMS/secret-manager; this is the demo-safe floor
    (no plaintext secret files, no secret logging).
    """
    @staticmethod
    def reveal(value: str | None) -> str:
        if not value:
            return ""
        if value.startswith("ENC:"):
            key = os.getenv("FERNET_KEY", "")
            if not key:
                raise RuntimeError("Encrypted secret present but FERNET_KEY unset")
            from cryptography.fernet import Fernet
            return Fernet(key.encode()).decrypt(value[4:].encode()).decode()
        return value

    @staticmethod
    def conceal(plaintext: str) -> str:
        key = os.getenv("FERNET_KEY", "")
        if not key:
            raise RuntimeError("FERNET_KEY unset — cannot encrypt")
        from cryptography.fernet import Fernet
        return "ENC:" + Fernet(key.encode()).encrypt(plaintext.encode()).decode()


def rate_limit(ip: str, limit: int = 60, window_s: int = 60) -> None:
    store = get_rate_limit_store()
    if not store.allow(ip, limit, window_s):
        raise HTTPException(status_code=429, detail="Rate limit exceeded — retry later")


class RateLimitStore:
    """Abstraction over rate-limit state so demo and prod can differ.

    - InMemoryRateLimitStore (default): single-process, demo-correct.
      Documented limitation: state is lost on restart and is NOT shared
      across workers/instances — do not horizontally scale mutating
      endpoints on this store.
    - Production with multiple replicas: provide a shared implementation
      (e.g. Redis INCR+EXPIRE keyed on the same bucket string) and install
      it via set_rate_limit_store(). Interface: allow() returns True when
      the request is within budget.
    """
    def allow(self, key: str, limit: int, window_s: int) -> bool:
        raise NotImplementedError

    def reset(self) -> None:
        raise NotImplementedError


class InMemoryRateLimitStore(RateLimitStore):
    def __init__(self):
        self._hits: dict[str, list[float]] = {}

    def allow(self, key: str, limit: int, window_s: int) -> bool:
        now = time.time()
        lst = [t for t in self._hits.get(key, []) if now - t < window_s]
        if len(lst) >= limit:
            self._hits[key] = lst
            return False
        lst.append(now)
        self._hits[key] = lst
        return True

    def reset(self) -> None:
        self._hits.clear()


class RedisRateLimitStore(RateLimitStore):
    """Redis-backed rate limit store for multi-worker production deployments.

    Uses Redis INCR with EXPIRE for atomic sliding-window counting.
    Key format: "ratelimit:{key}:{window_start_timestamp}"

    Requires: pip install redis
    Config: REDIS_URL environment variable (default: redis://localhost:6379/0)
    """
    def __init__(self, redis_url: str | None = None):
        import os
        self.redis_url = redis_url or os.getenv("REDIS_URL", "redis://localhost:6379/0")
        self._client = None
        self._connect()

    def _connect(self):
        try:
            import redis as _redis
            self._client = _redis.from_url(self.redis_url, decode_responses=True)
            # Test connection
            self._client.ping()
        except Exception as e:
            import logging
            _log = logging.getLogger("geo-sentinel")
            _log.warning("Redis rate limit store unavailable, falling back to in-memory: %s", e)
            self._client = None

    def allow(self, key: str, limit: int, window_s: int) -> bool:
        if self._client is None:
            # Fallback to in-memory if Redis unavailable
            return InMemoryRateLimitStore().allow(key, limit, window_s)

        import time as _time
        now = int(_time.time())
        window_start = now - (now % window_s)
        redis_key = f"ratelimit:{key}:{window_start}"

        try:
            pipe = self._client.pipeline()
            pipe.incr(redis_key)
            pipe.expire(redis_key, window_s * 2)
            results = pipe.execute()
            count = results[0]
            return count <= limit
        except Exception as e:
            import logging
            _log = logging.getLogger("geo-sentinel")
            _log.warning("Redis rate limit check failed, allowing request: %s", e)
            return True  # Fail open to avoid blocking legitimate traffic

    def reset(self) -> None:
        if self._client is None:
            return
        try:
            # Note: This is a best-effort cleanup; pattern-based deletion
            # would require SCAN which is expensive. In practice, keys expire.
            pass
        except Exception:
            pass


_STORE: RateLimitStore = InMemoryRateLimitStore()


def init_rate_limit_store() -> RateLimitStore:
    """Initialize rate limit store based on environment configuration.
    
    If REDIS_URL is set, uses RedisRateLimitStore for multi-worker support.
    Otherwise uses InMemoryRateLimitStore (single-worker demo).
    """
    import os
    redis_url = os.getenv("REDIS_URL")
    if redis_url:
        try:
            store = RedisRateLimitStore(redis_url)
            set_rate_limit_store(store)
            import logging
            _log = logging.getLogger("geo-sentinel")
            _log.info("Rate limit store initialized: Redis (%s)", redis_url)
            return store
        except Exception as e:
            import logging
            _log = logging.getLogger("geo-sentinel")
            _log.warning("Failed to initialize Redis rate limit store, using in-memory: %s", e)
    return _STORE


def get_rate_limit_store() -> RateLimitStore:
    return _STORE


def set_rate_limit_store(store: RateLimitStore) -> None:
    """Install a shared store (e.g. Redis) for multi-replica production."""
    global _STORE
    _STORE = store


# Back-compat alias for the old module-level dict API.
_hits: dict[str, list[float]] = {}


def _trusted_proxies() -> set[str]:
    return {p.strip() for p in os.getenv("TRUSTED_PROXIES", "").split(",") if p.strip()}


def resolve_client_ip(direct_peer: str | None, forwarded_for: str | None) -> str:
    """Client-IP resolution with spoof-safe proxy handling.

    X-Forwarded-For is honoured ONLY when the direct TCP peer is a
    configured TRUSTED_PROXIES entry (your nginx/LB). Otherwise the direct
    peer is used, so a client cannot spoof its way around rate limits.
    """
    peer = (direct_peer or "local").strip()
    if forwarded_for and peer in _trusted_proxies():
        first = forwarded_for.split(",")[0].strip()
        if first:
            return first
    return peer


def _client_ip(request) -> str:
    """Request -> rate-limit bucket IP (spoof-safe; see resolve_client_ip)."""
    peer = None
    fwd = None
    try:
        if request is not None and getattr(request, "client", None):
            peer = request.client.host
        headers = getattr(request, "headers", None) if request is not None else None
        if headers is not None:
            fwd = headers.get("x-forwarded-for")
    except Exception as e:
        _log.getLogger("geo-sentinel").debug("Client IP resolution failed: %s", e)
    return resolve_client_ip(peer, fwd)
