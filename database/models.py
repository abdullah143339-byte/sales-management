"""Data access functions for users, products, sales and settings.

Every function takes a ``sqlite3.Connection`` as its first argument so that
the layer stays easy to test with an in-memory database.
"""

from __future__ import annotations

import datetime
import hashlib
import secrets
import sqlite3

DEFAULT_ADMIN = "admin"
DEFAULT_ADMIN_PASSWORD = "admin123"

_PBKDF2_ITERATIONS = 120_000


# --------------------------------------------------------------------------
# Password hashing
# --------------------------------------------------------------------------

def hash_password(password: str) -> str:
    """Hash a password with PBKDF2-HMAC-SHA256 and a random salt."""
    salt = secrets.token_bytes(16)
    dk = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, _PBKDF2_ITERATIONS)
    return f"pbkdf2_sha256${_PBKDF2_ITERATIONS}${salt.hex()}${dk.hex()}"


def verify_password(password: str, stored: str) -> bool:
    """Verify a plain password against a stored hash (constant-time compare)."""
    try:
        algo, iterations, salt_hex, hash_hex = stored.split("$")
        if algo != "pbkdf2_sha256":
            return False
        dk = hashlib.pbkdf2_hmac(
            "sha256", password.encode("utf-8"), bytes.fromhex(salt_hex), int(iterations)
        )
        return secrets.compare_digest(dk.hex(), hash_hex)
    except (ValueError, TypeError):
        return False


def ensure_admin(conn: sqlite3.Connection) -> None:
    """Create the default admin user on first run (if no users exist)."""
    cur = conn.execute("SELECT COUNT(*) AS n FROM users")
    if cur.fetchone()["n"] == 0:
        with conn:
            conn.execute(
                "INSERT INTO users (username, password_hash) VALUES (?, ?)",
                (DEFAULT_ADMIN, hash_password(DEFAULT_ADMIN_PASSWORD)),
            )


def verify_login(conn: sqlite3.Connection, username: str, password: str) -> bool:
    """Return True when username + password are valid."""
    row = conn.execute("SELECT password_hash FROM users WHERE username = ?", (username,)).fetchone()
    if row is None:
        return False
    return verify_password(password, row["password_hash"])


