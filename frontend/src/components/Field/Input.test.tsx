import { createRef } from "react";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import { Input } from "./Input";

describe("Input", () => {
  it("accepts typed input", async () => {
    render(<Input aria-label="Email" />);
    await userEvent.type(screen.getByLabelText("Email"), "a.morgan@example.com");
    expect(screen.getByLabelText("Email")).toHaveValue("a.morgan@example.com");
  });

  it("marks itself invalid when error is set", () => {
    render(<Input aria-label="Email" error />);
    expect(screen.getByLabelText("Email")).toHaveAttribute("aria-invalid", "true");
  });

  it("has no aria-invalid attribute at all when there is no error", () => {
    render(<Input aria-label="Email" />);
    expect(screen.getByLabelText("Email")).not.toHaveAttribute("aria-invalid");
  });

  it("forwards a ref to the underlying element", () => {
    const ref = createRef<HTMLInputElement>();
    render(<Input ref={ref} aria-label="Email" />);
    expect(ref.current).toBeInstanceOf(HTMLInputElement);
  });

  it("is inert when disabled", async () => {
    const onChange = vi.fn();
    render(<Input aria-label="Email" disabled onChange={onChange} />);
    await userEvent.type(screen.getByLabelText("Email"), "x");
    expect(onChange).not.toHaveBeenCalled();
  });
});
