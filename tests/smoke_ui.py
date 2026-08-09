"""Headless smoke test: build the full UI, walk every page, exit cleanly."""

import os
import sys

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from PySide6.QtWidgets import QApplication

from database.database import Database
from database import models
from ui.login import LoginDialog
from ui.main_window import MainWindow, PAGES

app = QApplication(sys.argv)

db = Database(":memory:")
conn = db.conn

login = LoginDialog(conn)
assert login.username is None

# simulate failed login
login.username_edit.setText("admin")
login.password_edit.setText("wrong")
login.try_login()
assert login.username is None, "wrong password must fail"

# simulate correct login
login.password_edit.setText("admin123")
login.try_login()
assert login.username == "admin", "login must succeed"

window = MainWindow(db, "admin")
window.show()

# visit every page and refresh
for idx, (title, key) in enumerate(PAGES):
    window.nav.setCurrentRow(idx)
    window._on_nav(idx)
    page = window.pages[key]
    if hasattr(page, "refresh"):
        page.refresh()
    print(f"OK page: {title}")

# add a product and a sale through the services used by the UI
pid = models.create_product(conn, "Galaxy Silver Plus", 921500, 100)
from services import sales_service

sales_service.save_sale(conn, pid, 5)
window.pages["dashboard"].refresh()
window.pages["products"].reload()
window.pages["sales"]._do_search("galaxy")

# verify report pages reload
window.pages["daily_report"].reload()
window.pages["monthly_report"].reload()
window.pages["product_report"].reload()

db.close()
print("UI SMOKE TEST PASSED")
