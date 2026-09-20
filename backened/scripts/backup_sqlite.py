"""SQLite backup/restore helper (tested procedure, not automation).

Usage:
  python scripts/backup_sqlite.py backup [--out backups/geo-YYYYmmdd-HHMMSS.db]
  python scripts/backup_sqlite.py restore --from backups/geo-....db [--force]

Uses the sqlite3 online-backup API (consistent snapshot while running).
See docs/BACKUP_RECOVERY.md for RPO/RTO and the Postgres procedure.
"""
import argparse
import os
import sqlite3
import sys
from datetime import datetime, timezone

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from app.database import RESOLVED_DATABASE_URL  # noqa: E402


def _db_path():
    url = RESOLVED_DATABASE_URL
    assert url.startswith("sqlite:///"), f"not a sqlite URL: {url[:20]}..."
    return url[len("sqlite:///"):]


def backup(out=None):
    src = _db_path()
    if not os.path.exists(src):
        raise SystemExit(f"source DB missing: {src}")
    if out is None:
        stamp = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
        out = os.path.join(os.path.dirname(src), "backups", f"geo-{stamp}.db")
    os.makedirs(os.path.dirname(out), exist_ok=True)
    with sqlite3.connect(src) as s, sqlite3.connect(out) as d:
        s.backup(d)
    # integrity proof immediately after copy
    with sqlite3.connect(out) as d:
        row = d.execute("PRAGMA integrity_check").fetchone()
        assert row and row[0] == "ok", f"integrity_check failed: {row}"
    print(f"backup ok: {out}")
    return out


def restore(frm, force=False):
    if not os.path.exists(frm):
        raise SystemExit(f"backup file missing: {frm}")
    dst = _db_path()
    if os.path.exists(dst) and not force:
        raise SystemExit("refusing to overwrite live DB without --force")
    with sqlite3.connect(frm) as s, sqlite3.connect(dst) as d:
        s.backup(d)
    print(f"restore ok: {frm} -> {dst}")


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("action", choices=["backup", "restore"])
    p.add_argument("--out", default=None)
    p.add_argument("--from", dest="frm", default=None)
    p.add_argument("--force", action="store_true")
    a = p.parse_args()
    if a.action == "backup":
        backup(a.out)
    else:
        if not a.frm:
            raise SystemExit("--from is required for restore")
        restore(a.frm, a.force)
