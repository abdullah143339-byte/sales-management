"""Database access layer for the web app.

Two backends behind one interface so the app can be developed/tested with
SQLite and run in production on Vercel with Postgres (``DATABASE_URL``):

- ``Store.query(sql, params)``    -> list[dict]
- ``Store.query_one(sql, params)`` -> dict | None
- ``Store.execute(sql, params)``   -> inserted id (from RETURNING) or None
- ``Store.execute_many(sql, rows)``

Queries are written with Postgres-compatible ``%s`` placeholders and ``ILIKE``;
the SQLite backend translates them automatically. New rows are read back with
``INSERT ... RETURNING id`` (supported by SQLite >= 3.35).
"""

from __future__ import annotations

import os
import threading

SCHEMA_SQLITE = """
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT NOT NULL UNIQUE,
    password_hash TEXT NOT NULL,
    created_at TEXT NOT NULL DEFAULT (datetime('now', 'localtime')),
    updated_at TEXT NOT NULL DEFAULT (datetime('now', 'localtime'))
);
CREATE TABLE IF NOT EXISTS products (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    unit_price_paisa INTEGER NOT NULL DEFAULT 0,
    stock INTEGER NOT NULL DEFAULT 0,
    status TEXT NOT NULL DEFAULT 'active',
    created_at TEXT NOT NULL DEFAULT (datetime('now', 'localtime')),
    updated_at TEXT NOT NULL DEFAULT (datetime('now', 'localtime'))
);
CREATE TABLE IF NOT EXISTS sales (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    product_id INTEGER,
    product_name TEXT NOT NULL,
    unit_price_paisa INTEGER NOT NULL,
    quantity INTEGER NOT NULL,
    total_amount_paisa INTEGER NOT NULL,
    sale_date TEXT NOT NULL,
    sale_time TEXT NOT NULL,
    created_at TEXT NOT NULL DEFAULT (datetime('now', 'localtime')),
    FOREIGN KEY (product_id) REFERENCES products(id) ON DELETE SET NULL
);
CREATE TABLE IF NOT EXISTS settings (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS product_columns (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    created_at TEXT NOT NULL DEFAULT (datetime('now', 'localtime'))
);
CREATE TABLE IF NOT EXISTS product_column_values (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    product_id INTEGER NOT NULL,
    column_id INTEGER NOT NULL,
    value TEXT NOT NULL DEFAULT '',
    FOREIGN KEY (product_id) REFERENCES products(id) ON DELETE CASCADE,
    FOREIGN KEY (column_id) REFERENCES product_columns(id) ON DELETE CASCADE,
    UNIQUE (product_id, column_id)
);
CREATE INDEX IF NOT EXISTS idx_products_name ON products(name);
CREATE INDEX IF NOT EXISTS idx_sales_product_id ON sales(product_id);
CREATE INDEX IF NOT EXISTS idx_sales_date ON sales(sale_date);
"""

SCHEMA_POSTGRES = """
CREATE TABLE IF NOT EXISTS users (
    id SERIAL PRIMARY KEY,
    username TEXT NOT NULL UNIQUE,
    password_hash TEXT NOT NULL,
    created_at TEXT NOT NULL DEFAULT (to_char(now(), 'YYYY-MM-DD HH24:MI:SS')),
    updated_at TEXT NOT NULL DEFAULT (to_char(now(), 'YYYY-MM-DD HH24:MI:SS'))
);
CREATE TABLE IF NOT EXISTS products (
    id SERIAL PRIMARY KEY,
    name TEXT NOT NULL,
    unit_price_paisa INTEGER NOT NULL DEFAULT 0,
    stock INTEGER NOT NULL DEFAULT 0,
    status TEXT NOT NULL DEFAULT 'active',
    created_at TEXT NOT NULL DEFAULT (to_char(now(), 'YYYY-MM-DD HH24:MI:SS')),
    updated_at TEXT NOT NULL DEFAULT (to_char(now(), 'YYYY-MM-DD HH24:MI:SS'))
);
CREATE TABLE IF NOT EXISTS sales (
    id SERIAL PRIMARY KEY,
    product_id INTEGER,
    product_name TEXT NOT NULL,
    unit_price_paisa INTEGER NOT NULL,
    quantity INTEGER NOT NULL,
    total_amount_paisa INTEGER NOT NULL,
    sale_date TEXT NOT NULL,
    sale_time TEXT NOT NULL,
    created_at TEXT NOT NULL DEFAULT (to_char(now(), 'YYYY-MM-DD HH24:MI:SS')),
    FOREIGN KEY (product_id) REFERENCES products(id) ON DELETE SET NULL
);
CREATE TABLE IF NOT EXISTS settings (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS product_columns (
    id SERIAL PRIMARY KEY,
    name TEXT NOT NULL,
    created_at TEXT NOT NULL DEFAULT (to_char(now(), 'YYYY-MM-DD HH24:MI:SS'))
);
CREATE TABLE IF NOT EXISTS product_column_values (
    id SERIAL PRIMARY KEY,
    product_id INTEGER NOT NULL,
    column_id INTEGER NOT NULL,
    value TEXT NOT NULL DEFAULT '',
    FOREIGN KEY (product_id) REFERENCES products(id) ON DELETE CASCADE,
    FOREIGN KEY (column_id) REFERENCES product_columns(id) ON DELETE CASCADE,
    UNIQUE (product_id, column_id)
);
CREATE INDEX IF NOT EXISTS idx_products_name ON products(name);
CREATE INDEX IF NOT EXISTS idx_sales_product_id ON sales(product_id);
CREATE INDEX IF NOT EXISTS idx_sales_date ON sales(sale_date);
"""


