import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router-dom";
import { describe, expect, it, vi } from "vitest";

import { navFor } from "@/components/nav";

import { Sidebar } from "./Sidebar";

const activeRun = vi.fn();
const reviewQueue = vi.fn();

vi.mock("@/viewmodels/useActiveRun", () => ({
  useActiveRun: () => {
    activeRun();
    return { data: { run: { id: 1 } } };
  },
}));

vi.mock("@/viewmodels/useInstitutions", () => ({
  useReviewQueue: () => {
    reviewQueue();
    return { data: [{ id: 1 }, { id: 2 }] };
  },
}));

function renderSidebar(
  props: Partial<React.ComponentProps<typeof Sidebar>> = {},
  route = "/",
): void {
  render(
    <MemoryRouter initialEntries={[route]}>
      <Sidebar items={navFor("ADMIN")} {...props} />
    </MemoryRouter>,
  );
}

describe("Sidebar", () => {
  it("groups an admin's fourteen destinations under headings", () => {
    renderSidebar();

    for (const heading of ["Explore", "You", "Operations", "Analytics", "Administration"]) {
      expect(screen.getByRole("heading", { name: heading })).toBeInTheDocument();
    }
  });

  it("leads with the daily screens, ungrouped", () => {
    renderSidebar();

    const lists = screen.getAllByRole("list");
    const leading = within(lists[0]!)
      .getAllByRole("link")
      .map((link) => link.textContent);
    expect(leading).toEqual(["Jobs", "Saved", "Pipeline"]);
  });

  it("drops the groups a candidate has no items in", () => {
    renderSidebar({ items: navFor("CANDIDATE") });

    expect(screen.getByRole("heading", { name: "You" })).toBeInTheDocument();
    expect(screen.queryByRole("heading", { name: "Operations" })).not.toBeInTheDocument();
    expect(screen.queryByRole("heading", { name: "Administration" })).not.toBeInTheDocument();
  });

  it("marks the current route for assistive technology", () => {
    renderSidebar({}, "/saved");

    expect(screen.getByRole("link", { name: "Saved" })).toHaveAttribute("aria-current", "page");
    expect(screen.getByRole("link", { name: "Jobs" })).not.toHaveAttribute("aria-current");
  });

  it("lights exactly one item on a path that is a prefix of another", () => {
    renderSidebar({}, "/profile/cv");

    expect(screen.getByRole("link", { name: "CV & matching" })).toHaveAttribute(
      "aria-current",
      "page",
    );
    expect(screen.getByRole("link", { name: "Account" })).not.toHaveAttribute("aria-current");
  });

  it("never mounts the operator badges for a non-staff shell", () => {
    activeRun.mockClear();
    reviewQueue.mockClear();

    renderSidebar({ items: navFor("CANDIDATE"), isStaff: false });

    expect(activeRun).not.toHaveBeenCalled();
    expect(reviewQueue).not.toHaveBeenCalled();
  });

  it("shows the crawl pip and review count for staff", () => {
    renderSidebar({ isStaff: true });

    expect(screen.getByLabelText("A crawl is running")).toBeInTheDocument();
    expect(screen.getByLabelText("2 awaiting review")).toBeInTheDocument();
  });

  it("keeps every label reachable when collapsed to a rail", () => {
    renderSidebar({ collapsed: true });

    expect(screen.getByRole("link", { name: "Crawl console" })).toHaveAttribute(
      "title",
      "Crawl console",
    );
    expect(screen.getByRole("heading", { name: "Operations" })).toBeInTheDocument();
  });

  it("tells the shell when an item was followed, so the drawer can close", async () => {
    const onNavigate = vi.fn();
    renderSidebar({ onNavigate });

    await userEvent.click(screen.getByRole("link", { name: "Saved" }));
    expect(onNavigate).toHaveBeenCalledOnce();
  });
});
