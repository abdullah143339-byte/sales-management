"""Daily Sales Report page: pick a date, see the day's sales with totals,
print it or export it as a PDF."""

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

from PySide6.QtCore import QDate, Qt
from PySide6.QtWidgets import QFileDialog, QHBoxLayout, QLineEdit, QDateEdit, QTableWidget, QVBoxLayout, QWidget


class DailyReportPage(QWidget):
    def __init__(self, conn, parent=None):
        super().__init__(parent)
        self.conn = conn
        self._rows = []
        self._totals = {}

        root = QVBoxLayout(self)
        root.setContentsMargins(20, 20, 20, 20)
        self.page_title = page_header("Daily Sales Report")
        root.addWidget(self.page_title)
        root.addSpacing(8)

        controls = QHBoxLayout()
        controls.addWidget(label("Date:", size=13, color="#334155"))
        self.date_edit = QDateEdit()
        self.date_edit.setCalendarPopup(True)
        self.date_edit.setDisplayFormat("dd-MM-yyyy")
        self.date_edit.setDate(QDate.currentDate())
        self.date_edit.dateChanged.connect(self.reload)
        controls.addWidget(self.date_edit)

        controls.addWidget(label("Filter:", size=13, color="#334155"))
        self.filter_edit = QLineEdit()
        self.filter_edit.setPlaceholderText("Filter by product...")
        self.filter_edit.textChanged.connect(self._apply_filter)
        controls.addWidget(self.filter_edit, 1)

        controls.addWidget(make_button("Print", "", self.print_report))
        controls.addWidget(make_button("Export PDF", "secondary", self.export_pdf))
        root.addLayout(controls)
        root.addSpacing(8)

        self.table = QTableWidget()
        setup_table(self.table, ["Product", "Unit Price", "Quantity", "Total Amount"], [320, 120, 100, 140])
        root.addWidget(self.table, 1)

        self.totals_label = label("", size=15, bold=True, color="#1f2a3d")
        root.addWidget(self.totals_label, alignment=Qt.AlignmentFlag.AlignRight)

        self.reload()

    def play_entrance(self):
        from ui.animations import fade_in, stagger_fade

        stagger_fade([self.page_title, self.table], duration=350, step=90, func=fade_in)

    def reload(self):
        date_obj = self.date_edit.date().toPython()
        date_str = date_obj.isoformat()
        rows, totals = report_service.daily_report(self.conn, date_str)
        self._rows = []
        for r in rows:
            self._rows.append({
                "product": r["product_name"],
                "price": r["unit_price_paisa"],
                "qty": r["quantity"],
                "total": r["total_amount_paisa"],
            })
        self._totals = totals
        self._apply_filter()
        self.totals_label.setText(
            f"Total Quantity: {totals['qty']}      Total Sales: {format_currency(totals['total'])}      "
            f"Transactions: {totals['transactions']}"
        )

    def _apply_filter(self):
        term = self.filter_edit.text().strip().lower()
        rows = [r for r in self._rows if term in r["product"].lower()] if term else self._rows
        clear_table(self.table)
        fill_table(self.table, [
            (r["product"], r["price"], r["qty"], r["total"]) for r in rows
        ], money_columns=(1, 3))

    def _date_str(self):
        return self.date_edit.date().toPython().isoformat()

    def _display_rows(self):
        return [
            (r["product"], format_currency(r["price"]), r["qty"], format_currency(r["total"]))
            for r in self._rows
        ]

    def print_report(self):
        print_table(
            self,
            "Daily Sales Report",
            format_date(self._date_str()),
            ["Product", "Unit Price", "Quantity", "Total Amount"],
            self._display_rows(),
            ["TOTAL", "", self._totals["qty"], format_currency(self._totals["total"])],
        )

    def export_pdf(self):
        from ui.widgets import export_report_pdf, render_report_html

        path, _ = QFileDialog.getSaveFileName(
            self, "Export PDF", f"daily_report_{self._date_str()}.pdf", "PDF Files (*.pdf)"
        )
        if not path:
            return
        if not path.endswith(".pdf"):
            path += ".pdf"
        html = render_report_html(
            "Daily Sales Report",
            format_date(self._date_str()),
            ["Product", "Unit Price", "Quantity", "Total Amount"],
            self._display_rows(),
            ["TOTAL", "", self._totals["qty"], format_currency(self._totals["total"])],
        )
        try:
            export_report_pdf(self, html, path)
        except Exception as exc:  # noqa: BLE001
            notify(self, f"PDF export failed: {exc}", "Error", error=True)
            return
        notify(self, f"PDF exported to:\n{path}", "Export Complete")
