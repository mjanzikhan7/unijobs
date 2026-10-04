import type { Discipline, Screening, SponsorVerdict, ThresholdVerdict } from "@/models/api/types";

const GBP = new Intl.NumberFormat("en-GB", {
  style: "currency",
  currency: "GBP",
  maximumFractionDigits: 0,
});

const LONG_DATE = new Intl.DateTimeFormat("en-GB", {
  day: "numeric",
  month: "short",
  year: "numeric",
});

const CLOCK_TIME = new Intl.DateTimeFormat("en-GB", {
  hour: "2-digit",
  minute: "2-digit",
  second: "2-digit",
  hourCycle: "h23",
  timeZone: "Europe/London",
});

export function money(value: string | number | null | undefined): string {
  if (value === null || value === undefined || value === "") return "—";
  const amount = typeof value === "string" ? Number.parseFloat(value) : value;
  return Number.isFinite(amount) ? GBP.format(amount) : "—";
}

export function salaryRange(screening: Screening | null | undefined): string {
  if (!screening) return "—";
  const { salary_min: min, salary_max: max } = screening;
  if (min && max && min !== max) return `${money(min)} – ${money(max)}`;
  if (min && max && min === max) return money(min);
  if (!min && max) return `Up to ${money(max)}`;
  if (min && !max) return `From ${money(min)}`;
  return "—";
}

export function formatDate(value: string | null | undefined): string {
  if (!value) return "—";
  const parsed = new Date(value);
  return Number.isNaN(parsed.getTime()) ? "—" : LONG_DATE.format(parsed);
}

export function formatDateTime(value: string | null | undefined): string {
  if (!value) return "—";
  const parsed = new Date(value);
  if (Number.isNaN(parsed.getTime())) return "—";
  return `${LONG_DATE.format(parsed)}, ${CLOCK_TIME.format(parsed)}`;
}

export function formatTime(value: string | null | undefined): string {
  if (!value) return "—";
  const parsed = new Date(value);
  return Number.isNaN(parsed.getTime()) ? "—" : CLOCK_TIME.format(parsed);
}

export function daysUntil(value: string | null | undefined, today = new Date()): number | null {
  if (!value) return null;
  const closing = new Date(value);
  if (Number.isNaN(closing.getTime())) return null;
  const midnight = (date: Date) => Date.UTC(date.getFullYear(), date.getMonth(), date.getDate());
  return Math.round((midnight(closing) - midnight(today)) / 86_400_000);
}

export function closingLabel(value: string | null | undefined, today = new Date()): string {
  const days = daysUntil(value, today);
  if (days === null) return "No closing date";
  if (days < 0) return "Closed";
  if (days === 0) return "Closes today";
  if (days === 1) return "Closes tomorrow";
  return `Closes in ${days} days`;
}

export const SPONSOR_LABELS: Record<SponsorVerdict, string> = {
  CONFIRMED: "Sponsor confirmed",
  B_RATED: "B-rated sponsor",
  PROVISIONAL: "Provisional sponsor",
  CONFIRMED_VIA_PARENT: "Sponsored via parent",
  OTHER_ROUTE_ONLY: "Not Skilled Worker",
  NOT_FOUND: "No sponsor licence found",
};

export const THRESHOLD_LABELS: Record<ThresholdVerdict, string> = {
  EXCLUDED_BELOW_FLOOR: "Below floor",
  PAY_CUT: "Pay cut",
  LATERAL_CONTINGENT: "Lateral",
  TARGET_BAND: "Target band",
  SALARY_UNCLEAR: "Salary unclear",
};

export const DISCIPLINE_LABELS: Record<Discipline, string> = {
  AGRICULTURE_FOOD_VETERINARY: "Agriculture, Food & Veterinary",
  ARCHITECTURE_BUILDING_PLANNING: "Architecture, Building & Planning",
  BIOLOGICAL_SCIENCES: "Biological Sciences",
  BUSINESS_MANAGEMENT_STUDIES: "Business & Management Studies",
  COMPUTER_SCIENCES: "Computer Sciences",
  CREATIVE_ARTS_DESIGN: "Creative Arts & Design",
  ECONOMICS: "Economics",
  EDUCATION_STUDIES: "Education Studies",
  ENGINEERING_TECHNOLOGY: "Engineering & Technology",
  HEALTH_MEDICAL: "Health & Medical",
  HISTORICAL_PHILOSOPHICAL_STUDIES: "Historical & Philosophical Studies",
  INFORMATION_MANAGEMENT_LIBRARIANSHIP: "Information Management & Librarianship",
  LANGUAGES_LITERATURE_CULTURE: "Languages, Literature & Culture",
  LAW: "Law",
  MATHEMATICS_STATISTICS: "Mathematics & Statistics",
  MEDIA_COMMUNICATIONS: "Media & Communications",
  PHYSICAL_ENVIRONMENTAL_SCIENCES: "Physical & Environmental Sciences",
  POLITICS_GOVERNMENT: "Politics & Government",
  PSYCHOLOGY: "Psychology",
  SOCIAL_SCIENCES_SOCIAL_CARE: "Social Sciences & Social Care",
  ADMINISTRATIVE: "Administrative",
  ESTATES_FACILITIES_MANAGEMENT: "Estates & Facilities Management",
  FINANCE_PROCUREMENT: "Finance & Procurement",
  FUNDRAISING_ALUMNI_BIDS_GRANTS: "Fundraising, Alumni, Bids & Grants",
  HEALTH_WELLBEING_CARE: "Health, Wellbeing & Care",
  HOSPITALITY_RETAIL_EVENTS: "Hospitality, Retail, Conferences & Events",
  HUMAN_RESOURCES: "Human Resources",
  INTERNATIONAL_ACTIVITIES: "International Activities",
  IT_SERVICES: "IT Services",
  LABORATORY_CLINICAL_TECHNICIAN: "Laboratory, Clinical & Technician",
  LEGAL_COMPLIANCE_POLICY: "Legal, Compliance & Policy",
  LIBRARY_SERVICES_DATA_INFORMATION: "Library Services, Data & Information Management",
  PR_MARKETING_SALES_COMMUNICATION: "PR, Marketing, Sales & Communication",
  PROJECT_MANAGEMENT_CONSULTING: "Project Management & Consulting",
  SENIOR_MANAGEMENT: "Senior Management",
  STUDENT_SERVICES: "Student Services",
  SUSTAINABILITY: "Sustainability",
  WEB_DESIGN_DEVELOPMENT: "Web Design & Development",
  SPORT_LEISURE: "Sport & Leisure",
  STUDENTSHIPS_PHDS: "Studentships & PhDs",
  OTHER: "Other",
};

