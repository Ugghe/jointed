#!/usr/bin/env python3
"""
Copy all Jointed app tables from a source database to a target database.

Typical use: local SQLite (after imports and QA) → Render Postgres (live).

Prerequisites:
  - Target schema matches source (run `alembic upgrade head` on the target first).
  - Set JOINTED_PROMOTE_TARGET to the live connection string (see below).

Environment:
  JOINTED_PROMOTE_SOURCE   Optional. Source URL. Defaults to JOINTED_DATABASE_URL,
                           then DATABASE_URL, then sqlite:///./data/jointed.db
  JOINTED_PROMOTE_TARGET   Required unless --dry-run. Destination URL (e.g. Render Postgres).

Examples (PowerShell):
  $env:JOINTED_PROMOTE_TARGET = "postgresql+psycopg://user:pass@host:5432/dbname"
  python scripts/promote_db.py --dry-run
  python scripts/promote_db.py --yes

Examples (bash):
  export JOINTED_PROMOTE_TARGET="postgresql+psycopg://..."
  python scripts/promote_db.py --yes
"""

from __future__ import annotations

import argparse
import os
import sys
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import create_engine, delete, func, insert, inspect as sa_inspect, select, text
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

# Repo root on path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.config import normalize_database_url  # noqa: E402
from app.models import Base  # noqa: E402


def _mask_url(url: str) -> str:
    if "@" not in url:
        return url
    head, tail = url.rsplit("@", 1)
    if "://" not in head:
        return url
    scheme, rest = head.split("://", 1)
    if ":" in rest:
        user, _ = rest.split(":", 1)
        return f"{scheme}://{user}:***@{tail}"
    return f"{scheme}://***@{tail}"


def _resolve_source_url() -> str:
    raw = (
        os.environ.get("JOINTED_PROMOTE_SOURCE")
        or os.environ.get("JOINTED_DATABASE_URL")
        or os.environ.get("DATABASE_URL")
        or "sqlite:///./data/jointed.db"
    )
    return normalize_database_url(raw)


def _resolve_target_url() -> str | None:
    raw = os.environ.get("JOINTED_PROMOTE_TARGET")
    return normalize_database_url(raw) if raw else None


def _aware_dt(value: Any) -> Any:
    if isinstance(value, datetime) and value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value


def _row_for_insert(row: dict[str, Any]) -> dict[str, Any]:
    return {k: _aware_dt(v) for k, v in row.items()}


def _clear_target(session: Session, dialect: str) -> None:
    tables = list(reversed(Base.metadata.sorted_tables))
    names = ", ".join(f'"{t.name}"' for t in tables)
    if dialect == "postgresql":
        session.execute(text(f"TRUNCATE {names} RESTART IDENTITY CASCADE"))
    elif dialect == "sqlite":
        for t in tables:
            session.execute(delete(t))
        bind = session.get_bind()
        if sa_inspect(bind).has_table("sqlite_sequence"):
            session.execute(text("DELETE FROM sqlite_sequence"))
    else:
        raise SystemExit(f"Unsupported target dialect for wipe: {dialect}")


def _reset_postgres_serials(session: Session) -> None:
    """Align SERIAL sequences with current MAX(id) for tables with a single integer `id` PK."""
    for table in Base.metadata.sorted_tables:
        cols = list(table.primary_key.columns)
        if len(cols) != 1 or cols[0].name != "id":
            continue
        tname = table.name
        max_id = session.execute(select(func.max(table.c.id))).scalar_one_or_none()
        if max_id is None:
            session.execute(
                text("SELECT setval(pg_get_serial_sequence(:tbl, 'id'), 1, false)").bindparams(tbl=tname)
            )
        else:
            session.execute(
                text("SELECT setval(pg_get_serial_sequence(:tbl, 'id'), :m, true)").bindparams(
                    tbl=tname, m=max_id
                )
            )


def _table_counts(session: Session) -> list[tuple[str, int]]:
    out: list[tuple[str, int]] = []
    for table in Base.metadata.sorted_tables:
        n = session.execute(select(func.count()).select_from(table)).scalar_one()
        out.append((table.name, int(n)))
    return out


def _copy_tables(source: Engine, target: Engine, dry_run: bool) -> tuple[int, list[tuple[str, int]]]:
    sm = sessionmaker(bind=source)
    tm = sessionmaker(bind=target)

    with sm() as ss:
        counts_before = _table_counts(ss)
        total = sum(c for _, c in counts_before)

    if dry_run:
        return total, counts_before

    with sm() as ss, tm() as ts:
        dialect = ts.get_bind().dialect.name
        if dialect not in ("postgresql", "sqlite"):
            raise SystemExit(f"Target must be postgresql or sqlite (got {dialect})")

        _clear_target(ts, dialect)

        for table in Base.metadata.sorted_tables:
            rows = ss.execute(select(table)).mappings().all()
            if not rows:
                continue
            for row in rows:
                ts.execute(insert(table).values(**_row_for_insert(dict(row))))

        if dialect == "postgresql":
            _reset_postgres_serials(ts)

    with tm() as ts:
        counts_after = _table_counts(ts)

    return sum(c for _, c in counts_after), counts_after


def main() -> None:
    p = argparse.ArgumentParser(description="Copy Jointed DB data from source to target.")
    p.add_argument(
        "--dry-run",
        action="store_true",
        help="Show row counts per table on source only; do not write to target.",
    )
    p.add_argument(
        "--yes",
        action="store_true",
        help="Required to replace all data on the target (destructive).",
    )
    p.add_argument(
        "--allow-empty-source",
        action="store_true",
        help="Allow promoting when the source has zero rows (wipes the target).",
    )
    args = p.parse_args()

    source_url = _resolve_source_url()
    target_url = _resolve_target_url()

    print(f"Source: {_mask_url(source_url)}")
    if target_url:
        print(f"Target: {_mask_url(target_url)}")
    elif not args.dry_run:
        print("Error: set JOINTED_PROMOTE_TARGET to the destination database URL.", file=sys.stderr)
        sys.exit(1)

    src = create_engine(source_url, echo=False)
    if args.dry_run:
        total, counts = _copy_tables(src, src, dry_run=True)
        print("Tables (source row counts):")
        for name, n in counts:
            print(f"  {name}: {n}")
        print(f"Total rows: {total}")
        print("Dry run - no changes made.")
        return

    if not args.yes:
        print(
            "Refusing to replace target data without --yes. "
            "Run with --dry-run first, then: python scripts/promote_db.py --yes",
            file=sys.stderr,
        )
        sys.exit(1)

    if not target_url:
        sys.exit(1)

    sm = sessionmaker(bind=src)
    with sm() as ss:
        src_total = sum(n for _, n in _table_counts(ss))
    if src_total == 0 and not args.allow_empty_source:
        print(
            "Source database has no rows. Refusing to wipe the target. "
            "If you really want an empty target, pass --allow-empty-source.",
            file=sys.stderr,
        )
        sys.exit(1)

    dst = create_engine(target_url, echo=False)
    total, counts = _copy_tables(src, dst, dry_run=False)
    print("Promoted tables (row counts on target after copy):")
    for name, n in counts:
        print(f"  {name}: {n}")
    print(f"Total rows: {total}")
    print("Done.")


if __name__ == "__main__":
    main()
