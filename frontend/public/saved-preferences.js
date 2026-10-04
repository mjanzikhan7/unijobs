(function applyColourTheme() {
  try {
    var stored = localStorage.getItem("theme");
    var prefersDark = window.matchMedia && window.matchMedia("(prefers-color-scheme: dark)").matches;
    var theme = stored === "light" || stored === "dark" ? stored : prefersDark ? "dark" : "light";
    document.documentElement.dataset.theme = theme;
  } catch (error) {
    // Storage is blocked. The stylesheet falls back to the system colour scheme.
  }
})();

(function applyAccessibilitySettings() {
  try {
    var saved = JSON.parse(localStorage.getItem("unijobs.a11y") || "null");
    if (!saved || typeof saved !== "object") return;
    var root = document.documentElement;
    var themes =
      /^(contrast-dark|contrast-light|monochrome|saturation-low|saturation-high|invert|protanopia|deuteranopia|tritanopia)$/;
    if (themes.test(saved.theme)) root.dataset.a11yTheme = saved.theme;
    if (saved.fontFamily === "readable" || saved.fontFamily === "dyslexic") {
      root.dataset.a11yFont = saved.fontFamily;
    }
    if (saved.motion === "reduced" || saved.motion === "off") root.dataset.a11yMotion = saved.motion;
    if (typeof saved.fontScale === "number" && saved.fontScale > 1 && saved.fontScale <= 2) {
      root.dataset.a11yTextScale = "true";
      root.style.setProperty("--a11y-font-scale", String(saved.fontScale));
    }
  } catch (error) {
    // Storage is blocked or the value is broken. The toolbar sorts it out when it loads.
  }
})();
