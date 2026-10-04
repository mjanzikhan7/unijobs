import { expect, test } from "./fixtures";

const LIGHT_BG = "rgb(246, 248, 252)";
const DARK_BG = "rgb(11, 15, 26)";
const DARK_SURFACE = "rgb(20, 26, 40)";

async function expectBodyBackground(page: import("@playwright/test").Page, colour: string) {
  await expect
    .poll(() => page.evaluate(() => getComputedStyle(document.body).backgroundColor))
    .toBe(colour);
}

test.describe("Theming and tokens", () => {
  test("paints the light palette from the tokens by default", async ({ page }) => {
    await page.goto("/login");
    await page.waitForSelector("h1");

    await expectBodyBackground(page, LIGHT_BG);
    await expect(page.locator("h1")).toHaveCSS("font-family", /Space Grotesk/);
    await expect(page.locator("body")).toHaveCSS("font-family", /Inter/);
  });

  test("a chosen dark theme survives a reload", async ({ page }) => {
    await page.goto("/login");
    await page.waitForSelector("h1");

    await page.evaluate(() => window.localStorage.setItem("theme", "dark"));
    await page.reload();
    await page.waitForSelector("h1");

    await expect(page.locator("html")).toHaveAttribute("data-theme", "dark");
    await expectBodyBackground(page, DARK_BG);
    await expect(page.locator("form")).toHaveCSS("background-color", DARK_SURFACE);
  });

  test("the toggle switches theme and says which way it goes", async ({ authedPage: page }) => {
    await page.goto("/");
    const toggle = page.getByRole("button", { name: /Switch to (dark|light) theme/ });
    await expect(toggle).toBeVisible();

    const before = await page.getAttribute("html", "data-theme");
    await toggle.click();

    await expect(page.locator("html")).not.toHaveAttribute("data-theme", before ?? "light");
    await expect(toggle).toHaveAccessibleName(
      before === "dark" ? "Switch to dark theme" : "Switch to light theme",
    );
  });

  test("controls meet the 44px touch-target floor", async ({ page }) => {
    await page.goto("/login");
    await page.waitForSelector("h1");

    for (const locator of [
      page.getByRole("button", { name: "Sign in" }),
      page.getByLabel("Username"),
    ]) {
      const box = await locator.boundingBox();
      expect(box?.height ?? 0).toBeGreaterThanOrEqual(44);
    }
  });

  test("no screen scrolls sideways at 390px", async ({ authedPage: page }) => {
    await page.setViewportSize({ width: 390, height: 844 });

    for (const path of ["/", "/saved", "/pipeline", "/institutions", "/profile"]) {
      await page.goto(path);
      await page.waitForLoadState("networkidle");

      const overflows = await page.evaluate(
        () => document.documentElement.scrollWidth > window.innerWidth,
      );
      expect(overflows, `${path} scrolls sideways at 390px`).toBe(false);
    }
  });

  test("the sign-in page names no working credentials", async ({ page }) => {
    await page.goto("/login");
    await page.waitForSelector("h1");

    const text = (await page.textContent("body")) ?? "";
    expect(text).not.toMatch(/changeme/i);
    expect(text).not.toMatch(/dev credentials/i);
  });
});
