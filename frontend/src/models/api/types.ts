import type { components } from "./schema";

type Schemas = components["schemas"];

export type Job = Schemas["JobList"];
export type JobDetail = Schemas["JobDetail"];
export type Screening = Schemas["Screening"];
export type Institution = Schemas["Institution"];
export type SponsorMatch = Schemas["SponsorMatch"];
export type CrawlRun = Schemas["CrawlRun"];
export type CrawlRunDetail = Schemas["CrawlRunDetail"];
export type CrawlRunInstitution = Schemas["CrawlRunInstitution"];
export type CrawlLogEntry = Schemas["CrawlLogEntry"];
export type CrawlRunStatus = Schemas["CrawlRunStatus"];
export type RestartScope = "all" | "failures";
export type SavedJob = Schemas["SavedJob"];
export type Application = Schemas["Application"];
export type SavedSearch = Schemas["SavedSearch"];
export type Ruleset = Schemas["Ruleset"];
export type RulesetFigure = Schemas["RulesetFigure"];
type ProfileTermField = "skills" | "domains" | "seniority" | "projects" | "education";

export type CandidateProfile = Omit<Schemas["CandidateProfile"], ProfileTermField> &
  Record<ProfileTermField, string[]>;

export type SponsorVerdict = Schemas["SponsorVerdict"];
export type Discipline = Schemas["Discipline"];
export type ContractType = Schemas["ContractType"];
export type Hours = Schemas["Hours"];
export type Workplace = Schemas["Workplace"];
export type ThresholdVerdict = Schemas["ThresholdVerdict"];
export type SalaryConfidence = Schemas["SalaryConfidence"];
export type CrawlOutcome = Schemas["CrawlOutcome"];
export type ExtractionStrategy = Schemas["ExtractionStrategy"];
export type Platform = Schemas["Platform"];
export type JobStatus = Schemas["JobStatus"];
export type ApplicationStatus = Schemas["ApplicationStatus"];
export type Nation = Schemas["Nation"];
export type InstitutionType = Schemas["InstitutionType"];

export interface Paginated<T> {
  count: number;
  total_pages: number;
  page: number;
  page_size: number;
  next: string | null;
  previous: string | null;
  results: T[];
}

export interface JobRevision {
  id: number;
  job: number;
  job_title: string;
  institution_name: string;
  field: string;
  value_before: string;
  value_after: string;
  changed_at: string;
}

export interface RevisionEntry {
  field: string;
  before: string;
  after: string;
  changed_at: string;
}

export interface LastCrawl {
  run_id: number;
  outcome: CrawlOutcome;
  adapter: string;
  strategy: ExtractionStrategy;
  vacancies_found: number;
  previous_vacancies_found: number | null;
  dropped_to_zero: boolean;
  fallback_fired: boolean;
  error_class: string;
  error_detail: string;
  started_at: string;
  duration_ms: number;
}

export interface RegisterCandidate {
  organisation_name: string;
  town_city: string;
  type_rating: string;
  routes: string[];
  similarity: number;
}

export interface FacetValue {
  value: string;
  count: number;
}

export interface FacetResponse {
  total: number;
  facets: Record<string, FacetValue[]>;
}

export interface RunDiff {
  run: CrawlRun;
  new: Job[];
  changed: JobRevision[];
  disappeared: Job[];
}

export interface FitnessReason {
  criterion: string;
  weight: number;
  fraction: number;
  matched: string[];
  missing: string[];
  note: string;
}

export interface ApiErrorBody {
  detail: string;
  code: string;
  errors?: Record<string, string[]>;
  extra?: Record<string, unknown>;
}

export function fitnessReasons(
  job: { fitness_reasons?: unknown } | null | undefined,
): FitnessReason[] {
  return Array.isArray(job?.fitness_reasons) ? (job.fitness_reasons as FitnessReason[]) : [];
}

export function savedTags(saved: Pick<SavedJob, "tags"> | null | undefined): string[] {
  return Array.isArray(saved?.tags) ? saved.tags.map(String) : [];
}

export function sponsorCandidates(
  match: Pick<SponsorMatch, "candidates"> | null | undefined,
): RegisterCandidate[] {
  return Array.isArray(match?.candidates) ? (match.candidates as RegisterCandidate[]) : [];
}

export function jobRevisions(detail: JobDetail | null | undefined): RevisionEntry[] {
  return Array.isArray(detail?.revisions) ? (detail.revisions as unknown as RevisionEntry[]) : [];
}

export function lastCrawl(institution: Institution | null | undefined): LastCrawl | null {
  const last = institution?.last_crawl;
  return last && typeof last === "object" ? (last as unknown as LastCrawl) : null;
}
