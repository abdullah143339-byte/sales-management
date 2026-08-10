"""Data access functions for the web app (users, products, sales, reports).

Ported from the desktop app's ``database/models.py`` to work against the
Store interface (SQLite locally, Postgres on Vercel).
"""

from __future__ import annotations

import datetime

from database.models import hash_password, verify_password
from web.store import Store

DEFAULT_ADMIN = "admin"
DEFAULT_ADMIN_PASSWORD = "admin123"

BUILTIN_COLUMNS = [
    {"id": "name", "name": "Product Name", "builtin": True},
    {"id": "unit_price_paisa", "name": "Unit Price", "builtin": True},
    {"id": "stock", "name": "Stock", "builtin": True},
]
HIDDEN_COLUMNS_KEY = "hidden_columns"

_ts = lambda: datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def ensure_admin(store: Store) -> None:
    if store.query_one("SELECT COUNT(*) AS n FROM users")["n"] == 0:
        store.execute(
            "INSERT INTO users (username, password_hash) VALUES (%s, %s)",
            (DEFAULT_ADMIN, hash_password(DEFAULT_ADMIN_PASSWORD)),
        )


def verify_login(store: Store, username: str, password: str) -> bool:
    row = store.query_one("SELECT password_hash FROM users WHERE username = %s", (username,))
    return bool(row) and verify_password(password, row["password_hash"])


def change_password(store: Store, username: str, new_password: str) -> None:
    store.execute(
        "UPDATE users SET password_hash = %s, updated_at = %s WHERE username = %s",
        (hash_password(new_password), _ts(), username),
    )


def get_setting(store: Store, key: str, default=None):
    row = store.query_one("SELECT value FROM settings WHERE key = %s", (key,))
    return row["value"] if row else default


def set_setting(store: Store, key: str, value) -> None:
    store.execute(
        "INSERT INTO settings (key, value) VALUES (%s, %s)"
        " ON CONFLICT(key) DO UPDATE SET value = excluded.value",
        (key, value),
    )


# --------------------------------------------------------------------------
# Products
# --------------------------------------------------------------------------

def create_product(store: Store, name, unit_price_paisa, stock=0, status="active"):
    existing = store.query_one(
        "SELECT id FROM products WHERE LOWER(name) = LOWER(%s)", (name,)
    )
    if existing is not None:
        raise ValueError(f"A product named '{name}' already exists.")
    now = _ts()
    return store.execute(
        "INSERT INTO products (name, unit_price_paisa, stock, status, created_at, updated_at)"
        " VALUES (%s, %s, %s, %s, %s, %s) RETURNING id",
        (name, unit_price_paisa, stock, status, now, now),
    )


def update_product(store: Store, product_id, name, unit_price_paisa, stock, status):
    store.execute(
        "UPDATE products SET name = %s, unit_price_paisa = %s, stock = %s, status = %s,"
        " updated_at = %s WHERE id = %s",
        (name, unit_price_paisa, stock, status, _ts(), product_id),
    )


def set_product_status(store: Store, product_id, status):
    store.execute("UPDATE products SET status = %s WHERE id = %s", (status, product_id))


def get_product(store: Store, product_id):
    return store.query_one("SELECT * FROM products WHERE id = %s", (product_id,))


def get_product_by_name(store: Store, name):
    return store.query_one(
        "SELECT * FROM products WHERE LOWER(name) = LOWER(%s)", (name,)
    )


def product_has_sales(store: Store, product_id) -> bool:
    row = store.query_one("SELECT COUNT(*) AS n FROM sales WHERE product_id = %s", (product_id,))
    return row["n"] > 0


def delete_product(store: Store, product_id):
    store.execute("DELETE FROM products WHERE id = %s", (product_id,))


def list_products(store: Store, search="", status="all"):
    sql = "SELECT * FROM products WHERE 1=1"
    params: list = []
    if search:
        sql += " AND (name ILIKE %s OR CAST(id AS TEXT) ILIKE %s)"
        params += [f"%{search}%", f"%{search}%"]
    if status == "active":
        sql += " AND status = 'active'"
    elif status == "inactive":
        sql += " AND status = 'inactive'"
    sql += " ORDER BY LOWER(name)"
    return store.query(sql, params)


# --------------------------------------------------------------------------
# Sales
# --------------------------------------------------------------------------

