import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import type { Screening } from "@/models/api/types";

import { SalaryDisplay, isPureRepunctuation } from "./SalaryDisplay";

function screening(overrides: Partial<Screening>): Screening {
  return {
    sponsor_verdict: "CONFIRMED",
    threshold_verdict: "TARGET_BAND",
    ruleset_version: 1,
    ...overrides,
  };
}

describe("isPureRepunctuation", () => {
  it("recognises the same two numbers with a different dash and no spaces as a duplicate", () => {
    expect(isPureRepunctuation("£33,002 – £35,608", "£33,002-£35,608")).toBe(true);
  });

  it("is not fooled by a matching digit count in the wrong order", () => {
    expect(isPureRepunctuation("£38,784 – £46,049", "£46,049 – £38,784")).toBe(false);
  });

  it("keeps a raw string that carries a word the parsed figure does not", () => {
    expect(isPureRepunctuation("£33,002 – £35,608", "£33,002-£35,608 per annum")).toBe(false);
  });

  it("is not a duplicate when the digits genuinely differ", () => {
    expect(isPureRepunctuation("£33,002 – £35,608", "£33,002-£35,600")).toBe(false);
  });
});

describe("SalaryDisplay", () => {
  it("shows the parsed range and the raw string together when the raw carries more than the figure", () => {
    render(
      <SalaryDisplay
        screening={screening({ salary_min: "38784", salary_max: "46049" })}
        raw="£38,784 to £46,049 per annum"
      />,
    );

    expect(screen.getByText("£38,784 – £46,049")).toBeInTheDocument();
    expect(screen.getByText("£38,784 to £46,049 per annum")).toBeInTheDocument();
  });

  it("hides the raw string when it is the parsed range with different punctuation and nothing else", () => {
    render(
      <SalaryDisplay
        screening={screening({ salary_min: "33002", salary_max: "35608" })}
        raw="£33,002-£35,608"
      />,
    );

    expect(screen.getByText("£33,002 – £35,608")).toBeInTheDocument();
    expect(screen.queryByText("£33,002-£35,608")).not.toBeInTheDocument();
  });

  it("keeps the raw string visible even when nothing could be parsed from it", () => {
    render(<SalaryDisplay screening={screening({})} raw="Competitive, dependent on experience" />);

    expect(screen.getByText("Not parsed")).toBeInTheDocument();
    expect(screen.getByText("Competitive, dependent on experience")).toBeInTheDocument();
  });

  it("says the salary was never stated when there is no raw string either", () => {
    render(<SalaryDisplay screening={screening({})} raw={null} />);

    expect(screen.getByText("Salary not stated")).toBeInTheDocument();
    expect(screen.queryByText("Not parsed")).not.toBeInTheDocument();
  });

  it("marks a ceiling-only range as a ceiling, so it can't read as a starting figure", () => {
    render(
      <SalaryDisplay
        screening={screening({ salary_max: "46049" })}
        raw="Salary of up to £46,049 depending on skills"
      />,
    );
    expect(screen.getByText("Up to £46,049")).toBeInTheDocument();
  });

  it("marks a floor-only range as a floor", () => {
    render(
      <SalaryDisplay
        screening={screening({ salary_min: "38784" })}
        raw="£38,784 per annum and upwards"
      />,
    );
    expect(screen.getByText("From £38,784")).toBeInTheDocument();
  });

  it("truncates a long raw string on screen but keeps the whole thing in its title", () => {
    const long =
      "£38,784 to £46,049 per annum pro rata, plus London weighting and a market supplement";
    render(<SalaryDisplay screening={screening({ salary_min: "38784" })} raw={long} />);

    expect(screen.queryByText(long)).not.toBeInTheDocument();
    expect(screen.getByTitle(long)).toBeInTheDocument();
  });

  it("renders before a job has been screened at all", () => {
    render(<SalaryDisplay screening={null} raw="£38,784 to £46,049" />);

    expect(screen.getByText("Not parsed")).toBeInTheDocument();
    expect(screen.getByText("£38,784 to £46,049")).toBeInTheDocument();
  });
});
