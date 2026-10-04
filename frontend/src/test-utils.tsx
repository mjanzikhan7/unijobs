import type { ReactElement, ReactNode } from "react";
import { Provider } from "react-redux";
import { MemoryRouter } from "react-router-dom";
import { render } from "@testing-library/react";
import type { RenderOptions, RenderResult } from "@testing-library/react";
import { vi } from "vitest";
import { A11yProvider } from "@unijobs/a11y/react";
import { createNoopStorageAdapter } from "@unijobs/a11y/core";

import { urlOf } from "@/models/api/client";
import type { Job, JobDetail, Paginated, Screening } from "@/models/api/types";
import type { QueryKey } from "@/store/queries/queryKey";
import { queryDataSet, selectQuery } from "@/store/queries/slice";
import { createAppStore } from "@/store/store";
import type { AppStore } from "@/store/store";

export function createTestStore(): AppStore {
  return createAppStore({ retry: false, gcTime: 0, staleTime: 0 });
}

export function storeWrapper(store: AppStore = createTestStore()) {
  return function Wrapper({ children }: { children: ReactNode }) {
    return <Provider store={store}>{children}</Provider>;
  };
}

export function seedQuery(store: AppStore, key: QueryKey, data: unknown = {}): void {
  store.dispatch(queryDataSet({ key, data }));
}

export function isInvalidated(store: AppStore, key: QueryKey): boolean {
  return selectQuery(store.getState(), key)?.isInvalidated ?? false;
}

interface Options extends Omit<RenderOptions, "wrapper"> {
  route?: string;
  store?: AppStore;
}

export function renderWithProviders(ui: ReactElement, options: Options = {}): RenderResult {
  const store = options.store ?? createTestStore();
  const route = options.route ?? "/";

  function Wrapper({ children }: { children: ReactNode }) {
    return (
      <A11yProvider options={{ storage: createNoopStorageAdapter() }}>
        <Provider store={store}>
          <MemoryRouter initialEntries={[route]}>{children}</MemoryRouter>
        </Provider>
      </A11yProvider>
    );
  }

  return render(ui, { wrapper: Wrapper, ...options });
}

export function makeScreening(overrides: Partial<Screening> = {}): Screening {
  return {
    sponsor_verdict: "CONFIRMED",
    sponsor_matched_name: "The University of Test",
    sponsor_confidence: 1,
    advert_excludes_sponsorship: false,
    advert_exclusion_phrase: "",
    salary_min: "38784.00",
    salary_max: "46049.00",
    salary_currency: "GBP",
    salary_period: "ANNUAL",
    salary_confidence: "PARSED",
    threshold_verdict: "PAY_CUT",
    threshold_explanation: "Screened on the bottom of the range.",
    screened_on: "38784.00",
    general_threshold_met: false,
    going_rate_met: false,
    going_rate_key: "soc_2134_going_rate",
    ruleset_version: 1,
    screened_at: "2026-08-23T09:00:00Z",
    ...overrides,
  };
}

export function makeJob(overrides: Partial<Job> = {}): Job {
  return {
    id: 1,
    title: "Research Software Engineer",
    institution_name: "University of Test",
    institution_slug: "university-of-test",
    nation: "ENGLAND",
    department: "Department of Computer Science",
    city: "Bath",
    location_raw: "Bath, Somerset",
    salary_raw: "£38,784 to £46,049 per annum",
    grade_raw: "Grade 7",
    contract_type: "PERMANENT",
    hours: "FULL_TIME",
    workplace: "HYBRID",
    posted_date: "2026-08-20",
    closing_date: "2026-09-30",
    status: "OPEN",
    source: "PORTAL",
    source_url: "https://jobs.test.ac.uk/vacancy/1",
    first_seen_at: "2026-08-20T09:00:00Z",
    last_seen_at: "2026-08-23T06:00:00Z",
    screening: makeScreening(),
    is_saved: false,
    fitness_score: 65,
    fitness_reasons: [],
    ...overrides,
  };
}

export function makeJobDetail(overrides: Partial<JobDetail> = {}): JobDetail {
  return {
    ...makeJob(),
    apply_url: "https://jobs.test.ac.uk/vacancy/1/apply",
    description_html: "<p>We are seeking a Research Software Engineer.</p>",
    description_text: "We are seeking a Research Software Engineer.",
    reference: "CC12345",
    revisions: [],
    last_crawl: null,
    application_id: null,
    application_status: null,
    ...overrides,
  } as JobDetail;
}

export function paginate<T>(results: T[]): Paginated<T> {
  return {
    count: results.length,
    total_pages: 1,
    page: 1,
    page_size: 25,
    next: null,
    previous: null,
    results,
  };
}

export function stubFetch(routes: Record<string, unknown>): void {
  vi.spyOn(globalThis, "fetch").mockClear().mockImplementation((input: RequestInfo | URL) => {
    const url = urlOf(input);
    const match = Object.keys(routes).find((fragment) => url.includes(fragment));
    if (match === undefined) {
      throw new Error(`Unstubbed request to ${url}. Registered: ${Object.keys(routes).join(", ")}`);
    }
    return Promise.resolve(
      new Response(JSON.stringify(routes[match]), {
        status: 200,
        headers: { "Content-Type": "application/json" },
      }),
    );
  });
}
