"""Dashboard page.

Shows a full searchable list of every product the admin has added (including any
custom columns) with each product's today / month / all-time sales, and a 14-day
daily sales table. Top selling and recent sales have their own pages.
"""

from __future__ import annotations

from datetime import datetime

from services import report_service
from ui.animations import fade_in
from ui.widgets import clear_table, fill_table, label, setup_table
from utils.formatting import format_date

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QHeaderView,
    QLineEdit,
    QTableWidget,
    QVBoxLayout,
    QWidget,
)


def _today_pill():
    return datetime.now().strftime("%A, %d %b %Y")


class DashboardPage(QWidget):
    def __init__(self, conn, parent=None):
        super().__init__(parent)
        self.conn = conn
        self._products = []
        self._columns = []

        root = QVBoxLayout(self)
        root.setContentsMargins(20, 20, 20, 20)
        root.setSpacing(12)

        # ---- Hero banner ------------------------------------------------
        hero = QFrame()
        hero.setObjectName("heroBanner")
        hero_lay = QVBoxLayout(hero)
        hero_lay.setContentsMargins(22, 18, 22, 18)
        hero_inner = QHBoxLayout()
        title_box = QVBoxLayout()
        title_box.addWidget(label("Dashboard", size=22, bold=True, color="#ffffff"))
        title_box.addWidget(label("Overview of all products and sales", size=12, color="#dbe7ff"))
        hero_inner.addLayout(title_box)
        hero_inner.addStretch()
        date_pill = label(_today_pill(), size=11, bold=True, color="#ffffff")
        date_pill.setObjectName("pill")
        date_pill.setAlignment(Qt.AlignmentFlag.AlignCenter)
        hero_inner.addWidget(date_pill)
        hero_lay.addLayout(hero_inner)
        root.addWidget(hero)

        # ---- All products (searchable) ----------------------------------
        products_header = self._section_title("All Products")
        self.product_count = label("", size=12, color="#64748b")
        products_header.addWidget(self.product_count)
        products_header.addStretch()
        self.search_edit = QLineEdit()
        self.search_edit.setPlaceholderText("Search products...  (type a name or ID)")
        self.search_edit.setFixedWidth(280)
        self.search_edit.textChanged.connect(self._apply_filter)
        products_header.addWidget(self.search_edit)
        root.addLayout(products_header)

        self.product_table = QTableWidget()
        self._setup_product_headers()
        root.addWidget(self.product_table, 1)

        # ---- Daily sales chart table -----------------------------------
        root.addLayout(self._section_title("Daily Sales (last 14 days)"))
        self.chart_table = QTableWidget()
        setup_table(self.chart_table, ["Date", "Total Sales"], [150, 220])
        root.addWidget(self.chart_table)

    # ------------------------------------------------------------------

    def _section_title(self, text):
        box = QHBoxLayout()
        box.setSpacing(8)
        accent = QFrame()
        accent.setObjectName("sectionAccent")
        accent.setFixedSize(4, 18)
        box.addWidget(accent)
        box.addWidget(label(text, size=15, bold=True, color="#1f2a3d"))
        return box

    def play_entrance(self):
        fade_in(self.product_table, 550)
        fade_in(self.chart_table, 550)

    def _setup_product_headers(self):
        from database import models

        self._columns = models.visible_columns(self.conn)
        headers = ["ID"]
        widths = [45]
        for col in self._columns:
            if col["builtin"] and col["id"] == "name":
                widths.append(200)
            elif col["builtin"] and col["id"] == "unit_price_paisa":
                widths.append(100)
            elif col["builtin"] and col["id"] == "stock":
                widths.append(70)
            else:
                widths.append(110)
            headers.append(col["name"])
        setup_table(self.product_table, headers, widths)
        if len(headers) > 1:
            self.product_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)

    def refresh(self):
        data = report_service.dashboard_data(self.conn)

        self._products = data["products"]
        self._apply_filter()

        clear_table(self.chart_table)
        fill_table(self.chart_table, [
            (format_date(day), total) for day, total in data["chart"]
        ], money_columns=(1,))

    def _apply_filter(self):
        from database import models

        term = self.search_edit.text().strip().lower()
        rows = [
            p for p in self._products
            if not term or term in p["name"].lower() or term == str(p["id"])
        ]
        self._setup_product_headers()
        values_map = models.all_product_column_values(self.conn)
        clear_table(self.product_table)
        data = []
        for p in rows:
            row = [p["id"]]
            for col in self._columns:
                if col["builtin"]:
                    row.append(p[col["id"]])
                else:
                    row.append(values_map.get(p["id"], {}).get(col["id"], ""))
            data.append(row)
        money_cols = tuple(
            idx for idx, col in enumerate(self._columns, start=1)
            if col["builtin"] and col["id"] == "unit_price_paisa"
        )
        fill_table(self.product_table, data, money_columns=money_cols)
        shown = len(rows)
        total = len(self._products)
        if shown == total:
            self.product_count.setText(f"{total} product(s)")
        else:
            self.product_count.setText(f"{shown} of {total} product(s)")