class Store:
    """Shared interface over SQLite and Postgres connections."""

    backend = "sqlite"

    def query(self, sql, params=()):  # pragma: no cover - per-backend
        raise NotImplementedError

    def query_one(self, sql, params=()):
        rows = self.query(sql, params)
        return rows[0] if rows else None

    def execute(self, sql, params=()):
        raise NotImplementedError

    def execute_many(self, sql, params_seq):
        raise NotImplementedError


class SqliteStore(Store):
    backend = "sqlite"

    def __init__(self, path=None):
        import sqlite3

        if path is None:
            path = os.environ.get("WEB_DB_PATH", "web/data.db")
        self.path = str(path)
        self._conn = sqlite3.connect(self.path, check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        self._conn.execute("PRAGMA foreign_keys = ON")
        self._lock = threading.Lock()
        self._init_schema()

    def _init_schema(self):
        with self._lock:
            self._conn.executescript(SCHEMA_SQLITE)

    def _translate(self, sql):
        # Postgres-style placeholders + ILIKE -> SQLite equivalents
        return sql.replace("%s", "?").replace("ILIKE", "LIKE")

    def query(self, sql, params=()):
        with self._lock:
            cur = self._conn.execute(self._translate(sql), tuple(params))
            rows = [dict(r) for r in cur.fetchall()]
        return rows

    def execute(self, sql, params=()):
        with self._lock:
            cur = self._conn.execute(self._translate(sql), tuple(params))
            last = None
            try:
                row = cur.fetchone()
                if row is not None:
                    last = row[0]
            except Exception:  # noqa: BLE001 - no result set (UPDATE/DELETE)
                last = None
            self._conn.commit()
        return last

    def execute_many(self, sql, params_seq):
        with self._lock:
            self._conn.executemany(self._translate(sql), [tuple(r) for r in params_seq])
            self._conn.commit()

    def close(self):
        try:
            self._conn.close()
        except Exception:  # noqa: BLE001
            pass


class PostgresStore(Store):
    backend = "postgres"

    def __init__(self, url=None):
        import psycopg2
        from psycopg2.extras import RealDictCursor

        url = url or os.environ.get("DATABASE_URL")
        if not url:
            raise RuntimeError("DATABASE_URL is not set")
        self._conn = psycopg2.connect(url)
        self._conn.autocommit = False
        self._cursor_factory = RealDictCursor
        self._init_schema()

    def _init_schema(self):
        self._conn.cursor().execute(SCHEMA_POSTGRES)
        self._conn.commit()

    def query(self, sql, params=()):
        with self._conn.cursor(cursor_factory=self._cursor_factory) as cur:
            cur.execute(sql, tuple(params))
            return [dict(r) for r in cur.fetchall()]

    def execute(self, sql, params=()):
        with self._conn.cursor() as cur:
            cur.execute(sql, tuple(params))
            last = None
            try:
                row = cur.fetchone()
                if row is not None:
                    last = row[0]
            except Exception:  # noqa: BLE001
                last = None
            self._conn.commit()
        return last

    def execute_many(self, sql, params_seq):
        with self._conn.cursor() as cur:
            cur.executemany(sql, [tuple(r) for r in params_seq])
        self._conn.commit()

    def close(self):
        try:
            self._conn.close()
        except Exception:  # noqa: BLE001
            pass


_local = threading.local()


def get_store() -> Store:
    """Return a request-scoped store (kept alive across the request)."""
    if getattr(_local, "store", None) is None:
        if os.environ.get("DATABASE_URL"):
            _local.store = PostgresStore()
        else:
            _local.store = SqliteStore()
    return _local.store


def reset_store():
    _local.store = None


def close_store():
    store = getattr(_local, "store", None)
    if store is not None:
        store.close()
        _local.store = None
