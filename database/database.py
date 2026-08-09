"""Database connection management and schema creation.

The application stores all data in a local SQLite database file. This module is
responsible for opening the connection, creating the schema and seeding the
default admin user.
"""

from __future__ import annotations

import sqlite3
import sys
from pathlib import Path

from database.models import ensure_admin

SCHEMA = """
PRAGMA foreign_keys = ON;

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
CREATE INDEX IF NOT EXISTS idx_products_status ON products(status);
CREATE UNIQUE INDEX IF NOT EXISTS idx_products_name_unique ON products(name COLLATE NOCASE);
CREATE INDEX IF NOT EXISTS idx_sales_product_id ON sales(product_id);
CREATE INDEX IF NOT EXISTS idx_sales_date ON sales(sale_date);
CREATE INDEX IF NOT EXISTS idx_sales_date_product ON sales(sale_date, product_id);
"""


def _default_data_dir() -> Path:
    """Writable folder for the database.

    - Frozen Windows app: keep ``data`` next to the .exe so users can back it up.
    - Running from source: the project's ``data`` folder (current behaviour).
    - Fallback (e.g. Android or a non-writable install dir): the user's app-data
      location, which is guaranteed writable.
    """
    if getattr(sys, "frozen", False) and sys.platform == "win32":
        base = Path(sys.executable).resolve().parent
    else:
        base = Path(__file__).resolve().parent.parent
    data_dir = base / "data"
    try:
        data_dir.mkdir(parents=True, exist_ok=True)
        probe = data_dir / ".probe"
        probe.write_text("ok")
        probe.unlink()
        return data_dir
    except OSError:
        try:
            from PySide6.QtCore import QStandardPaths

            loc = QStandardPaths.writableLocation(
                QStandardPaths.StandardLocation.AppDataLocation
            )
        except Exception:  # noqa: BLE001
            loc = str(Path.home())
        fallback = Path(loc) / "SalesManagement"
        fallback.mkdir(parents=True, exist_ok=True)
        return fallback


class Database:
    """Owns the SQLite connection used by the whole application."""

    def __init__(self, db_path=None):
        if db_path is None:
            db_path = _default_data_dir() / "sales.db"
        self.db_path = str(db_path)
        self._conn = sqlite3.connect(self.db_path, check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        self._conn.execute("PRAGMA foreign_keys = ON")
        self._conn.execute("PRAGMA journal_mode = WAL")
        self._init_schema()
        ensure_admin(self._conn)

    def _init_schema(self):
        with self._conn:
            self._conn.executescript(SCHEMA)
        self._migrate_product_columns_unique()

    def _migrate_product_columns_unique(self):
        """Rebuild product_columns without the old UNIQUE(name) constraint.

        Older databases created the table with ``name TEXT NOT NULL UNIQUE``,
        which prevented having two columns with the same name. The constraint is
        dropped so admin-defined duplicates are allowed; values are preserved and
        the foreign key from product_column_values stays intact.
        """
        row = self._conn.execute(
            "SELECT sql FROM sqlite_master"
            " WHERE type='table' AND name='product_columns'"
        ).fetchone()
        if row is None or "UNIQUE" not in (row["sql"] or "").upper():
            return
        self._conn.execute("PRAGMA foreign_keys = OFF")
        try:
            with self._conn:
                self._conn.execute("ALTER TABLE product_columns RENAME TO product_columns_old")
                self._conn.executescript("""
                    CREATE TABLE product_columns (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        name TEXT NOT NULL,
                        created_at TEXT NOT NULL DEFAULT (datetime('now', 'localtime'))
                    );
                    INSERT INTO product_columns (id, name, created_at)
                        SELECT id, name, created_at FROM product_columns_old;
                    DROP TABLE product_columns_old;
                """)
        finally:
            self._conn.execute("PRAGMA foreign_keys = ON")

    @property
    def conn(self) -> sqlite3.Connection:
        return self._conn

    def close(self):
        try:
            self._conn.close()
        except sqlite3.Error:
            pass
