export interface LiveAnnouncer {
  announce: (message: string, politeness?: "polite" | "assertive") => void;
  unmount: () => void;
}

const POLITE_ID = "unijobs-a11y-live-polite";
const ASSERTIVE_ID = "unijobs-a11y-live-assertive";
export const ANNOUNCE_WINDOW_MS = 500;

function ensureRegion(id: string, politeness: "polite" | "assertive"): HTMLElement {
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
      border: "0",
    });
    document.body.appendChild(el);
  }
  return el;
}

export function createLiveAnnouncer(): LiveAnnouncer {
  const polite = ensureRegion(POLITE_ID, "polite");
  const assertive = ensureRegion(ASSERTIVE_ID, "assertive");
  let lastAt = Number.NEGATIVE_INFINITY;
  let pending: { message: string; politeness: "polite" | "assertive" } | null = null;
  let timer: ReturnType<typeof setTimeout> | undefined;

  const flush = (message: string, politeness: "polite" | "assertive") => {
    lastAt = Date.now();
    const region = politeness === "assertive" ? assertive : polite;
    region.textContent = "";
    requestAnimationFrame(() => {
      region.textContent = message;
    });
  };

  const announce: LiveAnnouncer["announce"] = (message, politeness = "polite") => {
    const wait = ANNOUNCE_WINDOW_MS - (Date.now() - lastAt);
    if (wait <= 0 && !timer) {
      flush(message, politeness);
      return;
    }
    pending = { message, politeness };
    if (timer) return;
    timer = setTimeout(() => {
      timer = undefined;
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
