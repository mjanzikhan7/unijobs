import { describe, expect, it } from "vitest";

import type { Institution, LastCrawl } from "@/models/api/types";
import {
  activeFilterCount,
  attentionRank,
  compareByAttention,
  compareByRanking,
  filtersToParams,
  mostRestrictiveFilter,
  parseFilters,
  toQueryParams,
} from "./filters";
import type { JobFilters } from "./filters";

function institution(overrides: Partial<Institution> = {}): Institution {
  return {
    id: 1,
    slug: "test",
    name: "Test",
    nation: "ENGLAND",
    city: "Testington",
    institution_type: "UNIVERSITY",
    ranking: null,
    website: "https://test.ac.uk",
    careers_url: "https://test.ac.uk/jobs",
    platform: "STONEFISH",
    adapter_override: "",
    effective_platform: "STONEFISH",
    crawl_enabled: true,
    notes: "",
    description: "",
    logo_url: null,
    banner_url: null,
    sponsor_match: { method: "NONE", confidence: 0, candidates: [], resolved_at: null },
    last_crawl: null,
    open_jobs: 0,
    ...overrides,
  };
}

function lastCrawlAt(overrides: Partial<LastCrawl> = {}): Record<string, unknown> {
  return {
    run_id: 1,
    outcome: "OK",
    adapter: "stonefish",
    strategy: "HTML",
    vacancies_found: 10,
    previous_vacancies_found: 10,
    dropped_to_zero: false,
    fallback_fired: false,
    error_class: "",
    error_detail: "",
    started_at: "2026-09-01T09:00:00Z",
    duration_ms: 1200,
    ...overrides,
  };
}

describe("parseFilters", () => {
  it("reads a single-value filter", () => {
    const filters = parseFilters(new URLSearchParams("?q=research+software"));

    expect(filters.single.q).toBe("research software");
  });

  it("reads repeated values into an array", () => {
    const filters = parseFilters(new URLSearchParams("?nation=ENGLAND&nation=SCOTLAND"));

    expect(filters.multi.nation).toEqual(["ENGLAND", "SCOTLAND"]);
  });

  it("ignores parameters it does not know", () => {
    const filters = parseFilters(new URLSearchParams("?utm_source=email&q=x"));

    expect(Object.keys(filters.single)).toEqual(["q"]);
  });

  it("drops empty values rather than filtering on nothing", () => {
    const filters = parseFilters(new URLSearchParams("?q=&nation="));

    expect(filters).toEqual({ multi: {}, single: {} });
  });
});

describe("round-tripping", () => {
  const cases: Array<[string, string]> = [
    ["?q=engineer", "q=engineer"],
    ["?nation=ENGLAND&nation=SCOTLAND", "nation=ENGLAND&nation=SCOTLAND"],
    ["?sponsorable=true&min_fitness=70", "sponsorable=true&min_fitness=70"],
    [
      "?institution=university-of-bath&threshold_verdict=TARGET_BAND&order=-salary",
      "institution=university-of-bath&threshold_verdict=TARGET_BAND&order=-salary",
    ],
  ];

  const entries = (params: URLSearchParams) => [...params.entries()].sort();

  it.each(cases)("a pasted URL %s restores the same filters", (input, expected) => {
    const restored = filtersToParams(parseFilters(new URLSearchParams(input)));

    expect(entries(restored)).toEqual(entries(new URLSearchParams(expected)));
  });

  it("writes a canonical order, so the same view always produces the same query string", () => {
    const oneWay = filtersToParams(parseFilters(new URLSearchParams("?min_fitness=70&q=x")));
    const other = filtersToParams(parseFilters(new URLSearchParams("?q=x&min_fitness=70")));

    expect(oneWay.toString()).toBe(other.toString());
  });

  it("survives a second round trip unchanged", () => {
    const once = filtersToParams(parseFilters(new URLSearchParams("?nation=WALES&q=lecturer")));
    const twice = filtersToParams(parseFilters(once));

    expect(twice.toString()).toBe(once.toString());
  });
});

