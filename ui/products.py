"""Products management page: add, edit, delete/deactivate, search, sort,
view per-product sales history, and manage admin-defined custom columns."""

from __future__ import annotations

import datetime

from database import models
from ui.animations import fade_in
from ui.widgets import (
    clear_table,
    confirm,
    fill_table,
    form_row,
    label,
    notify,
    setup_table,
)
from utils import validation

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QHBoxLayout,
    QHeaderView,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QPushButton,
    QTableWidget,
    QVBoxLayout,
    QWidget,
)


class ManageColumnsDialog(QDialog):
    """Add, remove or hide product columns (standard and custom)."""

    def __init__(self, conn, parent=None):
        super().__init__(parent)
        self.conn = conn
        self.setWindowTitle("Manage Product Columns")
        self.setMinimumWidth(380)
        self._animated = False

        lay = QVBoxLayout(self)
        lay.addWidget(label(
            "Add extra fields for your products (e.g. Colour, Size, Category). "
            "Values are filled in when adding/editing a product.",
            size=12, color="#64748b",
        ))
        lay.addWidget(label(
            "Standard columns (Product Name, Unit Price, Stock) can be hidden. "
            "Deleting a hidden standard column shows it again.",
            size=11, color="#94a3b8",
        ))
        lay.addSpacing(8)

        self.list_widget = QListWidget()
        lay.addWidget(self.list_widget)

        add_row = QHBoxLayout()
        self.name_edit = QLineEdit()
        self.name_edit.setPlaceholderText("New column name (e.g. Colour)")
        self.name_edit.returnPressed.connect(self.add_column)
        add_row.addWidget(self.name_edit, 1)
        add_btn = QPushButton("Add Column")
        add_btn.clicked.connect(self.add_column)
        add_row.addWidget(add_btn)
        lay.addLayout(add_row)

        btn_row = QHBoxLayout()
        delete_btn = QPushButton("Delete / Hide Selected")
        delete_btn.setObjectName("danger")
        delete_btn.clicked.connect(self.delete_column)
        btn_row.addWidget(delete_btn)
        btn_row.addStretch()
        close_btn = QPushButton("Close")
        close_btn.setObjectName("secondary")
        close_btn.clicked.connect(self.accept)
        btn_row.addWidget(close_btn)
        lay.addLayout(btn_row)

        self.reload()

    def showEvent(self, event):
        super().showEvent(event)
        if not self._animated:
            self._animated = True
            fade_in(self, 260)

    def reload(self):
        self.list_widget.clear()
        for col in models.list_builtin_columns(self.conn):
            text = f"{col['name']} (Standard)"
            if col["hidden"]:
                text += " — hidden"
            item = QListWidgetItem(text)
            item.setData(Qt.ItemDataRole.UserRole, ("builtin", col["id"]))
            self.list_widget.addItem(item)
        for col in models.list_product_columns(self.conn):
            item = QListWidgetItem(col["name"])
            item.setData(Qt.ItemDataRole.UserRole, ("custom", col["id"]))
            self.list_widget.addItem(item)

    def add_column(self):
        name = self.name_edit.text().strip()
        if not name:
            notify(self, "Column name cannot be empty.", "Error", error=True)
            return

        builtin = next(
            (c for c in models.BUILTIN_COLUMNS if c["name"].lower() == name.lower()),
            None,
        )
        if builtin is not None:
            if builtin["id"] in models.get_hidden_columns(self.conn):
                if confirm(self, f"The standard '{builtin['name']}' column is hidden. Show it again instead?"):
                    models.show_builtin_column(self.conn, builtin["id"])
                    self.name_edit.clear()
                    self.reload()
                return
            if not confirm(
                self,
                f"The standard '{builtin['name']}' column already exists. "
                "Create a separate duplicate column anyway?",
            ):
                return

        existing = next(
            (c for c in models.list_product_columns(self.conn) if c["name"].lower() == name.lower()),
            None,
        )
        if existing is not None:
            if not confirm(
                self,
                f"A column named '{name}' already exists. Create it again anyway?",
            ):
                return

        try:
            models.create_product_column(self.conn, name)
        except ValueError as exc:
            notify(self, str(exc), "Error", error=True)
            return
        self.name_edit.clear()
        self.reload()

    def delete_column(self):
        item = self.list_widget.currentItem()
        if item is None:
            notify(self, "Please select a column first.", "Notice")
            return
        kind, data = item.data(Qt.ItemDataRole.UserRole)
        if kind == "builtin":
            col = next(c for c in models.BUILTIN_COLUMNS if c["id"] == data)
            if not confirm(self, f"Hide the standard column '{col['name']}'? It will be removed from the tables."):
                return
            models.hide_builtin_column(self.conn, data)
            notify(self, f"'{col['name']}' is now hidden.", "Success")
        else:
            col = next(c for c in models.list_product_columns(self.conn) if c["id"] == data)
            if not confirm(self, f"Delete the column '{col['name']}' and its values?", "Confirm Delete"):
                return
            models.delete_product_column(self.conn, data)
            notify(self, f"Column '{col['name']}' deleted.", "Success")
        self.reload()


