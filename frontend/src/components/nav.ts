import type { IconName } from "@/components/Icon/Icon";
import type { Role } from "@/viewmodels/auth";

export type NavSection = "Explore" | "You" | "Operations" | "Analytics" | "Administration";

export const NAV_SECTIONS: readonly NavSection[] = [
  "Explore",
  "You",
  "Operations",
  "Analytics",
  "Administration",
];

export interface NavItem {
  to: string;
  label: string;
  end?: boolean;
  pip?: boolean;
  badge?: "review";
  section?: NavSection;
  icon: IconName;
}

export interface NavGroup {
  section: NavSection | null;
  items: readonly NavItem[];
}

export function groupNav(items: readonly NavItem[]): readonly NavGroup[] {
  const groups: NavGroup[] = [
    { section: null, items: items.filter((item) => !item.section) },
    ...NAV_SECTIONS.map((section) => ({
      section,
      items: items.filter((item) => item.section === section),
    })),
  ];
  return groups.filter((group) => group.items.length > 0);
}

const CANDIDATE_NAV: readonly NavItem[] = [
  { to: "/", label: "Jobs", end: true, icon: "jobs" },
  { to: "/institutions", label: "Institutions", section: "Explore", icon: "institutions" },
  { to: "/saved", label: "Saved", icon: "saved" },
  { to: "/pipeline", label: "Pipeline", icon: "pipeline" },
  { to: "/profile/cv", label: "CV & matching", section: "You", icon: "cv" },
  { to: "/profile", label: "Account", end: true, section: "You", icon: "account" },
];

const MANAGER_NAV: readonly NavItem[] = [
  { to: "/admin/insights", label: "Insights", end: true, section: "Analytics", icon: "insights" },
  { to: "/admin/insights/institutions", label: "Trends", section: "Analytics", icon: "trends" },
  {
    to: "/admin/crawl",
    label: "Crawl console",
    pip: true,
    section: "Operations",
    icon: "crawl",
  },
  {
    to: "/admin/review",
    label: "Sponsor review",
    badge: "review",
    section: "Operations",
    icon: "review",
  },
  { to: "/admin/jobs", label: "Manage jobs", section: "Operations", icon: "manage-jobs" },
  {
    to: "/admin/institutions",
    label: "Manage institutions",
    section: "Operations",
    icon: "manage-institutions",
  },
];

const ADMIN_NAV: readonly NavItem[] = [
  { to: "/admin/users", label: "Users", section: "Administration", icon: "users" },
  { to: "/admin/thresholds", label: "Thresholds", section: "Administration", icon: "thresholds" },
];

const RECRUITER_NAV: readonly NavItem[] = [
  { to: "/", label: "Jobs", end: true, icon: "jobs" },
  { to: "/institutions", label: "Institutions", section: "Explore", icon: "institutions" },
  { to: "/admin/jobs", label: "Manage jobs", section: "Operations", icon: "manage-jobs" },
  {
    to: "/recruiter/institution",
    label: "My institution",
    section: "Operations",
    icon: "manage-institutions",
  },
  { to: "/profile", label: "Account", end: true, section: "You", icon: "account" },
];

export function navFor(role: Role | null): readonly NavItem[] {
  if (role === "ADMIN") return [...CANDIDATE_NAV, ...MANAGER_NAV, ...ADMIN_NAV];
  if (role === "MANAGER") return [...CANDIDATE_NAV, ...MANAGER_NAV];
  if (role === "RECRUITER") return RECRUITER_NAV;
  return CANDIDATE_NAV;
}