describe("activeFilterCount", () => {
  it("counts nothing on the default view", () => {
    expect(activeFilterCount({ multi: {}, single: {} })).toBe(0);
  });

  it("does not count sorting or paging as filters", () => {
    const filters: JobFilters = { multi: {}, single: { order: "-salary", page: "3" } };

    expect(activeFilterCount(filters)).toBe(0);
  });

  it("counts a multi-value facet once, however many values it holds", () => {
    const filters: JobFilters = { multi: { nation: ["ENGLAND", "WALES"] }, single: {} };

    expect(activeFilterCount(filters)).toBe(1);
  });

  it("counts single and multi filters together", () => {
    const filters: JobFilters = { multi: { nation: ["ENGLAND"] }, single: { q: "engineer" } };

    expect(activeFilterCount(filters)).toBe(2);
  });
});

describe("mostRestrictiveFilter", () => {
  it("names the search term above everything else", () => {
    const filters: JobFilters = { multi: { nation: ["ENGLAND"] }, single: { q: "engineer" } };

    expect(mostRestrictiveFilter(filters)).toBe("q");
  });

  it("prefers a fitness floor to a nation", () => {
    const filters: JobFilters = { multi: { nation: ["ENGLAND"] }, single: { min_fitness: "90" } };

    expect(mostRestrictiveFilter(filters)).toBe("min_fitness");
  });

  it("falls back to whatever is set", () => {
    const filters: JobFilters = { multi: { hours: ["PART_TIME"] }, single: {} };

    expect(mostRestrictiveFilter(filters)).toBe("hours");
  });

  it("names nothing when nothing is filtered", () => {
    expect(mostRestrictiveFilter({ multi: {}, single: {} })).toBeNull();
  });
});

describe("toQueryParams", () => {
  it("flattens both kinds of filter into one object", () => {
    const filters: JobFilters = {
      multi: { nation: ["ENGLAND"] },
      single: { q: "engineer" },
    };

    expect(toQueryParams(filters)).toEqual({ nation: ["ENGLAND"], q: "engineer" });
  });
});

describe("attentionRank", () => {
  it("puts a never-crawled institution ahead of a healthy one", () => {
    expect(attentionRank(institution({ last_crawl: null }))).toBe(1);
  });

  it("puts a drop to zero at the front", () => {
    const last = lastCrawlAt({ dropped_to_zero: true });
    expect(attentionRank(institution({ last_crawl: last }))).toBe(0);
  });

  it("puts a non-OK outcome at the front, even without a drop to zero", () => {
    const last = lastCrawlAt({ outcome: "BLOCKED" });
    expect(attentionRank(institution({ last_crawl: last }))).toBe(0);
  });

  it("ranks a browser fallback above a clean run, but below anything broken", () => {
    const last = lastCrawlAt({ fallback_fired: true });
    expect(attentionRank(institution({ last_crawl: last }))).toBe(2);
  });

  it("ranks a clean run last", () => {
    const last = lastCrawlAt({});
    expect(attentionRank(institution({ last_crawl: last }))).toBe(3);
  });
});

describe("compareByRanking", () => {
  it("sorts by league-table ranking", () => {
    const first = institution({ name: "A", ranking: 5 });
    const second = institution({ name: "B", ranking: 2 });

    expect(compareByRanking(first, second)).toBeGreaterThan(0);
  });

  it("sorts an unranked institution after every ranked one", () => {
    const ranked = institution({ name: "A", ranking: 999 });
    const unranked = institution({ name: "B", ranking: null });

    expect(compareByRanking(ranked, unranked)).toBeLessThan(0);
  });

  it("breaks a ranking tie alphabetically", () => {
    const first = institution({ name: "Zebra", ranking: 10 });
    const second = institution({ name: "Aardvark", ranking: 10 });

    expect(compareByRanking(first, second)).toBeGreaterThan(0);
  });
});

describe("compareByAttention", () => {
  it("sorts a dropped-to-zero institution ahead of a clean run", () => {
    const alarming = institution({ name: "A", last_crawl: lastCrawlAt({ dropped_to_zero: true }) });
    const clean = institution({ name: "B", last_crawl: lastCrawlAt({}) });

    expect(compareByAttention(alarming, clean)).toBeLessThan(0);
  });

  it("breaks an attention-rank tie alphabetically", () => {
    const first = institution({ name: "Zebra", last_crawl: lastCrawlAt({}) });
    const second = institution({ name: "Aardvark", last_crawl: lastCrawlAt({}) });

    expect(compareByAttention(first, second)).toBeGreaterThan(0);
  });
});
