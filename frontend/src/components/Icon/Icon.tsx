import type { SVGProps } from "react";

export type IconName =
  | "jobs"
  | "institutions"
  | "saved"
  | "pipeline"
  | "cv"
  | "account"
  | "insights"
  | "trends"
  | "crawl"
  | "review"
  | "manage-jobs"
  | "manage-institutions"
  | "users"
  | "thresholds"
  | "menu"
  | "close"
  | "chevron-left"
  | "chevron-right"
  | "chevron-down"
  | "mail"
  | "phone"
  | "map-pin"
  | "external-link"
  | "search";

const paths: Record<IconName, string> = {
  jobs: "M4 8h16v11a1 1 0 0 1-1 1H5a1 1 0 0 1-1-1V8Zm4 0V6a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2M4 13h16",
  institutions:
    "M5 21V6l7-3 7 3v15M5 21h14M9 21v-6h6v6M9 10h.01M15 10h.01M9 14h.01M15 14h.01",
  saved: "M6 4h12a1 1 0 0 1 1 1v15l-7-4-7 4V5a1 1 0 0 1 1-1Z",
  pipeline: "M4 4h5v10H4V4Zm7.5 0h5v16h-5V4ZM19 4h1v6h-1V4Z",
  cv: "M7 3h7l5 5v13a1 1 0 0 1-1 1H7a1 1 0 0 1-1-1V4a1 1 0 0 1 1-1Zm7 0v5h5M9 12h6M9 15h6M9 9h2",
  account: "M12 12a4 4 0 1 0 0-8 4 4 0 0 0 0 8Zm-7 9a7 7 0 0 1 14 0",
  insights: "M4 20V10M10 20V4M16 20v-7M22 20H2",
  trends: "M3 17l6-6 4 4 8-8M15 7h6v6",
  crawl: "M12 3v9l6 3M12 3a9 9 0 1 1-6.36 2.64",
  review: "M12 3l7 3v6c0 4.5-3 7.5-7 9-4-1.5-7-4.5-7-9V6l7-3Zm-3 9 2 2 4-4",
  "manage-jobs":
    "M4 8h11v11a1 1 0 0 1-1 1H5a1 1 0 0 1-1-1V8Zm4 0V6a2 2 0 0 1 2-2h2M15 21l6-6-2-2-6 6v2h2Z",
  "manage-institutions":
    "M5 21V8l6-4 4 2.5M5 21h7M9 21v-6h3v2M15 21l6-6-2-2-6 6v2h2Z",
  users:
    "M9 11a3 3 0 1 0 0-6 3 3 0 0 0 0 6Zm-6 9a6 6 0 0 1 12 0M17 8a3 3 0 1 1 0 6M23 20a6 6 0 0 0-5-5.91",
  thresholds: "M4 6h9M17 6h3M4 12h3M11 12h9M4 18h13M21 18h-1M8 4v4M15 10v4M18 16v4",
  menu: "M4 6h16M4 12h16M4 18h16",
  close: "M6 6l12 12M18 6 6 18",
  "chevron-left": "M14 6l-6 6 6 6",
  "chevron-right": "M10 6l6 6-6 6",
  "chevron-down": "M6 10l6 6 6-6",
  mail: "M4 6h16v12H4V6Zm0 0 8 7 8-7",
  phone:
    "M6 3h3l2 5-2.5 1.5a11 11 0 0 0 5 5L15 12l5 2v3a2 2 0 0 1-2 2A16 16 0 0 1 4 5a2 2 0 0 1 2-2Z",
  "map-pin": "M12 21s7-6.5 7-11.5A7 7 0 0 0 5 9.5C5 14.5 12 21 12 21Zm0-9a2.5 2.5 0 1 0 0-5 2.5 2.5 0 0 0 0 5Z",
  "external-link": "M14 4h6v6M20 4 10 14M18 13v6a1 1 0 0 1-1 1H5a1 1 0 0 1-1-1V6a1 1 0 0 1 1-1h6",
  search: "M11 19a8 8 0 1 0 0-16 8 8 0 0 0 0 16Zm9 2-5.5-5.5",
};

export interface IconProps extends Omit<SVGProps<SVGSVGElement>, "viewBox"> {
  name: IconName;
}

export function Icon({ name, className = "", ...rest }: IconProps) {
  return (
    <svg
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth={2}
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden="true"
      className={`h-5 w-5 shrink-0 ${className}`}
      {...rest}
    >
      <path d={paths[name]} />
    </svg>
  );
}
