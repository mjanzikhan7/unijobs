import { useCallback, useState } from "react";

const STORAGE_KEY = "sidebar-collapsed";

function readStored(): boolean {
  try {
    return window.localStorage.getItem(STORAGE_KEY) === "true";
  } catch {
    return false;
  }
}

export function useSidebarCollapsed(): { collapsed: boolean; toggleCollapsed: () => void } {
  const [collapsed, setCollapsed] = useState<boolean>(readStored);

  const toggleCollapsed = useCallback(() => {
    setCollapsed((current) => {
      const next = !current;
      try {
        window.localStorage.setItem(STORAGE_KEY, String(next));
      } catch {
        // As above - the preference simply does not survive this session.
      }
      return next;
    });
  }, []);

  return { collapsed, toggleCollapsed };
}
