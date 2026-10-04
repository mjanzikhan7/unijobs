import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import { CVDropzone } from "./CVDropzone";

function aFile(name = "cv.pdf") {
  return new File(["a cv"], name, { type: "application/pdf" });
}

describe("CVDropzone", () => {
  it("states the limits before a file is chosen, not after one is rejected", () => {
    render(<CVDropzone onFile={vi.fn()} />);

    expect(screen.getByText(/PDF,DOCX, up to 5MB/)).toBeInTheDocument();
    expect(screen.getByText(/never sent anywhere else/)).toBeInTheDocument();
  });

  it("keeps a real file input, since dragging is impossible with a keyboard", async () => {
    const onFile = vi.fn();
    render(<CVDropzone onFile={onFile} />);

    await userEvent.upload(screen.getByLabelText("Choose a CV"), aFile());

    expect(onFile).toHaveBeenCalledOnce();
    expect(onFile.mock.calls[0]?.[0]).toBeInstanceOf(File);
  });

  it("says which file it read, once it has one", () => {
    render(<CVDropzone onFile={vi.fn()} fileName="a-morgan-cv.pdf" />);

    expect(screen.getByText("a-morgan-cv.pdf")).toBeInTheDocument();
    expect(screen.getByText(/Choose another to replace it/)).toBeInTheDocument();
  });

  it("blocks a second upload while one is in flight", () => {
    render(<CVDropzone onFile={vi.fn()} uploading />);
    expect(screen.getByRole("button", { name: "Reading your CV…" })).toBeDisabled();
  });

  it("raises a rejection as an alert, in place of the hint", () => {
    render(<CVDropzone onFile={vi.fn()} error="That file is larger than 5MB." />);

    expect(screen.getByRole("alert")).toHaveTextContent("That file is larger than 5MB.");
    expect(screen.queryByText(/never sent anywhere else/)).not.toBeInTheDocument();
  });

  it("tracks its own state in the DOM, so the drag target is never colour-only", () => {
    const { container, rerender } = render(<CVDropzone onFile={vi.fn()} />);
    expect(container.querySelector('[data-state="idle"]')).toBeInTheDocument();

    rerender(<CVDropzone onFile={vi.fn()} uploading />);
    expect(container.querySelector('[data-state="uploading"]')).toBeInTheDocument();

    rerender(<CVDropzone onFile={vi.fn()} fileName="cv.pdf" />);
    expect(container.querySelector('[data-state="parsed"]')).toBeInTheDocument();
  });
});
