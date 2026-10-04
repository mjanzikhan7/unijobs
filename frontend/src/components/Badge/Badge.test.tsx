import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { MissingBadge, SponsorBadge, ThresholdBadge } from "./Badge";
import type { SponsorVerdict, ThresholdVerdict } from "@/models/api/types";

describe("SponsorBadge", () => {
  const verdicts: SponsorVerdict[] = [
    "CONFIRMED",
    "B_RATED",
    "PROVISIONAL",
    "CONFIRMED_VIA_PARENT",
    "OTHER_ROUTE_ONLY",
    "NOT_FOUND",
  ];

  it.each(verdicts)("renders %s with readable text, not just a colour", (verdict) => {
    render(<SponsorBadge verdict={verdict} />);
    expect(screen.getByText(/./)).toBeInTheDocument();
  });

  it("names the register entry it matched", () => {
    render(<SponsorBadge verdict="CONFIRMED" matchedName="The University of Cambridge" />);
    expect(screen.getByTitle(/The University of Cambridge/)).toBeInTheDocument();
  });

  it("warns loudly when a verdict is missing rather than rendering nothing", () => {
    render(<SponsorBadge verdict={null} />);
    expect(screen.getByText(/Not screened/)).toBeInTheDocument();
  });

  it("shows an advert exclusion in preference to the register verdict", () => {
    render(<SponsorBadge verdict="CONFIRMED" advertExcludes />);
    expect(screen.getByText(/Advert excludes sponsorship/)).toBeInTheDocument();
    expect(screen.queryByText(/Sponsor confirmed/)).not.toBeInTheDocument();
  });

  it("marks a confirmed sponsor as a positive signal", () => {
    render(<SponsorBadge verdict="CONFIRMED" />);
    expect(screen.getByText(/Sponsor confirmed/)).toHaveAttribute("data-tone", "positive");
  });

  it("marks a missing licence as a negative signal", () => {
    render(<SponsorBadge verdict="NOT_FOUND" />);
    expect(screen.getByText(/No sponsor licence/)).toHaveAttribute("data-tone", "negative");
  });
});

describe("ThresholdBadge", () => {
  const verdicts: ThresholdVerdict[] = [
    "EXCLUDED_BELOW_FLOOR",
    "PAY_CUT",
    "LATERAL_CONTINGENT",
    "TARGET_BAND",
    "SALARY_UNCLEAR",
  ];

  it.each(verdicts)("renders %s", (verdict) => {
    render(<ThresholdBadge verdict={verdict} />);
    expect(screen.getByText(/./)).toBeInTheDocument();
  });

  it("warns when the verdict is missing", () => {
    render(<ThresholdBadge verdict={undefined} />);
    expect(screen.getByText(/Not screened/)).toBeInTheDocument();
  });

  it("carries the explanation so a badge can be argued with", () => {
    render(
      <ThresholdBadge verdict="PAY_CUT" explanation="£38,784 is below the current package." />,
    );
    expect(screen.getByTitle(/below the current package/)).toBeInTheDocument();
  });

  it("treats an unclear salary as unknown rather than as a failure", () => {
    render(<ThresholdBadge verdict="SALARY_UNCLEAR" />);
    expect(screen.getByText(/Salary unclear/)).toHaveAttribute("data-tone", "unknown");
  });
});

describe("MissingBadge", () => {
  it("explains that the job has not been screened", () => {
    render(<MissingBadge kind="sponsor" />);
    expect(screen.getByTitle(/has not been screened/)).toBeInTheDocument();
  });

  it("tells the reader not to treat it as cleared", () => {
    render(<MissingBadge kind="threshold" />);
    expect(screen.getByTitle(/do not treat it as cleared/)).toBeInTheDocument();
  });
});
