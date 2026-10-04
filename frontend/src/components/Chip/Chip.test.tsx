import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { Chip } from "./Chip";

describe("Chip", () => {
  it("renders its text", () => {
    render(<Chip>Permanent</Chip>);
    expect(screen.getByText("Permanent")).toBeInTheDocument();
  });

  it("defaults to outline, neutral", () => {
    render(<Chip>Full time</Chip>);
    expect(screen.getByText("Full time")).toHaveAttribute("data-variant", "outline");
  });

  it("marks itself solid for a state chip", () => {
    render(
      <Chip tone="positive" variant="solid">
        Hybrid
      </Chip>,
    );
    expect(screen.getByText("Hybrid")).toHaveAttribute("data-variant", "solid");
  });
});
