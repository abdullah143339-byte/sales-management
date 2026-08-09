"""Top Selling Products page: all products ranked by total sales amount."""

from __future__ import annotations

from database import models
from ui.widgets import clear_table, fill_table, label, setup_table
from utils.formatting import format_currency, format_integer

from PySide6.QtWidgets import QTableWidget, QVBoxLayout, QWidget


class TopSellingPage(QWidget):
    def __init__(self, conn, parent=None):
        super().__init__(parent)
        self.conn = conn

        root = QVBoxLayout(self)
        root.setContentsMargins(20, 20, 20, 20)
        root.setSpacing(10)

        title = label("Top Selling Products", size=20, bold=True, color="#1f2a3d")
        root.addWidget(title)
        self.page_title = title
        subtitle = label("All products ranked by total sales amount (highest first).",
                         size=12, color="#64748b")
        root.addWidget(subtitle)
        root.addSpacing(6)

        self.table = QTableWidget()
        setup_table(self.table, ["Rank", "Product", "Total Sold Qty", "Total Sales"],
                    [70, 320, 150, 180])
        root.addWidget(self.table, 1)

        self.count_label = label("", size=12, color="#64748b")
        root.addWidget(self.count_label)

    def refresh(self):
        clear_table(self.table)
        top = models.top_selling(self.conn, limit=200)
        rows = []
        for i, item in enumerate(top, start=1):
            rows.append((i, item["product_name"], format_integer(item["qty"]), item["total"]))
        fill_table(self.table, rows, money_columns=(3,))
        total_sales = sum(item["total"] for item in top)
        self.count_label.setText(
            f"{len(top)} product(s) sold   |   Grand Total: {format_currency(total_sales)}"
        )

    def play_entrance(self):
        from ui.animations import fade_in, stagger_fade

        stagger_fade([self.page_title, self.table], duration=350, step=90, func=fade_in)
