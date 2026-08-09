"""Flask application: web version of the Sales & Inventory Management System.

Served on Vercel (Postgres) and runnable locally (SQLite) for development.
"""

from __future__ import annotations

import datetime
import functools
import os
import pathlib

from flask import (
    Flask,
    flash,
    redirect,
    render_template,
    request,
    session,
    url_for,
)

from utils import validation
from utils.formatting import format_currency, format_date, format_time
from web import data
from web.store import close_store, get_store

_BASE_DIR = pathlib.Path(__file__).resolve().parent.parent

app = Flask(__name__, static_folder=str(_BASE_DIR / "public" / "static"),
            static_url_path="/static")
app.secret_key = os.environ.get("SECRET_KEY", "dev-secret-change-me")


@app.template_filter("rs")
def rs_filter(paisa):
    return format_currency(paisa or 0)


@app.template_filter("fdate")
def fdate_filter(date_str):
    return format_date(date_str)


@app.template_filter("ftime")
def ftime_filter(time_str):
    return format_time(time_str)


@app.template_filter("inum")
def inum_filter(value):
    return format(int(value or 0), ",d")


@app.teardown_request
def _close_store(_exc):
    close_store()


_admin_checked = False


@app.before_request
def _ensure_admin():
    global _admin_checked
    if not _admin_checked:
        data.ensure_admin(get_store())
        _admin_checked = True


def login_required(view):
    @functools.wraps(view)
    def wrapped(*args, **kwargs):
        if not session.get("username"):
            return redirect(url_for("login"))
        return view(*args, **kwargs)
    return wrapped


def render(template, **ctx):
    ctx.setdefault("active", "")
    ctx.setdefault("username", session.get("username"))
    return render_template(template, **ctx)


# --------------------------------------------------------------------------
# Auth
# --------------------------------------------------------------------------

@app.route("/")
def index():
    if session.get("username"):
        return redirect(url_for("dashboard"))
    return redirect(url_for("login"))


@app.route("/login", methods=["GET", "POST"])
def login():
    if session.get("username"):
        return redirect(url_for("dashboard"))
    error = None
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")
        if data.verify_login(get_store(), username, password):
            session["username"] = username
            return redirect(url_for("dashboard"))
        error = "Invalid username or password."
    return render_template("login.html", error=error)


@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))


@app.route("/api/health")
def health():
    return {"ok": True, "backend": get_store().backend}


# --------------------------------------------------------------------------
# Dashboard
# --------------------------------------------------------------------------

@app.route("/dashboard")
@login_required
def dashboard():
    store = get_store()
    today = datetime.date.today().isoformat()
    month_start = today[:8] + "01"
    today_stats = data.period_stats(store, today, today)
    month_stats = data.period_stats(store, month_start, today)

    products = data.list_products(store, status="all")
    cols = data.visible_columns(store)
    values_map = data.all_product_column_values(store)
    today_map, month_map, all_map = data.product_stats_all(store)

    term = request.args.get("q", "").strip().lower()
    status = request.args.get("status", "all")
    shown = []
    for p in products:
        if status == "active" and p["status"] != "active":
            continue
        if status == "inactive" and p["status"] != "inactive":
            continue
        if term and not (term in p["name"].lower() or term == str(p["id"])):
            continue
        row = {"product": p, "cols": {}, "stats": {
            "today": today_map.get(p["id"], {}),
            "month": month_map.get(p["id"], {}),
            "all_time": all_map.get(p["id"], {}),
        }}
        vals = values_map.get(p["id"], {})
        for c in cols:
            if c["builtin"]:
                row["cols"][c["id"]] = p[c["id"]]
            else:
                row["cols"][c["id"]] = vals.get(c["id"], "")
        shown.append(row)

    start = (datetime.date.today() - datetime.timedelta(days=13)).isoformat()
    chart = {}
    for row in data.sales_in_range(store, start, today):
        chart[row["sale_date"]] = chart.get(row["sale_date"], 0) + row["total_amount_paisa"]
    chart_data = []
    for offset in range(13, -1, -1):
        day = (datetime.date.today() - datetime.timedelta(days=offset)).isoformat()
        chart_data.append((format_date(day), chart.get(day, 0)))

    return render("dashboard.html", active="dashboard",
                  today_stats=today_stats, month_stats=month_stats,
                  products=shown, columns=cols, chart=chart_data,
                  count=len(shown), total=len(products), q=request.args.get("q", ""),
                  status=status)


# --------------------------------------------------------------------------
# Products
# --------------------------------------------------------------------------

@app.route("/products")
@login_required
def products_page():
    store = get_store()
    q = request.args.get("q", "").strip()
    status = request.args.get("status", "all")
    cols = data.visible_columns(store)
    values_map = data.all_product_column_values(store)
    rows = []
    for p in data.list_products(store, search=q, status=status):
        row = {"product": p, "cols": {}}
        vals = values_map.get(p["id"], {})
        for c in cols:
            if c["builtin"]:
                row["cols"][c["id"]] = p[c["id"]]
            else:
                row["cols"][c["id"]] = vals.get(c["id"], "")
        rows.append(row)
    return render("products.html", active="products", rows=rows, columns=cols,
                  q=q, status=status)