def add_sale(store: Store, product_id, product_name, unit_price_paisa, quantity,
             sale_date, sale_time):
    total = unit_price_paisa * quantity
    if product_id is not None:
        row = store.query_one("SELECT stock FROM products WHERE id = %s", (product_id,))
        if row is None or row["stock"] < quantity:
            raise ValueError(
                f"Insufficient stock. Available: {row['stock'] if row else 0}, requested: {quantity}."
            )
    sale_id = store.execute(
        "INSERT INTO sales (product_id, product_name, unit_price_paisa, quantity,"
        " total_amount_paisa, sale_date, sale_time) VALUES (%s, %s, %s, %s, %s, %s, %s)"
        " RETURNING id",
        (product_id, product_name, unit_price_paisa, quantity, total, sale_date, sale_time),
    )
    if product_id is not None:
        store.execute(
            "UPDATE products SET stock = stock - %s, updated_at = %s WHERE id = %s",
            (quantity, _ts(), product_id),
        )
    return sale_id


def list_sales(store: Store, limit=None):
    sql = "SELECT * FROM sales ORDER BY sale_date DESC, id DESC"
    params: list = []
    if limit:
        sql += " LIMIT %s"
        params.append(int(limit))
    return store.query(sql, params)


def sales_by_date(store: Store, sale_date):
    return store.query(
        """
        SELECT s.product_id, s.product_name,
               MAX(s.unit_price_paisa) AS unit_price_paisa,
               SUM(s.quantity) AS quantity,
               SUM(s.total_amount_paisa) AS total_amount_paisa,
               COUNT(*) AS transactions
        FROM sales s
        WHERE s.sale_date = %s
        GROUP BY s.product_id, s.product_name
        ORDER BY LOWER(s.product_name)
        """,
        (sale_date,),
    )


def sale_dates(store: Store):
    return [r["sale_date"] for r in store.query(
        "SELECT DISTINCT sale_date FROM sales ORDER BY sale_date DESC"
    )]


def latest_sale_date(store: Store):
    row = store.query_one("SELECT MAX(sale_date) AS d FROM sales")
    return row["d"]


def daily_totals(store: Store, sale_date):
    return store.query_one(
        "SELECT COALESCE(SUM(quantity),0) AS qty, COALESCE(SUM(total_amount_paisa),0) AS total,"
        " COUNT(*) AS transactions FROM sales WHERE sale_date = %s",
        (sale_date,),
    )


def sales_in_range(store: Store, start_date, end_date):
    return store.query(
        "SELECT * FROM sales WHERE sale_date BETWEEN %s AND %s ORDER BY sale_date, id",
        (start_date, end_date),
    )


def monthly_product_summary(store: Store, year, month):
    prefix = f"{int(year)}-{int(month):02d}-"
    return store.query(
        """
        SELECT s.product_id, s.product_name,
               CAST(ROUND(AVG(s.unit_price_paisa)) AS INTEGER) AS avg_price_paisa,
               SUM(s.quantity) AS quantity,
               SUM(s.total_amount_paisa) AS total_amount_paisa
        FROM sales s
        WHERE s.sale_date LIKE %s
        GROUP BY s.product_id, s.product_name
        ORDER BY SUM(s.total_amount_paisa) DESC, LOWER(s.product_name)
        """,
        (f"{prefix}%",),
    )


def monthly_daily_summary(store: Store, year, month):
    prefix = f"{int(year)}-{int(month):02d}-"
    return store.query(
        """
        SELECT s.sale_date, SUM(s.quantity) AS quantity,
               SUM(s.total_amount_paisa) AS total_amount_paisa
        FROM sales s
        WHERE s.sale_date LIKE %s
        GROUP BY s.sale_date ORDER BY s.sale_date
        """,
        (f"{prefix}%",),
    )


def monthly_totals(store: Store, year, month):
    prefix = f"{int(year)}-{int(month):02d}-"
    return store.query_one(
        "SELECT COALESCE(SUM(quantity),0) AS qty, COALESCE(SUM(total_amount_paisa),0) AS total,"
        " COUNT(*) AS transactions FROM sales WHERE sale_date LIKE %s",
        (f"{prefix}%",),
    )


def product_sales_history(store: Store, product_id):
    return store.query(
        "SELECT * FROM sales WHERE product_id = %s ORDER BY sale_date DESC, id DESC",
        (product_id,),
    )


def search_sales_by_product(store: Store, product_name):
    return store.query(
        "SELECT * FROM sales WHERE product_name ILIKE %s ORDER BY sale_date DESC, id DESC LIMIT 200",
        (f"%{product_name}%",),
    )


def period_stats(store: Store, start_date, end_date):
    return store.query_one(
        "SELECT COALESCE(SUM(total_amount_paisa),0) AS total,"
        " COALESCE(SUM(quantity),0) AS qty, COUNT(*) AS transactions"
        " FROM sales WHERE sale_date BETWEEN %s AND %s",
        (start_date, end_date),
    )


