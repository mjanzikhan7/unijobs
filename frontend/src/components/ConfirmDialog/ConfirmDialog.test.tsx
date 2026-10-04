import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import { ConfirmDialog } from "./ConfirmDialog";

const base = {
  title: "Did you apply to this job?",
  description: "This only updates your own Pipeline board.",
  confirmLabel: "Yes, mark Applied",
  cancelLabel: "Not yet",
};

describe("ConfirmDialog", () => {
  it("stays out of the tree until it is open", () => {
    render(<ConfirmDialog {...base} open={false} onConfirm={vi.fn()} onCancel={vi.fn()} />);
    expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
  });

  it("names itself by its question", () => {
    render(<ConfirmDialog {...base} open onConfirm={vi.fn()} onCancel={vi.fn()} />);

    expect(screen.getByRole("dialog", { name: base.title })).toBeInTheDocument();
    expect(screen.getByText(base.description)).toBeInTheDocument();
  });

  it("reports each answer separately — neither is a no-op", async () => {
    const onConfirm = vi.fn();
    const onCancel = vi.fn();
    render(<ConfirmDialog {...base} open onConfirm={onConfirm} onCancel={onCancel} />);

    await userEvent.click(screen.getByRole("button", { name: base.confirmLabel }));
    expect(onConfirm).toHaveBeenCalledOnce();
    expect(onCancel).not.toHaveBeenCalled();

    await userEvent.click(screen.getByRole("button", { name: base.cancelLabel }));
    expect(onCancel).toHaveBeenCalledOnce();
  });

  it("treats Escape as the cancelling answer, not as a silent dismissal", async () => {
    const onCancel = vi.fn();
    render(<ConfirmDialog {...base} open onConfirm={vi.fn()} onCancel={onCancel} />);

    await userEvent.keyboard("{Escape}");
    await waitFor(() => expect(onCancel).toHaveBeenCalledOnce());
  });

  it("traps focus inside itself while open", async () => {
    render(
      <>
        <button type="button">Outside</button>
        <ConfirmDialog {...base} open onConfirm={vi.fn()} onCancel={vi.fn()} />
      </>,
    );

    const dialog = screen.getByRole("dialog");
    await waitFor(() =>
      expect(dialog).toContainElement(document.activeElement as HTMLElement | null),
    );
  });
});
