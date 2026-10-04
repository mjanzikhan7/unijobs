import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import { FacetGroup } from "./FacetGroup";

const VALUES = [
  { value: "CONFIRMED", count: 42 },
  { value: "NOT_FOUND", count: 0 },
  { value: "B_RATED", count: 3 },
];

describe("FacetGroup", () => {
  it("renders each facet value with its count", () => {
    render(
      <FacetGroup
        name="sponsor_verdict"
        label="Sponsorship"
        values={VALUES}
        selected={[]}
        onToggle={vi.fn()}
      />,
    );

    expect(screen.getByLabelText("42 results")).toBeInTheDocument();
  });

  it("disables a value that would yield nothing", () => {
    render(
      <FacetGroup
        name="sponsor_verdict"
        label="Sponsorship"
        values={VALUES}
        selected={[]}
        onToggle={vi.fn()}
      />,
    );

    expect(screen.getByRole("checkbox", { name: /Not found/i })).toBeDisabled();
  });

  it("leaves a non-empty value clickable", () => {
    render(
      <FacetGroup
        name="sponsor_verdict"
        label="Sponsorship"
        values={VALUES}
        selected={[]}
        onToggle={vi.fn()}
      />,
    );

    expect(screen.getByRole("checkbox", { name: /Confirmed/ })).toBeEnabled();
  });

  it("keeps a selected value clickable even at zero, so it can be turned off", () => {
    render(
      <FacetGroup
        name="sponsor_verdict"
        label="Sponsorship"
        values={VALUES}
        selected={["NOT_FOUND"]}
        onToggle={vi.fn()}
      />,
    );

    expect(screen.getByRole("checkbox", { name: /Not found/i })).toBeEnabled();
  });

  it("reports a toggle with the raw enum value, not the label", async () => {
    const onToggle = vi.fn();
    render(
      <FacetGroup
        name="sponsor_verdict"
        label="Sponsorship"
        values={VALUES}
        selected={[]}
        onToggle={onToggle}
      />,
    );

    await userEvent.click(screen.getByRole("checkbox", { name: /Confirmed/ }));

    expect(onToggle).toHaveBeenCalledWith("CONFIRMED");
  });

  it("shows selected values as checked", () => {
    render(
      <FacetGroup
        name="sponsor_verdict"
        label="Sponsorship"
        values={VALUES}
        selected={["B_RATED"]}
        onToggle={vi.fn()}
      />,
    );

    expect(screen.getByRole("checkbox", { name: /B rated/i })).toBeChecked();
  });

  it("renders nothing when the facet has no values at all", () => {
    const { container } = render(
      <FacetGroup name="nation" label="Nation" values={[]} selected={[]} onToggle={vi.fn()} />,
    );

    expect(container).toBeEmptyDOMElement();
  });

  it("uses a supplied formatter for values that are slugs", () => {
    render(
      <FacetGroup
        name="institution"
        label="Institution"
        values={[{ value: "university-of-bath", count: 12 }]}
        selected={[]}
        onToggle={vi.fn()}
        formatValue={() => "University of Bath"}
      />,
    );

    expect(screen.getByText("University of Bath")).toBeInTheDocument();
  });

  it("groups its options under a labelled fieldset", () => {
    render(
      <FacetGroup
        name="nation"
        label="Nation"
        values={VALUES}
        selected={[]}
        onToggle={vi.fn()}
      />,
    );

    expect(screen.getByRole("group", { name: "Nation" })).toBeInTheDocument();
  });

  it("starts collapsed when nothing in it is selected", () => {
    const { container } = render(
      <FacetGroup name="nation" label="Nation" values={VALUES} selected={[]} onToggle={vi.fn()} />,
    );

    expect(container.querySelector("details")).not.toHaveAttribute("open");
  });

  it("starts open when it already carries a selection, so the choice stays visible", () => {
    const { container } = render(
      <FacetGroup
        name="sponsor_verdict"
        label="Sponsorship"
        values={VALUES}
        selected={["B_RATED"]}
        onToggle={vi.fn()}
      />,
    );

    expect(container.querySelector("details")).toHaveAttribute("open");
  });
});
