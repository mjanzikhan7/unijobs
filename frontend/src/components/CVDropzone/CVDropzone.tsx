import { useRef, useState } from "react";

import { Button } from "@/components/Button/Button";

export interface CVDropzoneProps {
  onFile: (file: File) => void;
  accept?: string;
  maxBytes?: number;
  uploading?: boolean;
  error?: string | null;
  fileName?: string | null;
}

const MB = 1024 * 1024;

export function CVDropzone({
  onFile,
  accept = ".pdf,.docx",
  maxBytes = 5 * MB,
  uploading = false,
  error = null,
  fileName = null,
}: CVDropzoneProps) {
  const inputRef = useRef<HTMLInputElement>(null);
  const [dragOver, setDragOver] = useState(false);

  const state = uploading ? "uploading" : error ? "error" : fileName ? "parsed" : "idle";

  function accepted(file: File | undefined) {
    if (file) onFile(file);
  }

  return (
    <div
      data-state={dragOver ? "drag-over" : state}
      onDragOver={(event) => {
        event.preventDefault();
        setDragOver(true);
      }}
      onDragLeave={() => setDragOver(false)}
      onDrop={(event) => {
        event.preventDefault();
        setDragOver(false);
        accepted(event.dataTransfer.files[0]);
      }}
      className={[
        "flex flex-col items-center gap-2 rounded-md border border-dashed px-6 py-8 text-center",
        dragOver ? "border-brand bg-brand-subtle" : "border-border-strong bg-surface-sunken",
        error ? "border-danger" : "",
      ]
        .filter(Boolean)
        .join(" ")}
    >
      <label className="sr-only" htmlFor="cv-file">
        Choose a CV
      </label>
      <input
        id="cv-file"
        ref={inputRef}
        type="file"
        accept={accept}
        className="sr-only"
        onChange={(event) => accepted(event.target.files?.[0])}
      />

      <Button variant="primary" disabled={uploading} onClick={() => inputRef.current?.click()}>
        {uploading ? "Reading your CV…" : "Choose a CV"}
      </Button>

      {error ? (
        <p role="alert" className="text-body-sm text-danger">
          {error}
        </p>
      ) : (
        <p className="text-body-sm text-text-secondary">
          {fileName ? (
            <>
              Read <strong>{fileName}</strong>. Choose another to replace it.
            </>
          ) : (
            <>
              Drop a file here, or choose one. {accept.replace(/\./g, "").toUpperCase()}, up to{" "}
              {Math.round(maxBytes / MB)}MB. It is read on this server and never sent anywhere
              else.
            </>
          )}
        </p>
      )}
    </div>
  );
}
