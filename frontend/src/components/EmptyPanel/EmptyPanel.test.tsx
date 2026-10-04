import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import { Button } from "@/components/Button/Button";

import { EmptyPanel } from "./EmptyPanel";

describe("EmptyPanel", () => {
  it("announces itself, since it replaces a list that had rows a moment ago", () => {
    render(<EmptyPanel title="No vacancies yet" body="Nothing has been crawled into this view." />);
    expect(screen.getByRole("status")).toBeInTheDocument();
  });

  it("shows the title as a heading and the body beside it", () => {
    render(
      <EmptyPanel
        title="No jobs match these filters"
        body="Minimum fitness (70) is the most restrictive filter you have on."
      />,
    );

    expect(screen.getByRole("heading", { name: "No jobs match these filters" })).toBeInTheDocument();
    expect(screen.getByText(/most restrictive filter/)).toBeInTheDocument();
  });

  it("renders a way out when one is given", async () => {
    const onClear = vi.fn();
    render(
      <EmptyPanel
        title="No jobs match these filters"
        body="Minimum fitness (70) is the most restrictive filter you have on."
        action={<Button onClick={onClear}>Clear minimum fitness</Button>}
      />,
    );

    await userEvent.click(screen.getByRole("button", { name: "Clear minimum fitness" }));
    expect(onClear).toHaveBeenCalledOnce();
  });

  it("omits the action region entirely when there is nothing to offer", () => {
    render(<EmptyPanel title="No vacancies yet" body="Start a crawl to populate this view." />);
    expect(screen.queryByRole("button")).not.toBeInTheDocument();
  });

  it("hides a decorative icon from assistive technology", () => {
    render(<EmptyPanel icon={<svg data-testid="glyph" />} title="Nothing here" body="Yet." />);
    expect(screen.getByTestId("glyph").parentElement).toHaveAttribute("aria-hidden", "true");
  });
});
