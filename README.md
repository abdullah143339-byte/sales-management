# Sales & Inventory Management System

A complete, offline desktop application that replaces a monthly Excel sales
report. Built with **Python + PySide6 + SQLite**.

## Features

- **Admin login** with secure PBKDF2 password hashing (default: `admin` / `admin123`, change it after first login)
- **Dashboard** — today's and this month's total sales, quantity sold and transactions, plus a searchable list of all products with their today / month / all-time sales and a 14-day daily sales chart
- **Products** — add / edit / delete / deactivate, search, update price, view sales history (history is never deleted)
- **Custom Columns** — the admin can add extra product fields (e.g. Colour, Size, Category) from the Products page; they appear in the product form and in every product table
- **Add Sale** — search a product, see its live price, enter quantity, auto-calculated total (Unit Price × Quantity), price is snapshotted so old sales keep their original price
- **Strict Stock Control** — stock decreases with every sale; once it reaches 0, no further sales are allowed until the admin adds more stock
- **Top Selling** — a standalone page ranking all products by total sales amount
- **Recent Sales** — a standalone page listing the latest sales with a live product filter
- **Global Search** — instant product search by name or ID with today / month / all-time sales stats
- **Daily Sales Report** — per-date report with totals, filter, print and PDF export
- **Monthly Sales Report** — per-product summary + daily summary + totals, export to PDF, print
- **Product-wise Report** — current price, today / month / all-time totals and full transaction history
- Full data validation with clear error messages; money stored as integer paisa (no floating-point errors)

## Installation (Windows)

Requirements: **Python 3.9+** installed and on PATH.

```bat
cd sales_management
pip install -r requirements.txt
python main.py
```

All data is stored locally in `data/sales.db`. Nothing needs the internet.

## Default Login

```
Username: admin
Password: admin123
```

Change the password from **Settings → Change Password**.

## Using custom product columns

1. Open **Products → Manage Columns**.
2. Type a column name (e.g. `Colour`) and click **Add Column**.
3. Fill in the values when adding/editing a product — they appear in the
   Products and Dashboard tables.

Delete a column with **Manage Columns → Delete Selected**.

## Strict stock control

Every sale reduces the product's stock. When stock reaches `0`, the app refuses
new sales for that product until the admin adds more stock (Products → Edit →
Stock). The Add Sale screen shows a clear warning when the entered quantity
exceeds the available stock.

## Creating reports

- **Daily Report** — pick a date, then Print or Export PDF as needed.
- **Monthly Report** — pick year + month; two tabs (Product Summary, Daily Summary).
- **Product Report** — pick a product to see its full history.
- **Top Selling / Recent Sales** — dedicated pages from the sidebar.

All report totals are computed from the actual sales records in the database.

## Building a Windows .exe (PyInstaller)

```bat
pip install pyinstaller
pyinstaller --noconfirm --windowed --name "SalesManagement" ^
  --collect-all PySide6 ^
  --add-data "data;data" ^
  main.py
```

The executable will be created in `dist/SalesManagement/SalesManagement.exe`.

Notes:
- Keep the `data` folder next to the .exe (or run the .exe, then it will create `data/sales.db` beside it).

## Running the tests

```bat
python -m pytest tests -q
```

## Project structure

```
sales_management/
├── main.py                 # entry point
├── requirements.txt
├── README.md
├── database/               # connection + schema + data access
├── services/               # sales + report logic
├── ui/                     # PySide6 screens (login, dashboard, ...)
├── utils/                  # validation + currency formatting
├── tests/                  # automated tests
└── data/                   # SQLite database
```
