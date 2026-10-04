import { useA11yContext, useAnnounce, useA11y, useSpeech, Tip } from '../chunk-VDQ2JXBJ.js';
export { A11yProvider, Tip, useA11y, useA11yContext, useA11ySnapshot, useAnnounce, useSpeech } from '../chunk-VDQ2JXBJ.js';
import { TOOLBAR_HOST_ID } from '../chunk-S7H7F2SZ.js';
import { lazy, useRef, useEffect, useState, useId, Suspense, useLayoutEffect } from 'react';
import { jsx, jsxs } from 'react/jsx-runtime';
import { createPortal } from 'react-dom';

function useRouteAnnouncer({
  routeKey,
  title,
  focusTarget: focusTarget2,
  suppress = false
}) {
  const { engine } = useA11yContext();
  const announce = useAnnounce();
  const previousKey = useRef(null);
  useEffect(() => {
    if (previousKey.current === null) {
      previousKey.current = routeKey;
      return;
    }
    if (previousKey.current === routeKey) return;
    previousKey.current = routeKey;
    engine.speech.stop();
    if (suppress) return;
    const target = focusTarget2 && "current" in focusTarget2 ? focusTarget2.current : focusTarget2;
    target?.focus({ preventScroll: true });
    announce(`${title}, page loaded`, "polite");
    window.scrollTo(0, 0);
  }, [routeKey, suppress]);
}
var FOCUSABLE_SELECTOR = [
  "a[href]",
  "button:not([disabled])",
  "input:not([disabled])",
  "select:not([disabled])",
  "textarea:not([disabled])",
  "[tabindex]:not([tabindex='-1'])"
].join(",");
function useFocusTrap(containerRef, active) {
  useEffect(() => {
    if (!active) return;
    const container = containerRef.current;
    if (!container) return;
    function getRootActiveElement() {
      const root = container?.getRootNode();
      if (root instanceof ShadowRoot || root instanceof Document) return root.activeElement;
      return document.activeElement;
    }
    function getFocusable() {
      if (!container) return [];
      return Array.from(container.querySelectorAll(FOCUSABLE_SELECTOR)).filter(
        (el) => el.offsetParent !== null || el === document.activeElement
      );
    }
    function onKeyDown(event) {
      if (event.key !== "Tab") return;
      const focusable = getFocusable();
      if (focusable.length === 0) return;
      const first = focusable[0];
      const last = focusable[focusable.length - 1];
      const current = getRootActiveElement();
      if (event.shiftKey && current === first) {
        event.preventDefault();
        last?.focus();
      } else if (!event.shiftKey && current === last) {
        event.preventDefault();
        first?.focus();
      }
    }
    container.addEventListener("keydown", onKeyDown);
    return () => container.removeEventListener("keydown", onKeyDown);
  }, [containerRef, active]);
}
var ITEM_SELECTOR = "[data-roving-item]";
function useRovingTabIndex(containerRef, orientation = "horizontal") {
  useEffect(() => {
    const container = containerRef.current;
    if (!container) return;
    function items() {
      if (!container) return [];
      return Array.from(container.querySelectorAll(ITEM_SELECTOR));
    }
    function setActive(next) {
      for (const item of items()) item.tabIndex = item === next ? 0 : -1;
      next.focus();
    }
    const nextKey = orientation === "horizontal" ? "ArrowRight" : "ArrowDown";
    const prevKey = orientation === "horizontal" ? "ArrowLeft" : "ArrowUp";
    function onKeyDown(event) {
      const all2 = items();
      if (all2.length === 0) return;
      const currentIndex = all2.indexOf(document.activeElement);
      if (currentIndex === -1) return;
      if (event.key === nextKey) {
        event.preventDefault();
        setActive(all2[(currentIndex + 1) % all2.length]);
      } else if (event.key === prevKey) {
        event.preventDefault();
        setActive(all2[(currentIndex - 1 + all2.length) % all2.length]);
      } else if (event.key === "Home") {
        event.preventDefault();
        setActive(all2[0]);
      } else if (event.key === "End") {
        event.preventDefault();
        setActive(all2[all2.length - 1]);
      }
    }
    const all = items();
    if (all.length > 0 && !all.some((el) => el.tabIndex === 0)) {
      all[0].tabIndex = 0;
      for (const item of all.slice(1)) item.tabIndex = -1;
    }
    container.addEventListener("keydown", onKeyDown);
    return () => container.removeEventListener("keydown", onKeyDown);
  }, [containerRef, orientation]);
}
function VisuallyHidden({
  children,
  as: Component = "span"
}) {
  return /* @__PURE__ */ jsx(
    Component,
    {
      style: {
        position: "absolute",
        width: "1px",
        height: "1px",
        padding: 0,
        margin: "-1px",
        overflow: "hidden",
        clip: "rect(0, 0, 0, 0)",
        whiteSpace: "nowrap",
        border: 0
      },
      children
    }
  );
}
function focusTarget(targetId) {
  return (event) => {
    event.preventDefault();
    const el = document.getElementById(targetId);
    if (!el) return;
    if (!el.hasAttribute("tabindex")) el.setAttribute("tabindex", "-1");
    el.focus();
    el.scrollIntoView();
  };
}
var linkStyle = {
  position: "absolute",
  top: 0,
  left: 0,
  transform: "translateY(-150%)",
  transition: "transform 0.15s ease-out",
  background: "var(--a11y-focus-ring, #0b57d0)",
  color: "#fff",
  padding: "0.5rem 1rem",
  zIndex: 2147483e3,
  borderRadius: "0 0 4px 0",
  textDecoration: "none"
};
function SkipLinks({ links, className }) {
  return /* @__PURE__ */ jsx("nav", { "aria-label": "Skip links", className, children: links.map((link) => /* @__PURE__ */ jsx(
    "a",
    {
      href: `#${link.targetId}`,
      onClick: focusTarget(link.targetId),
      style: linkStyle,
      onFocus: (e) => e.currentTarget.style.transform = "translateY(0)",
      onBlur: (e) => e.currentTarget.style.transform = "translateY(-150%)",
      children: link.label
    },
    link.targetId
  )) });
}
function AccessibilityIcon() {
  return /* @__PURE__ */ jsxs("svg", { width: "20", height: "20", viewBox: "0 0 24 24", fill: "none", "aria-hidden": "true", focusable: "false", children: [
    /* @__PURE__ */ jsx("circle", { cx: "12", cy: "4", r: "2", fill: "currentColor" }),
    /* @__PURE__ */ jsx(
      "path",
      {
        d: "M4 8.5c2.5 1 5.2 1.5 8 1.5s5.5-.5 8-1.5M12 10v4l-3 7M12 14l3 7M9 13.5 8 17M15 13.5l1 3.5",
        stroke: "currentColor",
        strokeWidth: "1.8",
        strokeLinecap: "round",
        fill: "none"
      }
    )
  ] });
}
function ShadowPortal({ children, css, hostId = TOOLBAR_HOST_ID }) {
  const [container, setContainer] = useState(null);
  useLayoutEffect(() => {
    let host = document.getElementById(hostId);
    let createdHost = false;
    if (!host) {
      host = document.createElement("div");
      host.id = hostId;
      document.body.appendChild(host);
      createdHost = true;
    }
    const shadow = host.shadowRoot ?? host.attachShadow({ mode: "open" });
    let mountPoint = shadow.getElementById("mount");
    if (!mountPoint) {
      mountPoint = document.createElement("div");
      mountPoint.id = "mount";
      shadow.appendChild(mountPoint);
    }
    const supportsAdoptedStyleSheets = typeof CSSStyleSheet !== "undefined" && "replaceSync" in CSSStyleSheet.prototype;
    if (supportsAdoptedStyleSheets) {
      const sheet = new CSSStyleSheet();
      sheet.replaceSync(css);
      shadow.adoptedStyleSheets = [sheet];
    } else {
      let styleTag = shadow.querySelector("style");
      if (!styleTag) {
        styleTag = document.createElement("style");
        shadow.insertBefore(styleTag, shadow.firstChild);
      }
      styleTag.textContent = css;
    }
    setContainer(mountPoint);
    return () => {
      if (createdHost) host?.remove();
    };
  }, [css, hostId]);
  if (!container) return null;
  return createPortal(children, container);
}

