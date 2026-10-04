import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import { Pagination } from "./Pagination";

const base = { page: 3, totalPages: 12, hasPrevious: true, hasNext: true, onChange: () => {} };

describe("Pagination", () => {
  it("always states the position, not just the arrows", () => {
    render(<Pagination {...base} />);
    expect(screen.getByText("Page 3 of 12")).toBeInTheDocument();
  });

  it("renders nothing when there is only one page", () => {
    const { container } = render(<Pagination {...base} page={1} totalPages={1} />);
    expect(container).toBeEmptyDOMElement();
  });

  it("renders nothing when there are no pages at all", () => {
    const { container } = render(<Pagination {...base} page={1} totalPages={0} />);
    expect(container).toBeEmptyDOMElement();
  });

  it("steps forward and back by one", async () => {
    const onChange = vi.fn();
    render(<Pagination {...base} onChange={onChange} />);

    await userEvent.click(screen.getByRole("button", { name: "Next" }));
    expect(onChange).toHaveBeenCalledWith(4);

    await userEvent.click(screen.getByRole("button", { name: "Previous" }));
    expect(onChange).toHaveBeenCalledWith(2);
  });

  it("disables Previous on the first page", () => {
    render(<Pagination {...base} page={1} hasPrevious={false} />);

    expect(screen.getByRole("button", { name: "Previous" })).toBeDisabled();
    expect(screen.getByRole("button", { name: "Next" })).toBeEnabled();
  });

  it("disables Next on the last page", () => {
    render(<Pagination {...base} page={12} hasNext={false} />);

    expect(screen.getByRole("button", { name: "Next" })).toBeDisabled();
    expect(screen.getByRole("button", { name: "Previous" })).toBeEnabled();
  });

  it("announces the position change, since the list swaps in place", () => {
    render(<Pagination {...base} />);
    expect(screen.getByText("Page 3 of 12")).toHaveAttribute("aria-live", "polite");
  });

  it("names the landmark after what is being paged", () => {
    render(<Pagination {...base} label="Institutions" />);
    expect(screen.getByRole("navigation", { name: "Institutions" })).toBeInTheDocument();
  });
});
