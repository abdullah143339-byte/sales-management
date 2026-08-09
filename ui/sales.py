"""Add Sale page: search a product, enter quantity, auto-calculate total,
and save the sale with a price snapshot."""

from __future__ import annotations

from database import models
from services import sales_service
from ui.widgets import label, notify, page_header
from utils.formatting import format_currency, format_integer

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QGridLayout,
    QHBoxLayout,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QPushButton,
    QVBoxLayout,
    QWidget,
)


class AddSalePage(QWidget):
    def __init__(self, conn, parent=None):
        super().__init__(parent)
        self.conn = conn
        self.current_product = None
        self._matches = []

        root = QVBoxLayout(self)
        root.setContentsMargins(20, 20, 20, 20)
        self.page_title = page_header("Add Sale")
        root.addWidget(self.page_title)
        root.addSpacing(12)

        grid = QGridLayout()
        grid.setSpacing(12)

        # Left: product search
        left = QVBoxLayout()
        left.addWidget(label("Search / Select Product", size=14, bold=True, color="#1f2a3d"))
        self.search_edit = QLineEdit()
        self.search_edit.setPlaceholderText("Type product name or ID...")
        self.search_edit.textChanged.connect(self._do_search)
        left.addWidget(self.search_edit)
        self.result_list = QListWidget()
        self.result_list.itemClicked.connect(self._select_product)
        self.result_list.setMinimumHeight(220)
        left.addWidget(self.result_list)
        self.left_panel = QWidget()
        self.left_panel.setLayout(left)
        grid.addWidget(self.left_panel, 0, 0)

        # Right: sale details
        right = QVBoxLayout()
        right.addWidget(label("Sale Details", size=14, bold=True, color="#1f2a3d"))
        self.detail_label = label("Select a product to begin.", size=12, color="#64748b")
        self.detail_label.setWordWrap(True)
        right.addWidget(self.detail_label)

        price_row = QHBoxLayout()
        price_row.addWidget(label("Unit Price:", size=13, color="#334155"))
        self.price_value = label("Rs. 0", size=15, bold=True, color="#16a34a")
        price_row.addWidget(self.price_value)
        price_row.addStretch()
        right.addLayout(price_row)

        qty_row = QHBoxLayout()
        qty_row.addWidget(label("Quantity:", size=13, color="#334155"))
        self.qty_edit = QLineEdit()
        self.qty_edit.setPlaceholderText("Enter quantity sold")
        self.qty_edit.setFixedWidth(160)
        self.qty_edit.textChanged.connect(self._update_total)
        qty_row.addWidget(self.qty_edit)
        qty_row.addStretch()
        right.addLayout(qty_row)

        self.remaining_label = label("", size=12, color="#334155")
        right.addWidget(self.remaining_label)

        self.stock_warning = label("", size=12, color="#dc2626")
        self.stock_warning.setWordWrap(True)
        self.stock_warning.setVisible(False)
        right.addWidget(self.stock_warning)

        total_row = QHBoxLayout()
        total_row.addWidget(label("Total Amount:", size=14, bold=True, color="#1f2a3d"))
        self.total_value = label("Rs. 0", size=22, bold=True, color="#1f2a3d")
        total_row.addWidget(self.total_value)
        total_row.addStretch()
        right.addLayout(total_row)

        self.save_btn = QPushButton("Save Sale")
        self.save_btn.setObjectName("success")
        self.save_btn.setEnabled(False)
        self.save_btn.clicked.connect(self.save_sale)
        right.addWidget(self.save_btn, alignment=Qt.AlignmentFlag.AlignLeft)
        right.addStretch()
        self.right_panel = QWidget()
        self.right_panel.setLayout(right)
        grid.addWidget(self.right_panel, 0, 1)

        root.addLayout(grid, 1)
        self._do_search("")

    # ------------------------------------------------------------------

    def play_entrance(self):
        from ui.animations import fade_in, stagger_fade

        stagger_fade([self.page_title, self.left_panel, self.right_panel],
                     duration=350, step=90, func=fade_in)

    def _do_search(self, text):
        term = text.strip()
        if term:
            self._matches = sales_service.quick_search(self.conn, term)
        else:
            self._matches = sales_service.quick_search(self.conn, "", limit=15)
        self.result_list.clear()
        for p in self._matches:
            item = QListWidgetItem(f"{p['name']}   |   {format_currency(p['unit_price_paisa'])}")
            item.setData(Qt.ItemDataRole.UserRole, p["id"])
            self.result_list.addItem(item)

    def _select_product(self, item):
        product_id = item.data(Qt.ItemDataRole.UserRole)
        self.current_product = models.get_product(self.conn, product_id)
        p = self.current_product
        self.price_value.setText(format_currency(p["unit_price_paisa"]))

        stats = models.product_stats(self.conn, p["id"])
        self.detail_label.setText(
            f"<b>{p['name']}</b><br>"
            f"Stock available: {format_integer(p['stock'])}<br><br>"
            f"<b>Today</b> &nbsp; Qty: {format_integer(stats['today']['qty'])}"
            f" &nbsp;|&nbsp; Sales: {format_currency(stats['today']['total'])}<br>"
            f"<b>This Month</b> &nbsp; Qty: {format_integer(stats['month']['qty'])}"
            f" &nbsp;|&nbsp; Sales: {format_currency(stats['month']['total'])}<br>"
            f"<b>All Time</b> &nbsp; Qty: {format_integer(stats['all_time']['qty'])}"
            f" &nbsp;|&nbsp; Sales: {format_currency(stats['all_time']['total'])}"
        )
        self._update_total()

    def _update_total(self):
        if self.current_product is None:
            self.total_value.setText("Rs. 0")
            self.remaining_label.setText("")
            self.stock_warning.setVisible(False)
            self.save_btn.setEnabled(False)
            return
        stock = self.current_product["stock"]
        text = self.qty_edit.text().strip()
        if not text.isdigit() or int(text) <= 0:
            self.total_value.setText("Rs. 0")
            self.remaining_label.setText(f"Current stock: {format_integer(stock)}")
            self.stock_warning.setVisible(False)
            self.save_btn.setEnabled(False)
            return
        qty = int(text)
        total = self.current_product["unit_price_paisa"] * qty
        self.total_value.setText(format_currency(total))
        remaining = stock - qty
        if remaining < 0:
            self.remaining_label.setText(
                f"Remaining after this sale: 0  ({format_integer(qty)} requested, "
                f"only {format_integer(stock)} in stock)"
            )
            self.stock_warning.setText(
                f"Insufficient stock! Available: {format_integer(stock)}, requested: {qty}. "
                "No sale is allowed until the stock is updated."
            )
            self.stock_warning.setVisible(True)
            self.save_btn.setEnabled(False)
            return
        self.remaining_label.setText(f"Remaining stock after this sale: {format_integer(remaining)}")
        self.stock_warning.setVisible(False)
        self.save_btn.setEnabled(True)

    def save_sale(self):
        if self.current_product is None:
            notify(self, "Please select a product first.", "Notice")
            return
        try:
            sales_service.save_sale(self.conn, self.current_product["id"], self.qty_edit.text())
        except (sales_service.SaleError, ValueError) as exc:
            notify(self, str(exc), "Error", error=True)
            return
        notify(self, "Sale saved successfully.", "Success")
        p = self.current_product
        self.qty_edit.clear()
        self.stock_warning.setVisible(False)
        self.current_product = models.get_product(self.conn, p["id"])
        self.detail_label.setText(f"<b>{p['name']}</b><br>Sale saved.")
        self._do_search(self.search_edit.text())
