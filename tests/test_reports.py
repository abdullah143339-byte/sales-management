"""Tests for daily, monthly, product reports and dashboard calculations."""

import datetime

import pytest

from database import models
from services import report_service, sales_service


@pytest.fixture()
def populated(conn):
    p1 = models.create_product(conn, "Galaxy Silver Plus", 921500, 1000)
    p2 = models.create_product(conn, "Samsung A55", 250000, 1000)
    sales_service.save_sale(conn, p1, 5, "2026-08-01", "10:00:00")
    sales_service.save_sale(conn, p1, 2, "2026-08-02", "11:00:00")
    sales_service.save_sale(conn, p2, 1, "2026-08-02", "12:00:00")
    return p1, p2


def test_daily_report_totals(conn, populated):
    rows, totals = report_service.daily_report(conn, "2026-08-01")
    assert len(rows) == 1
    assert rows[0]["product_name"] == "Galaxy Silver Plus"
    assert rows[0]["quantity"] == 5
    assert rows[0]["total_amount_paisa"] == 921500 * 5
    assert totals["qty"] == 5
    assert totals["total"] == 921500 * 5
    assert totals["transactions"] == 1

    rows2, totals2 = report_service.daily_report(conn, "2026-08-02")
    assert len(rows2) == 2
    assert totals2["qty"] == 3
    assert totals2["total"] == (921500 * 2) + 250000

    rows3, totals3 = report_service.daily_report(conn, "2026-08-03")
    assert len(rows3) == 0
    assert totals3["qty"] == 0
    assert totals3["total"] == 0


def test_daily_report_groups_same_product(conn):
    pid = models.create_product(conn, "Socks", 500, 100)
    sales_service.save_sale(conn, pid, 2, "2026-08-01", "09:00:00")
    sales_service.save_sale(conn, pid, 3, "2026-08-01", "18:00:00")
    rows, totals = report_service.daily_report(conn, "2026-08-01")
    assert len(rows) == 1
    assert rows[0]["quantity"] == 5
    assert rows[0]["total_amount_paisa"] == 2500
    assert totals["transactions"] == 2


def test_monthly_report(conn, populated):
    products, daily, totals = report_service.monthly_report(conn, 2026, 8)
    assert totals["qty"] == 8
    assert totals["total"] == (921500 * 7) + 250000
    assert totals["transactions"] == 3

    names = {r["product_name"] for r in products}
    assert names == {"Galaxy Silver Plus", "Samsung A55"}
    by_name = {r["product_name"]: r for r in products}
    assert by_name["Galaxy Silver Plus"]["quantity"] == 7
    assert by_name["Samsung A55"]["quantity"] == 1

    assert len(daily) == 2
    assert daily[0]["sale_date"] == "2026-08-01"
    assert daily[1]["sale_date"] == "2026-08-02"


def test_monthly_report_empty_month(conn, populated):
    products, daily, totals = report_service.monthly_report(conn, 2025, 1)
    assert products == []
    assert daily == []
    assert totals["qty"] == 0
    assert totals["total"] == 0


def test_product_report(conn, populated):
    p1, _p2 = populated
    product, stats, history = report_service.product_report(conn, p1)
    assert product["name"] == "Galaxy Silver Plus"
    assert stats["all_time"]["qty"] == 7
    assert stats["all_time"]["total"] == 921500 * 7
    assert stats["month"]["qty"] == 7
    assert stats["today"]["qty"] == 0
    assert len(history) == 2


def test_dashboard_data(conn, populated):
    data = report_service.dashboard_data(conn)
    assert data["today_stats"]["qty"] == 0  # sales are on Aug 1/2, today is real date
    assert data["month_stats"]["total"] >= 0
    assert len(data["chart"]) == 14
    assert "columns" in data
    assert len(data["products"]) == 2


def test_dashboard_contains_all_products(conn, populated):
    data = report_service.dashboard_data(conn)
    names = {p["name"] for p in data["products"]}
    assert names == {"Galaxy Silver Plus", "Samsung A55"}
    by_name = {p["name"]: p for p in data["products"]}
    galaxy = by_name["Galaxy Silver Plus"]
    assert galaxy["unit_price_paisa"] == 921500
    assert galaxy["stock"] == 1000 - 7
    assert data["columns"] == ["Product Name", "Unit Price", "Stock"]
    assert galaxy["column_values"] == ["", "", ""]  # built-in columns carry no custom value


def test_product_stats_all_maps(conn, populated):
    today_map, month_map, all_map = models.product_stats_all(conn)
    assert len(all_map) == 2
    assert all_map[populated[0]]["qty"] == 7
    assert all_map[populated[0]]["total"] == 921500 * 7
    assert len(today_map) == 0  # sales are dated in the past
    assert len(month_map) == 2
