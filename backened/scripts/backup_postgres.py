"""PostgreSQL backup/restore helper (production procedure).

Usage:
    python scripts/backup_postgres.py backup [--out backups/geo-YYYYmmdd-HHMMSS.dump]
    python scripts/backup_postgres.py restore --from backups/geo-....dump [--force]

Uses pg_dump/pg_restore for consistent backups with compression.
Requires: pg_dump and pg_restore in PATH (PostgreSQL client tools).
See docs/BACKUP_RECOVERY.md for RPO/RTO and full procedure.
"""
import argparse
import os
import subprocess
import sys
from datetime import datetime, timezone
from urllib.parse import urlparse

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from app.database import RESOLVED_DATABASE_URL  # noqa: E402


def _parse_pg_url(url: str) -> dict:
    """Parse PostgreSQL URL into connection parameters for pg_dump/pg_restore."""
    parsed = urlparse(url)
    return {
        "host": parsed.hostname or "localhost",
        "port": parsed.port or 5432,
        "user": parsed.username or "postgres",
        "password": parsed.password or "",
        "dbname": parsed.path.lstrip("/") or "postgres",
    }


def _pg_env(params: dict) -> dict:
    """Build environment dict for pg_dump/pg_restore with PGPASSWORD."""
    env = os.environ.copy()
    if params["password"]:
        env["PGPASSWORD"] = params["password"]
    return env


def backup(out=None):
    """Create a compressed PostgreSQL backup using pg_dump."""
    url = RESOLVED_DATABASE_URL
    if not url.startswith(("postgresql://", "postgres://", "postgresql+psycopg2://")):
        raise SystemExit(f"backup_postgres.py requires PostgreSQL URL, got: {url[:30]}...")

    params = _parse_pg_url(url)

    if out is None:
        stamp = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
        out = os.path.join(os.path.dirname(__file__), "..", "backups", f"geo-{stamp}.dump")

    os.makedirs(os.path.dirname(out), exist_ok=True)

    cmd = [
        "pg_dump",
        "-h", params["host"],
        "-p", str(params["port"]),
        "-U", params["user"],
        "-d", params["dbname"],
        "-Fc",  # custom format (compressed)
        "-f", out,
    ]

    print(f"[backup] Running: {' '.join(cmd[:-2])} -f {out}")
    result = subprocess.run(cmd, env=_pg_env(params), capture_output=True, text=True)
    if result.returncode != 0:
        raise SystemExit(f"pg_dump failed: {result.stderr}")

    # Verify backup integrity
    verify_cmd = ["pg_restore", "-l", out]
    verify_result = subprocess.run(verify_cmd, env=_pg_env(params), capture_output=True, text=True)
    if verify_result.returncode != 0:
        raise SystemExit(f"Backup verification failed: {verify_result.stderr}")

    print(f"[backup] OK: {out}")
    return out


def restore(frm, force=False):
    """Restore PostgreSQL database from a pg_dump custom-format backup."""
    url = RESOLVED_DATABASE_URL
    if not url.startswith(("postgresql://", "postgres://", "postgresql+psycopg2://")):
        raise SystemExit(f"restore requires PostgreSQL URL, got: {url[:30]}...")

    if not os.path.exists(frm):
        raise SystemExit(f"Backup file missing: {frm}")

    params = _parse_pg_url(url)

    if not force:
        # Check if database has data
        check_cmd = [
            "psql",
            "-h", params["host"],
            "-p", str(params["port"]),
            "-U", params["user"],
            "-d", params["dbname"],
            "-t", "-c", "SELECT count(*) FROM information_schema.tables WHERE table_schema='public'",
        ]
        check_result = subprocess.run(check_cmd, env=_pg_env(params), capture_output=True, text=True)
        if check_result.returncode == 0:
            table_count = int(check_result.stdout.strip() or "0")
            if table_count > 0:
                raise SystemExit(
                    f"Database has {table_count} tables. Use --force to overwrite."
                )

    cmd = [
        "pg_restore",
        "-h", params["host"],
        "-p", str(params["port"]),
        "-U", params["user"],
        "-d", params["dbname"],
        "--clean",
        "--if-exists",
        "--no-owner",
        "--no-privileges",
        frm,
    ]

    print(f"[restore] Running: {' '.join(cmd)}")
    result = subprocess.run(cmd, env=_pg_env(params), capture_output=True, text=True)
    if result.returncode != 0:
        raise SystemExit(f"pg_restore failed: {result.stderr}")

    print(f"[restore] OK: {frm} -> {params['dbname']}@{params['host']}:{params['port']}")


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