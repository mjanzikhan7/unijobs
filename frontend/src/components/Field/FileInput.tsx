import { useRef } from "react";
import type { ChangeEvent, ReactNode } from "react";

import { Button } from "@/components/Button/Button";
import type { ButtonVariant } from "@/components/Button/Button";

export interface FileInputProps {
  id: string;
  label: string;
  onFileChange: (file: File | null) => void;
  accept?: string;
  disabled?: boolean;
  buttonLabel?: string;
  buttonVariant?: ButtonVariant;
  fileName?: ReactNode;
}

export function FileInput({
  id,
  label,
  onFileChange,
  accept,
  disabled = false,
  buttonLabel = "Choose file",
  buttonVariant = "secondary",
  fileName,
}: FileInputProps) {
  const inputRef = useRef<HTMLInputElement>(null);

  return (
    <div className="flex flex-wrap items-center gap-3">
      <label className="sr-only" htmlFor={id}>
        {label}
      </label>
      <input
        id={id}
        ref={inputRef}
        type="file"
        accept={accept}
        disabled={disabled}
        className="sr-only"
        onChange={(event: ChangeEvent<HTMLInputElement>) =>
          onFileChange(event.target.files?.[0] ?? null)
        }
      />
      <Button
        type="button"
        variant={buttonVariant}
        size="sm"
        disabled={disabled}
        onClick={() => inputRef.current?.click()}
      >
        {buttonLabel}
      </Button>
      {fileName ? (
        <span className="min-w-0 truncate text-body-sm text-text-secondary">{fileName}</span>
      ) : null}
    </div>
  );
}
