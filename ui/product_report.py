"""Product-wise report: pick a product to see its current price, today / month
/ all-time totals and the full transaction history."""

from __future__ import annotations

import datetime

from database import models
from services import report_service
from ui.widgets import (
    clear_table,
    fill_table,
    label,
    make_button,
    notify,
    page_header,
    print_table,
    setup_table,
)
from utils.formatting import format_currency, format_date, format_integer

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QComboBox, QFileDialog, QHBoxLayout, QTableWidget, QVBoxLayout, QWidget


class ProductReportPage(QWidget):
    def __init__(self, conn, parent=None):
        super().__init__(parent)
        self.conn = conn
        self._history = []

        root = QVBoxLayout(self)
        root.setContentsMargins(20, 20, 20, 20)
        self.page_title = page_header("Product-wise Report")
        root.addWidget(self.page_title)
        root.addSpacing(8)

        controls = QHBoxLayout()
        controls.addWidget(label("Product:", size=13, color="#334155"))
        self.product_combo = QComboBox()
        self.product_combo.currentIndexChanged.connect(self.reload)
        controls.addWidget(self.product_combo, 1)
        controls.addWidget(make_button("Print", "", self.print_report))
        controls.addWidget(make_button("Export PDF", "secondary", self.export_pdf))
        root.addLayout(controls)
        root.addSpacing(8)

        self.summary_label = label("", size=13, color="#1f2a3d")
        self.summary_label.setWordWrap(True)
        root.addWidget(self.summary_label)
        root.addSpacing(6)

        root.addWidget(label("Transaction History", size=14, bold=True, color="#1f2a3d"))
        self.table = QTableWidget()
        setup_table(self.table, ["Date", "Time", "Quantity", "Unit Price", "Total"], [120, 80, 90, 110, 130])
        root.addWidget(self.table, 1)

        self._load_products()
        self.reload()

    def play_entrance(self):
        from ui.animations import fade_in, stagger_fade

        stagger_fade([self.page_title, self.table], duration=350, step=90, func=fade_in)

    def _load_products(self):
        self.product_combo.clear()
        self._products = models.list_products(self.conn, status="all")
        for p in self._products:
            self.product_combo.addItem(p["name"], p["id"])

    def _current_product(self):
        idx = self.product_combo.currentIndex()
        if idx < 0 or idx >= len(self._products):
            return None
        return self._products[idx]

    def reload(self):
        product = self._current_product()
        clear_table(self.table)
        if product is None:
            self.summary_label.setText("No products available.")
            return
        product, stats, history = report_service.product_report(self.conn, product["id"])
        if product is None:
            self.summary_label.setText("Product not found.")
            return
        self._history = history
        self.summary_label.setText(
            f"<b>{product['name']}</b>  |  Current Price: {format_currency(product['unit_price_paisa'])}<br>"
            f"<b>Today:</b> Qty {format_integer(stats['today']['qty'])}"
            f" &nbsp;|&nbsp; {format_currency(stats['today']['total'])}<br>"
            f"<b>This Month:</b> Qty {format_integer(stats['month']['qty'])}"
            f" &nbsp;|&nbsp; {format_currency(stats['month']['total'])}<br>"
            f"<b>All Time:</b> Qty {format_integer(stats['all_time']['qty'])}"
            f" &nbsp;|&nbsp; {format_currency(stats['all_time']['total'])}"
        )
        rows = []
        for h in history:
            d = datetime.date.fromisoformat(h["sale_date"])
            rows.append((
                d.strftime("%d-%m-%Y"), h["sale_time"][:5], h["quantity"],
                h["unit_price_paisa"], h["total_amount_paisa"],
            ))
        fill_table(self.table, rows, money_columns=(3, 4))

    def _display_rows(self):
        return [
            (format_date(h["sale_date"]), h["sale_time"][:5], h["quantity"],
             format_currency(h["unit_price_paisa"]), format_currency(h["total_amount_paisa"]))
            for h in self._history
        ]

    def print_report(self):
        product = self._current_product()
        if product is None:
            notify(self, "No product selected.", "Notice")
            return
        total_qty = sum(h["quantity"] for h in self._history)
        total_amt = sum(h["total_amount_paisa"] for h in self._history)
        print_table(
            self, "Product Sales History", product["name"],
            ["Date", "Time", "Quantity", "Unit Price", "Total"],
            self._display_rows(),
            ["TOTAL", "", total_qty, "", format_currency(total_amt)],
        )

    def export_pdf(self):
        from ui.widgets import export_report_pdf, render_report_html

        product = self._current_product()
        if product is None:
            notify(self, "No product selected.", "Notice")
            return
        safe_name = "".join(c for c in product["name"] if c.isalnum() or c in " _-")[:40]
        path, _ = QFileDialog.getSaveFileName(
            self, "Export Product History", f"{safe_name}_history.pdf", "PDF Files (*.pdf)"
        )
        if not path:
            return
        if not path.endswith(".pdf"):
            path += ".pdf"
        total_qty = sum(h["quantity"] for h in self._history)
        total_amt = sum(h["total_amount_paisa"] for h in self._history)
        html = render_report_html(
            "Product Sales History", product["name"],
            ["Date", "Time", "Quantity", "Unit Price", "Total"],
            self._display_rows(),
            ["TOTAL", "", total_qty, "", format_currency(total_amt)],
        )
        try:
            export_report_pdf(self, html, path)
        except Exception as exc:  # noqa: BLE001
            notify(self, f"PDF export failed: {exc}", "Error", error=True)
            return
        notify(self, f"PDF exported to:\n{path}", "Export Complete")