def top_selling(store: Store, limit=5, days=None):
    where = ""
    params: list = []
    if days:
        start = (datetime.date.today() - datetime.timedelta(days=days)).isoformat()
        where = "WHERE s.sale_date >= %s"
        params.append(start)
    return store.query(
        f"""
        SELECT s.product_name, SUM(s.quantity) AS qty, SUM(s.total_amount_paisa) AS total
        FROM sales s {where}
        GROUP BY s.product_name
        ORDER BY total DESC
        LIMIT %s
        """,
        params + [int(limit)],
    )


def product_stats(store: Store, product_id):
    today = datetime.date.today().isoformat()
    month_prefix = today[:7] + "-"
    stats = {}
    for key, where, params in (
        ("today", "sale_date = %s", (today,)),
        ("month", "sale_date LIKE %s", (f"{month_prefix}%",)),
        ("all_time", "1=1", ()),
    ):
        stats[key] = store.query_one(
            f"SELECT COALESCE(SUM(quantity),0) AS qty, COALESCE(SUM(total_amount_paisa),0) AS total"
            f" FROM sales WHERE product_id = %s AND {where}",
            (product_id,) + params,
        )
    return stats


def product_stats_all(store: Store):
    today = datetime.date.today().isoformat()
    month_prefix = today[:7] + "-"

    def group(sql, params):
        return {r["product_id"]: r for r in store.query(sql, params)}

    today_map = group(
        "SELECT product_id, COALESCE(SUM(quantity),0) AS qty,"
        " COALESCE(SUM(total_amount_paisa),0) AS total"
        " FROM sales WHERE sale_date = %s GROUP BY product_id",
        (today,),
    )
    month_map = group(
        "SELECT product_id, COALESCE(SUM(quantity),0) AS qty,"
        " COALESCE(SUM(total_amount_paisa),0) AS total"
        " FROM sales WHERE sale_date LIKE %s GROUP BY product_id",
        (f"{month_prefix}%",),
    )
    all_map = group(
        "SELECT product_id, COALESCE(SUM(quantity),0) AS qty,"
        " COALESCE(SUM(total_amount_paisa),0) AS total"
        " FROM sales GROUP BY product_id",
        (),
    )
    return today_map, month_map, all_map


# --------------------------------------------------------------------------
# Product columns (custom + hideable built-ins)
# --------------------------------------------------------------------------

def list_product_columns(store: Store):
    return store.query("SELECT * FROM product_columns ORDER BY id")


def create_product_column(store: Store, name):
    name = (name or "").strip()
    if not name:
        raise ValueError("Column name cannot be empty.")
    if len(name) > 60:
        raise ValueError("Column name is too long (max 60 characters).")
    return store.execute(
        "INSERT INTO product_columns (name) VALUES (%s) RETURNING id", (name,)
    )


def delete_product_column(store: Store, column_id):
    store.execute("DELETE FROM product_columns WHERE id = %s", (column_id,))


def get_hidden_columns(store: Store):
    raw = get_setting(store, HIDDEN_COLUMNS_KEY, "")
    return set(raw.split(",")) if raw else set()


def set_hidden_columns(store: Store, keys):
    set_setting(store, HIDDEN_COLUMNS_KEY, ",".join(sorted(keys)))


def hide_builtin_column(store: Store, key):
    hidden = get_hidden_columns(store)
    hidden.add(key)
    set_hidden_columns(store, hidden)


def show_builtin_column(store: Store, key):
    hidden = get_hidden_columns(store)
    hidden.discard(key)
    set_hidden_columns(store, hidden)


def list_builtin_columns(store: Store):
    hidden = get_hidden_columns(store)
    return [dict(c, hidden=c["id"] in hidden) for c in BUILTIN_COLUMNS]


def visible_columns(store: Store):
    cols = [c for c in list_builtin_columns(store) if not c["hidden"]]
    for col in list_product_columns(store):
        cols.append({"id": col["id"], "name": col["name"], "builtin": False})
    return cols


def set_product_column_value(store: Store, product_id, column_id, value):
    store.execute(
        "INSERT INTO product_column_values (product_id, column_id, value) VALUES (%s, %s, %s)"
        " ON CONFLICT(product_id, column_id) DO UPDATE SET value = excluded.value",
        (product_id, column_id, str(value or "").strip()),
    )


def all_product_column_values(store: Store):
    result = {}
    for row in store.query("SELECT product_id, column_id, value FROM product_column_values"):
        result.setdefault(row["product_id"], {})[row["column_id"]] = row["value"]
    return result
