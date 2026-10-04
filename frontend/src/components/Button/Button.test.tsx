import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import { Button } from "./Button";

describe("Button", () => {
  it("renders its label", () => {
    render(<Button>Save job</Button>);
    expect(screen.getByRole("button", { name: "Save job" })).toBeInTheDocument();
  });

  it("defaults to type=button so it never submits a form by accident", () => {
    render(<Button>Cancel</Button>);
    expect(screen.getByRole("button")).toHaveAttribute("type", "button");
  });

  it("calls onClick when clicked", async () => {
    const onClick = vi.fn();
    render(<Button onClick={onClick}>Run search</Button>);
    await userEvent.click(screen.getByRole("button"));
    expect(onClick).toHaveBeenCalledOnce();
  });

  it("is disabled and inert when disabled is set", async () => {
    const onClick = vi.fn();
    render(
      <Button disabled onClick={onClick}>
        Save job
      </Button>,
    );
    const button = screen.getByRole("button");
    expect(button).toBeDisabled();
    await userEvent.click(button);
    expect(onClick).not.toHaveBeenCalled();
  });

  it.each(["primary", "secondary", "quiet", "cta"] as const)(
    "renders the %s variant without throwing",
    (variant) => {
      render(<Button variant={variant}>Apply</Button>);
      expect(screen.getByRole("button")).toBeInTheDocument();
    },
  );
});
