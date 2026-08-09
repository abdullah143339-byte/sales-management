"""Main application window with sidebar navigation and stacked pages."""

from __future__ import annotations

from database.database import Database
from ui.daily_report import DailyReportPage
from ui.dashboard import DashboardPage
from ui.monthly_report import MonthlyReportPage
from ui.product_report import ProductReportPage
from ui.products import ProductsPage
from ui.recent_sales import RecentSalesPage
from ui.sales import AddSalePage
from ui.settings import SettingsPage
from ui.theme import QSS
from ui.top_selling import TopSellingPage
from ui.widgets import label

from PySide6.QtWidgets import (
    QHBoxLayout,
    QListWidget,
    QListWidgetItem,
    QMainWindow,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

PAGES = [
    ("Dashboard", "dashboard"),
    ("Products", "products"),
    ("Add Sale", "sales"),
    ("Top Selling", "top_selling"),
    ("Recent Sales", "recent_sales"),
    ("Daily Report", "daily_report"),
    ("Monthly Report", "monthly_report"),
    ("Product Report", "product_report"),
    ("Settings", "settings"),
]


class MainWindow(QMainWindow):
    def __init__(self, database: Database, username: str):
        super().__init__()
        self.database = database
        self.conn = database.conn
        self.username = username

        self.setWindowTitle("Sales & Inventory Management System")
        self.resize(1200, 760)
        self.setStyleSheet(QSS)

        central = QWidget()
        outer = QHBoxLayout(central)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)

        # Sidebar
        self.sidebar_box = QWidget()
        self.sidebar_box.setObjectName("sidebar")
        side_lay = QVBoxLayout(self.sidebar_box)
        side_lay.setContentsMargins(0, 0, 0, 0)
        side_lay.setSpacing(0)
        side_lay.addWidget(label("Sales Management", size=16, bold=True, object_name="sidebarTitle"))
        side_lay.addWidget(label("Inventory & Reports", size=11, object_name="sidebarSubtitle"))

        self.nav = QListWidget()
        self.nav.setObjectName("navList")
        for title, key in PAGES:
            self.nav.addItem(QListWidgetItem(title))
        side_lay.addWidget(self.nav, 1)

        side_lay.addWidget(label(
            f"Logged in: {username}", size=11, color="#8fa3bd", object_name="sidebarSubtitle"
        ))

        outer.addWidget(self.sidebar_box)

        # Content
        self.stack = QStackedWidget()
        self.stack.setObjectName("content")
        outer.addWidget(self.stack, 1)

        self.setCentralWidget(central)
        self._build_pages()

        self.nav.currentRowChanged.connect(self._on_nav)
        self.nav.setCurrentRow(0)

    def showEvent(self, event):
        super().showEvent(event)
        if not hasattr(self, "_faded_in"):
            self._faded_in = True
            from ui.animations import fade_in, rise_in

            fade_in(self.sidebar_box, 500)
            rise_in(self.stack, 500, distance=18)
            if "dashboard" in self.pages:
                self.pages["dashboard"].play_entrance()

    def _build_pages(self):
        self.pages = {}
        while self.stack.count():
            w = self.stack.widget(0)
            self.stack.removeWidget(w)
            w.deleteLater()
        builders = {
            "dashboard": lambda: DashboardPage(self.conn),
            "products": lambda: ProductsPage(self.conn),
            "sales": lambda: AddSalePage(self.conn),
            "top_selling": lambda: TopSellingPage(self.conn),
            "recent_sales": lambda: RecentSalesPage(self.conn),
            "daily_report": lambda: DailyReportPage(self.conn),
            "monthly_report": lambda: MonthlyReportPage(self.conn),
            "product_report": lambda: ProductReportPage(self.conn),
            "settings": lambda: SettingsPage(self.conn, self.username, self.database.db_path),
        }
        for _title, key in PAGES:
            page = builders[key]()
            self.pages[key] = page
            self.stack.addWidget(page)

    def _on_nav(self, row):
        if row < 0:
            return
        key = PAGES[row][1]
        page = self.pages[key]
        self.stack.setCurrentWidget(page)
        if hasattr(page, "refresh"):
            page.refresh()
        elif hasattr(page, "reload"):
            page.reload()
        if hasattr(page, "play_entrance"):
            page.play_entrance()
        from ui.animations import rise_in

        rise_in(page, duration=430, distance=22)
