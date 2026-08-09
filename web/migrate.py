"""Migrate existing SQLite data into a Postgres database (Vercel/Neon).

Usage:
    python web/migrate.py [path-to-sqlite.db]

Reads the SQLite file (default: data/sales.db) and writes every table into the
database pointed to by the ``DATABASE_URL`` environment variable, preserving
IDs and repairing Postgres sequences afterwards.
"""

from __future__ import annotations

import os
import sys

from web.store import PostgresStore, SqliteStore

TABLES = (
    "users",
    "settings",
    "products",
    "product_columns",
    "product_column_values",
    "sales",
)

SEQUENCES = {
    "users": "users_id_seq",
    "products": "products_id_seq",
    "sales": "sales_id_seq",
    "product_columns": "product_columns_id_seq",
    "product_column_values": "product_column_values_id_seq",
}


def migrate_sqlite_to_postgres(sqlite_path: str, url: str) -> None:
    src = SqliteStore(sqlite_path)
    dst = PostgresStore(url)
    dst._init_schema()

    for table in TABLES:
        cols = [r["name"] for r in src.query(f"PRAGMA table_info({table})")]
        rows = src.query(f"SELECT {', '.join(cols)} FROM {table}")
        if not rows:
            print(f"{table}: no rows")
            continue
        col_sql = ", ".join(cols)
        placeholders = ", ".join(["%s"] * len(cols))
        inserted = 0
        for row in rows:
            dst.execute(
                f"INSERT INTO {table} ({col_sql}) VALUES ({placeholders})"
                " ON CONFLICT DO NOTHING",
                [row[c] for c in cols],
            )
            inserted += 1
        print(f"{table}: copied {inserted} rows")

    for table, seq in SEQUENCES.items():
        row = dst.query_one(f"SELECT COALESCE(MAX(id), 0) AS m FROM {table}")
        top = max(int(row["m"]), 1)
        dst.execute(f"SELECT setval('{seq}', %s, true)", (top,))
        print(f"{table}: sequence {seq} -> {top}")

    print("Migration complete.")


def main() -> None:
    sqlite_path = sys.argv[1] if len(sys.argv) > 1 else "data/sales.db"
    url = os.environ.get("DATABASE_URL")
    if not url:
        sys.exit("DATABASE_URL is not set. Export it before running this script.")
    if not os.path.exists(sqlite_path):
        sys.exit(f"SQLite file not found: {sqlite_path}")
    migrate_sqlite_to_postgres(sqlite_path, url)


if __name__ == "__main__":
    main()
