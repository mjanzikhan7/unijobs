import { Suspense, lazy, useEffect, useId, useRef, useState } from "react";
import type { KeyboardEvent } from "react";

import { AccessibilityIcon } from "./AccessibilityIcon";
import { ShadowPortal } from "./ShadowPortal";
import { Tip } from "./Tooltip";
import { TOOLBAR_CSS } from "./toolbarStyles";
import { useA11y } from "./useA11y";
import { useAnnounce } from "./useAnnounce";
import { useSpeech } from "./useSpeech";

const Panel = lazy(() => import("./Panel").then((m) => ({ default: m.Panel })));

const PANEL_ID = "unijobs-a11y-panel";

export interface A11yToolbarProps {
  position?: "left" | "right";
  label?: string;
}

export function A11yToolbar({ position, label = "Accessibility settings" }: A11yToolbarProps) {
  const { value: toolbar, reset } = useA11y((s) => s.toolbar);
  const speech = useSpeech();
  const announce = useAnnounce();
  const [open, setOpen] = useState(false);
  const openRef = useRef(open);
  const launcherRef = useRef<HTMLButtonElement>(null);
  const headingRef = useRef<HTMLHeadingElement>(null);
  const headingId = useId();
  const side = position ?? toolbar.position;

  openRef.current = open;

  useEffect(() => {
    function onKeyDown(event: globalThis.KeyboardEvent) {
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
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [open]);

  if (toolbar.hidden) return null;

  const close = () => {
    setOpen(false);
    launcherRef.current?.focus();
  };

  const onPanelKeyDown = (event: KeyboardEvent<HTMLDivElement>) => {
    if (event.key === "Escape" && !event.defaultPrevented) {
      event.preventDefault();
      close();
    }
  };

  return (
    <ShadowPortal css={TOOLBAR_CSS}>
      <button
        ref={launcherRef}
        type="button"
        className="launcher"
        data-position={side}
        aria-expanded={open}
        aria-controls={open ? PANEL_ID : undefined}
        aria-label={label}
        aria-keyshortcuts="Alt+0"
        onClick={() => (open ? close() : setOpen(true))}
      >
        <AccessibilityIcon />
        <span className="launcher-label" aria-hidden="true">
          {label} <kbd>Alt+0</kbd>
        </span>
      </button>

      {!open && speech.status !== "idle" ? (
        <div className="player" data-position={side} role="region" aria-label="Read aloud controls">
          <span className="player-status">{speech.status === "paused" ? "Paused" : "Reading aloud…"}</span>
          {speech.status === "paused" ? (
            <Tip label="Carry on reading from where it paused.">
              <button type="button" className="player-btn" onClick={speech.resume}>
                Resume
              </button>
            </Tip>
          ) : (
            <Tip label="Pause reading. Resume carries on from the same place.">
              <button type="button" className="player-btn" onClick={speech.pause}>
                Pause
              </button>
            </Tip>
          )}
          <Tip label="Stop reading and clear the highlight.">
            <button type="button" className="player-btn" onClick={speech.stop}>
              Stop
            </button>
          </Tip>
        </div>
      ) : null}

      {open ? (
        <div
          id={PANEL_ID}
          className="panel"
          data-position={side}
          role="dialog"
          aria-modal="false"
          aria-labelledby={headingId}
          onKeyDown={onPanelKeyDown}
        >
          <div className="panel-header">
            <h2 id={headingId} ref={headingRef} tabIndex={-1}>
              Accessibility settings
            </h2>
            <Tip label="Close this panel (Esc). Your settings are kept.">
              <button type="button" className="close-btn" aria-label="Close accessibility settings" onClick={close}>
                <span aria-hidden="true">✕</span>
              </button>
            </Tip>
          </div>

          <Suspense fallback={<p className="panel-body">Loading settings…</p>}>
            <Panel />
          </Suspense>

          <div className="footer">
            <Tip label="Turns every setting in this panel back to its default, including any profile, and stops reading.">
              <button
                type="button"
                className="reset-all-btn"
                onClick={() => {
                  reset();
                  announce("All accessibility settings reset");
                }}
              >
                Reset all settings
              </button>
            </Tip>
            <span className="shortcut">
              <kbd>Alt</kbd>+<kbd>0</kbd> opens and closes
            </span>
          </div>
        </div>
      ) : null}
    </ShadowPortal>
  );
}
