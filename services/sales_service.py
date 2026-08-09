"""High-level sales operations (save sale, adjust stock, search)."""

from __future__ import annotations

import datetime
import sqlite3

from database import models
from utils import validation


class SaleError(Exception):
    """Raised when a sale cannot be saved."""


def save_sale(conn: sqlite3.Connection, product_id, quantity, sale_date=None, sale_time=None):
    """Validate and save a sale for the given product.

    The unit price is read from the product at the time of the sale and
    snapshotted onto the sales row, so later price changes never affect
    historical amounts.

    Returns the new sale id.
    """
    product = models.get_product(conn, product_id)
    if product is None:
        raise SaleError("Product not found.")
    qty = validation.validate_quantity(quantity)

    now = datetime.datetime.now()
    sale_date = sale_date or now.date().isoformat()
    sale_time = sale_time or now.time().strftime("%H:%M:%S")

    price_paisa = product["unit_price_paisa"]

    if product["stock"] < qty:
        raise SaleError(
            f"Insufficient stock. Available: {product['stock']}, requested: {qty}.\n"
            "No sale is allowed until the stock is updated."
        )

    return models.add_sale(
        conn,
        product_id=product["id"],
        product_name=product["name"],
        unit_price_paisa=price_paisa,
        quantity=qty,
        sale_date=sale_date,
        sale_time=sale_time,
    )


def save_sale_with_price(
    conn, product_id, product_name, unit_price_paisa, quantity, sale_date, sale_time
):
    """Insert a sale row directly (used by Excel imports of historical data)."""
    qty = validation.validate_quantity(quantity)
    return models.add_sale(
        conn,
        product_id=product_id,
        product_name=product_name,
        unit_price_paisa=unit_price_paisa,
        quantity=qty,
        sale_date=sale_date,
        sale_time=sale_time,
    )


def quick_search(conn, term, limit=25):
    """Return matching active products (name or id) for the add-sale box."""
    return models.list_products(conn, search=term, status="active")[:limit]
