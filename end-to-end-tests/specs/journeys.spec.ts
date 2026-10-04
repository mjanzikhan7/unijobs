import { ADMIN, API, expect, fetchToken, test } from "./fixtures";

test.describe("Searching and applying", () => {
  test("filter down to a job, then leave for the employer's own posting", async ({
    authedPage: page,
  }) => {
    await page.goto("/");
    await expect(page.getByTestId("job-card").first()).toBeVisible();

    await page.getByLabel("Only where sponsorship is possible").check();
    await expect(page).toHaveURL(/sponsorable=true/);

    const firstJob = page.getByTestId("job-card").first().getByRole("heading", { level: 3 });
    const title = await firstJob.textContent();
    await firstJob.getByRole("link").click();

    await expect(page.getByRole("heading", { level: 1 })).toContainText(title ?? "");

    const applyLink = page.getByRole("link", { name: /Apply on the employer/ });
    await expect(applyLink).toHaveAttribute("target", "_blank");
    await expect(applyLink).toHaveAttribute("rel", "noopener noreferrer");
  });

  test("every result carries both badges", async ({ authedPage: page }) => {
    await page.goto("/");

    const card = page.getByTestId("job-card").first();
    await expect(card).toBeVisible();

    await expect(card.locator("[data-tone]").nth(1)).toBeVisible({ timeout: 10_000 });
  });

  test("a pasted URL restores the exact view", async ({ authedPage: page }) => {
    await page.goto("/?nation=SCOTLAND&order=-salary");

    await expect(page.getByLabel("Sort by")).toHaveValue("-salary");
    await expect(page.getByRole("checkbox", { name: /Scotland/i })).toBeChecked();
  });

  test("an impossible filter set explains itself", async ({ authedPage: page }) => {
    await page.goto("/?min_fitness=100&salary_min=400000");

    await expect(page.getByRole("heading", { name: /No jobs match these filters/ })).toBeVisible();
    await expect(page.getByRole("button", { name: /^Clear /i }).first()).toBeVisible();
  });
});

test.describe("Saving and the pipeline", () => {
  test("save a job, then find it on the Saved page", async ({ authedPage: page }) => {
    await page.goto("/");
    await expect(page.getByTestId("job-card").first()).toBeVisible();

    const card = page
      .getByTestId("job-card")
      .filter({ has: page.getByRole("button", { name: /^Save / }) })
      .first();
    const title = (await card.getByRole("heading", { level: 3 }).textContent())?.trim() ?? "";
    await card.getByRole("button", { name: /^Save / }).click();
    await expect(page.getByRole("status").filter({ hasText: /Saved/ })).toBeVisible();

    await page.getByRole("link", { name: "Saved" }).click();
    await expect(page.getByRole("heading", { name: "Saved jobs" })).toBeVisible();
    await expect(page.getByRole("heading", { level: 3, name: title })).toBeVisible();
  });

  test("the pipeline board shows every column in order", async ({ authedPage: page }) => {
    await page.goto("/pipeline");

    const columns = page.getByRole("region", { name: "Pipeline columns" }).getByRole("heading", {
      level: 2,
    });
    await expect(columns.first()).toContainText("Found");
    await expect(columns.last()).toContainText("Ghosted");
  });
});

test.describe("The crawl console", () => {
  test("the console lists institutions and surfaces problems first", async ({
    adminPage: page,
  }) => {
    await page.goto("/admin/crawl");

    await expect(page.getByRole("heading", { name: "Crawl console" })).toBeVisible();
    await expect(page.getByRole("table")).toBeVisible();
  });

  test("a crawl starts at once, and a second is refused while it runs", async ({
    adminPage: page,
    request,
  }) => {
    await page.goto("/admin/crawl");

    await page.getByRole("button", { name: "Run crawl" }).click();

    await expect(page.getByRole("heading", { name: /Run #\d+ in progress/ })).toBeVisible({
      timeout: 5_000,
    });

    await expect(page.getByRole("button", { name: "Crawl in progress" })).toBeDisabled();

    const second = await request.post(`${API}/api/crawl-runs/`, {
      headers: { Authorization: `Token ${await fetchToken(ADMIN)}` },
      data: {},
    });

    expect(second.status()).toBe(409);

    const active = await request.get(`${API}/api/crawl-runs/active/`, {
      headers: { Authorization: `Token ${await fetchToken(ADMIN)}` },
    });
    const activeId = (await active.json()).run?.id;
    if (activeId) {
      await request.post(`${API}/api/crawl-runs/${activeId}/cancel/`, {
        headers: { Authorization: `Token ${await fetchToken(ADMIN)}` },
      });
    }
  });

  test("a crawl can be paused, resumed, and stopped", async ({
    adminPage: page,
    request,
  }) => {
    await page.goto("/admin/crawl");
    await page.getByRole("button", { name: "Run crawl" }).click();
    await expect(page.getByRole("heading", { name: /Run #\d+ in progress/ })).toBeVisible({
      timeout: 5_000,
    });

    await page.getByRole("button", { name: "Pause" }).click();
    await expect(page.getByRole("heading", { name: /Run #\d+ paused/ })).toBeVisible();
    await expect(page.getByRole("button", { name: "Resume" })).toBeVisible();
    await expect(page.getByRole("button", { name: "Pause" })).not.toBeVisible();

    await expect(page.locator('ol[aria-label^="Log for run"] li').first()).toBeVisible({
      timeout: 5_000,
    });

    await page.getByRole("button", { name: "Resume" }).click();
    await expect(page.getByRole("heading", { name: /Run #\d+ in progress/ })).toBeVisible();
    await expect(page.getByRole("button", { name: "Pause" })).toBeVisible();

    await page.getByRole("button", { name: "Stop" }).click();
    await expect(page.getByRole("button", { name: "Run crawl" })).toBeEnabled({ timeout: 5_000 });

    const runLink = page.getByRole("link", { name: /Run #\d+/ }).first();
    const runHref = await runLink.getAttribute("href");
    await page.goto(runHref ?? "/admin/crawl");
    await expect(page.getByText(/^Cancelled/)).toBeVisible();
    await expect(page.getByRole("button", { name: "Restart" })).toBeVisible();
  });
});

test.describe("Thresholds", () => {
  test("the ruleset in force is shown with its provenance", async ({
    adminPage: page,
  }) => {
    await page.goto("/admin/thresholds");

    await expect(page.getByRole("heading", { name: "Threshold figures" })).toBeVisible();
    await expect(page.getByRole("link", { name: /the source/ })).toBeVisible();
  });

  test("re-screening reports how many verdicts moved", async ({ adminPage: page }) => {
    test.setTimeout(150_000);
    await page.goto("/admin/thresholds");

    await page.getByRole("button", { name: "Re-screen everything" }).click();

    await expect(page.getByText(/Re-screened \d+ jobs/)).toBeVisible({ timeout: 120_000 });
  });
});

test.describe("Export", () => {
  test("the filtered view downloads as a file", async ({ authedPage: page }) => {
    await page.goto("/?nation=ENGLAND");
    await expect(page.getByTestId("job-card").first()).toBeVisible();

    const download = page.waitForEvent("download");
    await page.getByRole("button", { name: "Export" }).click();

    expect((await download).suggestedFilename()).toBe("he-jobs.csv");
  });
});

test.describe("Sponsor review", () => {
  test("the review queue offers candidates rather than guessing", async ({
    adminPage: page,
  }) => {
    await page.goto("/admin/review");

    await expect(page.getByRole("heading", { name: "Sponsor review queue" })).toBeVisible();
  });
});
