import AxeBuilder from "@axe-core/playwright";

import { expect, test } from "./fixtures";

const IMPACTS = new Set(["critical", "serious"]);

async function scan(page: import("@playwright/test").Page) {
  const results = await new AxeBuilder({ page })
    .withTags(["wcag2a", "wcag2aa", "wcag21a", "wcag21aa", "wcag22aa"])
    .analyze();

  return results.violations.filter((violation) => IMPACTS.has(violation.impact ?? ""));
}

function describe(violations: Awaited<ReturnType<typeof scan>>): string {
  return violations
    .map((violation) => `${violation.id} (${violation.impact}): ${violation.nodes[0]?.html ?? ""}`)
    .join("\n");
}

test.describe("Accessibility", () => {
  test("the job list has no serious violations", async ({ authedPage: page }) => {
    await page.goto("/");
    await expect(page.getByTestId("job-card").first()).toBeVisible();

    const violations = await scan(page);

    expect(describe(violations)).toBe("");
  });

  test("the job detail has no serious violations", async ({ authedPage: page }) => {
    await page.goto("/");
    await page.getByRole("heading", { level: 3 }).first().getByRole("link").click();
    await expect(page.getByRole("heading", { level: 1 })).toBeVisible();

    const violations = await scan(page);

    expect(describe(violations)).toBe("");
  });

  test("the crawl console has no serious violations", async ({ adminPage: page }) => {
    await page.goto("/admin/crawl");
    await expect(page.getByRole("table")).toBeVisible();

    const violations = await scan(page);

    expect(describe(violations)).toBe("");
  });

  test("the pipeline board has no serious violations", async ({ authedPage: page }) => {
    await page.goto("/pipeline");
    await expect(page.getByRole("heading", { name: "Pipeline" })).toBeVisible();

    const violations = await scan(page);

    expect(describe(violations)).toBe("");
  });

  test("every screen offers a skip link", async ({ authedPage: page }) => {
    await page.goto("/");
    await expect(page.getByRole("link", { name: "Skip to content" })).toBeAttached();

    await page.keyboard.press("Tab");

    await expect(page.getByRole("link", { name: "Skip to content" })).toBeFocused();
  });

  test("the crawl console is one click from the job list", async ({ adminPage: page }) => {
    await page.goto("/");

    await page.getByRole("link", { name: /Crawl console/ }).click();

    await expect(page.getByRole("heading", { name: "Crawl console" })).toBeVisible();
  });
});

const PUBLIC_SCREENS: [string, string][] = [
  ["/login", "Sign in"],
  ["/register", "Create an account"],
  ["/forgot-password", "Reset your password"],
  ["/accessibility", "Accessibility statement for UniJobs"],
  ["/privacy", "Privacy notice for UniJobs"],
];

const CANDIDATE_SCREENS: [string, string][] = [
  ["/institutions", "Institutions"],
  ["/saved", "Saved jobs"],
  ["/profile", "Account settings"],
  ["/profile/cv", "CV & job matching"],
];

const ADMIN_SCREENS: [string, string][] = [
  ["/admin/review", "Sponsor review queue"],
  ["/admin/thresholds", "Threshold figures"],
  ["/admin/users", "Users"],
  ["/admin/jobs", "Manage jobs"],
  ["/admin/institutions", "Manage institutions"],
  ["/admin/insights", "Candidate activity"],
];

test.describe("Accessibility on every screen", () => {
  for (const [path, heading] of PUBLIC_SCREENS) {
    test(`${path} has no serious violations`, async ({ page }) => {
      await page.goto(path);
      await expect(page.getByRole("heading", { level: 1, name: heading })).toBeVisible();

      expect(describe(await scan(page))).toBe("");
    });
  }

  for (const [path, heading] of CANDIDATE_SCREENS) {
    test(`${path} has no serious violations`, async ({ authedPage: page }) => {
      await page.goto(path);
      await expect(page.getByRole("heading", { level: 1, name: heading })).toBeVisible();

      expect(describe(await scan(page))).toBe("");
    });
  }

  for (const [path, heading] of ADMIN_SCREENS) {
    test(`${path} has no serious violations`, async ({ adminPage: page }) => {
      await page.goto(path);
      await expect(page.getByRole("heading", { level: 1, name: heading })).toBeVisible();

      expect(describe(await scan(page))).toBe("");
    });
  }
});
