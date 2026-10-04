import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it } from "vitest";

import { Select } from "./Select";

describe("Select", () => {
  it("renders its options and reflects a choice", async () => {
    render(
      <Select aria-label="Role" defaultValue="CANDIDATE">
        <option value="ADMIN">ADMIN</option>
        <option value="MANAGER">MANAGER</option>
        <option value="CANDIDATE">CANDIDATE</option>
      </Select>,
    );

    await userEvent.selectOptions(screen.getByLabelText("Role"), "ADMIN");
    expect(screen.getByLabelText("Role")).toHaveValue("ADMIN");
  });

  it("is inert when disabled", () => {
    render(
      <Select aria-label="Role" disabled>
        <option value="CANDIDATE">CANDIDATE</option>
      </Select>,
    );
    expect(screen.getByLabelText("Role")).toBeDisabled();
  });
});
