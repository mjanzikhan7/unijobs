import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it } from "vitest";

import { Textarea } from "./Textarea";

describe("Textarea", () => {
  it("accepts typed input", async () => {
    render(<Textarea aria-label="Description" />);
    await userEvent.type(screen.getByLabelText("Description"), "A conservatoire in London.");
    expect(screen.getByLabelText("Description")).toHaveValue("A conservatoire in London.");
  });

  it("defaults to 6 rows", () => {
    render(<Textarea aria-label="Description" />);
    expect(screen.getByLabelText("Description")).toHaveAttribute("rows", "6");
  });

  it("lets a caller override the row count", () => {
    render(<Textarea aria-label="Description" rows={10} />);
    expect(screen.getByLabelText("Description")).toHaveAttribute("rows", "10");
  });

  it("marks itself invalid when error is set", () => {
    render(<Textarea aria-label="Description" error />);
    expect(screen.getByLabelText("Description")).toHaveAttribute("aria-invalid", "true");
  });
});
