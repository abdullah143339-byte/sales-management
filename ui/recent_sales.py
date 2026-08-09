"""Recent Sales page: the latest sales in the system with live product filtering."""

from __future__ import annotations

import datetime

from database import models
from ui.widgets import clear_table, fill_table, label, setup_table
from utils.formatting import format_currency

from PySide6.QtWidgets import QHBoxLayout, QLineEdit, QTableWidget, QVBoxLayout, QWidget


class RecentSalesPage(QWidget):
    def __init__(self, conn, parent=None):
        super().__init__(parent)
        self.conn = conn
        self._sales = []

        root = QVBoxLayout(self)
        root.setContentsMargins(20, 20, 20, 20)
        root.setSpacing(10)

        title = label("Recent Sales", size=20, bold=True, color="#1f2a3d")
        root.addWidget(title)
        self.page_title = title
        subtitle = label("The latest sales recorded in the system (most recent first).",
                         size=12, color="#64748b")
        root.addWidget(subtitle)
        root.addSpacing(6)

        filter_row = QHBoxLayout()
        filter_row.addWidget(label("Filter:", size=13, color="#334155"))
        self.filter_edit = QLineEdit()
        self.filter_edit.setPlaceholderText("Type a product name to filter...")
        self.filter_edit.setFixedWidth(300)
        self.filter_edit.textChanged.connect(self._apply_filter)
        filter_row.addWidget(self.filter_edit)
        filter_row.addStretch()
        self.count_label = label("", size=12, color="#64748b")
        filter_row.addWidget(self.count_label)
        root.addLayout(filter_row)

        self.table = QTableWidget()
        setup_table(self.table, ["Date", "Time", "Product", "Quantity", "Unit Price", "Total"],
                    [110, 70, 320, 90, 120, 140])
        root.addWidget(self.table, 1)

    def refresh(self):
        self._sales = models.recent_sales(self.conn, limit=200)
        self._apply_filter()

    def _apply_filter(self):
        term = self.filter_edit.text().strip().lower()
        rows = [s for s in self._sales if not term or term in s["product_name"].lower()]
        clear_table(self.table)
        data = []
        for s in rows:
            d = datetime.date.fromisoformat(s["sale_date"])
            data.append((d.strftime("%d-%m-%Y"), s["sale_time"][:5], s["product_name"],
                         s["quantity"], s["unit_price_paisa"], s["total_amount_paisa"]))
        fill_table(self.table, data, money_columns=(4, 5))
        self.count_label.setText(f"{len(rows)} sale(s)")

    def play_entrance(self):
        from ui.animations import fade_in, stagger_fade

        stagger_fade([self.page_title, self.table], duration=350, step=90, func=fade_in)
