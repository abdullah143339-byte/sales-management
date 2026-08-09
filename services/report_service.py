"""Report services: daily, monthly and product-wise calculations.

All totals are computed from the ``sales`` table. Nothing is stored as a
pre-computed total, so reports always reflect the real underlying data.
"""

from __future__ import annotations

import datetime
import sqlite3

from database import models


def daily_report(conn: sqlite3.Connection, date_str):
    """Return (rows, totals) for a single day's report.

    rows: list of sqlite3.Row with product_name, unit_price_paisa, quantity,
          total_amount_paisa, transactions.
    totals: dict(qty, total, transactions).
    """
    rows = models.sales_by_date(conn, date_str)
    totals = models.daily_totals(conn, date_str)
    return rows, totals


def monthly_report(conn: sqlite3.Connection, year: int, month: int):
    """Return (product_rows, daily_rows, totals) for a month."""
    product_rows = models.monthly_product_summary(conn, year, month)
    daily_rows = models.monthly_daily_summary(conn, year, month)
    totals = models.monthly_totals(conn, year, month)
    return product_rows, daily_rows, totals


def product_report(conn: sqlite3.Connection, product_id: int):
    """Return (product, stats, history) for the product-wise report."""
    product = models.get_product(conn, product_id)
    if product is None:
        return None, None, None
    stats = models.product_stats(conn, product_id)
    history = models.product_sales_history(conn, product_id)
    return product, stats, history


def dashboard_data(conn: sqlite3.Connection):
    """Aggregate everything the dashboard shows in one call."""
    today = datetime.date.today()
    month_start = today.replace(day=1).isoformat()
    today_iso = today.isoformat()

    today_stats = models.period_stats(conn, today_iso, today_iso)
    month_stats = models.period_stats(conn, month_start, today_iso)

    # All products with their visible (non-hidden built-in + custom) column values.
    products = models.list_products(conn, status="all")
    col_defs = models.visible_columns(conn)
    all_col_values = models.all_product_column_values(conn)
    product_list = []
    for p in products:
        values = all_col_values.get(p["id"], {})
        product_list.append({
            "id": p["id"],
            "name": p["name"],
            "unit_price_paisa": p["unit_price_paisa"],
            "stock": p["stock"],
            "status": p["status"],
            "column_values": [values.get(c["id"], "") for c in col_defs],
        })

    # Daily sales for the last 14 days -> chart series
    start = (today - datetime.timedelta(days=13)).isoformat()
    chart = models.sales_in_range(conn, start, today_iso)
    daily = []
    daily_map = {}
    for row in chart:
        daily_map[row["sale_date"]] = daily_map.get(row["sale_date"], 0) + row["total_amount_paisa"]
    for offset in range(13, -1, -1):
        day = (today - datetime.timedelta(days=offset)).isoformat()
        daily.append((day, daily_map.get(day, 0)))

    return {
        "today_stats": today_stats,
        "month_stats": month_stats,
        "chart": daily,
        "products": product_list,
        "columns": [c["name"] for c in col_defs],
    }
