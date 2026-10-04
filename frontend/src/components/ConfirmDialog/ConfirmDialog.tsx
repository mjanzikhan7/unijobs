import Dialog from "@mui/material/Dialog";

import { Button } from "@/components/Button/Button";

interface ConfirmDialogProps {
  open: boolean;
  title: string;
  description?: string;
  confirmLabel: string;
  cancelLabel: string;
  onConfirm: () => void;
  onCancel: () => void;
}

export function ConfirmDialog({
  open,
  title,
  description,
  confirmLabel,
  cancelLabel,
  onConfirm,
  onCancel,
}: ConfirmDialogProps) {
  return (
    <Dialog
      open={open}
      onClose={onCancel}
      aria-labelledby="confirm-dialog-title"
      slotProps={{ paper: { sx: { backgroundImage: "none", maxWidth: 440 } } }}
    >
      <div className="bg-surface p-6">
        <h2 id="confirm-dialog-title" className="font-display text-heading-sm font-semibold">
          {title}
        </h2>
        {description ? (
          <p className="mt-2 text-body-sm text-text-secondary">{description}</p>
        ) : null}
        <div className="mt-5 flex justify-end gap-2">
          <Button onClick={onCancel}>{cancelLabel}</Button>
          <Button variant="primary" onClick={onConfirm}>
            {confirmLabel}
          </Button>
        </div>
      </div>
    </Dialog>
  );
}
