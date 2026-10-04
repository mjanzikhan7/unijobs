import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import { FileInput } from "./FileInput";

describe("FileInput", () => {
  it("renders a real button, not the browser's own file input chrome", () => {
    render(<FileInput id="logo" label="Upload a logo" onFileChange={vi.fn()} />);

    expect(screen.getByRole("button", { name: "Choose file" })).toBeInTheDocument();
  });

  it("reports the picked file to the caller", async () => {
    const onFileChange = vi.fn();
    render(<FileInput id="logo" label="Upload a logo" onFileChange={onFileChange} />);

    const file = new File(["logo"], "logo.png", { type: "image/png" });
    await userEvent.upload(screen.getByLabelText("Upload a logo"), file);

    expect(onFileChange).toHaveBeenCalledWith(file);
  });

  it("shows the picked file's name beside the button", () => {
    render(
      <FileInput id="logo" label="Upload a logo" onFileChange={vi.fn()} fileName="logo.png" />,
    );

    expect(screen.getByText("logo.png")).toBeInTheDocument();
  });

  it("uses a custom button label when given one", () => {
    render(
      <FileInput
        id="logo"
        label="Upload a logo"
        buttonLabel="Choose logo"
        onFileChange={vi.fn()}
      />,
    );

    expect(screen.getByRole("button", { name: "Choose logo" })).toBeInTheDocument();
  });

  it("disables the button, not just the hidden input", () => {
    render(<FileInput id="logo" label="Upload a logo" onFileChange={vi.fn()} disabled />);

    expect(screen.getByRole("button", { name: "Choose file" })).toBeDisabled();
  });
});
