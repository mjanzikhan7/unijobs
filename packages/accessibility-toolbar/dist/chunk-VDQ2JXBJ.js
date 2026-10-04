import { A11yEngine } from './chunk-S7H7F2SZ.js';
import { createContext, useRef, useEffect, useMemo, useContext, useSyncExternalStore, useCallback, useId, useState, useLayoutEffect, cloneElement } from 'react';
import { jsx, jsxs } from 'react/jsx-runtime';

// src/react/liveRegion.ts
var POLITE_ID = "unijobs-a11y-live-polite";
var ASSERTIVE_ID = "unijobs-a11y-live-assertive";
var ANNOUNCE_WINDOW_MS = 500;
function ensureRegion(id, politeness) {
  let el = document.getElementById(id);
  if (!el) {
    el = document.createElement("div");
    el.id = id;
    el.setAttribute("aria-live", politeness);
    el.setAttribute("aria-atomic", "true");
    Object.assign(el.style, {
      position: "absolute",
      width: "1px",
      height: "1px",
      margin: "-1px",
      overflow: "hidden",
      clip: "rect(0 0 0 0)",
      whiteSpace: "nowrap",
      border: "0"
    });
    document.body.appendChild(el);
  }
  return el;
}
function createLiveAnnouncer() {
  const polite = ensureRegion(POLITE_ID, "polite");
  const assertive = ensureRegion(ASSERTIVE_ID, "assertive");
  let lastAt = Number.NEGATIVE_INFINITY;
  let pending = null;
  let timer;
  const flush = (message, politeness) => {
    lastAt = Date.now();
    const region = politeness === "assertive" ? assertive : polite;
    region.textContent = "";
    requestAnimationFrame(() => {
      region.textContent = message;
    });
  };
  const announce = (message, politeness = "polite") => {
    const wait = ANNOUNCE_WINDOW_MS - (Date.now() - lastAt);
    if (wait <= 0 && !timer) {
      flush(message, politeness);
      return;
    }
    pending = { message, politeness };
    if (timer) return;
    timer = setTimeout(() => {
      timer = void 0;
      if (!pending) return;
      const next = pending;
      pending = null;
      flush(next.message, next.politeness);
    }, Math.max(wait, 0));
  };
  const unmount = () => {
    clearTimeout(timer);
    polite.remove();
    assertive.remove();
  };
  return { announce, unmount };
}
var A11yContext = createContext(null);
function A11yProvider({ children, options }) {
  const engineRef = useRef(null);
  if (!engineRef.current) {
    const { announce } = createLiveAnnouncer();
    engineRef.current = new A11yEngine({ ...options, announce });
  }
  const engine = engineRef.current;
  useEffect(() => {
    void engine.init();
    return () => engine.destroy();
  }, []);
  const value = useMemo(
    () => ({
      engine,
      getSettings: () => engine.settings,
      subscribe: (onChange) => engine.subscribe(onChange)
    }),
    [engine]
  );
  return /* @__PURE__ */ jsx(A11yContext.Provider, { value, children });
}
function useA11yContext() {
  const ctx = useContext(A11yContext);
  if (!ctx) throw new Error("useA11y() must be used inside <A11yProvider>");
  return ctx;
}
function useA11ySnapshot() {
  const ctx = useA11yContext();
  return useSyncExternalStore(ctx.subscribe, ctx.getSettings, ctx.getSettings);
}
function useA11y(selector) {
  const ctx = useA11yContext();
  const getSnapshot = useCallback(
    () => selector ? selector(ctx.getSettings()) : ctx.getSettings(),
    [ctx, selector]
  );
  const value = useSyncExternalStore(ctx.subscribe, getSnapshot, getSnapshot);
  const { engine } = ctx;
  return {
    value,
    set: (key, next) => engine.set(key, next),
    patch: (partial) => engine.patch(partial),
    applyProfile: (id) => engine.applyProfile(id),
    clearProfile: () => engine.clearProfile(),
    resetKeys: (keys) => engine.resetKeys(keys),
    reset: () => {
      engine.speech.stop();
      engine.reset();
    }
  };
}
function useAnnounce() {
  const ctx = useA11yContext();
  return useCallback(
    (message, politeness = "polite") => {
      ctx.engine.announce(message, politeness);
    },
    [ctx]
  );
}
function useSpeech() {
  const { engine } = useA11yContext();
  const speech = engine.speech;
  const subscribe = useCallback((onChange) => speech.subscribe(onChange), [speech]);
  const getState = useCallback(() => speech.state, [speech]);
  const state = useSyncExternalStore(subscribe, getState, getState);
  return useMemo(
    () => ({
      ...state,
      speakPage: (root) => speech.speakPage(root),
      speakSelection: () => speech.speakSelection(),
      speakText: (text) => speech.speakText(text),
      pause: () => speech.pause(),
      resume: () => speech.resume(),
      stop: () => speech.stop()
    }),
    [state, speech]
  );
}
var SHOW_DELAY_MS = 250;
var HIDE_DELAY_MS = 150;
var GAP_PX = 8;
var MARGIN_PX = 8;
function matchesFocusVisible(el) {
  try {
    return el.matches(":focus-visible");
  } catch {
    return true;
  }
}
function Tip({ label, children, block = false, className }) {
  const id = useId();
  const wrapperRef = useRef(null);
  const tipRef = useRef(null);
  const timer = useRef(void 0);
  const dismissed = useRef(false);
  const [open, setOpen] = useState(false);
  const [position, setPosition] = useState(null);
  useEffect(() => () => clearTimeout(timer.current), []);
  useEffect(() => {
    if (!open) return;
    function onKeyDown(event) {
      if (event.key !== "Escape") return;
      event.preventDefault();
      event.stopPropagation();
      clearTimeout(timer.current);
      dismissed.current = true;
      setOpen(false);
    }
    window.addEventListener("keydown", onKeyDown, true);
    return () => window.removeEventListener("keydown", onKeyDown, true);
  }, [open]);
  useLayoutEffect(() => {
    if (!open) {
      setPosition(null);
      return;
    }
    const anchor = wrapperRef.current?.firstElementChild ?? wrapperRef.current;
    const tip = tipRef.current;
    if (!anchor || !tip) return;
    const a = anchor.getBoundingClientRect();
    const t = tip.getBoundingClientRect();
    let top = a.top - t.height - GAP_PX;
    if (top < MARGIN_PX) top = a.bottom + GAP_PX;
    const left = Math.min(
      Math.max(a.left + a.width / 2 - t.width / 2, MARGIN_PX),
      Math.max(MARGIN_PX, window.innerWidth - t.width - MARGIN_PX)
    );
    setPosition({ top, left });
  }, [open, label]);
  const schedule = (next, delay) => {
    clearTimeout(timer.current);
    timer.current = setTimeout(() => setOpen(next), delay);
  };
  const describedBy = [children.props["aria-describedby"], id].filter(Boolean).join(" ");
  const classes = ["tip", block ? "tip-block" : "", className ?? ""].filter(Boolean).join(" ");
  return /* @__PURE__ */ jsxs(
    "span",
    {
      ref: wrapperRef,
      className: classes,
      onMouseEnter: () => {
        if (!dismissed.current) schedule(true, SHOW_DELAY_MS);
      },
      onMouseLeave: () => {
        dismissed.current = false;
        schedule(false, HIDE_DELAY_MS);
      },
      onFocus: (event) => {
        if (event.target === tipRef.current || !matchesFocusVisible(event.target)) return;
        clearTimeout(timer.current);
        dismissed.current = false;
        setOpen(true);
      },
      onBlur: () => {
        clearTimeout(timer.current);
        setOpen(false);
      },
      children: [
        cloneElement(children, { "aria-describedby": describedBy }),
        /* @__PURE__ */ jsx(
          "span",
          {
            ref: tipRef,
            id,
            role: "tooltip",
            className: "tooltip",
            "data-open": open && position ? "true" : "false",
            style: position ? { top: `${position.top}px`, left: `${position.left}px` } : void 0,
            children: label
          }
        )
      ]
    }
  );
}

export { A11yProvider, Tip, useA11y, useA11yContext, useA11ySnapshot, useAnnounce, useSpeech };
//# sourceMappingURL=chunk-VDQ2JXBJ.js.map
//# sourceMappingURL=chunk-VDQ2JXBJ.js.map