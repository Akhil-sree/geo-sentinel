# CI SQLite Repair Report — GEO-SENTINEL

**Commit:** `ae9f4254db0ba4d99c035179777407cebb6597a0`
**Workflow run:** `35501322333` (CI #6, 2026-09-20 09:04 UTC, 2m11s, Success)
**Branch:** `main`
**Date:** 2026-09-20

## Root cause

Two coupled failures produced `no such table: zones|sensors|ingestion_runs|audit_logs|risk_scores` and `PermissionError: [Errno 13] /data`:

1. **No test DB lifecycle.** `app/main.py:26-45` creates tables/seed only inside `lifespan`, which runs only within `with TestClient(app)`. Most tests instantiate `TestClient(app)` bare. On a fresh checkout (`backened/geo_sentinel.db` absent, `.db` is gitignored) no schema existed; 38+ tests failed with `no such table`. Prior fix `6186e8f` added `tests/conftest.py` session fixture doing `Base.metadata.create_all(engine)` but still bound to the default `DATABASE_URL` (`sqlite:///./geo_sentinel.db`), not isolated, and did not handle absolute vs relative path correctly for CI.

2. **`resolve_database_url` blind mkdir on every sqlite URL** (`backened/app/database.py:51-53` before `6186e8f`): `os.makedirs(parent)` executed even for absolute `/data/geo_sentinel.db` (compose shared volume). On GitHub `ubuntu-latest` runners `/data` is root-owned or absent; `mkdir -p /data` raised `PermissionError`, and even when it existed the relative vs absolute split-brain (API vs worker different CWDs) used different files. Fixed in `6186e8f` to `mkdir` only for relative paths; extended here to handle `:memory:` and to use SQLAlchemy `make_url` parsing.

3. **Artifact path drift for XAI.** `app/ml/xai.py:32` hardcoded `models/rf/event_rf_event/model.joblib`, while `app/ml/train_rf.py:main_event()` writes `event_rf_event_v1/`. On a clean checkout only `*_v1` exists, so `permutation_bundle()` returned `None`; the test either skipped (masked) or failed when cache poisoned (`_PERM_CACHE["done"]=True` cached the `None` forever, never retrying after `seed`).

4. **Isolated DB missing `dataset_versions`.** `tests/test_ner_pipeline.py::test_datasets_api_shapes` expects `GET /api/datasets/ner_v1 → 200`, but `DatasetVersion` rows are inserted only by `scripts/build_training_dataset.py`, not by `seed()`. On a fresh isolated `.pytest` DB the table was empty → `404`.

All four were fixed centrally; no tests were deleted or weakened.

## Database architecture

```
TEST_DATABASE_URL (env) ──┐
                          ↓
app/config.py: DATABASE_URL (default sqlite:///./geo_sentinel.db)
              TEST_DATABASE_URL (override, "" if not set)
                          ↓
app/database.py: _ACTIVE_URL = TEST_DATABASE_URL or DATABASE_URL
                 DB_BACKEND = backend_name(_ACTIVE_URL)
                 RESOLVED_DATABASE_URL = resolve_database_url(_ACTIVE_URL)
                 engine = create_engine(RESOLVED_DATABASE_URL,
                            check_same_thread=False,
                            poolclass=StaticPool if ":memory:" else default,
                            pool_pre_ping= (postgresql))
                 SessionLocal, Base, get_db()
                          ↓
tests/conftest.py:  import app.models_db  # registers all tables on Base
                    Base.metadata.create_all(bind=engine)  # before any test
                    app.dependency_overrides[get_db] = _get_test_db  # same SessionLocal
                    seed(db)  # idempotent
                    yield  →  pop override, engine.dispose()
```

- **Test engine:** single global `engine`/`SessionLocal` in `app/database.py`, resolved at import time. When `TEST_DATABASE_URL=sqlite:///./.pytest/geosentinel-test.db` is set, every consumer (`app.main`, `worker.py`, all `from app.database import SessionLocal` imports) binds to `D:/sih/backened/.pytest/geosentinel-test.db` (on Linux `/home/runner/.../backened/.pytest/...`).

- **Test database URL:** `sqlite:///./.pytest/geosentinel-test.db` — relative, resolved beneath `BACKEND_DIR` (`backened/`) via `resolve_database_url`, parent created. Alternative `sqlite:///:memory:` supported with `StaticPool` + `check_same_thread=False` so every session sees the same in-memory DB; current CI uses file-based `.pytest` (safer for multi-connection tests and persists for artifact caching).

- **Schema initialization:** `Base.metadata.create_all(bind=engine)` in `conftest.py` session `autouse` fixture, after `import app.models_db` (ensures `zones`, `sensors`, `ingestion_runs`, `audit_logs`, `risk_scores` + all 28 tables present). Verified by `test_schema_requires_expected_tables`.

- **API dependency override:** `app.dependency_overrides[get_db] = _get_test_db` where `_get_test_db` yields `SessionLocal()`; ensures `TestClient(app)` requests never silently use a different default DB. Removed in fixture teardown.

- **Worker database behavior:** `worker.py:11` does `from app.database import SessionLocal` — same global. With `TEST_DATABASE_URL` set at process start, worker would use the same `.pytest` file if invoked under test; no separate engine exists, so no split-brain `API → test SQLite, Worker → /data` remains.

- **SQLite path resolution (`resolve_database_url`):**
  - `":memory:" in url` → return unchanged, no `mkdir` (caller uses `StaticPool`).
  - `backend_name(url) != "sqlite"` (postgresql) → pass-through.
  - Otherwise parse via `sqlalchemy.engine.url.make_url` for robust `database` extraction; `raw` is `None` → fallback to string slice.
  - `os.path.isabs(raw) or raw.startswith("/")` → absolute (e.g. `sqlite:////data/geo_sentinel.db` on shared volume) → `os.path.normpath`, **no** `mkdir` (avoids `/data` permission error), preserve leading `/`.
  - Else relative (`./.pytest/...`, `geo_sentinel.db`) → strip leading `./`, join with `BACKEND_DIR`, `os.makedirs(parent, exist_ok=True)`. Uses SQLAlchemy URL parsing, not blind `Path("/data").mkdir`.

## Files changed

| File | Why |
|---|---|
| `backened/app/config.py:13-16` | Adds `TEST_DATABASE_URL = os.getenv("TEST_DATABASE_URL", "")` — test-time override, documented as `sqlite:///./.pytest/geosentinel-test.db` in CI. Keeps `DATABASE_URL` as production/demo default. |
| `backened/app/database.py` | Introduces `_ACTIVE_URL`, `StaticPool` import, `resolve_database_url` now handles `:memory:` (no FS), postgres pass-through via `backend_name`, SQLAlchemy `make_url` robust parsing, absolute preserved + no mkdir, relative anchored + mkdir, and `engine` branching `StaticPool` for `:memory:` else `check_same_thread=False`. Single log line `database backend=… url=…`. |
| `backened/tests/conftest.py` | Full session boot: `import app.models_db` to register all models, `Base.metadata.create_all(bind=engine)`, `app.dependency_overrides[get_db] = _get_test_db` (same `SessionLocal`), `seed(db)`, yield, then `pop` + `engine.dispose()`. Adds `test_schema_requires_expected_tables` asserting `zones,sensors,ingestion_runs,audit_logs,risk_scores` present. |
| `.github/workflows/ci.yml:47-52` | Backend job now `env: TEST_DATABASE_URL: sqlite:///./.pytest/geosentinel-test.db` and `rm -rf .pytest` before `pytest`, guaranteeing a writable, isolated, disposable DB that does not touch `/data` or `geo_sentinel.db`. |
| `backened/app/ml/xai.py:16-32` | Fixes `permutation_bundle` cache: only `done=True` on success, transient failures return `None` without caching (allows retry after `seed`). Supports both `event_rf_event/` and `event_rf_event_v1/` artifact paths (current `main_event` output), preventing spurious skip/failure on clean checkout. |
| `backened/tests/test_pipeline.py:172-194` | `test_xai_permutation_measured_and_labeled` now self-sufficient: checks both candidate model paths, generates via `main_event()` if neither exists, clears stale `None` cache, then asserts `permutation on events_v2` and `PERMUTATION_IMPORTANCE`. No `skipif` suppression. |
| `backened/tests/test_ner_pipeline.py:107-138` | `test_datasets_api_shapes` ensures isolated DB has `ner_v1` row: if `DatasetVersion` missing, inserts minimal `VALIDATED` row from `data/metadata/ner_training_ner_v1.json` before `TestClient` calls. Keeps existing `skipif` on CSV absence, but no longer fails on fresh `.pytest` DB. |
| `backened/app/config.py` / `database.py` together | Ensure `DATABASE_URL` and `TEST_DATABASE_URL` are not competing: `TEST_DATABASE_URL or DATABASE_URL` is single source; CI and local clean-env test set `TEST_DATABASE_URL` consistently. |

No docs, no `registry.json`, no `*.db` committed; `*.db` remains gitignored.

## Local verification

**Clean env 1 — isolated CI path (fresh, writable, correct schema):**
```powershell
# backened/
Remove-Item -Recurse -Force .pytest -ErrorAction SilentlyContinue
$env:TEST_DATABASE_URL="sqlite:///./.pytest/geosentinel-test.db"
python -m pytest tests/ -v --tb=short
# Result: 193 passed, 4 skipped in 82.85s
# - test_schema_requires_expected_tables PASSED
# - test_xai_permutation_measured_and_labeled PASSED (generated v1 artifact if needed, deterministic slope=0.0 etc.)
# - test_datasets_api_shapes PASSED (inserted ner_v1 row)
# - .pytest/geosentinel-test.db created at D:\sih\backened\.pytest\geosentinel-test.db, parent auto-created
```

**Clean env 2 — repeat delete, same env (verifies not dependent on previous DB):**
```powershell
Remove-Item -Recurse -Force .pytest
$env:TEST_DATABASE_URL="sqlite:///./.pytest/geosentinel-test.db"
python -m pytest tests/ -v --tb=short
# Result: 193 passed, 4 skipped in ~73s — schema recreated from scratch
```

**Resolver sanity:**
```powershell
python -c "from app.database import resolve_database_url; print(resolve_database_url('sqlite:///:memory:')); print(resolve_database_url('sqlite:////data/geo_sentinel.db')); print(resolve_database_url('sqlite:///./.pytest/geosentinel-test.db'))"
# sqlite:///:memory:
# sqlite:///\data\geo_sentinel.db  (on Linux: sqlite:////data/geo_sentinel.db)
# sqlite:///D:/sih/backened/.pytest/geosentinel-test.db
```

**Lint / type / frontend / docker (full CI-equivalent):**
```bash
ruff check app/ tests/          # All checks passed!
mypy app/ --ignore-missing-imports  # 107 advisory errors (pre-existing, || true in CI)
npx tsc --noEmit               # no errors (vite)
npm test -- --run               # 62 passed (12 files)
npm run build                   # built in 36s
python .github/scripts/check_markdown_links.py  # checked 1 links; 0 broken
docker compose config           # validated
docker build -t geosentinel-backend:test ./backened   # success (cached)
docker build -t geosentinel-frontend:test ./frontend  # success
```

**Default (no env) still works:**
```powershell
Remove-Item Env:\TEST_DATABASE_URL
Remove-Item -Force geo_sentinel.db
python -m pytest tests/test_db_shared_persistence.py tests/test_pipeline.py::test_seed_flushes_zones_before_dependents -v
# 5 passed — fallback to sqlite:///./geo_sentinel.db still creates schema
```

## GitHub Actions verification

**Commit SHA:** `ae9f4254db0ba4d99c035179777407cebb6597a0` (pushed `main` 2026-09-20 09:04 UTC)
**Workflow run ID:** `35501322333` (CI #6, `https://github.com/Akhil-sree/geo-sentinel/actions/runs/35501322333`)
**Run duration:** 2m11s (previous failing run `#5 6186e8f` 2m46s)

| Job | Result | Duration | Notes |
|---|---|---|---|
| Backend Tests (`ubuntu-latest`, `TEST_DATABASE_URL=sqlite:///./.pytest/geosentinel-test.db`) | **Success** | 48s | `rm -rf .pytest` + `pytest 193 passed 4 skipped`, no `/data` error, schema created on fresh runner |
| Frontend Tests & Build | **Success** | 30s | `tsc --noEmit`, `vitest 62 passed`, `vite build` |
| Documentation Check | **Success** | 3s | `check_markdown_links.py 1 links 0 broken` |
| Docker Build (needs backend+frontend) | **Success** | 1m14s | `docker build backend` + `frontend` + `compose config` validated |

**Overall result:** **Success** — all four CI jobs green. Verified via `https://github.com/Akhil-sree/geo-sentinel/actions/runs/35501322333` (poll every 30s, `Status Success`). Annotations are only `Node.js 20 deprecated` and `ubuntu-latest → 26` notices, not failures.

## Remaining issues

- `mypy` advisory (`|| true` in CI) still reports 107 pre-existing type errors (mostly `Column[str]` vs `str`, `no_implicit_optional`), unchanged by this fix. Requires dedicated type-clean pass to remove `|| true`.
- `TEST_DATABASE_URL` is file-based `.pytest/geosentinel-test.db`, not `:memory:`. Chosen as safer for multi-session `TestClient` usage without `StaticPool` nuances; `:memory:` path is fully handled if `TEST_DATABASE_URL=sqlite:///:memory:` is set (returns verbatim, `StaticPool` engine).
- `.pytest_cache` vs `.pytest` naming: CI uses `.pytest/` (per spec) while pytest cache uses `.pytest_cache/`; both are disposable and gitignored via `*.db`/`__pycache__` patterns.

No `no such table`, no `/data` permission error, no committed `.db`, no skipped database tests, no `continue-on-error`, no developer-specific Windows path, no hardcoded `/data` mkdir.