@app.route("/products/new", methods=["GET", "POST"])
@login_required
def product_new():
    store = get_store()
    cols = data.list_product_columns(store)
    if request.method == "POST":
        try:
            name = validation.validate_product_name(request.form.get("name", ""))
            price = validation.validate_price(request.form.get("price", ""))
            stock = validation.validate_stock(request.form.get("stock", ""))
            status = "active" if request.form.get("status") == "active" else "inactive"
            pid = data.create_product(store, name, price, stock, status)
            for c in cols:
                data.set_product_column_value(
                    store, pid, c["id"], request.form.get(f"col_{c['id']}", "")
                )
            flash("Product added.", "success")
            return redirect(url_for("products_page"))
        except ValueError as exc:
            flash(str(exc), "error")
    return render("product_form.html", active="products", cols=cols, product=None,
                  form=request.form)


@app.route("/products/<int:pid>/edit", methods=["GET", "POST"])
@login_required
def product_edit(pid):
    store = get_store()
    product = data.get_product(store, pid)
    if product is None:
        flash("Product not found.", "error")
        return redirect(url_for("products_page"))
    cols = data.list_product_columns(store)
    if request.method == "POST":
        try:
            name = validation.validate_product_name(request.form.get("name", ""))
            price = validation.validate_price(request.form.get("price", ""))
            stock = validation.validate_stock(request.form.get("stock", ""))
            status = "active" if request.form.get("status") == "active" else "inactive"
            other = data.get_product_by_name(store, name)
            if other is not None and other["id"] != pid:
                raise ValueError(f"A product named '{name}' already exists.")
            data.update_product(store, pid, name, price, stock, status)
            for c in cols:
                data.set_product_column_value(
                    store, pid, c["id"], request.form.get(f"col_{c['id']}", "")
                )
            flash("Product updated.", "success")
            return redirect(url_for("products_page"))
        except ValueError as exc:
            flash(str(exc), "error")
    values = data.all_product_column_values(store).get(pid, {})
    return render("product_form.html", active="products", cols=cols, product=product,
                  values=values, form=request.form)


@app.route("/products/<int:pid>/toggle", methods=["POST"])
@login_required
def product_toggle(pid):
    store = get_store()
    p = data.get_product(store, pid)
    if p is not None:
        new_status = "inactive" if p["status"] == "active" else "active"
        data.set_product_status(store, pid, new_status)
        flash(f"'{p['name']}' is now {'active' if new_status == 'active' else 'inactive'}.", "success")
    return redirect(request.referrer or url_for("products_page"))


@app.route("/products/<int:pid>/delete", methods=["POST"])
@login_required
def product_delete(pid):
    store = get_store()
    p = data.get_product(store, pid)
    if p is not None:
        data.delete_product(store, pid)
        flash(f"'{p['name']}' deleted.", "success")
    return redirect(request.referrer or url_for("products_page"))


# --------------------------------------------------------------------------
# Product columns
# --------------------------------------------------------------------------

@app.route("/columns")
@login_required
def columns_page():
    store = get_store()
    return render("columns.html", active="columns",
                  builtins=data.list_builtin_columns(store),
                  customs=data.list_product_columns(store))


@app.route("/columns/add", methods=["POST"])
@login_required
def column_add():
    store = get_store()
    name = request.form.get("name", "").strip()
    try:
        if not name:
            raise ValueError("Column name cannot be empty.")
        match = next((c for c in data.BUILTIN_COLUMNS if c["name"].lower() == name.lower()), None)
        if match is not None:
            if match["id"] in data.get_hidden_columns(store):
                data.show_builtin_column(store, match["id"])
                flash(f"Standard column '{match['name']}' is shown again.", "success")
                return redirect(url_for("columns_page"))
            flash(f"A standard column '{match['name']}' already exists.", "error")
            return redirect(url_for("columns_page"))
        data.create_product_column(store, name)
        flash(f"Column '{name}' added.", "success")
    except ValueError as exc:
        flash(str(exc), "error")
    return redirect(url_for("columns_page"))


@app.route("/columns/<path:col_key>/hide", methods=["POST"])
@login_required
def column_hide(col_key):
    store = get_store()
    match = next((c for c in data.BUILTIN_COLUMNS if c["id"] == col_key), None)
    if match is not None:
        data.hide_builtin_column(store, col_key)
        flash(f"Standard column '{match['name']}' is hidden.", "success")
    return redirect(url_for("columns_page"))


@app.route("/columns/<int:col_id>/delete", methods=["POST"])
@login_required
def column_delete(col_id):
    store = get_store()
    col = data.list_product_columns(store)
    name = next((c["name"] for c in col if c["id"] == col_id), None)
    if name is not None:
        data.delete_product_column(store, col_id)
        flash(f"Column '{name}' deleted.", "success")
    return redirect(url_for("columns_page"))


# --------------------------------------------------------------------------
# Sales
# --------------------------------------------------------------------------