export const ACADEMIC_DISCIPLINES: readonly Discipline[] = [
  "AGRICULTURE_FOOD_VETERINARY",
  "ARCHITECTURE_BUILDING_PLANNING",
  "BIOLOGICAL_SCIENCES",
  "BUSINESS_MANAGEMENT_STUDIES",
  "COMPUTER_SCIENCES",
  "CREATIVE_ARTS_DESIGN",
  "ECONOMICS",
  "EDUCATION_STUDIES",
  "ENGINEERING_TECHNOLOGY",
  "HEALTH_MEDICAL",
  "HISTORICAL_PHILOSOPHICAL_STUDIES",
  "INFORMATION_MANAGEMENT_LIBRARIANSHIP",
  "LANGUAGES_LITERATURE_CULTURE",
  "LAW",
  "MATHEMATICS_STATISTICS",
  "MEDIA_COMMUNICATIONS",
  "PHYSICAL_ENVIRONMENTAL_SCIENCES",
  "POLITICS_GOVERNMENT",
  "PSYCHOLOGY",
  "SOCIAL_SCIENCES_SOCIAL_CARE",
  "SPORT_LEISURE",
];

export const PROFESSIONAL_DISCIPLINES: readonly Discipline[] = [
  "ADMINISTRATIVE",
  "ESTATES_FACILITIES_MANAGEMENT",
  "FINANCE_PROCUREMENT",
  "FUNDRAISING_ALUMNI_BIDS_GRANTS",
  "HEALTH_WELLBEING_CARE",
  "HOSPITALITY_RETAIL_EVENTS",
  "HUMAN_RESOURCES",
  "INTERNATIONAL_ACTIVITIES",
  "IT_SERVICES",
  "LABORATORY_CLINICAL_TECHNICIAN",
  "LEGAL_COMPLIANCE_POLICY",
  "LIBRARY_SERVICES_DATA_INFORMATION",
  "PR_MARKETING_SALES_COMMUNICATION",
  "PROJECT_MANAGEMENT_CONSULTING",
  "SENIOR_MANAGEMENT",
  "STUDENT_SERVICES",
  "SUSTAINABILITY",
  "WEB_DESIGN_DEVELOPMENT",
];

const ACRONYMS = new Set([
  "ok",
  "json",
  "ld",
  "rss",
  "api",
  "html",
  "hr",
  "uk",
  "soc",
  "rqf",
  "fte",
  "nhs",
]);

export function humanise(value: string): string {
  const words = value.toLowerCase().split(/[_\s]+/).filter(Boolean);
  return words
    .map((word, index) => {
      if (ACRONYMS.has(word)) return word.toUpperCase();
      if (index === 0) return word.charAt(0).toUpperCase() + word.slice(1);
      return word;
    })
    .join(" ");
}

const FILTER_LABELS: Record<string, string> = {
  q: "Search term",
  min_fitness: "Minimum fitness",
  salary_min: "Salary floor",
  salary_max: "Salary ceiling",
  sponsorable: "Sponsorship possible",
  posted_after: "Posted after",
  closing_before: "Closing before",
  closing_after: "Closing after",
  institution: "Institution",
  threshold_verdict: "Salary band",
  sponsor_verdict: "Sponsorship",
  contract_type: "Contract",
};

export function filterLabel(key: string): string {
  return FILTER_LABELS[key] ?? humanise(key);
}

export function truncate(value: string, limit: number): string {
  if (value.length <= limit) return value;
  const cut = value.slice(0, limit);
  const lastSpace = cut.lastIndexOf(" ");
  return `${cut.slice(0, lastSpace > limit * 0.6 ? lastSpace : limit).trimEnd()}…`;
}