class ProductDialog(QDialog):
    """Add / edit one product (including any admin-defined columns)."""

    def __init__(self, conn, product=None, parent=None):
        super().__init__(parent)
        self.conn = conn
        self.product = product
        self.setWindowTitle("Edit Product" if product else "Add Product")
        self.setMinimumWidth(440)
        self._animated = False

        lay = QVBoxLayout(self)
        lay.addWidget(label(
            "Edit Product" if product else "Add Product", size=16, bold=True, color="#1f2a3d"
        ))
        lay.addSpacing(8)

        self.name_edit = QLineEdit()
        self.price_edit = QLineEdit()
        self.stock_edit = QLineEdit()
        self.status_combo = QComboBox()
        self.status_combo.addItems(["Active", "Inactive"])

        lay.addLayout(form_row([("Name:", self.name_edit)]))
        lay.addLayout(form_row([("Unit Price (Rs.):", self.price_edit)]))
        lay.addLayout(form_row([("Stock:", self.stock_edit)]))
        lay.addLayout(form_row([("Status:", self.status_combo)]))

        # Admin-defined columns
        self.columns = models.list_product_columns(self.conn)
        self.column_fields = {}
        if self.columns:
            lay.addWidget(label("Extra Details", size=13, bold=True, color="#1f2a3d"))
            saved_values = {}
            if product is not None:
                saved_values = models.get_product_column_values(self.conn, product["id"])
            for col in self.columns:
                field = QLineEdit()
                field.setPlaceholderText(f"Enter {col['name'].lower()}...")
                if col["id"] in saved_values:
                    field.setText(saved_values[col["id"]])
                self.column_fields[col["id"]] = field
                lay.addLayout(form_row([(f"{col['name']}:", field)]))

        self.error = label("", size=12, color="#dc2626")
        self.error.setWordWrap(True)
        lay.addWidget(self.error)

        self.btn_box = QDialogButtonBox()
        save_btn = self.btn_box.addButton("Save", QDialogButtonBox.ButtonRole.AcceptRole)
        self.btn_box.addButton("Cancel", QDialogButtonBox.ButtonRole.RejectRole)
        save_btn.clicked.connect(self.on_save)
        self.btn_box.rejected.connect(self.reject)
        lay.addWidget(self.btn_box)

        if product is not None:
            self.name_edit.setText(product["name"])
            self.price_edit.setText(str(product["unit_price_paisa"] / 100))
            self.stock_edit.setText(str(product["stock"]))
            self.status_combo.setCurrentText("Active" if product["status"] == "active" else "Inactive")
        self.name_edit.setFocus()

    def showEvent(self, event):
        super().showEvent(event)
        if not self._animated:
            self._animated = True
            fade_in(self, 260)

    def on_save(self):
        try:
            name = validation.validate_product_name(self.name_edit.text())
            price_paisa = validation.validate_price(self.price_edit.text())
            stock = validation.validate_stock(self.stock_edit.text())
        except ValueError as exc:
            self.error.setText(str(exc))
            return
        status = "active" if self.status_combo.currentText() == "Active" else "inactive"

        if self.product is None:
            existing = models.get_product_by_name(self.conn, name)
            if existing is not None:
                self.error.setText("A product with this name already exists.")
                return
            product_id = models.create_product(self.conn, name, price_paisa, stock, status)
        else:
            other = models.get_product_by_name(self.conn, name)
            if other is not None and other["id"] != self.product["id"]:
                self.error.setText("A product with this name already exists.")
                return
            product_id = self.product["id"]
            models.update_product(self.conn, product_id, name, price_paisa, stock, status)

        for column_id, field in self.column_fields.items():
            models.set_product_column_value(self.conn, product_id, column_id, field.text())
        self.accept()


