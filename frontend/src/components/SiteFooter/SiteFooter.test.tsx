import { render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";

import { SiteFooterLinks } from "./SiteFooter";

describe("SiteFooterLinks", () => {
  it("links to the accessibility statement and the privacy notice", () => {
    render(
      <MemoryRouter>
        <SiteFooterLinks />
      </MemoryRouter>,
    );

    expect(screen.getByRole("navigation", { name: "Legal and support" })).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Accessibility statement" })).toHaveAttribute(
      "href",
      "/accessibility",
    );
    expect(screen.getByRole("link", { name: "Privacy notice" })).toHaveAttribute(
      "href",
      "/privacy",
    );
  });
});
