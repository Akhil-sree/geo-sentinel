"""Production worker entrypoint (Phase 9).

15-min near-real-time periodic cycle: fetch rainfall → soil → satellite
metadata → validate → features → risk inference → GIS layers → alert
rules → alerts → audit. Never crashes on one bad cycle; heartbeat lock
prevents duplicates; SIGTERM shuts down gracefully between cycles.
"""
import time
import os
import signal
from app.database import SessionLocal
from app.ingest.runner import run_ingestion
from app.ingest.autoeval import auto_evaluate_alerts

INTERVAL = float(os.getenv("WORKER_INTERVAL_MIN", "15")) * 60
LOCK_PATH = os.path.join(os.path.dirname(__file__), ".worker.lock")


def _owner() -> dict:
    import socket
    return {"pid": os.getpid(), "host": socket.gethostname()}


def _single_instance() -> bool:
    """Heartbeat lock: a second worker exits unless the heartbeat is stale
    (>2 intervals = previous worker crashed). Prevents duplicate jobs.

    Restart-self rule: same host + same pid can only be a restarted self
    (live pids are unique per host), so a fresh lock from "ourselves" is
    taken over instead of exit-looping until stale. Cross-host / cross-pid
    locks keep the freshness check. (Fixed 2026-09-18.)
    """
    import json
    now = time.time()
    try:
        hb = json.load(open(LOCK_PATH, encoding="utf-8"))
        me = _owner()
        if hb.get("host") == me["host"] and hb.get("pid") == me["pid"]:
            print("[worker] own pre-restart heartbeat — taking over", flush=True)
            return True
        if now - hb.get("at", 0) < 2 * INTERVAL:
            print(f"[worker] another instance heartbeated "
                  f"{now - hb['at']:.0f}s ago — exiting", flush=True)
            return False
        print("[worker] stale heartbeat — previous instance crashed?", flush=True)
    except (FileNotFoundError, ValueError, KeyError):
        pass
    return True


def _heartbeat() -> None:
    import json
    try:
        json.dump({"at": time.time(), **_owner()},
                  open(LOCK_PATH, "w", encoding="utf-8"))
    except OSError:
        pass


def _release() -> None:
    """Remove our own heartbeat so a container/process restart boots cleanly.

    Without this, `docker compose restart worker` sees its own pre-restart
    heartbeat as "another instance" and exit-loops until it goes stale
    (2×interval). Only removes the file when it carries our pid+host, so a
    genuinely live peer is never disturbed. Best-effort: crashes skip this
    and the stale path still protects. (Fixed 2026-09-18.)
    """
    import json
    try:
        hb = json.load(open(LOCK_PATH, encoding="utf-8"))
        if hb.get("pid") == os.getpid():
            os.unlink(LOCK_PATH)
    except OSError:
        pass


def _mark_sensor_health(db) -> dict:
    """Age-based sensor health: ONLINE <6h, STALE ≥6h. Sensors never fake
    ONLINE — health derives from actual last_seen timestamps only.

    Defined BEFORE the __main__ block: the loop below blocks forever, so
    anything defined after it would be a NameError on the first cycle
    (reproduced in compose 2026-09-18).
    """
    from datetime import datetime, timezone
    from app.models_db import Sensor
    now = datetime.now(timezone.utc)
    counts = {"ONLINE": 0, "STALE": 0, "OFFLINE": 0}
    try:
        for s in db.query(Sensor).all():
            if not s.last_seen:
                s.status = "OFFLINE"
            else:
                last = s.last_seen.replace(tzinfo=timezone.utc) if s.last_seen.tzinfo is None else s.last_seen
                s.status = "ONLINE" if (now - last).total_seconds() < 6 * 3600 else "STALE"
            counts[s.status] += 1
        db.commit()
    except Exception as e:
        db.rollback()
        return {"status": "FAILED", "detail": str(e)[:120]}
    return {"status": "OK", **counts}


if __name__ == "__main__":
    import signal as _sig
    _stop = {"flag": False}
    _sig.signal(_sig.SIGTERM, lambda *_: _stop.update(flag=True))
    if not _single_instance():
        raise SystemExit(0)
    print(f"[worker] starting — ingestion every {INTERVAL/60:.0f} min", flush=True)
    try:
        while not _stop["flag"]:
            _heartbeat()
            db = SessionLocal()
            try:
                print("[worker] ingestion:", run_ingestion(db), flush=True)
                print("[worker] sensors:", _mark_sensor_health(db), flush=True)
                print("[worker] autoeval:", auto_evaluate_alerts(db), flush=True)
            except Exception as e:  # never crash the loop on one bad cycle
                print("[worker] cycle failed:", e, flush=True)
            finally:
                db.close()
            for _ in range(int(INTERVAL)):
                if _stop["flag"]:
                    break
                time.sleep(1)
    finally:
        _release()
    print("[worker] graceful shutdown", flush=True)
