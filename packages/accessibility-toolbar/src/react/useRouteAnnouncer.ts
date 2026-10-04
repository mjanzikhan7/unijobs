import { useEffect, useRef } from "react";
import type { RefObject } from "react";

import { useA11yContext } from "./A11yProvider";
import { useAnnounce } from "./useAnnounce";

export interface UseRouteAnnouncerOptions {
  routeKey: string;
  title: string;
  focusTarget: RefObject<HTMLElement | null> | HTMLElement | null;
  suppress?: boolean;
}

export function useRouteAnnouncer({
  routeKey,
  title,
  focusTarget,
  suppress = false,
}: UseRouteAnnouncerOptions): void {
  const { engine } = useA11yContext();
  const announce = useAnnounce();
  const previousKey = useRef<string | null>(null);

  useEffect(() => {
    if (previousKey.current === null) {
      previousKey.current = routeKey;
      return;
    }
    if (previousKey.current === routeKey) return;
    previousKey.current = routeKey;

    engine.speech.stop();
    if (suppress) return;

    const target = focusTarget && "current" in focusTarget ? focusTarget.current : focusTarget;
    target?.focus({ preventScroll: true });
    announce(`${title}, page loaded`, "polite");
    window.scrollTo(0, 0);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [routeKey, suppress]);
}
