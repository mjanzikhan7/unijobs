export const TOOLBAR_CSS = `
:host { all: initial; }
*, *::before, *::after { box-sizing: border-box; }

button, input, select { font: inherit; color: inherit; }

.launcher {
  position: fixed;
  bottom: 16px;
  z-index: 2147483000;
  display: inline-flex;
  align-items: center;
  gap: 8px;
  min-height: 48px;
  min-width: 48px;
  padding: 12px;
  border: 2px solid #ffffff;
  border-radius: 999px;
  background: #1d4ed8;
  color: #ffffff;
  cursor: pointer;
  box-shadow: 0 4px 16px rgba(0, 0, 0, 0.3);
  font: 600 14px/1.2 system-ui, -apple-system, "Segoe UI", sans-serif;
}
.launcher[data-position="right"] { right: 16px; }
.launcher[data-position="left"] { left: 16px; }
.launcher:hover { background: #1e40af; }
.launcher-label {
  max-width: 0;
  overflow: hidden;
  white-space: nowrap;
  opacity: 0;
  transition: max-width 0.15s ease, opacity 0.15s ease;
}
.launcher:hover .launcher-label,
.launcher:focus-visible .launcher-label { max-width: 280px; opacity: 1; }

kbd {
  display: inline-block;
  padding: 0 5px;
  border: 1px solid currentColor;
  border-radius: 4px;
  font: 600 12px/1.5 ui-monospace, "SF Mono", Menlo, Consolas, monospace;
}

.panel {
  position: fixed;
  top: 0;
  bottom: 0;
  z-index: 2147483001;
  width: min(380px, 100vw);
  display: flex;
  flex-direction: column;
  background: #ffffff;
  color: #1f2937;
  box-shadow: -8px 0 24px rgba(0, 0, 0, 0.2);
  font: 400 14px/1.45 system-ui, -apple-system, "Segoe UI", sans-serif;
}
.panel[data-position="right"] { right: 0; }
.panel[data-position="left"] { left: 0; box-shadow: 8px 0 24px rgba(0, 0, 0, 0.2); }

.panel-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  padding: 14px 16px;
  border-bottom: 1px solid #e5e7eb;
}
.panel-header h2 { margin: 0; font: 700 17px/1.3 system-ui, -apple-system, "Segoe UI", sans-serif; }

.panel-body { flex: 1; min-height: 0; overflow-y: auto; padding: 16px; }

fieldset { margin: 0 0 16px; padding: 10px 12px 12px; border: 1px solid #d1d5db; border-radius: 10px; }
legend { float: left; padding: 4px 0; font-weight: 700; font-size: 15px; }
.section-reset { float: right; }
.section-body { clear: both; padding-top: 6px; }

.hint { margin: 0 0 10px; color: #4b5563; font-size: 13px; }
.note { margin: 0; color: #4b5563; }
.status-line { margin: 6px 0 4px; color: #4b5563; font-size: 13px; }
.group-label { margin: 10px 0 6px; font-weight: 600; }

.grid { display: grid; gap: 6px; }
.grid-2 { grid-template-columns: repeat(2, minmax(0, 1fr)); }
.grid-3 { grid-template-columns: repeat(3, minmax(0, 1fr)); }

.choice, .action-btn, .step-btn, .reset-btn, .reset-all-btn, .close-btn, .player-btn {
  min-height: 36px;
  border: 1px solid #9ca3af;
  border-radius: 8px;
  background: #f9fafb;
  color: #1f2937;
  cursor: pointer;
  padding: 6px 10px;
}
.choice { width: 100%; text-align: left; font-weight: 500; }
.choice:hover, .action-btn:hover, .step-btn:hover, .reset-btn:hover, .reset-all-btn:hover, .close-btn:hover { background: #eef2ff; border-color: #1d4ed8; }
.choice[aria-pressed="true"] { background: #1d4ed8; border-color: #1d4ed8; color: #ffffff; }
.choice[aria-pressed="true"]::before { content: "✓ "; content: "✓ " / ""; }

.reset-btn { min-height: 30px; padding: 3px 10px; font-size: 13px; }
.close-btn { min-width: 36px; font-size: 16px; line-height: 1; }
.reset-all-btn { font-weight: 600; }

.button-row { display: flex; flex-wrap: wrap; gap: 6px; }

[aria-disabled="true"] { opacity: 0.55; cursor: not-allowed; }
[aria-disabled="true"]:hover { background: #f9fafb; border-color: #9ca3af; }
input:disabled { cursor: not-allowed; }

.row { display: flex; align-items: center; justify-content: space-between; gap: 12px; min-height: 36px; }
.row label { flex: 1; cursor: pointer; }
input[type="checkbox"] { width: 20px; height: 20px; margin: 0; accent-color: #1d4ed8; cursor: pointer; }

.range-row { display: flex; flex-direction: column; gap: 4px; padding: 6px 0; }
.range-row > label { display: flex; justify-content: space-between; gap: 8px; }
.range-row .value { font-variant-numeric: tabular-nums; color: #4b5563; }
input[type="range"] { width: 100%; margin: 6px 0; accent-color: #1d4ed8; cursor: pointer; }
select { width: 100%; min-height: 36px; padding: 4px 8px; border: 1px solid #9ca3af; border-radius: 8px; background: #ffffff; }

.stepper { display: flex; align-items: center; gap: 8px; }
.stepper .tip-block { flex: 1; }

.footer {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
  padding: 12px 16px;
  border-top: 1px solid #e5e7eb;
}
.shortcut { color: #4b5563; font-size: 12px; }

.player {
  position: fixed;
  bottom: 16px;
  z-index: 2147483000;
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 8px 10px;
  border-radius: 12px;
  background: #111827;
  color: #ffffff;
  box-shadow: 0 4px 16px rgba(0, 0, 0, 0.3);
  font: 500 14px/1.3 system-ui, -apple-system, "Segoe UI", sans-serif;
}
.player[data-position="right"] { right: 80px; }
.player[data-position="left"] { left: 80px; }
.player-btn { background: #ffffff; color: #111827; border-color: #ffffff; font-weight: 600; }
.player-btn:hover { background: #e5e7eb; }

.tip { position: relative; display: inline-flex; }
.tip-block { display: flex; width: 100%; }
.tip-block > :first-child { flex: 1; }
.tooltip {
  position: fixed;
  top: 0;
  left: 0;
  z-index: 2147483647;
  max-width: 260px;
  padding: 8px 10px;
  border-radius: 8px;
  background: #111827;
  color: #ffffff;
  box-shadow: 0 6px 18px rgba(0, 0, 0, 0.3);
  font: 400 13px/1.4 system-ui, -apple-system, "Segoe UI", sans-serif;
  text-align: left;
  white-space: normal;
  visibility: hidden;
  opacity: 0;
  pointer-events: none;
  transition: opacity 0.12s ease;
}
.tooltip[data-open="true"] { visibility: visible; opacity: 1; pointer-events: auto; }

button:focus-visible, input:focus-visible, select:focus-visible, h2:focus-visible {
  outline: 3px solid #f59e0b;
  outline-offset: 2px;
}
.launcher:focus-visible { outline-color: #111827; box-shadow: 0 0 0 6px #f59e0b; }

@media (prefers-reduced-motion: reduce) {
  *, *::before, *::after { transition: none !important; }
}
@media (forced-colors: active) {
  .choice[aria-pressed="true"] { forced-color-adjust: none; background: Highlight; color: HighlightText; }
  .tooltip { border: 1px solid CanvasText; }
}
@media (max-width: 420px) {
  .panel { width: 100vw; }
  .player[data-position="right"] { right: 72px; left: 8px; }
}
`;
