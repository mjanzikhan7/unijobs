import { useEffect } from "react";
import type { RefObject } from "react";

const ITEM_SELECTOR = "[data-roving-item]";

export function useRovingTabIndex(
  containerRef: RefObject<HTMLElement | null>,
  orientation: "horizontal" | "vertical" = "horizontal",
): void {
  useEffect(() => {
    const container = containerRef.current;
    if (!container) return;

    function items(): HTMLElement[] {
      if (!container) return [];
      return Array.from(container.querySelectorAll<HTMLElement>(ITEM_SELECTOR));
    }

    function setActive(next: HTMLElement) {
      for (const item of items()) item.tabIndex = item === next ? 0 : -1;
      next.focus();
    }

    const nextKey = orientation === "horizontal" ? "ArrowRight" : "ArrowDown";
    const prevKey = orientation === "horizontal" ? "ArrowLeft" : "ArrowUp";

    function onKeyDown(event: KeyboardEvent) {
      const all = items();
      if (all.length === 0) return;
      const currentIndex = all.indexOf(document.activeElement as HTMLElement);
      if (currentIndex === -1) return;

      if (event.key === nextKey) {
        event.preventDefault();
        setActive(all[(currentIndex + 1) % all.length]!);
      } else if (event.key === prevKey) {
        event.preventDefault();
        setActive(all[(currentIndex - 1 + all.length) % all.length]!);
      } else if (event.key === "Home") {
        event.preventDefault();
        setActive(all[0]!);
      } else if (event.key === "End") {
        event.preventDefault();
        setActive(all[all.length - 1]!);
      }
    }

    const all = items();
    if (all.length > 0 && !all.some((el) => el.tabIndex === 0)) {
      all[0]!.tabIndex = 0;
      for (const item of all.slice(1)) item.tabIndex = -1;
    }

    container.addEventListener("keydown", onKeyDown);
    return () => container.removeEventListener("keydown", onKeyDown);
  }, [containerRef, orientation]);
}
