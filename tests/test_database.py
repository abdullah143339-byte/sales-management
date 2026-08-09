"""Tests for authentication, password hashing, products and settings."""

import pytest

from database import models


def test_default_admin_exists(conn):
    assert models.verify_login(conn, "admin", "admin123")


def test_wrong_password_rejected(conn):
    assert not models.verify_login(conn, "admin", "wrongpass")
    assert not models.verify_login(conn, "nobody", "admin123")


def test_password_not_stored_plaintext(conn):
    row = conn.execute("SELECT password_hash FROM users WHERE username='admin'").fetchone()
    assert row["password_hash"] != "admin123"
    assert row["password_hash"].startswith("pbkdf2_sha256$")


def test_change_password(conn):
    models.change_password(conn, "admin", "newpass456")
    assert models.verify_login(conn, "admin", "newpass456")
    assert not models.verify_login(conn, "admin", "admin123")
    models.change_password(conn, "admin", "admin123")


def test_add_edit_search_product(conn):
    pid = models.create_product(conn, "Galaxy Silver Plus", 921500, 50)
    row = models.get_product(conn, pid)
    assert row["name"] == "Galaxy Silver Plus"
    assert row["unit_price_paisa"] == 921500
    assert row["stock"] == 50

    models.update_product(conn, pid, "Galaxy Silver Plus 2", 1000000, 5, "active")
    row = models.get_product(conn, pid)
    assert row["name"] == "Galaxy Silver Plus 2"
    assert row["unit_price_paisa"] == 1000000
    assert row["stock"] == 5

    found = models.list_products(conn, search="galaxy")
    assert len(found) == 1
    assert found[0]["id"] == pid
    assert models.get_product_by_name(conn, "Galaxy Silver Plus 2")["id"] == pid


def test_product_name_case_insensitive_search(conn):
    models.create_product(conn, "Samsung A55", 250000, 10)
    assert len(models.list_products(conn, search="SAMSUNG")) == 1
    assert len(models.list_products(conn, search="a55")) == 1


def test_status_filter(conn):
    p1 = models.create_product(conn, "Alpha", 100, 1, "active")
    models.create_product(conn, "Beta", 200, 1, "inactive")
    active = models.list_products(conn, status="active")
    inactive = models.list_products(conn, status="inactive")
    assert {r["name"] for r in active} == {"Alpha"}
    assert {r["name"] for r in inactive} == {"Beta"}

    models.set_product_status(conn, p1, "inactive")
    assert len(models.list_products(conn, status="inactive")) == 2


def test_delete_product_keeps_sales(conn):
    pid = models.create_product(conn, "Kept Product", 500, 3)
    models.add_sale(conn, pid, "Kept Product", 500, 2, "2026-08-01", "10:00:00")
    assert models.product_has_sales(conn, pid)
    models.delete_product(conn, pid)
    assert models.get_product(conn, pid) is None
    rows = models.list_sales(conn)
    assert len(rows) == 1
    assert rows[0]["product_name"] == "Kept Product"
    assert rows[0]["total_amount_paisa"] == 1000


def test_duplicate_product_rejected(conn):
    models.create_product(conn, "Only One", 100, 1)
    with pytest.raises(ValueError):
        models.create_product(conn, "only one", 200, 1)  # case-insensitive duplicate
    with pytest.raises(ValueError):
        models.create_product(conn, "ONLY ONE", 200, 1)
    assert len(models.list_products(conn, status="all")) == 1


def test_unique_index_enforced(conn):
    models.create_product(conn, "Unique Name", 100, 1)
    with pytest.raises(Exception):
        conn.execute(
            "INSERT INTO products (name, unit_price_paisa) VALUES (?, ?)",
            ("UNIQUE NAME", 50),
        )
        conn.commit()


def test_settings_roundtrip(conn):
    assert models.get_setting(conn, "foo") is None
    models.set_setting(conn, "foo", "bar")
    assert models.get_setting(conn, "foo") == "bar"
    models.set_setting(conn, "foo", "baz")
    assert models.get_setting(conn, "foo") == "baz"


def test_custom_columns_crud(conn):
    col1 = models.create_product_column(conn, "Colour")
    col2 = models.create_product_column(conn, "Size")
    names = [c["name"] for c in models.list_product_columns(conn)]
    assert names == ["Colour", "Size"]

    pid = models.create_product(conn, "T-Shirt", 1200, 10)
    models.set_product_column_value(conn, pid, col1, "Black")
    models.set_product_column_value(conn, pid, col2, "M")
    values = models.get_product_column_values(conn, pid)
    assert values[col1] == "Black"
    assert values[col2] == "M"

    models.set_product_column_value(conn, pid, col1, "Red")  # update value
    assert models.get_product_column_values(conn, pid)[col1] == "Red"

    all_values = models.all_product_column_values(conn)
    assert all_values[pid][col2] == "M"

    models.delete_product_column(conn, col1)
    remaining = [c["name"] for c in models.list_product_columns(conn)]
    assert remaining == ["Size"]
    assert col1 not in models.get_product_column_values(conn, pid)


def test_custom_column_duplicates_allowed_blank_rejected(conn):
    models.create_product_column(conn, "Colour")
    models.create_product_column(conn, "colour")  # duplicate names now allowed
    names = [c["name"] for c in models.list_product_columns(conn)]
    assert names == ["Colour", "colour"]
    with pytest.raises(ValueError):
        models.create_product_column(conn, "   ")


def test_builtin_columns_hide_and_show(conn):
    assert [c["name"] for c in models.visible_columns(conn)] == [
        "Product Name", "Unit Price", "Stock",
    ]

    models.hide_builtin_column(conn, "stock")
    assert [c["name"] for c in models.visible_columns(conn)] == [
        "Product Name", "Unit Price",
    ]
    hidden = models.get_hidden_columns(conn)
    assert hidden == {"stock"}

    models.show_builtin_column(conn, "stock")
    assert models.get_hidden_columns(conn) == set()
    assert [c["name"] for c in models.visible_columns(conn)] == [
        "Product Name", "Unit Price", "Stock",
    ]


def test_visible_columns_include_custom_after_builtins(conn):
    col = models.create_product_column(conn, "Colour")
    names = [c["name"] for c in models.visible_columns(conn)]
    assert names == ["Product Name", "Unit Price", "Stock", "Colour"]
    ids = [c["id"] for c in models.visible_columns(conn)]
    assert ids == ["name", "unit_price_paisa", "stock", col]


def test_product_column_values_removed_with_product(conn):
    col = models.create_product_column(conn, "Colour")
    pid = models.create_product(conn, "Cap", 800, 5)
    models.set_product_column_value(conn, pid, col, "Blue")
    models.delete_product(conn, pid)
    assert models.all_product_column_values(conn) == {}


def test_add_sale_cannot_make_stock_negative(conn):
    pid = models.create_product(conn, "Socks", 500, 3)
    with pytest.raises(ValueError):
        models.add_sale(conn, pid, "Socks", 500, 4, "2026-08-01", "10:00:00")
    assert models.get_product(conn, pid)["stock"] == 3
    assert len(models.list_sales(conn)) == 0


def test_adjust_stock_cannot_go_below_zero(conn):
    pid = models.create_product(conn, "Socks", 500, 3)
    assert models.adjust_stock(conn, pid, -3) == 0
    with pytest.raises(ValueError):
        models.adjust_stock(conn, pid, -1)
    assert models.get_product(conn, pid)["stock"] == 0
