const STATIC_LABELS: Record<string, string> = {
  "/": "Job search",
  "/institutions": "Institutions",
  "/saved": "Saved jobs",
  "/pipeline": "Pipeline",
  "/profile": "Account settings",
  "/profile/cv": "CV and matching",
  "/admin/crawl": "Crawl console",
  "/admin/review": "Sponsor review",
  "/admin/jobs": "Manage jobs",
  "/admin/institutions": "Manage institutions",
  "/admin/insights": "Candidate insights",
  "/admin/insights/institutions": "Institution trends",
  "/admin/users": "Users",
  "/admin/thresholds": "Thresholds",
  "/recruiter/institution": "My institution",
  "/accessibility": "Accessibility statement",
  "/privacy": "Privacy notice",
};

export function routeTitle(pathname: string): string {
  return STATIC_LABELS[pathname] ?? "Page";
}