class ProductHistoryDialog(QDialog):
    """Shows a product's complete sales history."""

    def __init__(self, conn, product, parent=None):
        super().__init__(parent)
        self.conn = conn
        self.product = product
        self.setWindowTitle("Sales History - " + product["name"])
        self.resize(700, 480)
        self._animated = False

        lay = QVBoxLayout(self)
        from utils.formatting import format_currency

        head = label(
            f"{product['name']}   |   Current Price: {format_currency(product['unit_price_paisa'])}",
            size=14, bold=True, color="#1f2a3d",
        )
        lay.addWidget(head)

        stats = models.product_stats(conn, product["id"])
        info = label(
            f"Today: Qty {stats['today']['qty']}  |  {format_currency(stats['today']['total'])}"
            f"      This Month: Qty {stats['month']['qty']}  |  {format_currency(stats['month']['total'])}"
            f"      All Time: Qty {stats['all_time']['qty']}  |  {format_currency(stats['all_time']['total'])}",
            size=12, color="#64748b",
        )
        info.setWordWrap(True)
        lay.addWidget(info)
        lay.addSpacing(8)

        self.table = QTableWidget()
        setup_table(self.table, ["Date", "Time", "Quantity", "Unit Price", "Total"], [120, 80, 90, 110, 130])
        lay.addWidget(self.table)
        self.reload()

    def showEvent(self, event):
        super().showEvent(event)
        if not self._animated:
            self._animated = True
            fade_in(self, 260)

    def reload(self):
        clear_table(self.table)
        history = models.product_sales_history(self.conn, self.product["id"])
        rows = []
        for h in history:
            d = datetime.date.fromisoformat(h["sale_date"])
            rows.append((
                d.strftime("%d-%m-%Y"), h["sale_time"][:5], h["quantity"],
                h["unit_price_paisa"], h["total_amount_paisa"],
            ))
        fill_table(self.table, rows, money_columns=(3, 4))


