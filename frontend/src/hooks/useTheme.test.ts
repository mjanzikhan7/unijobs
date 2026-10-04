import { ThemeProvider } from "@mui/material/styles";
import { act, renderHook } from "@testing-library/react";
import { createElement } from "react";
import type { ReactNode } from "react";
import { afterEach, beforeEach, describe, expect, it } from "vitest";

import { muiTheme } from "@/styles/muiTheme";

import { useTheme } from "./useTheme";

function wrapper({ children }: { children: ReactNode }) {
  return createElement(
    ThemeProvider,
    { theme: muiTheme, defaultMode: "system", modeStorageKey: "theme", noSsr: true },
    children,
  );
}

function stubSystemPrefersDark(prefersDark: boolean): void {
  window.matchMedia = ((query: string) => ({
    matches: query === "(prefers-color-scheme: dark)" && prefersDark,
    media: query,
    onchange: null,
    addListener: () => undefined,
    removeListener: () => undefined,
    addEventListener: () => undefined,
    removeEventListener: () => undefined,
    dispatchEvent: () => false,
  }));
}

describe("useTheme", () => {
  beforeEach(() => {
    window.localStorage.clear();
    delete document.documentElement.dataset.theme;
    stubSystemPrefersDark(false);
  });

  afterEach(() => {
    window.localStorage.clear();
    delete document.documentElement.dataset.theme;
  });

  it("follows the system preference when nothing has been chosen", () => {
    stubSystemPrefersDark(true);

    const { result } = renderHook(() => useTheme(), { wrapper });

    expect(result.current.theme).toBe("dark");
  });

  it("defaults to light when the system has no preference for dark", () => {
    const { result } = renderHook(() => useTheme(), { wrapper });

    expect(result.current.theme).toBe("light");
  });

  it("a stored choice overrides the system preference", () => {
    stubSystemPrefersDark(true);
    window.localStorage.setItem("theme", "light");

    const { result } = renderHook(() => useTheme(), { wrapper });

    expect(result.current.theme).toBe("light");
  });

  it("toggling flips the theme", () => {
    const { result } = renderHook(() => useTheme(), { wrapper });

    act(() => result.current.toggleTheme());

    expect(result.current.theme).toBe("dark");
  });

  it("toggling updates the root element's data-theme attribute", () => {
    const { result } = renderHook(() => useTheme(), { wrapper });

    act(() => result.current.toggleTheme());

    expect(document.documentElement.dataset.theme).toBe("dark");
  });

  it("toggling persists the choice where the next visit will find it", () => {
    const { result } = renderHook(() => useTheme(), { wrapper });

    act(() => result.current.toggleTheme());

    expect(window.localStorage.getItem("theme")).toBe("dark");
  });

  it("toggling twice returns to where it started", () => {
    const { result } = renderHook(() => useTheme(), { wrapper });

    act(() => result.current.toggleTheme());
    act(() => result.current.toggleTheme());

    expect(result.current.theme).toBe("light");
    expect(document.documentElement.dataset.theme).toBe("light");
  });
});
