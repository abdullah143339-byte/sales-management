(function () {
  "use strict";

  function flash(el) {
    if (!el) return;
    setTimeout(function () { el.classList.add("fade"); }, 4000);
  }
  document.querySelectorAll(".flash").forEach(flash);

  /* ---------- Mobile drawer menu ---------- */
  var menuBtn = document.getElementById("menu-btn");
  var drawer = document.getElementById("drawer");
  if (menuBtn && drawer) {
    var drawerBackdrop = document.getElementById("drawer-backdrop");
    menuBtn.addEventListener("click", function () { drawer.classList.add("open"); });
    if (drawerBackdrop) {
      drawerBackdrop.addEventListener("click", function () { drawer.classList.remove("open"); });
    }
    drawer.querySelectorAll("a").forEach(function (a) {
      a.addEventListener("click", function () { drawer.classList.remove("open"); });
    });
  }

  function fmtRs(paisa) {
    return "Rs. " + Math.round(paisa / 100).toLocaleString("en-US");
  }
  function fmtInt(n) {
    return Math.round(n || 0).toLocaleString("en-US");
  }

  /* ---------- Dashboard: search products ---------- */
  var dashSearch = document.getElementById("dash-search");
  if (dashSearch) {
    var dashRows = Array.prototype.slice.call(document.querySelectorAll("#dash-products tbody tr[data-name]"));
    var dashCount = document.getElementById("product-count");
    function filterDashboard() {
      var term = dashSearch.value.trim().toLowerCase();
      var shown = 0;
      dashRows.forEach(function (tr) {
        var hit = !term || tr.getAttribute("data-name").indexOf(term) >= 0 || tr.getAttribute("data-id") === term;
        tr.style.display = hit ? "" : "none";
        if (hit) shown++;
      });
      if (dashCount) dashCount.textContent = shown + " product(s)" + (shown !== dashRows.length ? " (filtered)" : "");
    }
    dashSearch.addEventListener("input", filterDashboard);
    filterDashboard();
  }

  /* ---------- Products: row selection + action buttons ---------- */
  var rowSel = document.querySelectorAll(".row-sel");
  var prodActs = document.querySelectorAll(".prod-act");
  var prodPid = document.getElementById("prod-pid");
  var prodForms = document.getElementById("prod-forms");
  var selectedPid = null;

  function currentProductName() {
    if (!selectedPid) return "";
    var tr = document.querySelector('tr[data-pid="' + selectedPid + '"]');
    return tr ? tr.getAttribute("data-name") : "";
  }

  function refreshActions() {
    var has = selectedPid !== null;
    prodActs.forEach(function (btn) {
      btn.disabled = !has;
      if (!has) btn.classList.remove("btn-primary", "btn-danger");
      else if (btn.getAttribute("data-act") === "delete") btn.classList.add("btn-danger");
    });
  }
  rowSel.forEach(function (radio) {
    radio.addEventListener("change", function () {
      selectedPid = radio.value;
      if (prodPid) prodPid.value = selectedPid;
      refreshActions();
      rowSel.forEach(function (r) {
        var tr = r.closest("tr");
        if (tr) tr.classList.toggle("sel", r.checked);
      });
    });
  });
  prodActs.forEach(function (btn) {
    btn.addEventListener("click", function () {
      if (!selectedPid) return;
      var act = btn.getAttribute("data-act");
      if (act === "edit") { window.location.href = "/products/" + selectedPid + "/edit"; return; }
      if (act === "history") { window.location.href = "/products/" + selectedPid + "/history"; return; }
      if (act === "toggle") {
        if (!window.confirm("Toggle status of '" + currentProductName() + "'?")) return;
        prodForms.action = "/products/" + selectedPid + "/toggle";
        prodForms.submit();
        return;
      }
      if (act === "delete") {
        if (!window.confirm("Delete '" + currentProductName() + "'? This cannot be undone.")) return;
        prodForms.action = "/products/" + selectedPid + "/delete";
        prodForms.submit();
      }
    });
  });
  refreshActions();

  /* ---------- Recent sales filter ---------- */
  var recentFilter = document.getElementById("recent-filter");
  if (recentFilter) {
    var recentRows = Array.prototype.slice.call(document.querySelectorAll("#recent-table tbody tr[data-name]"));
    var recentCount = document.getElementById("recent-count");
    function filterRecent() {
      var term = recentFilter.value.trim().toLowerCase();
      var shown = 0;
      recentRows.forEach(function (tr) {
        var hit = !term || tr.getAttribute("data-name").indexOf(term) >= 0;
        tr.style.display = hit ? "" : "none";
        if (hit) shown++;
      });
      if (recentCount) recentCount.textContent = shown + " sale(s)";
    }
    recentFilter.addEventListener("input", filterRecent);
    filterRecent();
  }

  /* ---------- Daily report filter ---------- */
  var dFilter = document.getElementById("d-filter");
  if (dFilter) {
    dFilter.addEventListener("input", function () {
      var term = dFilter.value.trim().toLowerCase();
      document.querySelectorAll("#daily-table tbody tr[data-name]").forEach(function (tr) {
        tr.style.display = !term || tr.getAttribute("data-name").indexOf(term) >= 0 ? "" : "none";
      });
    });
  }

  /* ---------- Monthly report: tabs + filter ---------- */
  var tabs = document.querySelectorAll(".tab");
  tabs.forEach(function (tab) {
    tab.addEventListener("click", function () {
      tabs.forEach(function (t) { t.classList.remove("active"); });
      tab.classList.add("active");
      document.querySelectorAll(".tab-panel").forEach(function (p) { p.style.display = "none"; });
      var panel = document.getElementById("tab-" + tab.getAttribute("data-tab"));
      if (panel) panel.style.display = "";
    });
  });
  var mFilter = document.getElementById("m-filter");
  if (mFilter) {
    mFilter.addEventListener("input", function () {
      var term = mFilter.value.trim().toLowerCase();
      document.querySelectorAll("#monthly-products tbody tr[data-name]").forEach(function (tr) {
        tr.style.display = !term || tr.getAttribute("data-name").indexOf(term) >= 0 ? "" : "none";
      });
    });
  }

  /* ---------- Add Sale: search + select + total ---------- */
  var saleSearch = document.getElementById("sale-search");
  if (saleSearch) {
    var saleResults = document.getElementById("sale-results");
    var saleProductId = document.getElementById("sale-product-id");
    var saleDetail = document.getElementById("sale-detail");
    var salePrice = document.getElementById("sale-price");
    var saleQty = document.getElementById("sale-qty");
    var saleRemaining = document.getElementById("sale-remaining");
    var saleWarning = document.getElementById("sale-warning");
    var saleTotal = document.getElementById("sale-total");
    var saleSave = document.getElementById("sale-save");
    var current = null;
    var debounceTimer = null;

    function renderResults(items) {
      saleResults.innerHTML = "";
      if (!items.length) {
        saleResults.innerHTML = '<div class="sale-hint">No products found.</div>';
        return;
      }
      items.forEach(function (p) {
        var div = document.createElement("div");
        div.className = "sale-item";
        div.innerHTML = "<div class='sale-item-name'>" + escapeHtml(p.name) + "</div>" +
          "<div class='sale-item-price'>" + fmtRs(p.price) + "</div>";
        div.addEventListener("click", function () { selectProduct(p); });
        saleResults.appendChild(div);
      });
    }

    function selectProduct(p) {
      current = p;
      saleProductId.value = p.id;
      var st = p.stats || {};
      var line = function (label, v) { return "<b>" + label + "</b> &nbsp; Qty: " + fmtInt(v.qty) + " &nbsp;|&nbsp; " + fmtRs(v.total); };
      saleDetail.innerHTML =
        "<b>" + escapeHtml(p.name) + "</b><br>" +
        "Stock available: " + fmtInt(p.stock) + "<br><br>" +
        line("Today", st.today || {}) + "<br>" +
        line("This Month", st.month || {}) + "<br>" +
        line("All Time", st.all_time || {});
      salePrice.textContent = fmtRs(p.price);
      saleQty.value = "";
      recompute();
    }

    function recompute() {
      if (!current) {
        saleTotal.textContent = "Rs. 0";
        saleRemaining.textContent = "";
        saleWarning.textContent = "";
        saleWarning.className = "sale-warning";
        saleSave.disabled = true;
        return;
      }
      var text = saleQty.value.trim();
      if (!/^\d+$/.test(text) || parseInt(text, 10) <= 0) {
        saleTotal.textContent = "Rs. 0";
        saleRemaining.textContent = "Current stock: " + fmtInt(current.stock);
        saleWarning.textContent = "";
        saleWarning.className = "sale-warning";
        saleSave.disabled = true;
        return;
      }
      var qty = parseInt(text, 10);
      var total = current.price * qty;
      saleTotal.textContent = fmtRs(total);
      var remaining = current.stock - qty;
      if (remaining < 0) {
        saleRemaining.textContent = "Remaining after this sale: 0  (" + fmtInt(qty) + " requested, only " + fmtInt(current.stock) + " in stock)";
        saleWarning.textContent = "Insufficient stock! Available: " + fmtInt(current.stock) + ", requested: " + qty + ". No sale is allowed until the stock is updated.";
        saleWarning.className = "sale-warning on";
        saleSave.disabled = true;
        return;
      }
      saleRemaining.textContent = "Remaining stock after this sale: " + fmtInt(remaining);
      saleWarning.textContent = "";
      saleWarning.className = "sale-warning";
      saleSave.disabled = false;
    }

    saleQty.addEventListener("input", recompute);

    saleSearch.addEventListener("input", function () {
      var term = saleSearch.value.trim();
      clearTimeout(debounceTimer);
      if (!term) {
        saleResults.innerHTML = '<div class="sale-hint">Start typing to search for a product.</div>';
        return;
      }
      debounceTimer = setTimeout(function () {
        fetch("/api/products/search?q=" + encodeURIComponent(term), { headers: { "X-Requested-With": "fetch" } })
          .then(function (r) { return r.json(); })
          .then(function (d) { renderResults(d.items || []); })
          .catch(function () { saleResults.innerHTML = '<div class="sale-hint">Search failed. Try again.</div>'; });
      }, 220);
    });
  }

  function escapeHtml(s) {
    return String(s == null ? "" : s).replace(/[&<>"']/g, function (c) {
      return { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c];
    });
  }

  /* ---------- Generic confirm ---------- */
  document.querySelectorAll("form[data-confirm]").forEach(function (form) {
    form.addEventListener("submit", function (e) {
      if (!window.confirm(form.getAttribute("data-confirm"))) e.preventDefault();
    });
  });

  /* ---------- Search input URL sync ---------- */
  var searchInput = document.getElementById("q");
  if (searchInput) {
    searchInput.addEventListener("input", function () {
      var url = new URL(window.location.href);
      url.searchParams.set("q", searchInput.value);
      window.history.replaceState({}, "", url);
    });
  }

  /* ---------- Service worker ---------- */
  if ("serviceWorker" in navigator) {
    window.addEventListener("load", function () {
      navigator.serviceWorker.register("/sw.js").catch(function () {});
    });
  }
})();