def change_password(conn: sqlite3.Connection, username: str, new_password: str) -> None:
    """Update a user's password (must be pre-validated)."""
    with conn:
        conn.execute(
            "UPDATE users SET password_hash = ?, updated_at = ? WHERE username = ?",
            (hash_password(new_password), datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"), username),
        )


# --------------------------------------------------------------------------
# Products
# --------------------------------------------------------------------------

def create_product(conn, name, unit_price_paisa, stock=0, status="active"):
    """Insert a new product and return its id. Raises ValueError on duplicate."""
    existing = conn.execute(
        "SELECT id FROM products WHERE name = ? COLLATE NOCASE", (name,)
    ).fetchone()
    if existing is not None:
        raise ValueError(f"A product named '{name}' already exists.")
    now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with conn:
        cur = conn.execute(
            "INSERT INTO products (name, unit_price_paisa, stock, status, created_at, updated_at)"
            " VALUES (?, ?, ?, ?, ?, ?)",
            (name, unit_price_paisa, stock, status, now, now),
        )
    return cur.lastrowid


def update_product(conn, product_id, name, unit_price_paisa, stock, status):
    """Update product details. Returns True when a row changed."""
    now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with conn:
        cur = conn.execute(
            "UPDATE products SET name = ?, unit_price_paisa = ?, stock = ?, status = ?,"
            " updated_at = ? WHERE id = ?",
            (name, unit_price_paisa, stock, status, now, product_id),
        )
    return cur.rowcount > 0


def set_product_status(conn, product_id, status):
    with conn:
        conn.execute("UPDATE products SET status = ? WHERE id = ?", (status, product_id))


def get_product(conn, product_id):
    return conn.execute("SELECT * FROM products WHERE id = ?", (product_id,)).fetchone()


def get_product_by_name(conn, name):
    return conn.execute(
        "SELECT * FROM products WHERE name = ? COLLATE NOCASE", (name,)
    ).fetchone()


def product_has_sales(conn, product_id) -> bool:
    row = conn.execute(
        "SELECT COUNT(*) AS n FROM sales WHERE product_id = ?", (product_id,)
    ).fetchone()
    return row["n"] > 0


def delete_product(conn, product_id):
    """Hard delete a product. Sales rows are kept (product_id becomes NULL)."""
    with conn:
        conn.execute("DELETE FROM products WHERE id = ?", (product_id,))


def list_products(conn, search="", status="all"):
    """List products, filtered by search text and status. Sorted by name."""
    sql = "SELECT * FROM products WHERE 1=1"
    params: list = []
    if search:
        sql += " AND (name LIKE ? OR CAST(id AS TEXT) LIKE ?)"
        params.append(f"%{search}%")
        params.append(f"%{search}%")
    if status == "active":
        sql += " AND status = 'active'"
    elif status == "inactive":
        sql += " AND status = 'inactive'"
    sql += " ORDER BY name COLLATE NOCASE"
    return conn.execute(sql, params).fetchall()


# --------------------------------------------------------------------------
# Sales
# --------------------------------------------------------------------------

def add_sale(conn, product_id, product_name, unit_price_paisa, quantity, sale_date, sale_time):
    """Record one sale. Returns the new sale id. Stock never goes below 0."""
    total = unit_price_paisa * quantity
    with conn:
        if product_id is not None:
            row = conn.execute(
                "SELECT stock FROM products WHERE id = ?", (product_id,)
            ).fetchone()
            if row is None or row["stock"] < quantity:
                raise ValueError(
                    f"Insufficient stock. Available: {row['stock'] if row else 0}, "
                    f"requested: {quantity}."
                )
        cur = conn.execute(
            "INSERT INTO sales (product_id, product_name, unit_price_paisa, quantity,"
            " total_amount_paisa, sale_date, sale_time) VALUES (?, ?, ?, ?, ?, ?, ?)",
            (product_id, product_name, unit_price_paisa, quantity, total, sale_date, sale_time),
        )
        if product_id is not None:
            conn.execute(
                "UPDATE products SET stock = stock - ?, updated_at = ? WHERE id = ?",
                (quantity, datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"), product_id),
            )
    return cur.lastrowid


def adjust_stock(conn, product_id, delta):
    """Manually add/subtract stock. Never allows the stock to go below 0.
    Returns the new stock value."""
    with conn:
        row = conn.execute("SELECT stock FROM products WHERE id = ?", (product_id,)).fetchone()
        if row is None:
            return None
        new_stock = row["stock"] + delta
        if new_stock < 0:
            raise ValueError(
                f"Cannot go below 0. Available stock: {row['stock']}, adjustment: {delta}."
            )
        conn.execute(
            "UPDATE products SET stock = ?, updated_at = ? WHERE id = ?",
            (new_stock, datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"), product_id),
        )
    return new_stock


def list_sales(conn, limit=None):
    sql = "SELECT s.* FROM sales s ORDER BY s.sale_date DESC, s.id DESC"
    if limit:
        sql += f" LIMIT {int(limit)}"
    return conn.execute(sql).fetchall()


def sales_by_date(conn, sale_date):
    """All sales for one date, grouped per product for the daily report."""
    return conn.execute(
        """
        SELECT s.product_id,
               s.product_name,
               MAX(s.unit_price_paisa) AS unit_price_paisa,
               SUM(s.quantity) AS quantity,
               SUM(s.total_amount_paisa) AS total_amount_paisa,
               COUNT(*) AS transactions
        FROM sales s
        WHERE s.sale_date = ?
        GROUP BY s.product_id, s.product_name
        ORDER BY s.product_name COLLATE NOCASE
        """,
        (sale_date,),
    ).fetchall()


def daily_totals(conn, sale_date):
    row = conn.execute(
        "SELECT COALESCE(SUM(quantity),0) AS qty, COALESCE(SUM(total_amount_paisa),0) AS total,"
        " COUNT(*) AS transactions FROM sales WHERE sale_date = ?",
        (sale_date,),
    ).fetchone()
    return row


def sales_in_range(conn, start_date, end_date):
    """Every individual sale row between two dates (inclusive)."""
    return conn.execute(
        "SELECT s.* FROM sales s WHERE s.sale_date BETWEEN ? AND ? ORDER BY s.sale_date, s.id",
        (start_date, end_date),
    ).fetchall()


def monthly_product_summary(conn, year, month):
    """Per-product aggregation for the monthly report."""
    prefix = f"{int(year)}-{int(month):02d}-"
    return conn.execute(
        """
        SELECT s.product_id,
               s.product_name,
               CAST(ROUND(AVG(s.unit_price_paisa)) AS INTEGER) AS avg_price_paisa,
               SUM(s.quantity) AS quantity,
               SUM(s.total_amount_paisa) AS total_amount_paisa
        FROM sales s
        WHERE s.sale_date LIKE ?
        GROUP BY s.product_id, s.product_name
        ORDER BY SUM(s.total_amount_paisa) DESC, s.product_name COLLATE NOCASE
        """,
        (f"{prefix}%",),
    ).fetchall()


def monthly_daily_summary(conn, year, month):
    """Per-date aggregation for the monthly report."""
    prefix = f"{int(year)}-{int(month):02d}-"
    return conn.execute(
        """
        SELECT s.sale_date,
               SUM(s.quantity) AS quantity,
               SUM(s.total_amount_paisa) AS total_amount_paisa
        FROM sales s
        WHERE s.sale_date LIKE ?
        GROUP BY s.sale_date
        ORDER BY s.sale_date
        """,
        (f"{prefix}%",),
    ).fetchall()


def monthly_totals(conn, year, month):
    prefix = f"{int(year)}-{int(month):02d}-"
    row = conn.execute(
        "SELECT COALESCE(SUM(quantity),0) AS qty, COALESCE(SUM(total_amount_paisa),0) AS total,"
        " COUNT(*) AS transactions FROM sales WHERE sale_date LIKE ?",
        (f"{prefix}%",),
    ).fetchone()
    return row


def product_sales_history(conn, product_id):
    """Every sale row for one product (most recent first)."""
    return conn.execute(
        "SELECT * FROM sales WHERE product_id = ? ORDER BY sale_date DESC, id DESC",
        (product_id,),
    ).fetchall()


def product_stats(conn, product_id):
    """Today / this-month / all-time stats for a product."""
    today = datetime.date.today().isoformat()
    month_prefix = today[:7] + "-"
    stats = {}
    for key, where, params in (
        ("today", "sale_date = ?", (today,)),
        ("month", "sale_date LIKE ?", (f"{month_prefix}%",)),
        ("all_time", "1=1", ()),
    ):
        row = conn.execute(
            f"SELECT COALESCE(SUM(quantity),0) AS qty,"
            f" COALESCE(SUM(total_amount_paisa),0) AS total FROM sales WHERE product_id = ? AND {where}",
            (product_id,) + params,
        ).fetchone()
        stats[key] = row
    return stats


def product_stats_by_name(conn, product_name):
    """Same as :func:`product_stats` but keyed by the stored name snapshot."""
    today = datetime.date.today().isoformat()
    month_prefix = today[:7] + "-"
    stats = {}
    for key, where, params in (
        ("today", "sale_date = ?", (today,)),
        ("month", "sale_date LIKE ?", (f"{month_prefix}%",)),
        ("all_time", "1=1", ()),
    ):
        row = conn.execute(
            f"SELECT COALESCE(SUM(quantity),0) AS qty,"
            f" COALESCE(SUM(total_amount_paisa),0) AS total"
            f" FROM sales WHERE product_name = ? AND {where}",
            (product_name,) + params,
        ).fetchone()
        stats[key] = row
    return stats


def product_stats_all(conn):
    """Efficiently compute today / this-month / all-time sales for every product.

    Runs three grouped queries (indexed on product_id) and returns them as
    dicts keyed by product id, so the dashboard can show stats for all
    products without one query per product.
    """
    today = datetime.date.today().isoformat()
    month_prefix = today[:7] + "-"

    def group(sql, params):
        result = {}
        for row in conn.execute(sql, params):
            result[row["product_id"]] = row
        return result

    today_map = group(
        "SELECT product_id, COALESCE(SUM(quantity),0) AS qty,"
        " COALESCE(SUM(total_amount_paisa),0) AS total"
        " FROM sales WHERE sale_date = ? GROUP BY product_id",
        (today,),
    )
    month_map = group(
        "SELECT product_id, COALESCE(SUM(quantity),0) AS qty,"
        " COALESCE(SUM(total_amount_paisa),0) AS total"
        " FROM sales WHERE sale_date LIKE ? GROUP BY product_id",
        (f"{month_prefix}%",),
    )
    all_map = group(
        "SELECT product_id, COALESCE(SUM(quantity),0) AS qty,"
        " COALESCE(SUM(total_amount_paisa),0) AS total"
        " FROM sales GROUP BY product_id",
        (),
    )
    return today_map, month_map, all_map


def search_sales_by_product(conn, product_name):
    """Sales rows matching a product name (fuzzy) — used by global search."""
    return conn.execute(
        "SELECT * FROM sales WHERE product_name LIKE ? ORDER BY sale_date DESC, id DESC LIMIT 200",
        (f"%{product_name}%",),
    ).fetchall()


# --------------------------------------------------------------------------
# Custom product columns (admin-defined fields like colour, size, ...)
# --------------------------------------------------------------------------

# The standard columns every product has. They live on the products table and
# are treated like any other column in the UI, so an admin may hide them.
# "id" is the products-table field; "name" is the display label.
BUILTIN_COLUMNS = [
    {"id": "name", "name": "Product Name", "builtin": True},
    {"id": "unit_price_paisa", "name": "Unit Price", "builtin": True},
    {"id": "stock", "name": "Stock", "builtin": True},
]

HIDDEN_COLUMNS_KEY = "hidden_columns"


def list_product_columns(conn):
    """Return the admin-defined product columns ordered by creation."""
    return conn.execute(
        "SELECT * FROM product_columns ORDER BY id"
    ).fetchall()


def create_product_column(conn, name):
    """Add a new product column. Duplicate names are allowed."""
    name = (name or "").strip()
    if not name:
        raise ValueError("Column name cannot be empty.")
    if len(name) > 60:
        raise ValueError("Column name is too long (max 60 characters).")
    with conn:
        cur = conn.execute("INSERT INTO product_columns (name) VALUES (?)", (name,))
    return cur.lastrowid


def delete_product_column(conn, column_id):
    """Remove a column and all of its stored values."""
    with conn:
        conn.execute("DELETE FROM product_columns WHERE id = ?", (column_id,))


def get_hidden_columns(conn):
    """Return the set of built-in column ids that are hidden."""
    raw = get_setting(conn, HIDDEN_COLUMNS_KEY, "")
    return set(raw.split(",")) if raw else set()


def set_hidden_columns(conn, keys):
    """Persist which built-in columns are hidden."""
    set_setting(conn, HIDDEN_COLUMNS_KEY, ",".join(sorted(keys)))


def hide_builtin_column(conn, key):
    """Hide one built-in column id."""
    hidden = get_hidden_columns(conn)
    hidden.add(key)
    set_hidden_columns(conn, hidden)


def show_builtin_column(conn, key):
    """Show one built-in column id again."""
    hidden = get_hidden_columns(conn)
    hidden.discard(key)
    set_hidden_columns(conn, hidden)


def list_builtin_columns(conn):
    """Return the built-in columns, each flagged with its hidden state."""
    hidden = get_hidden_columns(conn)
    result = []
    for col in BUILTIN_COLUMNS:
        entry = dict(col)
        entry["hidden"] = entry["id"] in hidden
        result.append(entry)
    return result


def visible_columns(conn):
    """Columns shown in product tables: non-hidden built-ins then customs."""
    cols = []
    for col in list_builtin_columns(conn):
        if not col["hidden"]:
            cols.append(col)
    for col in list_product_columns(conn):
        cols.append({"id": col["id"], "name": col["name"], "builtin": False})
    return cols


def set_product_column_value(conn, product_id, column_id, value):
    """Store (or update) the value of a custom column for a product."""
    with conn:
        conn.execute(
            "INSERT INTO product_column_values (product_id, column_id, value) VALUES (?, ?, ?)"
            " ON CONFLICT(product_id, column_id) DO UPDATE SET value = excluded.value",
            (product_id, column_id, str(value or "").strip()),
        )


def get_product_column_values(conn, product_id):
    """Return {column_id: value} for one product."""
    rows = conn.execute(
        "SELECT column_id, value FROM product_column_values WHERE product_id = ?",
        (product_id,),
    ).fetchall()
    return {r["column_id"]: r["value"] for r in rows}


def all_product_column_values(conn):
    """Return {product_id: {column_id: value}} for every product."""
    result = {}
    for row in conn.execute("SELECT product_id, column_id, value FROM product_column_values"):
        result.setdefault(row["product_id"], {})[row["column_id"]] = row["value"]
    return result


# --------------------------------------------------------------------------
# Dashboard helpers
# --------------------------------------------------------------------------

def period_stats(conn, start_date, end_date):
    """Aggregated stats for a date range."""
    row = conn.execute(
        "SELECT COALESCE(SUM(total_amount_paisa),0) AS total,"
        " COALESCE(SUM(quantity),0) AS qty, COUNT(*) AS transactions"
        " FROM sales WHERE sale_date BETWEEN ? AND ?",
        (start_date, end_date),
    ).fetchone()
    return row


def top_selling(conn, limit=5, days=None):
    """Top-selling products by total amount within an optional window."""
    where = ""
    params: list = []
    if days:
        start = (datetime.date.today() - datetime.timedelta(days=days)).isoformat()
        where = "WHERE s.sale_date >= ?"
        params.append(start)
    return conn.execute(
        f"""
        SELECT s.product_name, SUM(s.quantity) AS qty, SUM(s.total_amount_paisa) AS total
        FROM sales s {where}
        GROUP BY s.product_name
        ORDER BY total DESC
        LIMIT ?
        """,
        params + [int(limit)],
    ).fetchall()


def recent_sales(conn, limit=10):
    return list_sales(conn, limit=limit)


# --------------------------------------------------------------------------
# Settings
# --------------------------------------------------------------------------

def get_setting(conn, key, default=None):
    row = conn.execute("SELECT value FROM settings WHERE key = ?", (key,)).fetchone()
    return row["value"] if row else default


def set_setting(conn, key, value):
    with conn:
        conn.execute(
            "INSERT INTO settings (key, value) VALUES (?, ?)"
            " ON CONFLICT(key) DO UPDATE SET value = excluded.value",
            (key, value),
        )
