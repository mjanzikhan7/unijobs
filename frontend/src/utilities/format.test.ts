import { describe, expect, it } from "vitest";

import { closingLabel, daysUntil, formatDate, formatTime, humanise, money, salaryRange, truncate } from "./format";
import { makeScreening } from "@/test-utils";

describe("money", () => {
  it.each([
    ["54700", "£54,700"],
    ["54700.00", "£54,700"],
    [38784, "£38,784"],
  ])("formats %s as %s", (input, expected) => {
    expect(money(input)).toBe(expected);
  });

  it.each([null, undefined, "", "not a number"])("renders %s as a dash", (input) => {
    expect(money(input)).toBe("—");
  });
});

describe("salaryRange", () => {
  it("renders a range", () => {
    expect(salaryRange(makeScreening())).toBe("£38,784 – £46,049");
  });

  it("renders a single figure once, not as a range of itself", () => {
    const screening = makeScreening({ salary_min: "36636.00", salary_max: "36636.00" });

    expect(salaryRange(screening)).toBe("£36,636");
  });

  it("renders a ceiling with no floor as 'Up to', never as a starting salary", () => {
    const screening = makeScreening({ salary_min: null, salary_max: "86500.00" });

    expect(salaryRange(screening)).toBe("Up to £86,500");
  });

  it("renders a floor with no ceiling as 'From'", () => {
    const screening = makeScreening({ salary_min: "9883.00", salary_max: null });

    expect(salaryRange(screening)).toBe("From £9,883");
  });

  it("renders an unparseable salary as a dash", () => {
    const screening = makeScreening({ salary_min: null, salary_max: null });

    expect(salaryRange(screening)).toBe("—");
  });

  it("renders a missing screening as a dash rather than throwing", () => {
    expect(salaryRange(null)).toBe("—");
  });
});

describe("formatDate", () => {
  it("formats an ISO date the way a UK advert would", () => {
    expect(formatDate("2026-09-30")).toBe("30 Sept 2026");
  });

  it.each([null, undefined, "", "nonsense"])("renders %s as a dash", (input) => {
    expect(formatDate(input)).toBe("—");
  });
});

describe("formatTime", () => {
  it("formats as a 24-hour clock, pinned to Europe/London regardless of the viewer's own zone", () => {
    expect(formatTime("2026-08-24T13:05:09Z")).toBe("14:05:09");
  });

  it("still applies the UK offset outside BST", () => {
    expect(formatTime("2026-01-15T13:05:09Z")).toBe("13:05:09");
  });

  it.each([null, undefined, "", "nonsense"])("renders %s as a dash", (input) => {
    expect(formatTime(input)).toBe("—");
  });
});

describe("daysUntil", () => {
  const today = new Date("2026-08-23T12:00:00Z");

  it.each([
    ["2026-08-23", 0],
    ["2026-08-24", 1],
    ["2026-08-30", 7],
    ["2026-08-22", -1],
  ])("counts %s as %i days", (date, expected) => {
    expect(daysUntil(date, today)).toBe(expected);
  });

  it("returns nothing when the advert gave no closing date", () => {
    expect(daysUntil(null, today)).toBeNull();
  });
});

describe("closingLabel", () => {
  const today = new Date("2026-08-23T12:00:00Z");

  it.each([
    ["2026-08-23", "Closes today"],
    ["2026-08-24", "Closes tomorrow"],
    ["2026-08-30", "Closes in 7 days"],
    ["2026-08-20", "Closed"],
    [null, "No closing date"],
  ])("describes %s as %s", (date, expected) => {
    expect(closingLabel(date, today)).toBe(expected);
  });
});

describe("humanise", () => {
  it.each([
    ["NOT_FOUND", "Not found"],
    ["B_RATED", "B rated"],
    ["FULL_TIME", "Full time"],
    ["ZERO_RESULTS", "Zero results"],
    ["ROBOTS_DISALLOWED", "Robots disallowed"],
  ])("renders %s as %s", (input, expected) => {
    expect(humanise(input)).toBe(expected);
  });

  it.each([
    ["OK", "OK"],
    ["JSON_LD", "JSON LD"],
    ["JSON_API", "JSON API"],
    ["RSS", "RSS"],
  ])("keeps the acronym in %s", (input, expected) => {
    expect(humanise(input)).toBe(expected);
  });
});

describe("truncate", () => {
  it("leaves a short string alone", () => {
    expect(truncate("Research Fellow", 40)).toBe("Research Fellow");
  });

  it("cuts a long string at a word boundary", () => {
    expect(truncate("Senior Research Software Engineer in Computational Biology", 30)).toBe(
      "Senior Research Software…",
    );
  });

  it("marks a truncated string so nobody mistakes it for the whole title", () => {
    expect(truncate("a".repeat(80), 20)).toMatch(/…$/);
  });
});
