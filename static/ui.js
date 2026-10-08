// Applies the few dynamic style values the server provides as data-* attributes.
// Done through the CSSOM so the Content-Security-Policy can forbid inline style attributes.
(function () {
  "use strict";
  var COLOR = /^#[0-9a-fA-F]{3,8}$/;
  document.querySelectorAll("[data-accent]").forEach(function (el) {
    var c = el.getAttribute("data-accent");
    if (COLOR.test(c)) el.style.setProperty("--accent", c);
  });
  document.querySelectorAll("[data-pct]").forEach(function (el) {
    var n = parseFloat(el.getAttribute("data-pct"));
    if (isFinite(n)) el.style.width = Math.max(0, Math.min(100, n)) + "%";
  });

  // Completion pop-up: the x button, Escape, or a click on the backdrop closes it.
  var modal = document.getElementById("complete-modal");
  if (modal) {
    var close = function () { modal.hidden = true; };
    modal.querySelectorAll("[data-close-modal]").forEach(function (b) { b.addEventListener("click", close); });
    modal.addEventListener("click", function (e) { if (e.target === modal) close(); });
    document.addEventListener("keydown", function (e) { if (e.key === "Escape") close(); });
    var first = modal.querySelector(".modal-actions .btn");
    if (first) first.focus();
  }

  // Buttons that need an "are you sure?" (reset / restart).
  document.querySelectorAll("[data-confirm]").forEach(function (el) {
    el.addEventListener("click", function (e) {
      if (!window.confirm(el.getAttribute("data-confirm"))) e.preventDefault();
    });
  });
})();
