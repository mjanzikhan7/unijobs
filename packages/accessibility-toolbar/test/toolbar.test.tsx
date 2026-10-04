import { act, fireEvent, render, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { createNoopStorageAdapter } from "../src/core/storage";
import { A11yProvider } from "../src/react/A11yProvider";
import { A11yToolbar } from "../src/react/A11yToolbar";

const html = document.documentElement;

function renderToolbar() {
  return render(
    <A11yProvider options={{ storage: createNoopStorageAdapter() }}>
      <div id="app">
        <main>
          <h1>Jobs</h1>
          <p>App content.</p>
        </main>
      </div>
      <A11yToolbar />
    </A11yProvider>,
  );
}

async function shadow(): Promise<ShadowRoot> {
  let root: ShadowRoot | null | undefined;
  await waitFor(() => {
    root = document.getElementById("unijobs-a11y-toolbar")?.shadowRoot;
    expect(root).toBeTruthy();
  });
  return root!;
}

async function openPanel(root: ShadowRoot): Promise<HTMLButtonElement> {
  const launcher = root.querySelector<HTMLButtonElement>("button.launcher")!;
  await act(async () => launcher.click());
  await waitFor(() => expect(root.querySelector("fieldset")).not.toBeNull());
  return launcher;
}

function section(root: ShadowRoot, title: string): HTMLFieldSetElement {
  const found = Array.from(root.querySelectorAll("fieldset")).find(
    (fieldset) => fieldset.querySelector("legend")?.textContent === title,
  );
  if (!found) throw new Error(`No section "${title}"`);
  return found;
}

function buttonIn(scope: ParentNode, name: string): HTMLButtonElement {
  const found = Array.from(scope.querySelectorAll("button")).find((button) => button.textContent?.trim() === name);
  if (!found) throw new Error(`No button "${name}"`);
  return found;
}

async function click(element: HTMLElement) {
  await act(async () => element.click());
}

describe("A11yToolbar", () => {
  afterEach(() => {
    vi.restoreAllMocks();
    for (const key of Object.keys(html.dataset)) delete html.dataset[key];
    html.removeAttribute("style");
  });

  it("mounts in an open shadow root whose host is never a tab stop", async () => {
    renderToolbar();
    const root = await shadow();

    expect(root.mode).toBe("open");
    expect(root.host.hasAttribute("tabindex")).toBe(false);
  });

  it("opens a non-modal panel with no overlay, and Escape closes it back to the launcher", async () => {
    renderToolbar();
    const root = await shadow();
    const launcher = await openPanel(root);

    const dialog = root.querySelector('[role="dialog"]')!;
    expect(launcher.getAttribute("aria-expanded")).toBe("true");
    expect(dialog.getAttribute("aria-modal")).toBe("false");
    expect(root.querySelector(".overlay")).toBeNull();
    await waitFor(() => expect(root.activeElement?.tagName).toBe("H2"));

    await act(async () => {
      fireEvent.keyDown(root.activeElement!, { key: "Escape" });
    });

    expect(root.querySelector('[role="dialog"]')).toBeNull();
    expect(root.activeElement).toBe(launcher);
  });

  it("toggles on Alt+0 by key position, including a Mac's Option+0 which types º", async () => {
    renderToolbar();
    const root = await shadow();

    await act(async () => {
      fireEvent.keyDown(document, { altKey: true, code: "Digit0", key: "º" });
    });
    await waitFor(() => expect(root.querySelector('[role="dialog"]')).not.toBeNull());

    await act(async () => {
      fireEvent.keyDown(document, { altKey: true, code: "Digit0", key: "º" });
    });
    expect(root.querySelector('[role="dialog"]')).toBeNull();
  });

  it("gives every control in the panel a tooltip describing what it does", async () => {
    renderToolbar();
    const root = await shadow();
    await openPanel(root);

    const controls = Array.from(root.querySelectorAll<HTMLElement>(".panel button, .panel input, .panel select"));
    expect(controls.length).toBeGreaterThan(20);
    for (const control of controls) {
      const ids = (control.getAttribute("aria-describedby") ?? "").split(" ").filter(Boolean);
      const tooltip = ids.map((id) => root.getElementById(id)).find((el) => el?.getAttribute("role") === "tooltip");
      expect(tooltip?.textContent?.trim(), `tooltip for "${control.textContent || control.id}"`).toBeTruthy();
    }
  });

  it("shows a tooltip on keyboard focus, and the first Escape dismisses it without closing the panel", async () => {
    const matches = Element.prototype.matches;
    vi.spyOn(Element.prototype, "matches").mockImplementation(function (this: Element, selector: string) {
      return selector === ":focus-visible" ? true : matches.call(this, selector);
    });
    renderToolbar();
    const root = await shadow();
    await openPanel(root);
    const choice = buttonIn(section(root, "Colour and contrast"), "Monochrome");
    const tooltip = root.getElementById(choice.getAttribute("aria-describedby")!)!;

    await act(async () => choice.focus());
    await waitFor(() => expect(tooltip.getAttribute("data-open")).toBe("true"));

    await act(async () => {
      fireEvent.keyDown(choice, { key: "Escape" });
    });

    expect(tooltip.getAttribute("data-open")).toBe("false");
    expect(root.querySelector('[role="dialog"]')).not.toBeNull();
  });

  it("Reset profile turns the profile off and gives back the settings from before it", async () => {
    renderToolbar();
    const root = await shadow();
    await openPanel(root);

    await click(buttonIn(section(root, "Text"), "Bigger"));
    expect(html.style.getPropertyValue("--a11y-font-scale")).toBe("1.1");

    const lowVision = buttonIn(section(root, "Profiles"), "Low vision");
    await click(lowVision);
    expect(html.dataset.a11yTheme).toBe("contrast-dark");
    expect(html.style.getPropertyValue("--a11y-font-scale")).toBe("1.5");
    expect(lowVision.getAttribute("aria-pressed")).toBe("true");

    const resetProfile = buttonIn(section(root, "Profiles"), "Reset profile");
    await click(resetProfile);

    expect(html.dataset.a11yTheme).toBeUndefined();
    expect(html.style.getPropertyValue("--a11y-font-scale")).toBe("1.1");
    expect(lowVision.getAttribute("aria-pressed")).toBe("false");
    expect(resetProfile.getAttribute("aria-disabled")).toBe("true");
  });

  it("choosing the active profile again turns it off", async () => {
    renderToolbar();
    const root = await shadow();
    await openPanel(root);
    const dyslexia = buttonIn(section(root, "Profiles"), "Dyslexia");

    await click(dyslexia);
    expect(html.dataset.a11yFont).toBe("dyslexic");

    await click(dyslexia);
    expect(html.dataset.a11yFont).toBeUndefined();
    expect(dyslexia.getAttribute("aria-pressed")).toBe("false");
  });

  it("a section's reset only undoes that section", async () => {
    renderToolbar();
    const root = await shadow();
    await openPanel(root);

    await click(buttonIn(section(root, "Colour and contrast"), "High contrast dark"));
    await click(buttonIn(section(root, "Text"), "Bigger"));
    await click(buttonIn(section(root, "Colour and contrast"), "Reset colours"));

    expect(html.dataset.a11yTheme).toBeUndefined();
    expect(html.dataset.a11yTextScale).toBe("true");
  });

  it("Reset all settings clears everything", async () => {
    renderToolbar();
    const root = await shadow();
    await openPanel(root);

    await click(buttonIn(section(root, "Profiles"), "Low vision"));
    await click(buttonIn(root, "Reset all settings"));

    expect(Object.keys(html.dataset).filter((key) => key.startsWith("a11y"))).toEqual([]);
  });

  it("changing settings never touches the host app's own DOM", async () => {
    renderToolbar();
    const root = await shadow();
    await openPanel(root);
    const before = document.getElementById("app")!.innerHTML;

    await click(buttonIn(section(root, "Profiles"), "Low vision"));
    await click(buttonIn(section(root, "Text"), "Bigger"));

    expect(document.getElementById("app")!.innerHTML).toBe(before);
  });
});
