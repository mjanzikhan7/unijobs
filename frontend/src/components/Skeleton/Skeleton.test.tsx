import { render } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { Skeleton } from "./Skeleton";

describe("Skeleton", () => {
  it("is aria-hidden, since the loading state is announced elsewhere", () => {
    const { container } = render(<Skeleton />);
    expect(container.firstChild).toHaveAttribute("aria-hidden", "true");
  });

  it("accepts sizing classes from the caller", () => {
    const { container } = render(<Skeleton className="h-10 w-10 rounded-full" />);
    expect(container.firstChild).toHaveClass("h-10", "w-10", "rounded-full");
  });
});