@app.route("/sales", methods=["GET", "POST"])
@login_required
def sales_page():
    store = get_store()
    products = data.list_products(store, status="active")
    if request.method == "POST":
        try:
            pid = int(request.form.get("product_id", "0") or 0)
            qty = validation.validate_quantity(request.form.get("quantity", ""))
            p = data.get_product(store, pid)
            if p is None or p["status"] != "active":
                raise ValueError("Please select a product.")
            sale_date = request.form.get("sale_date") or datetime.date.today().isoformat()
            sale_time = request.form.get("sale_time") or datetime.datetime.now().strftime("%H:%M:%S")
            data.add_sale(store, p["id"], p["name"], p["unit_price_paisa"], qty,
                          sale_date, sale_time)
            flash("Sale saved.", "success")
            return redirect(url_for("sales_page"))
        except (ValueError, TypeError) as exc:
            flash(str(exc), "error")
    return render("sales.html", active="sales", products=products,
                  today=datetime.date.today().isoformat())


@app.route("/api/products/search")
@login_required
def api_product_search():
    term = request.args.get("q", "").strip()
    rows = data.list_products(store=get_store(), search=term, status="active")[:20]
    return {
        "items": [
            {
                "id": p["id"],
                "name": p["name"],
                "price": p["unit_price_paisa"],
                "price_text": format_currency(p["unit_price_paisa"]),
                "stock": p["stock"],
            }
            for p in rows
        ]
    }


# --------------------------------------------------------------------------
# Reports
# --------------------------------------------------------------------------

@app.route("/reports/daily", methods=["GET", "POST"])
@login_required
def report_daily():
    store = get_store()
    date_str = request.form.get("date") or request.args.get("date") or datetime.date.today().isoformat()
    rows = data.sales_by_date(store, date_str)
    totals = data.daily_totals(store, date_str)
    return render("reports_daily.html", active="daily", date=date_str,
                  rows=rows, totals=totals, fdate=format_date)


@app.route("/reports/monthly", methods=["GET", "POST"])
@login_required
def report_monthly():
    store = get_store()
    today = datetime.date.today()
    year = int(request.form.get("year") or request.args.get("year") or today.year)
    month = int(request.form.get("month") or request.args.get("month") or today.month)
    product_rows = data.monthly_product_summary(store, year, month)
    daily_rows = data.monthly_daily_summary(store, year, month)
    totals = data.monthly_totals(store, year, month)
    return render("reports_monthly.html", active="monthly", year=year, month=month,
                  product_rows=product_rows, daily_rows=daily_rows, totals=totals)


@app.route("/reports/product", methods=["GET", "POST"])
@login_required
def report_product():
    store = get_store()
    products = data.list_products(store, status="all")
    pid = request.form.get("product_id") or request.args.get("product_id")
    product = stats = history = None
    if pid:
        product = data.get_product(store, int(pid))
        if product is not None:
            stats = data.product_stats(store, int(pid))
            history = data.product_sales_history(store, int(pid))
    return render("reports_product.html", active="product", products=products,
                  product=product, stats=stats, history=history)


@app.route("/top-selling")
@login_required
def top_selling():
    store = get_store()
    days = request.args.get("days", type=int)
    rows = data.top_selling(store, limit=20, days=days)
    return render("rankings.html", active="top", kind="top", rows=rows, days=days)


@app.route("/recent-sales")
@login_required
def recent_sales():
    store = get_store()
    term = request.args.get("q", "").strip()
    if term:
        rows = data.search_sales_by_product(store, term)
    else:
        rows = data.list_sales(store, limit=50)
    return render("rankings.html", active="recent", kind="recent", rows=rows, q=term)


# --------------------------------------------------------------------------
# Settings
# --------------------------------------------------------------------------

@app.route("/settings")
@login_required
def settings_page():
    return render("settings.html", active="settings",
                  username=session["username"],
                  update_url=data.get_setting(get_store(), "update_url", ""),
                  version=os.environ.get("APP_VERSION", "web"))


@app.route("/settings/password", methods=["POST"])
@login_required
def settings_password():
    store = get_store()
    old = request.form.get("old", "")
    new = request.form.get("new", "")
    confirm = request.form.get("confirm", "")
    if not data.verify_login(store, session["username"], old):
        flash("Current password is incorrect.", "error")
    elif len(new) < 6:
        flash("New password must be at least 6 characters.", "error")
    elif new != confirm:
        flash("New password and confirmation do not match.", "error")
    else:
        data.change_password(store, session["username"], new)
        flash("Password changed successfully.", "success")
    return redirect(url_for("settings_page"))


# --------------------------------------------------------------------------
# PWA
# --------------------------------------------------------------------------

_WEB_DIR = os.path.dirname(os.path.abspath(__file__))


@app.route("/manifest.webmanifest")
def manifest():
    path = os.path.join(_WEB_DIR, "manifest.webmanifest")
    with open(path) as fh:
        return app.response_class(fh.read(), mimetype="application/manifest+json")


@app.route("/sw.js")
def service_worker():
    path = os.path.join(_WEB_DIR, "sw.js")
    with open(path) as fh:
        return app.response_class(fh.read(), mimetype="application/javascript")


if __name__ == "__main__":
    app.run(debug=True, port=int(os.environ.get("PORT", "5000")))
