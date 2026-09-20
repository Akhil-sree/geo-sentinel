# ALERT PIPELINE

Lifecycle: DETECTED (worker auto-eval, HIGH+) → EVALUATED (thresholds from
`risk_thresholds.yaml`) → TRIGGERED (cooldown 360m, escalation-only resend,
hourly idempotency key `zone:severity:UTChour`) → SENT (SMS/email providers;
MOCK labeled, LIVE only with credentials) → ACKNOWLEDGED → RESOLVED.
Every transition writes AuditLog; dispatch records the idempotency key.

Dedup layers: per-zone cooldown (escalation bypasses) → hourly idempotency
(double-submit safe) → severity gate (HIGH/VERY_HIGH only) → role gate
(operator/admin). Manual dispatch: `POST /alerts/send` (rate-limited 60/m,
role-gated). No evacuation orders; templates en/hi reviewed, others fall
back to en (never machine-translated).

Failure behavior: provider exception → `FAILED: ...` status per recipient,
logged, never claimed delivered. Delivery mode always returned
(`MOCK DELIVERY` vs `LIVE provider`).
