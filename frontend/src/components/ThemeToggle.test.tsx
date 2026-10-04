import { ThemeProvider } from "@mui/material/styles";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, describe, expect, it } from "vitest";

import { muiTheme } from "@/styles/muiTheme";

import { ThemeToggle } from "./ThemeToggle";

function renderToggle() {
  return render(
    <ThemeProvider theme={muiTheme} defaultMode="system" modeStorageKey="theme" noSsr>
      <ThemeToggle />
    </ThemeProvider>,
  );
}

describe("ThemeToggle", () => {
  beforeEach(() => {
    window.localStorage.clear();
    delete document.documentElement.dataset.theme;
    window.matchMedia = ((query: string) => ({
      matches: false,
      media: query,
      onchange: null,
      addListener: () => undefined,
      removeListener: () => undefined,
      addEventListener: () => undefined,
      removeEventListener: () => undefined,
      dispatchEvent: () => false,
    }));
  });

  afterEach(() => {
    window.localStorage.clear();
    delete document.documentElement.dataset.theme;
  });

  it("offers to switch to dark theme when currently light", () => {
    renderToggle();

    expect(screen.getByRole("button", { name: "Switch to dark theme" })).toBeInTheDocument();
  });

  it("switches to dark on click, and then offers to switch back to light", async () => {
    renderToggle();

    await userEvent.click(screen.getByRole("button", { name: "Switch to dark theme" }));

    expect(screen.getByRole("button", { name: "Switch to light theme" })).toBeInTheDocument();
    expect(document.documentElement.dataset.theme).toBe("dark");
  });

  it("reports its state to assistive technology", async () => {
    renderToggle();

    const button = screen.getByRole("button");
    expect(button).toHaveAttribute("aria-pressed", "false");

    await userEvent.click(button);

    expect(button).toHaveAttribute("aria-pressed", "true");
  });
});
