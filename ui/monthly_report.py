"""Monthly Sales Report page: pick year + month, view the per-product summary,
daily summary and totals, and print / export as PDF."""

from __future__ import annotations

import datetime

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
from utils.formatting import format_currency, format_date

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QComboBox,
    QFileDialog,
    QHBoxLayout,
    QLineEdit,
    QTabWidget,
    QTableWidget,
    QVBoxLayout,
    QWidget,
)

_MONTHS = [
    "January", "February", "March", "April", "May", "June",
    "July", "August", "September", "October", "November", "December",
]


class MonthlyReportPage(QWidget):
    def __init__(self, conn, parent=None):
        super().__init__(parent)
        self.conn = conn
        self._products = []
        self._daily = []
        self._totals = {}
        self._month_index = None
        self._year = None

        root = QVBoxLayout(self)
        root.setContentsMargins(20, 20, 20, 20)
        self.page_title = page_header("Monthly Sales Report")
        root.addWidget(self.page_title)
        root.addSpacing(8)

        controls = QHBoxLayout()
        controls.addWidget(label("Year:", size=13, color="#334155"))
        self.year_combo = QComboBox()
        current_year = datetime.date.today().year
        for y in range(current_year, current_year - 15, -1):
            self.year_combo.addItem(str(y))
        self.year_combo.setCurrentText(str(current_year))
        self.year_combo.currentTextChanged.connect(self.reload)
        controls.addWidget(self.year_combo)

        controls.addWidget(label("Month:", size=13, color="#334155"))
        self.month_combo = QComboBox()
        self.month_combo.addItems(_MONTHS)
        self.month_combo.setCurrentIndex(datetime.date.today().month - 1)
        self.month_combo.currentIndexChanged.connect(self.reload)
        controls.addWidget(self.month_combo)

        controls.addWidget(label("Filter:", size=13, color="#334155"))
        self.filter_edit = QLineEdit()
        self.filter_edit.setPlaceholderText("Filter by product...")
        self.filter_edit.textChanged.connect(self._apply_filter)
        controls.addWidget(self.filter_edit, 1)

        controls.addWidget(make_button("Print", "", self.print_report))
        controls.addWidget(make_button("Export PDF", "secondary", self.export_pdf))
        root.addLayout(controls)
        root.addSpacing(8)

        self.tabs = QTabWidget()
        self.product_table = QTableWidget()
        setup_table(
            self.product_table,
            ["Sr No", "Product Name", "Avg Price", "Total Qty", "Total Amount"],
            [60, 320, 120, 110, 140],
        )
        self.daily_table = QTableWidget()
        setup_table(self.daily_table, ["Date", "Quantity Sold", "Total Sales"], [140, 130, 180])
        self.tabs.addTab(self.product_table, "Product Summary")
        self.tabs.addTab(self.daily_table, "Daily Summary")
        root.addWidget(self.tabs, 1)

        self.totals_label = label("", size=15, bold=True, color="#1f2a3d")
        root.addWidget(self.totals_label, alignment=Qt.AlignmentFlag.AlignRight)

        self.reload()

    def play_entrance(self):
        from ui.animations import fade_in, stagger_fade

        stagger_fade([self.page_title, self.tabs], duration=350, step=90, func=fade_in)

    def _params(self):
        year = int(self.year_combo.currentText())
        month = self.month_combo.currentIndex() + 1
        return year, month

    def reload(self):
        year, month = self._params()
        products, daily, totals = report_service.monthly_report(self.conn, year, month)
        self._products = products
        self._daily = daily
        self._totals = totals
        self._month_index = month
        self._year = year

        clear_table(self.daily_table)
        fill_table(self.daily_table, [
            (format_date(d["sale_date"]), d["quantity"], d["total_amount_paisa"]) for d in daily
        ], money_columns=(2,))

        self._apply_filter()
        month_name = _MONTHS[month - 1]
        self.totals_label.setText(
            f"Month: {month_name} {year}      TOTAL QUANTITY: {totals['qty']}"
            f"      TOTAL SALES: {format_currency(totals['total'])}"
        )

    def _apply_filter(self):
        term = self.filter_edit.text().strip().lower()
        rows = [p for p in self._products if term in p["product_name"].lower()] if term else self._products
        clear_table(self.product_table)
        data = []
        for i, r in enumerate(rows, start=1):
            data.append((i, r["product_name"], r["avg_price_paisa"], r["quantity"], r["total_amount_paisa"]))
        fill_table(self.product_table, data, money_columns=(2, 4))

    def _display_products(self):
        return [
            (i, r["product_name"], format_currency(r["avg_price_paisa"]), r["quantity"],
             format_currency(r["total_amount_paisa"]))
            for i, r in enumerate(self._products, start=1)
        ]

    def _display_daily(self):
        return [
            (format_date(d["sale_date"]), d["quantity"], format_currency(d["total_amount_paisa"]))
            for d in self._daily
        ]

    def print_report(self):
        month_name = _MONTHS[self._month_index - 1]
        subtitle = f"{month_name} {self._year}"
        print_table(
            self, "Monthly Sales Report", subtitle,
            ["Sr No", "Product Name", "Avg Price", "Total Qty", "Total Amount"],
            self._display_products(),
            ["", "TOTAL", "", self._totals["qty"], format_currency(self._totals["total"])],
        )

    def export_pdf(self):
        from ui.widgets import export_report_pdf, render_report_html

        year, month = self._params()
        month_name = _MONTHS[month - 1]
        path, _ = QFileDialog.getSaveFileName(
            self, "Export PDF", f"monthly_report_{year}_{month:02d}.pdf", "PDF Files (*.pdf)"
        )
        if not path:
            return
        if not path.endswith(".pdf"):
            path += ".pdf"
        html = render_report_html(
            "Monthly Sales Report", f"{month_name} {year}",
            ["Sr No", "Product Name", "Avg Price", "Total Qty", "Total Amount"],
            self._display_products(),
            ["", "TOTAL", "", self._totals["qty"], format_currency(self._totals["total"])],
        )
        html += render_report_html(
            "Daily Summary", "", ["Date", "Quantity Sold", "Total Sales"],
            self._display_daily(), ["TOTAL", "", format_currency(self._totals["total"])],
        )
        try:
            export_report_pdf(self, html, path)
        except Exception as exc:  # noqa: BLE001
            notify(self, f"PDF export failed: {exc}", "Error", error=True)
            return
        notify(self, f"PDF exported to:\n{path}", "Export Complete")
