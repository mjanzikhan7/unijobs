import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import { JobListEmpty } from "./JobListEmpty";

const base = {
  restrictiveFilter: null,
  onClearFilter: () => {},
  onClearAll: () => {},
  activeFilters: 0,
};

describe("JobListEmpty", () => {
  it("distinguishes nothing crawled from nothing matching", () => {
    const { rerender } = render(<JobListEmpty {...base} />);
    expect(screen.getByRole("heading", { name: "No vacancies yet" })).toBeInTheDocument();

    rerender(<JobListEmpty {...base} activeFilters={4} />);
    expect(screen.getByRole("heading", { name: "No jobs match these filters" })).toBeInTheDocument();
  });

  it("offers nothing to clear when there are no filters to blame", () => {
    render(<JobListEmpty {...base} />);
    expect(screen.queryByRole("button")).not.toBeInTheDocument();
  });

  it("names the filter doing the damage, with its value", () => {
    render(
      <JobListEmpty
        {...base}
        activeFilters={4}
        restrictiveFilter="q"
        filterValue="quantum computing"
      />,
    );

    expect(screen.getByText("Search term")).toBeInTheDocument();
    expect(screen.getByText(/\(quantum computing\)/)).toBeInTheDocument();
  });

  it("clears the named filter, not everything", async () => {
    const onClearFilter = vi.fn();
    const onClearAll = vi.fn();
    render(
      <JobListEmpty
        {...base}
        activeFilters={4}
        restrictiveFilter="min_fitness"
        onClearFilter={onClearFilter}
        onClearAll={onClearAll}
      />,
    );

    await userEvent.click(screen.getByRole("button", { name: "Clear minimum fitness" }));

    expect(onClearFilter).toHaveBeenCalledWith("min_fitness");
    expect(onClearAll).not.toHaveBeenCalled();
  });

  it("also offers the blunt way out, counting what it would remove", async () => {
    const onClearAll = vi.fn();
    render(<JobListEmpty {...base} activeFilters={4} onClearAll={onClearAll} />);

    await userEvent.click(screen.getByRole("button", { name: "Clear all 4 filters" }));
    expect(onClearAll).toHaveBeenCalledOnce();
  });

  it("still offers a way out when no single filter is the obvious culprit", () => {
    render(<JobListEmpty {...base} activeFilters={2} />);

    expect(screen.getByText("Try removing a filter.")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Clear all 2 filters" })).toBeInTheDocument();
  });
});
