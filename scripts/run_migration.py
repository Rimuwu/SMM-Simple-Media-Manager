#!/usr/bin/env python3
"""Run DB migration inside docker-compose postgres container (Windows & Linux).

Features:
- Creates a SQL dump backup locally (in `backups/`) before running migration
- Loads SQL from `scripts/migrate_cards.sql` and pipes it into `psql` inside the `postgres` container
- Respects `.env` values for POSTGRES_USER and POSTGRES_DB if present
"""
from __future__ import annotations

import argparse
import os
import shlex
import subprocess
import sys
from datetime import datetime
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
SCRIPTS = ROOT / "scripts"
SQL_FILE = SCRIPTS / "migrate_cards.sql"
BACKUPS = ROOT / "backups"


def load_env(env_path: Path) -> dict:
    env = {}
    if not env_path.exists():
        return env
    for line in env_path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        if "=" not in line:
            continue
        k, v = line.split("=", 1)
        env[k.strip()] = v.strip().strip('"')
    return env


def run(cmd: list[str], input_bytes: bytes | None = None, capture_output=False) -> subprocess.CompletedProcess:
    # Use check=True to raise on failures
    return subprocess.run(cmd, input=input_bytes, check=True, capture_output=capture_output)


def backup_db(user: str, db: str, compose_cmd: list[str]) -> Path:
    BACKUPS.mkdir(parents=True, exist_ok=True)
    ts = datetime.utcnow().strftime("%Y%m%dT%H%M%SZ")
    out_file = BACKUPS / f"{db}_backup_{ts}.sql"
    print(f"Creating backup to {out_file} ...")
    cmd = compose_cmd + ["exec", "-T", "postgres", "pg_dump", "-U", user, "-d", db]
    proc = run(cmd, capture_output=True)
    out_file.write_bytes(proc.stdout)
    print("Backup created.")
    return out_file


def run_migration(sql: str, user: str, db: str, compose_cmd: list[str]):
    cmd = compose_cmd + ["exec", "-T", "postgres", "psql", "-U", user, "-d", db, "-v", "ON_ERROR_STOP=1", "-f", "-"]
    print("Running migration inside postgres container...")
    run(cmd, input_bytes=sql.encode("utf-8"))
    print("Migration completed successfully.")


def main(argv: list[str] | None = None):
    p = argparse.ArgumentParser()
    p.add_argument("--no-backup", action="store_true", help="Skip creating SQL dump backup")
    p.add_argument("--sql", type=Path, default=SQL_FILE, help="Path to SQL file")
    p.add_argument("--compose", default="docker compose", help="Docker compose command (default: 'docker compose')")
    args = p.parse_args(argv)

    if not args.sql.exists():
        print(f"SQL file not found: {args.sql}")
        sys.exit(1)

    env = load_env(ROOT / ".env")
    pg_user = os.getenv("POSTGRES_USER") or env.get("POSTGRES_USER") or "as1"
    pg_db = os.getenv("POSTGRES_DB") or env.get("POSTGRES_DB") or "smm"

    compose_parts = shlex.split(args.compose)

    if not args.no_backup:
        try:
            backup_db(pg_user, pg_db, compose_parts)
        except subprocess.CalledProcessError as exc:
            print("Backup failed:", exc, file=sys.stderr)
            sys.exit(2)

    sql = args.sql.read_text(encoding="utf-8")
    try:
        run_migration(sql, pg_user, pg_db, compose_parts)
    except subprocess.CalledProcessError as exc:
        print("Migration failed:", exc, file=sys.stderr)
        sys.exit(3)


if __name__ == "__main__":
    main()
