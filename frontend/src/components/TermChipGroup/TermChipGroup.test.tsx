import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import { TermChipGroup } from "./TermChipGroup";

const terms = ["Python", "Kubernetes", "Fortran"];

describe("TermChipGroup", () => {
  it("names the field it belongs to", () => {
    render(
      <TermChipGroup field="skills" terms={terms} selected={terms} onToggle={vi.fn()} />,
    );
    expect(screen.getByRole("group", { name: "skills" })).toBeInTheDocument();
  });

  it("prefers a human label over the raw field name", () => {
    render(
      <TermChipGroup
        field="years_experience"
        label="Years of experience"
        terms={terms}
        selected={[]}
        onToggle={vi.fn()}
      />,
    );
    expect(screen.getByRole("group", { name: "Years of experience" })).toBeInTheDocument();
  });

  it("uses checkboxes, since these are several independent choices", () => {
    render(
      <TermChipGroup field="skills" terms={terms} selected={["Python"]} onToggle={vi.fn()} />,
    );

    expect(screen.getAllByRole("checkbox")).toHaveLength(3);
    expect(screen.getByRole("checkbox", { name: "Python" })).toBeChecked();
    expect(screen.getByRole("checkbox", { name: "Fortran" })).not.toBeChecked();
  });

  it("reports a term the candidate rejected without changing anything itself", async () => {
    const onToggle = vi.fn();
    render(
      <TermChipGroup field="skills" terms={terms} selected={terms} onToggle={onToggle} />,
    );

    await userEvent.click(screen.getByRole("checkbox", { name: "Fortran" }));

    expect(onToggle).toHaveBeenCalledWith("Fortran");
    expect(screen.getByRole("checkbox", { name: "Fortran" })).toBeChecked();
  });

  it("says the parser found nothing rather than showing an empty group", () => {
    render(<TermChipGroup field="education" terms={[]} selected={[]} onToggle={vi.fn()} />);

    expect(screen.getByText("Nothing found.")).toBeInTheDocument();
    expect(screen.queryByRole("checkbox")).not.toBeInTheDocument();
  });
});
