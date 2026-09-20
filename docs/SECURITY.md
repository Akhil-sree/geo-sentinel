# SECURITY

Auth: role API keys (`API_KEYS="k:admin,k:operator,k:viewer"`, legacy
`ADMIN_API_KEY`=admin), enforced server-side via `require_role` on
send/evaluate/ack/resolve/moderate. Open-demo when unset (labeled
`auth_mode`). Roles: admin > operator > viewer. Object-level: moderation +
alert lifecycle require operator+; no cross-user data (reports are
id-keyed, no accounts).

Secrets: env-only; `ENC:` values decrypt via `FERNET_KEY` (SecretBox);
never logged (tests assert roundtrip, SMTP uses reveal). JWT with
expiry/refresh/revocation: ROADMAP — not faked (no half-working tokens).

Transport/input: security headers (nosniff/DENY/no-referrer, tested);
CORS demo-open `*` unless `CORS_ORIGINS` set (documented); rate limits —
send 60/m, moderate 30/m, upload 20/m (in-memory, single worker by design; no Redis
roadmap for multi-instance); GPS range validation; uploads: MIME +
magic-byte + size + sanitized names + sha256 dedup (409); path traversal
prevented (server-generated names, static mount).

DB: SQLite demo (labeled); versioned migrations (`schema_versions`, fresco
steps, never destructive); Postgres/PostGIS via `DATABASE_URL` + compose
prod profile (runtime-unverified). Audit: REPORT_* / ALERT_* / SEED actions.

Media (`/media`): public-read BY DOCUMENTED DEMO DESIGN — dashboard clients
fetch field-report photos without a session layer (no accounts/JWT in demo
scope). Uploads stay hardened: MIME allowlist (no SVG/HTML), magic-byte
check, 8/25 MB caps, server-generated uuid names (traversal-proof), sha256
dedup; regression tests in `backened/tests/test_media_security.py`.
Production with sensitive imagery: move to S3 + signed URLs (see
`backened/.env.example` S3 keys) and gate reads.

Rate limiting (2026-09-19): `RateLimitStore` abstraction
(`app/auth.py`) — in-memory default (single-process; lost on restart, not
shared across replicas), swappable shared store for multi-replica prod.
Client-IP via `resolve_client_ip`: X-Forwarded-For honoured ONLY from
`TRUSTED_PROXIES` peers; spoofed headers ignored (tested).

Routing safety (2026-09-19): `ROUTE_MAX_SNAP_DISTANCE_M` (default 5000);
beyond-threshold snaps answer OUT_OF_COVERAGE; routes require >= 1 segment
and >= 2 valid geometry positions (`tests/test_routing_safety.py`).

Error contracts (2026-09-19): unknown zone -> 404, invalid coords -> 422,
missing roads/model artifact -> 503 (`tests/test_error_contracts.py`).
Observability: JSON request logs + `/api/metrics` request/route/ML/provider
counters (in-memory, resets on restart).
