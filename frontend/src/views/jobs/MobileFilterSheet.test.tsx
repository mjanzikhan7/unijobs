import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it } from "vitest";

import { MobileFilterSheet } from "./MobileFilterSheet";

function renderSheet(activeCount = 0) {
  return render(
    <MobileFilterSheet activeCount={activeCount}>
      <label htmlFor="only-sponsorable">
        <input id="only-sponsorable" type="checkbox" /> Only where sponsorship is possible
      </label>
    </MobileFilterSheet>,
  );
}

describe("MobileFilterSheet", () => {
  it("says how many filters are already on, since the panel is off screen", () => {
    renderSheet(3);
    expect(screen.getByRole("button", { name: "Filters (3)" })).toBeInTheDocument();
  });

  it("shows no count when nothing is set, rather than a bracketed zero", () => {
    renderSheet(0);
    expect(screen.getByRole("button", { name: "Filters" })).toBeInTheDocument();
  });

  it("keeps the filters out of the tree until the sheet is opened", () => {
    renderSheet();
    expect(screen.queryByLabelText(/Only where sponsorship/)).not.toBeInTheDocument();
  });

  it("reveals the filters when opened, and closes on Show results", async () => {
    renderSheet(2);

    await userEvent.click(screen.getByRole("button", { name: "Filters (2)" }));
    expect(await screen.findByLabelText(/Only where sponsorship/)).toBeInTheDocument();

    await userEvent.click(screen.getByRole("button", { name: "Show results" }));
    await waitFor(() =>
      expect(screen.queryByLabelText(/Only where sponsorship/)).not.toBeInTheDocument(),
    );
  });

  it("returns focus to the trigger, so a keyboard user resumes where they were", async () => {
    renderSheet(1);

    const trigger = screen.getByRole("button", { name: "Filters (1)" });
    await userEvent.click(trigger);
    await userEvent.click(await screen.findByRole("button", { name: "Show results" }));

    await waitFor(() => expect(trigger).toHaveFocus());
  });

  it("closes on Escape", async () => {
    renderSheet();

    await userEvent.click(screen.getByRole("button", { name: "Filters" }));
    await screen.findByLabelText(/Only where sponsorship/);

    await userEvent.keyboard("{Escape}");
    await waitFor(() =>
      expect(screen.queryByLabelText(/Only where sponsorship/)).not.toBeInTheDocument(),
    );
  });
});
