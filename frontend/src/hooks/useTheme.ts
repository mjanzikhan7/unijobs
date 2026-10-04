import { useColorScheme } from "@mui/material/styles";
import { useCallback } from "react";

export type Theme = "light" | "dark";

export function useTheme(): { theme: Theme; toggleTheme: () => void } {
  const { mode, systemMode, setMode } = useColorScheme();

  const resolved: Theme =
    mode === "dark" || mode === "light"
      ? mode
      : (systemMode ?? (document.documentElement.dataset.theme === "dark" ? "dark" : "light"));

  const toggleTheme = useCallback(() => {
    setMode(resolved === "dark" ? "light" : "dark");
  }, [resolved, setMode]);

  return { theme: resolved, toggleTheme };
}
