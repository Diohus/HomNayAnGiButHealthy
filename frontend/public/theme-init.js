// Áp chế độ sáng/tối đã lưu TRƯỚC khi React render để không bị nháy.
// File ngoài (không inline) để hợp CSP script-src 'self'. Cùng logic với src/theme.ts.
(function () {
  var theme = null;
  try {
    theme = localStorage.getItem("hnag_theme");
  } catch (e) {
    /* storage bị chặn: theo hệ thống */
  }
  var root = document.documentElement;
  if (theme === "light" || theme === "dark") root.setAttribute("data-theme", theme);
  try {
    var lang = localStorage.getItem("hnag_lang");
    if (lang === "en" || lang === "vi") root.setAttribute("lang", lang);
  } catch (e) {
    /* bỏ qua */
  }
  var dark = theme === "dark" || (theme !== "light" && window.matchMedia &&
    window.matchMedia("(prefers-color-scheme: dark)").matches);
  var meta = document.querySelector('meta[name="theme-color"]');
  if (meta) meta.setAttribute("content", dark ? "#0f1218" : "#f6f7f9");
})();