class ProductsPage(QWidget):
    def __init__(self, conn, parent=None):
        super().__init__(parent)
        self.conn = conn
        self._products = []
        self._columns = []

        root = QVBoxLayout(self)
        root.setContentsMargins(20, 20, 20, 20)

        header = QHBoxLayout()
        self.page_title = label("Products", size=20, bold=True, color="#1f2a3d")
        header.addWidget(self.page_title)
        header.addStretch()

        self.search_edit = QLineEdit()
        self.search_edit.setPlaceholderText("Search product name or ID...")
        self.search_edit.setFixedWidth(260)
        self.search_edit.textChanged.connect(self.reload)
        header.addWidget(self.search_edit)

        self.filter_combo = QComboBox()
        self.filter_combo.addItems(["All", "Active", "Inactive"])
        self.filter_combo.currentTextChanged.connect(self.reload)
        header.addWidget(self.filter_combo)
        root.addLayout(header)
        root.addSpacing(8)

        buttons = QHBoxLayout()
        self.add_btn = self._make_btn("Add Product", "success", self.add_product)
        self.edit_btn = self._make_btn("Edit", "", self.edit_product)
        self.history_btn = self._make_btn("Sales History", "", self.show_history)
        self.toggle_btn = self._make_btn("Deactivate / Activate", "secondary", self.toggle_status)
        self.delete_btn = self._make_btn("Delete", "danger", self.delete_product)
        self.columns_btn = self._make_btn("Manage Columns", "secondary", self.manage_columns)
        for b in (self.add_btn, self.edit_btn, self.history_btn, self.toggle_btn, self.delete_btn, self.columns_btn):
            buttons.addWidget(b)
        buttons.addStretch()
        root.addLayout(buttons)
        root.addSpacing(8)

        self.table = QTableWidget()
        self._setup_headers()
        self.table.doubleClicked.connect(self.edit_product)
        root.addWidget(self.table, 1)

        self.count_label = label("", size=12, color="#64748b")
        root.addWidget(self.count_label)

        self.reload()

    def _make_btn(self, text, obj_name, handler):
        from ui.widgets import make_button

        return make_button(text, obj_name, handler)

    def play_entrance(self):
        from ui.animations import fade_in, stagger_fade

        stagger_fade([self.page_title, self.table], duration=350, step=90, func=fade_in)

    def _setup_headers(self):
        self._columns = models.visible_columns(self.conn)
        widths = [50]
        for col in self._columns:
            if col["builtin"] and col["id"] == "name":
                widths.append(200)
            elif col["builtin"] and col["id"] == "unit_price_paisa":
                widths.append(100)
            elif col["builtin"] and col["id"] == "stock":
                widths.append(70)
            else:
                widths.append(110)
        headers = ["ID"] + [c["name"] for c in self._columns] + ["Status", "Created", "Updated"]
        widths += [90, 100, 100]
        setup_table(self.table, headers, widths)
        if len(headers) > 1:
            self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)

    def _selected(self):
        row = self.table.currentRow()
        if row < 0:
            return None
        return self._products[row]

    def reload(self):
        search = self.search_edit.text().strip()
        status = {"All": "all", "Active": "active", "Inactive": "inactive"}[self.filter_combo.currentText()]
        self._products = models.list_products(self.conn, search=search, status=status)
        self._setup_headers()
        clear_table(self.table)
        values_map = models.all_product_column_values(self.conn)
        rows = []
        for p in self._products:
            row = [p["id"]]
            for col in self._columns:
                if col["builtin"]:
                    row.append(p[col["id"]])
                else:
                    row.append(values_map.get(p["id"], {}).get(col["id"], ""))
            row += [
                p["status"].capitalize(),
                p["created_at"][:10] if p["created_at"] else "",
                p["updated_at"][:10] if p["updated_at"] else "",
            ]
            rows.append(row)
        money_cols = tuple(
            idx for idx, col in enumerate(self._columns, start=1)
            if col["builtin"] and col["id"] == "unit_price_paisa"
        )
        fill_table(self.table, rows, money_columns=money_cols)
        self.count_label.setText(f"{len(self._products)} product(s)")

    def manage_columns(self):
        dlg = ManageColumnsDialog(self.conn, parent=self)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            self.reload()

    def add_product(self):
        dlg = ProductDialog(self.conn, parent=self)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            notify(self, "Product added successfully.", "Success")
            self.reload()

    def edit_product(self, *args):
        product = self._selected()
        if product is None:
            notify(self, "Please select a product first.", "Notice")
            return
        dlg = ProductDialog(self.conn, product, parent=self)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            notify(self, "Product updated successfully.", "Success")
            self.reload()

    def show_history(self):
        product = self._selected()
        if product is None:
            notify(self, "Please select a product first.", "Notice")
            return
        ProductHistoryDialog(self.conn, product, self).exec()

    def toggle_status(self):
        product = self._selected()
        if product is None:
            notify(self, "Please select a product first.", "Notice")
            return
        new_status = "inactive" if product["status"] == "active" else "active"
        action = "deactivate" if new_status == "inactive" else "activate"
        if not confirm(self, f"{action.title()} '{product['name']}'?", "Confirm"):
            return
        models.set_product_status(self.conn, product["id"], new_status)
        notify(self, f"Product {action}d.", "Success")
        self.reload()

    def delete_product(self):
        product = self._selected()
        if product is None:
            notify(self, "Please select a product first.", "Notice")
            return
        has_sales = models.product_has_sales(self.conn, product["id"])
        if has_sales:
            if not confirm(
                self,
                f"'{product['name']}' has sales history. Deleting it will keep the sales "
                "history but the product will be removed permanently. Continue?",
                "Confirm Delete",
            ):
                return
            models.delete_product(self.conn, product["id"])
            notify(self, "Product deleted. Sales history was kept for reports.", "Success")
        else:
            if not confirm(self, f"Delete '{product['name']}' permanently?", "Confirm Delete"):
                return
            models.delete_product(self.conn, product["id"])
            notify(self, "Product deleted.", "Success")
        self.reload()