// src/react/toolbarStyles.ts
var TOOLBAR_CSS = `
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
.choice[aria-pressed="true"]::before { content: "\u2713 "; content: "\u2713 " / ""; }

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
var Panel = lazy(() => import('../Panel-ATKMLKCH.js').then((m) => ({ default: m.Panel })));
var PANEL_ID = "unijobs-a11y-panel";
function A11yToolbar({ position, label = "Accessibility settings" }) {
  const { value: toolbar, reset } = useA11y((s) => s.toolbar);
  const speech = useSpeech();
  const announce = useAnnounce();
  const [open, setOpen] = useState(false);
  const openRef = useRef(open);
  const launcherRef = useRef(null);
  const headingRef = useRef(null);
  const headingId = useId();
  const side = position ?? toolbar.position;
  openRef.current = open;
  useEffect(() => {
    function onKeyDown(event) {
      if (!event.altKey || event.ctrlKey || event.metaKey || event.shiftKey) return;
      if (event.code !== "Digit0" && event.key !== "0") return;
      event.preventDefault();
      if (openRef.current) {
        setOpen(false);
        launcherRef.current?.focus();
      } else {
        setOpen(true);
      }
    }
    document.addEventListener("keydown", onKeyDown, true);
    return () => document.removeEventListener("keydown", onKeyDown, true);
  }, []);
  useEffect(() => {
    if (!open) return;
    headingRef.current?.focus();
    announce("Accessibility settings opened");
  }, [open]);
  if (toolbar.hidden) return null;
  const close = () => {
    setOpen(false);
    launcherRef.current?.focus();
  };
  const onPanelKeyDown = (event) => {
    if (event.key === "Escape" && !event.defaultPrevented) {
      event.preventDefault();
      close();
    }
  };
  return /* @__PURE__ */ jsxs(ShadowPortal, { css: TOOLBAR_CSS, children: [
    /* @__PURE__ */ jsxs(
      "button",
      {
        ref: launcherRef,
        type: "button",
        className: "launcher",
        "data-position": side,
        "aria-expanded": open,
        "aria-controls": open ? PANEL_ID : void 0,
        "aria-label": label,
        "aria-keyshortcuts": "Alt+0",
        onClick: () => open ? close() : setOpen(true),
        children: [
          /* @__PURE__ */ jsx(AccessibilityIcon, {}),
          /* @__PURE__ */ jsxs("span", { className: "launcher-label", "aria-hidden": "true", children: [
            label,
            " ",
            /* @__PURE__ */ jsx("kbd", { children: "Alt+0" })
          ] })
        ]
      }
    ),
    !open && speech.status !== "idle" ? /* @__PURE__ */ jsxs("div", { className: "player", "data-position": side, role: "region", "aria-label": "Read aloud controls", children: [
      /* @__PURE__ */ jsx("span", { className: "player-status", children: speech.status === "paused" ? "Paused" : "Reading aloud\u2026" }),
      speech.status === "paused" ? /* @__PURE__ */ jsx(Tip, { label: "Carry on reading from where it paused.", children: /* @__PURE__ */ jsx("button", { type: "button", className: "player-btn", onClick: speech.resume, children: "Resume" }) }) : /* @__PURE__ */ jsx(Tip, { label: "Pause reading. Resume carries on from the same place.", children: /* @__PURE__ */ jsx("button", { type: "button", className: "player-btn", onClick: speech.pause, children: "Pause" }) }),
      /* @__PURE__ */ jsx(Tip, { label: "Stop reading and clear the highlight.", children: /* @__PURE__ */ jsx("button", { type: "button", className: "player-btn", onClick: speech.stop, children: "Stop" }) })
    ] }) : null,
    open ? /* @__PURE__ */ jsxs(
      "div",
      {
        id: PANEL_ID,
        className: "panel",
        "data-position": side,
        role: "dialog",
        "aria-modal": "false",
        "aria-labelledby": headingId,
        onKeyDown: onPanelKeyDown,
        children: [
          /* @__PURE__ */ jsxs("div", { className: "panel-header", children: [
            /* @__PURE__ */ jsx("h2", { id: headingId, ref: headingRef, tabIndex: -1, children: "Accessibility settings" }),
            /* @__PURE__ */ jsx(Tip, { label: "Close this panel (Esc). Your settings are kept.", children: /* @__PURE__ */ jsx("button", { type: "button", className: "close-btn", "aria-label": "Close accessibility settings", onClick: close, children: /* @__PURE__ */ jsx("span", { "aria-hidden": "true", children: "\u2715" }) }) })
          ] }),
          /* @__PURE__ */ jsx(Suspense, { fallback: /* @__PURE__ */ jsx("p", { className: "panel-body", children: "Loading settings\u2026" }), children: /* @__PURE__ */ jsx(Panel, {}) }),
          /* @__PURE__ */ jsxs("div", { className: "footer", children: [
            /* @__PURE__ */ jsx(Tip, { label: "Turns every setting in this panel back to its default, including any profile, and stops reading.", children: /* @__PURE__ */ jsx(
              "button",
              {
                type: "button",
                className: "reset-all-btn",
                onClick: () => {
                  reset();
                  announce("All accessibility settings reset");
                },
                children: "Reset all settings"
              }
            ) }),
            /* @__PURE__ */ jsxs("span", { className: "shortcut", children: [
              /* @__PURE__ */ jsx("kbd", { children: "Alt" }),
              "+",
              /* @__PURE__ */ jsx("kbd", { children: "0" }),
              " opens and closes"
            ] })
          ] })
        ]
      }
    ) : null
  ] });
}

export { A11yToolbar, SkipLinks, VisuallyHidden, useFocusTrap, useRouteAnnouncer, useRovingTabIndex };
//# sourceMappingURL=index.js.map
//# sourceMappingURL=index.js.map