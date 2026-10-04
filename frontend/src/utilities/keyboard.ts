import { useEffect } from "react";

export interface Shortcut {
  key: string;
  description: string;
  handler: (event: KeyboardEvent) => void;
  allowInInput?: boolean;
}

const EDITABLE_TAGS = new Set(["INPUT", "TEXTAREA", "SELECT"]);

export function isTypingTarget(target: EventTarget | null): boolean {
  if (!(target instanceof HTMLElement)) return false;
  return EDITABLE_TAGS.has(target.tagName) || Boolean(target.isContentEditable);
}

export function useShortcuts(shortcuts: Shortcut[], enabled = true): void {
  useEffect(() => {
    if (!enabled) return;

    const onKeyDown = (event: KeyboardEvent) => {
      if (event.metaKey || event.ctrlKey || event.altKey) return;

      const typing = isTypingTarget(event.target);
      for (const shortcut of shortcuts) {
        if (event.key !== shortcut.key) continue;
        if (typing && !shortcut.allowInInput) continue;
        event.preventDefault();
        shortcut.handler(event);
        return;
      }
    };

    window.addEventListener("keydown", onKeyDown);
    return () => window.removeEventListener("keydown", onKeyDown);
  }, [shortcuts, enabled]);
}

export const JOB_LIST_SHORTCUTS: ReadonlyArray<{ key: string; description: string }> = [
  { key: "/", description: "Focus search" },
  { key: "j", description: "Next job" },
  { key: "k", description: "Previous job" },
  { key: "s", description: "Save or unsave" },
  { key: "Enter", description: "Open job" },
  { key: "?", description: "Show shortcuts" },
  { key: "Escape", description: "Close panel" },
];
