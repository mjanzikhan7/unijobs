import { render } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { Icon } from "./Icon";

describe("Icon", () => {
  it("stays out of the accessibility tree — the label beside it carries the meaning", () => {
    const { container } = render(<Icon name="jobs" />);
    expect(container.querySelector("svg")).toHaveAttribute("aria-hidden", "true");
  });

  it("renders a distinct path per name", () => {
    const { container: a } = render(<Icon name="jobs" />);
    const { container: b } = render(<Icon name="account" />);

    const pathA = a.querySelector("path")?.getAttribute("d");
    const pathB = b.querySelector("path")?.getAttribute("d");
    expect(pathA).not.toBe(pathB);
  });

  it("lets a caller extend the geometry without losing the shared stroke style", () => {
    const { container } = render(<Icon name="jobs" className="h-8 w-8" />);
    const svg = container.querySelector("svg");
    expect(svg?.getAttribute("class")).toContain("h-8 w-8");
    expect(svg).toHaveAttribute("stroke", "currentColor");
  });
});
