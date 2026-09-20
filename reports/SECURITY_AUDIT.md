# SECURITY_AUDIT.md — GEO-SENTINEL (scan + live error-path tests, 2026-09-18)

- **Secrets**: none hardcoded (grep `ADMIN_API_KEY|API_KEYS|SECRET|PASSWORD|TOKEN|sk-|AKIA|ghp_` over `app/` → only `os.getenv` + missing-credential messages). `.env` gitignored; both `.env.example` values empty except weak `POSTGRES_PASSWORD=change-me-in-production`. None exposed in reports (redaction N/A).
- **Auth**: open-demo by default (`auth.py:36-60`, keys unset in compose) — documented, but insecure if hosted. Mutating endpoints without auth/rate-limit: `POST /reports*`, `/vision/analyze`, `/satellite/change` (DB write), `/routes/recalculate`, `/risk/simulation` (expensive).
- **CORS**: `*` by default (`main.py:44-46`, `config.py:25`) — P1 for any hosted demo.
- **Validation**: strong on uploads (MIME + magic bytes + size + sha256 + random names) and sensors; weak elsewhere — `ReportIn.accuracy` str→float 500 risk (`reports.py:162`); unbounded `features`/`sequence`/`limit` (5000-step seq accepted, `limit=1000000` DB DoS); no proxy-aware IP in limiter; limiter in-memory single-worker (documented, no Redis by design).
- **Unsafe load**: `torch.load` without `weights_only=True` (`gs_inference.py:74-75`) — P1 one-flag fix. `joblib.load` on local trusted artifacts only (acceptable; host-write = code-exec boundary, document).
- **Traversal (low-med)**: `GET /datasets/{version}` joins unsanitized version into metadata path (`datasets.py:48-60`); `_observed_cells(zone_id)` similar (`risk.py:1249-1261`, `.json` suffix limits impact).
- **Leakage**: error bodies truncate OS errors (`gs.py:24` `str(e)[:200]`); no SQLi (ORM only); no `eval/exec/shell=True`; `yaml.safe_load`; media filenames server-generated.
- **Deps**: `Pillow/scipy/cryptography` unpinned (non-reproducible builds); `python:3.11-slim` unpinned minor; no hashes.

## Remediation update (2026-09-18, verified)

- FIXED: all `torch.load` use `weights_only=True` (`gs_inference`,
  `mamba_model`, `benchmark_real`); checkpoints verified loadable this way
  (gs folds = raw state dicts; legacy wrapper = `{state_dict,seed,dataset}`);
  repo-wide grep regression test added.
- FIXED: CORS fails closed in production (`_cors_origins`); auth fails closed
  in production (`guard`/`require_role` 401 without keys). Dev/demo unchanged.
- FIXED: traversal — `_read_json_under` allowlist + containment, version
  regex, `_observed_cells` zone allowlist; regression tests added.
- FIXED: `ReportIn` bounds (accuracy non-numeric → 422, not 500); gs/history
  `limit` caps; sequence/features size caps.
- PARTIAL: deps bounded (`Pillow>=10,<13`, `scipy>=1.11,<1.18`,
  `cryptography>=41,<51`); `python:3.11-slim` minor-pinned (patch floats);
  npm exact via `package-lock.json`. No hashes; no hardcoded secrets (re-grep
  clean — only `os.getenv` + missing-credential messages).

## Runtime verification (2026-09-18, executed)

- Production fail-closed proven IN-CONTAINER (`ENVIRONMENT=production`:
  `_cors_origins() == []`, `guard` → 401 without keys); dev stays usable.
- `.env`/DB files confirmed gitignored; container logs secret-free.
- Full null-safety pass over 10 more components (unguided `.toFixed` audit);
  "(SMAP)" title removed (source is modeled/proxy).
