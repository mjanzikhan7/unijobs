import AxeBuilder from "@axe-core/playwright";
import type { Locator, Page } from "@playwright/test";

import { expect, test } from "./fixtures";

function computed(locator: Locator, property: string): Promise<string> {
  return locator.evaluate((el, name) => getComputedStyle(el).getPropertyValue(name), property);
}

async function fontSize(locator: Locator): Promise<number> {
  return parseFloat(await computed(locator, "font-size"));
}

async function openJobList(page: Page): Promise<Locator> {
  await page.goto("/");
  const title = page.getByTestId("job-card").first().getByRole("heading", { level: 3 });
  await expect(title).toBeVisible();
  return title;
}

async function openSettings(page: Page): Promise<Locator> {
  await page.getByRole("button", { name: "Accessibility settings" }).click();
  const panel = page.getByRole("dialog", { name: "Accessibility settings" });
  await expect(panel.getByRole("group", { name: "Profiles" })).toBeVisible();
  return panel;
}

function a11yAttributes(page: Page): Promise<string[]> {
  return page.evaluate(() => Object.keys(document.documentElement.dataset).filter((k) => k.startsWith("a11y")));
}

test.describe("Accessibility toolbar", () => {
  test("changes nothing on the page until a setting is used", async ({ authedPage: page }) => {
    await openJobList(page);
    await openSettings(page);

    expect(await a11yAttributes(page)).toEqual([]);
  });

  test("text size scales every rem-sized piece of text, not just body copy", async ({ authedPage: page }) => {
    const title = await openJobList(page);
    const navLink = page.getByRole("navigation").getByRole("link").first();
    const titleBefore = await fontSize(title);
    const navBefore = await fontSize(navLink);

    const panel = await openSettings(page);
    const bigger = panel.getByRole("button", { name: "Bigger" });
    for (let step = 0; step < 5; step += 1) await bigger.click();

    await expect.poll(() => fontSize(title)).toBeCloseTo(titleBefore * 1.5, 0);
    await expect.poll(() => fontSize(navLink)).toBeCloseTo(navBefore * 1.5, 0);
  });

  test("high contrast replaces the page's own colours", async ({ authedPage: page }) => {
    const title = await openJobList(page);
    const card = page.getByTestId("job-card").first();
    const panel = await openSettings(page);

    await panel.getByRole("button", { name: "High contrast dark" }).click();

    await expect.poll(() => computed(card, "background-color")).toBe("rgb(0, 0, 0)");
    await expect.poll(() => computed(title.getByRole("link"), "color")).toBe("rgb(255, 233, 77)");
  });

  test("the dyslexia font is bundled, loads and is applied", async ({ authedPage: page }) => {
    const title = await openJobList(page);
    const panel = await openSettings(page);

    await panel.getByRole("group", { name: "Font" }).getByRole("button", { name: "Dyslexia" }).click();

    await expect.poll(() => computed(title, "font-family")).toContain("UniJobs A11y Dyslexic");
    const loaded = await page.evaluate(async () => (await document.fonts.load('16px "UniJobs A11y Dyslexic"')).length);
    expect(loaded).toBeGreaterThan(0);
  });

  test("Reset text puts the app's own line height back exactly", async ({ authedPage: page }) => {
    const title = await openJobList(page);
    const before = await computed(title, "line-height");
    const panel = await openSettings(page);

    await panel.getByRole("slider", { name: "Line height" }).fill("2.2");
    await expect.poll(() => computed(title, "line-height")).not.toBe(before);

    await panel.getByRole("button", { name: "Reset text" }).click();
    await expect.poll(() => computed(title, "line-height")).toBe(before);
  });

  test("a profile toggles off, and Reset profile gives back the earlier settings", async ({ authedPage: page }) => {
    const title = await openJobList(page);
    const base = await fontSize(title);
    const panel = await openSettings(page);

    await panel.getByRole("button", { name: "Bigger" }).click();
    await expect.poll(() => fontSize(title)).toBeCloseTo(base * 1.1, 0);

    await panel.getByRole("group", { name: "Profiles" }).getByRole("button", { name: "Low vision" }).click();
    await expect.poll(() => fontSize(title)).toBeCloseTo(base * 1.5, 0);
    await expect.poll(() => a11yAttributes(page)).toContain("a11yTheme");

    await panel.getByRole("button", { name: "Reset profile" }).click();
    await expect.poll(() => fontSize(title)).toBeCloseTo(base * 1.1, 0);
    expect(await a11yAttributes(page)).not.toContain("a11yTheme");
  });

  test("tooltips explain a control, and the first Escape dismisses only the tooltip", async ({ authedPage: page }) => {
    await openJobList(page);
    const panel = await openSettings(page);

    await panel.getByRole("button", { name: "High contrast dark" }).hover();
    const tooltip = page.getByRole("tooltip", { name: /White text on black/ });
    await expect(tooltip).toBeVisible();

    await page.keyboard.press("Escape");
    await expect(tooltip).toBeHidden();
    await expect(panel).toBeVisible();
  });

  test("read aloud reads the page with highlighting, and Stop ends it", async ({ authedPage: page }) => {
    await page.addInitScript(() => {
      const spoken: string[] = [];
      Object.defineProperty(window, "__spoken", { value: spoken });
      class RecordingUtterance {
        text: string;
        rate = 1;
        pitch = 1;
        lang = "";
        voice: SpeechSynthesisVoice | null = null;
        onstart: ((event: Event) => void) | null = null;
        onend: ((event: Event) => void) | null = null;
        onerror: ((event: Event) => void) | null = null;
        onboundary: ((event: Event) => void) | null = null;
        constructor(text: string) {
          this.text = text;
        }
      }
      const synth = {
        getVoices: () => [],
        speak(utterance: RecordingUtterance) {
          spoken.push(utterance.text);
          setTimeout(() => utterance.onstart?.(new Event("start")), 10);
        },
        cancel() {},
        pause() {},
        resume() {},
        addEventListener() {},
        removeEventListener() {},
      };
      Object.defineProperty(window, "speechSynthesis", { value: synth, configurable: true });
      Object.defineProperty(window, "SpeechSynthesisUtterance", { value: RecordingUtterance, configurable: true });
    });

    await openJobList(page);
    const panel = await openSettings(page);
    await panel.getByRole("button", { name: "Read page" }).click();

    await expect
      .poll(() => page.evaluate(() => (window as unknown as { __spoken: string[] }).__spoken.length))
      .toBeGreaterThan(0);
    await expect.poll(() => page.evaluate(() => CSS.highlights.has("unijobs-a11y-reading"))).toBe(true);

    await page.keyboard.press("Escape");
    const player = page.getByRole("region", { name: "Read aloud controls" });
    await expect(player).toBeVisible();

    await player.getByRole("button", { name: "Stop" }).click();
    await expect(player).toBeHidden();
    expect(await page.evaluate(() => CSS.highlights.has("unijobs-a11y-reading"))).toBe(false);
  });

  test("the open panel has no serious or critical axe violations", async ({ authedPage: page }) => {
    await openJobList(page);
    await openSettings(page);

    const results = await new AxeBuilder({ page })
      .include("#unijobs-a11y-toolbar")
      .withTags(["wcag2a", "wcag2aa", "wcag21a", "wcag21aa", "wcag22aa"])
      .analyze();
    const serious = results.violations.filter((v) => v.impact === "serious" || v.impact === "critical");

    expect(serious.map((v) => `${v.id}: ${v.nodes[0]?.html ?? ""}`)).toEqual([]);
  });
});
