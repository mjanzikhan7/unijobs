import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import { DisciplineBrowse } from "./DisciplineBrowse";

describe("DisciplineBrowse", () => {
  it("renders nothing when the discipline facet carries no values", () => {
    const { container } = render(
      <DisciplineBrowse values={[]} selected={[]} onSelect={vi.fn()} />,
    );

    expect(container).toBeEmptyDOMElement();
  });

  it("groups the taxonomy into academic and professional sections, and no others", () => {
    render(
      <DisciplineBrowse
        values={[
          { value: "PSYCHOLOGY", count: 12 },
          { value: "HUMAN_RESOURCES", count: 4 },
          { value: "STUDENTSHIPS_PHDS", count: 2 },
        ]}
        selected={[]}
        onSelect={vi.fn()}
      />,
    );

    expect(
      screen.getByRole("heading", { name: "Academic discipline / field of expertise" }),
    ).toBeInTheDocument();
    expect(
      screen.getByRole("heading", { name: "Professional, managerial & support services" }),
    ).toBeInTheDocument();
    expect(screen.queryByText(/Studentships/)).not.toBeInTheDocument();
  });

  it("shows each discipline's own count", () => {
    render(
      <DisciplineBrowse
        values={[{ value: "PSYCHOLOGY", count: 12 }]}
        selected={[]}
        onSelect={vi.fn()}
      />,
    );

    expect(screen.getByLabelText("12 results")).toBeInTheDocument();
  });

  it("disables a discipline with nothing behind it", () => {
    render(
      <DisciplineBrowse
        values={[{ value: "PSYCHOLOGY", count: 0 }]}
        selected={[]}
        onSelect={vi.fn()}
      />,
    );

    expect(screen.getByRole("button", { name: /Psychology/ })).toBeDisabled();
  });

  it("reports the discipline that was chosen", async () => {
    const onSelect = vi.fn();
    render(
      <DisciplineBrowse
        values={[{ value: "PSYCHOLOGY", count: 12 }]}
        selected={[]}
        onSelect={onSelect}
      />,
    );

    await userEvent.click(screen.getByRole("button", { name: /Psychology/ }));

    expect(onSelect).toHaveBeenCalledWith("PSYCHOLOGY");
  });

  it("starts open when nothing is selected yet", () => {
    const { container } = render(
      <DisciplineBrowse
        values={[{ value: "PSYCHOLOGY", count: 12 }]}
        selected={[]}
        onSelect={vi.fn()}
      />,
    );

    expect(container.querySelector("details")).toHaveAttribute("open");
  });

  it("starts collapsed once a discipline is already selected", () => {
    const { container } = render(
      <DisciplineBrowse
        values={[{ value: "PSYCHOLOGY", count: 12 }]}
        selected={["PSYCHOLOGY"]}
        onSelect={vi.fn()}
      />,
    );

    expect(container.querySelector("details")).not.toHaveAttribute("open");
  });
});
