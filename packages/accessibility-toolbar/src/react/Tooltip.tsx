import { cloneElement, useEffect, useId, useLayoutEffect, useRef, useState } from "react";
import type { ReactElement } from "react";

const SHOW_DELAY_MS = 250;
const HIDE_DELAY_MS = 150;
const GAP_PX = 8;
const MARGIN_PX = 8;

export interface TipProps {
  label: string;
  children: ReactElement<{ "aria-describedby"?: string }>;
  block?: boolean;
  className?: string;
}

function matchesFocusVisible(el: Element): boolean {
  try {
    return el.matches(":focus-visible");
  } catch {
    return true;
  }
}

export function Tip({ label, children, block = false, className }: TipProps) {
  const id = useId();
  const wrapperRef = useRef<HTMLSpanElement>(null);
  const tipRef = useRef<HTMLSpanElement>(null);
  const timer = useRef<ReturnType<typeof setTimeout> | undefined>(undefined);
  const dismissed = useRef(false);
  const [open, setOpen] = useState(false);
  const [position, setPosition] = useState<{ top: number; left: number } | null>(null);

  useEffect(() => () => clearTimeout(timer.current), []);

  useEffect(() => {
    if (!open) return;
    function onKeyDown(event: KeyboardEvent) {
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
      Math.max(MARGIN_PX, window.innerWidth - t.width - MARGIN_PX),
    );
    setPosition({ top, left });
  }, [open, label]);

  const schedule = (next: boolean, delay: number) => {
    clearTimeout(timer.current);
    timer.current = setTimeout(() => setOpen(next), delay);
  };

  const describedBy = [children.props["aria-describedby"], id].filter(Boolean).join(" ");
  const classes = ["tip", block ? "tip-block" : "", className ?? ""].filter(Boolean).join(" ");

  return (
    <span
      ref={wrapperRef}
      className={classes}
      onMouseEnter={() => {
        if (!dismissed.current) schedule(true, SHOW_DELAY_MS);
      }}
      onMouseLeave={() => {
        dismissed.current = false;
        schedule(false, HIDE_DELAY_MS);
      }}
      onFocus={(event) => {
        if (event.target === tipRef.current || !matchesFocusVisible(event.target)) return;
        clearTimeout(timer.current);
        dismissed.current = false;
        setOpen(true);
      }}
      onBlur={() => {
        clearTimeout(timer.current);
        setOpen(false);
      }}
    >
      {cloneElement(children, { "aria-describedby": describedBy })}
      <span
        ref={tipRef}
        id={id}
        role="tooltip"
        className="tooltip"
        data-open={open && position ? "true" : "false"}
        style={position ? { top: `${position.top}px`, left: `${position.left}px` } : undefined}
      >
        {label}
      </span>
    </span>
  );
}
