"""End-to-end tests for the Flask web app (runs against a temp SQLite DB)."""

from __future__ import annotations

import os
import tempfile
import unittest

import web.app as webapp
from web import data
from web.app import app
from web.store import get_store, reset_store


class WebAppTestCase(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
        self.tmp.close()
        os.environ["WEB_DB_PATH"] = self.tmp.name
        os.environ.pop("DATABASE_URL", None)
        webapp._admin_checked = False
        reset_store()
        app.config["TESTING"] = True
        self.client = app.test_client()

    def tearDown(self):
        reset_store()
        os.unlink(self.tmp.name)

    def login(self, username="admin", password="admin123"):
        return self.client.post(
            "/login",
            data={"username": username, "password": password},
            follow_redirects=True,
        )

    def add_product(self, name="Biscuit", price="50", stock="10"):
        return self.client.post(
            "/products/new",
            data={"name": name, "price": price, "stock": stock, "status": "active"},
            follow_redirects=True,
        )

    def add_sale(self, product_id, quantity=2):
        return self.client.post(
            "/sales",
            data={"product_id": str(product_id), "quantity": str(quantity)},
            follow_redirects=True,
        )

    # ------------------------------------------------------------------ auth

    def test_login_page_loads(self):
        resp = self.client.get("/login")
        self.assertEqual(resp.status_code, 200)
        self.assertIn(b"Sign In", resp.data)

    def test_wrong_password_rejected(self):
        resp = self.client.post(
            "/login", data={"username": "admin", "password": "wrong"},
            follow_redirects=True,
        )
        self.assertIn(b"Invalid username or password", resp.data)

    def test_default_admin_login(self):
        resp = self.login()
        self.assertEqual(resp.status_code, 200)
        self.assertIn(b"Dashboard", resp.data)

    def test_pages_require_login(self):
        for path in ("/dashboard", "/products", "/sales", "/columns",
                     "/reports/daily", "/reports/monthly", "/settings",
                     "/top-selling", "/recent-sales"):
            resp = self.client.get(path)
            self.assertIn(resp.status_code, (301, 302))
            self.assertIn("/login", resp.headers.get("Location", ""))

    def test_logout(self):
        self.login()
        resp = self.client.get("/logout")
        self.assertIn("/login", resp.headers.get("Location", ""))
        resp = self.client.get("/dashboard")
        self.assertIn("/login", resp.headers.get("Location", ""))

    # --------------------------------------------------------------- products

    def test_add_product_and_list(self):
        self.login()
        resp = self.add_product()
        self.assertIn(b"Product added", resp.data)
        resp = self.client.get("/products")
        self.assertIn(b"Biscuit", resp.data)

    def test_duplicate_product_rejected(self):
        self.login()
        self.add_product("Biscuit")
        resp = self.add_product("Biscuit")
        self.assertIn(b"already exists", resp.data)
        self.assertEqual(resp.data.count(b"Biscuit"), 2)

    def test_edit_product(self):
        self.login()
        self.add_product("Biscuit", "50", "10")
        resp = self.client.post(
            "/products/1/edit",
            data={"name": "Biscuit Pack", "price": "60", "stock": "5", "status": "active"},
            follow_redirects=True,
        )
        self.assertIn(b"Product updated", resp.data)
        self.assertIn(b"Biscuit Pack", resp.data)
        self.assertIn(b"Rs. 60", resp.data)

    def test_toggle_and_delete_product(self):
        self.login()
        self.add_product("Biscuit")
        self.client.post("/products/1/toggle", follow_redirects=True)
        self.assertIn(b"inactive", self.client.get("/products").data.lower())
        self.client.post("/products/1/delete", follow_redirects=True)
        self.assertNotIn(b"Biscuit", self.client.get("/products").data)

    def test_builtin_columns_hide_and_show(self):
        self.login()
        self.add_product("Biscuit", "50", "10")
        self.client.post("/columns/name/hide", follow_redirects=True)
        resp = self.client.get("/products")
        self.assertNotIn(b"Product Name", resp.data)
        self.assertIn(b"Biscuit", resp.data)
        self.client.post("/columns/add", data={"name": "Product Name"}, follow_redirects=True)
        self.assertIn(b"Product Name", self.client.get("/products").data)

    def test_custom_column_roundtrip(self):
        self.login()
        self.client.post("/columns/add", data={"name": "Color"}, follow_redirects=True)
        self.add_product("Biscuit", "50", "10")
        self.client.post(
            "/products/1/edit",
            data={"name": "Biscuit", "price": "50", "stock": "10",
                  "status": "active", "col_1": "Red"},
            follow_redirects=True,
        )
        self.assertIn(b"Red", self.client.get("/products").data)

    def test_duplicate_custom_column_allowed(self):
        self.login()
        self.client.post("/columns/add", data={"name": "Color"}, follow_redirects=True)
        resp = self.client.post("/columns/add", data={"name": "Color"}, follow_redirects=True)
        self.assertIn(b"added", resp.data)

    # ------------------------------------------------------------------ sales

    def test_add_sale_reduces_stock(self):
        self.login()
        self.add_product("Biscuit", "50", "10")
        self.add_sale(1, quantity=3)
        store = get_store()
        product = data.get_product(store, 1)
        self.assertEqual(product["stock"], 7)
        self.assertIn(b"Biscuit", self.client.get("/products").data)

    def test_sale_above_stock_rejected(self):
        self.login()
        self.add_product("Biscuit", "50", "2")
        resp = self.add_sale(1, quantity=5)
        self.assertIn(b"Insufficient stock", resp.data)

    def test_recent_sales_shows_sale(self):
        self.login()
        self.add_product("Biscuit", "50", "10")
        self.add_sale(1)
        resp = self.client.get("/recent-sales")
        self.assertIn(b"Biscuit", resp.data)
        self.assertIn(b"Rs. 100", resp.data)

    def test_product_search_api(self):
        self.login()
        self.add_product("Biscuit", "50", "10")
        resp = self.client.get("/api/products/search?q=Bisc")
        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()
        self.assertEqual(len(data["items"]), 1)
        self.assertEqual(data["items"][0]["price"], 5000)

    # ---------------------------------------------------------------- reports

    def test_reports_pages(self):
        self.login()
        self.add_product("Biscuit", "50", "10")
        self.add_sale(1)
        for path in ("/reports/daily", "/reports/monthly",
                     "/reports/product", "/top-selling"):
            resp = self.client.get(path)
            self.assertEqual(resp.status_code, 200)
        resp = self.client.get("/top-selling")
        self.assertIn(b"Biscuit", resp.data)
        self.assertIn(b"Rs. 100", resp.data)

    def test_daily_report_shows_totals(self):
        self.login()
        self.add_product("Biscuit", "50", "10")
        self.add_sale(1, quantity=4)
        resp = self.client.get("/reports/daily")
        self.assertIn(b"Rs. 200", resp.data)
        self.assertIn(b">4<", resp.data)

    # ---------------------------------------------------------------- settings

    def test_change_password(self):
        self.login()
        resp = self.client.post(
            "/settings/password",
            data={"old": "admin123", "new": "newpass123", "confirm": "newpass123"},
            follow_redirects=True,
        )
        self.assertIn(b"Password changed", resp.data)
        self.client.get("/logout")
        resp = self.client.post("/login", data={"username": "admin", "password": "admin123"})
        self.assertIn(b"Invalid username or password", resp.data)
        resp = self.client.post("/login", data={"username": "admin", "password": "newpass123"},
                                follow_redirects=True)
        self.assertIn(b"Dashboard", resp.data)

    def _follow(self, resp):
        return self.client.get(resp.headers["Location"], follow_redirects=True)

    # ------------------------------------------------------------------- misc

    def test_dashboard_shows_products_and_stats(self):
        self.login()
        self.add_product("Biscuit", "50", "10")
        self.add_sale(1, quantity=2)
        resp = self.client.get("/dashboard")
        self.assertIn(b"Biscuit", resp.data)
        self.assertIn(b"Rs. 100", resp.data)

    def test_health_endpoint(self):
        resp = self.client.get("/api/health")
        self.assertEqual(resp.status_code, 200)
        self.assertTrue(resp.get_json()["ok"])

    def test_manifest_and_sw(self):
        self.login()
        self.assertEqual(self.client.get("/manifest.webmanifest").status_code, 200)
        self.assertEqual(self.client.get("/sw.js").status_code, 200)
        self.assertEqual(self.client.get("/static/style.css").status_code, 200)


if __name__ == "__main__":
    unittest.main()
