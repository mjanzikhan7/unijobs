import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { Fact } from "./Fact";

describe("Fact", () => {
  it("renders the label and value", () => {
    render(<Fact label="Grade" value="Grade 8" />);
    expect(screen.getByText("Grade")).toBeInTheDocument();
    expect(screen.getByText("Grade 8")).toBeInTheDocument();
  });

  it("renders an em dash for a missing value, never a blank cell", () => {
    render(<Fact label="Registered as" value={null} />);
    expect(screen.getByText("—")).toBeInTheDocument();
  });

  it("renders an em dash for an empty string too", () => {
    render(<Fact label="Registered as" value="" />);
    expect(screen.getByText("—")).toBeInTheDocument();
  });

  it("renders zero as a real value, not as missing", () => {
    render(<Fact label="Open vacancies" value={0} />);
    expect(screen.getByText("0")).toBeInTheDocument();
  });

  it("marks a danger fact so the value itself carries the warning", () => {
    render(<Fact label="Salary band" value="£38,784" danger />);
    expect(screen.getByText("£38,784")).toHaveClass("text-danger");
  });
});
