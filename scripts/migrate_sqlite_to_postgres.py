"""Migrate LLM API data from SQLite to PostgreSQL/Supabase.

Usage:
  python scripts/migrate_sqlite_to_postgres.py \
    --source sqlite:////absolute/path/to/llm_api.db \
    --target postgresql+psycopg://user:pass@host:5432/postgres?sslmode=require
"""

from __future__ import annotations

import argparse
from typing import Iterable

from sqlalchemy import MetaData, create_engine, select, text


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Migrate SQLite DB to PostgreSQL")
    parser.add_argument("--source", required=True, help="Source SQLAlchemy DB URL (SQLite)")
    parser.add_argument("--target", required=True, help="Target SQLAlchemy DB URL (PostgreSQL)")
    parser.add_argument(
        "--truncate-target",
        action="store_true",
        help="Delete existing rows in matching target tables before copy",
    )
    return parser.parse_args()


def _table_names(metadata: MetaData) -> Iterable[str]:
    return sorted(metadata.tables.keys())


def main() -> None:
    args = _parse_args()

    source_engine = create_engine(args.source)
    target_engine = create_engine(args.target)

    source_md = MetaData()
    target_md = MetaData()

    source_md.reflect(bind=source_engine)
    target_md.reflect(bind=target_engine)

    source_tables = list(_table_names(source_md))
    print(f"Found {len(source_tables)} source tables")

    copied_tables = 0
    copied_rows = 0

    with source_engine.connect() as source_conn, target_engine.begin() as target_conn:
        for table_name in source_tables:
            source_table = source_md.tables[table_name]
            target_table = target_md.tables.get(table_name)
            if target_table is None:
                print(f"Skipping {table_name}: not found in target")
                continue

            rows = source_conn.execute(select(source_table)).mappings().all()

            if args.truncate_target:
                try:
                    target_conn.execute(
                        text(f'TRUNCATE TABLE "{table_name}" RESTART IDENTITY CASCADE')
                    )
                except Exception:
                    target_conn.execute(text(f'DELETE FROM "{table_name}"'))

            if rows:
                target_conn.execute(target_table.insert(), [dict(row) for row in rows])

            copied_tables += 1
            copied_rows += len(rows)
            print(f"Copied {len(rows)} rows: {table_name}")

    print(f"Migration complete. Tables copied: {copied_tables}, rows copied: {copied_rows}")


if __name__ == "__main__":
    main()
