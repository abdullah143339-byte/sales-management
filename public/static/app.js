(function () {
  "use strict";

  function flash(el) {
    if (!el) return;
    setTimeout(function () { el.classList.add("fade"); }, 4000);
  }
  document.querySelectorAll(".flash").forEach(flash);

  var searchInput = document.getElementById("q");
  if (searchInput) {
    searchInput.addEventListener("input", function () {
      var url = new URL(window.location.href);
      url.searchParams.set("q", searchInput.value);
      window.history.replaceState({}, "", url);
    });
  }

  var productSearch = document.getElementById("product-search");
  if (productSearch) {
    var productId = document.getElementById("product-id");
    var priceHint = document.getElementById("price-hint");
    var catalog = {};
    document.querySelectorAll("#product-list option").forEach(function (o) {
      catalog[o.value] = { id: o.getAttribute("data-id"), price: o.getAttribute("data-price") };
    });
    productSearch.addEventListener("input", function () {
      var match = catalog[productSearch.value];
      if (match) {
        productId.value = match.id;
        if (priceHint) priceHint.value = match.price;
      } else {
        productId.value = "";
        if (priceHint) priceHint.value = "";
      }
    });
  }

  var confirmForms = document.querySelectorAll("form[data-confirm]");
  confirmForms.forEach(function (form) {
    form.addEventListener("submit", function (e) {
      if (!window.confirm(form.getAttribute("data-confirm"))) {
        e.preventDefault();
      }
    });
  });

  if ("serviceWorker" in navigator) {
    window.addEventListener("load", function () {
      navigator.serviceWorker.register("/sw.js").catch(function () {});
    });
  }
})();
