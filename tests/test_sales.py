"""Tests for sales entry: calculation, price snapshot, validation and stock."""

import pytest

from database import models
from services import sales_service


@pytest.fixture()
def product(conn):
    return models.get_product(conn, models.create_product(conn, "Galaxy Silver Plus", 921500, 100))


def test_sale_auto_total(conn, product):
    sale_id = sales_service.save_sale(conn, product["id"], 5)
    row = conn.execute("SELECT * FROM sales WHERE id=?", (sale_id,)).fetchone()
    assert row["quantity"] == 5
    assert row["unit_price_paisa"] == 921500
    assert row["total_amount_paisa"] == 921500 * 5
    assert row["product_id"] == product["id"]
    assert row["sale_date"] == __import__("datetime").date.today().isoformat()


def test_price_change_keeps_old_price_on_old_sales(conn, product):
    sales_service.save_sale(conn, product["id"], 2)
    models.update_product(conn, product["id"], product["name"], 999999, 100, "active")
    sales_service.save_sale(conn, product["id"], 1)
    rows = models.list_sales(conn)  # newest first
    assert len(rows) == 2
    assert rows[0]["unit_price_paisa"] == 999999
    assert rows[0]["total_amount_paisa"] == 999999
    assert rows[1]["unit_price_paisa"] == 921500
    assert rows[1]["total_amount_paisa"] == 921500 * 2


def test_stock_decreases_on_sale(conn, product):
    sales_service.save_sale(conn, product["id"], 3)
    assert models.get_product(conn, product["id"])["stock"] == 97


def test_sale_over_stock_rejected(conn, product):
    with pytest.raises(sales_service.SaleError):
        sales_service.save_sale(conn, product["id"], 500)


def test_sale_blocked_when_stock_reaches_zero(conn, product):
    sales_service.save_sale(conn, product["id"], 100)
    assert models.get_product(conn, product["id"])["stock"] == 0
    # once stock is 0, no more sales are allowed
    with pytest.raises(sales_service.SaleError):
        sales_service.save_sale(conn, product["id"], 1)
    # after new stock arrives, sales resume and stock decreases again
    models.adjust_stock(conn, product["id"], 5)
    sales_service.save_sale(conn, product["id"], 3)
    assert models.get_product(conn, product["id"])["stock"] == 2


def test_invalid_quantity_rejected(conn, product):
    for bad in ("0", "-5", "abc", "", "1.5", "1,000,000,000,000"):
        with pytest.raises((sales_service.SaleError, ValueError)):
            sales_service.save_sale(conn, product["id"], bad)


def test_unknown_product_rejected(conn):
    with pytest.raises(sales_service.SaleError):
        sales_service.save_sale(conn, 999999, 1)


def test_multiple_sales_same_product(conn, product):
    for _ in range(3):
        sales_service.save_sale(conn, product["id"], 10)
    assert len(models.list_sales(conn)) == 3


def test_explicit_date_time_sale(conn, product):
    sales_service.save_sale(conn, product["id"], 4, "2026-08-08", "14:30:00")
    rows = models.sales_by_date(conn, "2026-08-08")
    assert len(rows) == 1
    assert rows[0]["quantity"] == 4
