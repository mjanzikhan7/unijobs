import { forwardRef } from "react";
import type { InputHTMLAttributes } from "react";

import { Input } from "@/components/Field/Input";

interface AuthFieldProps extends InputHTMLAttributes<HTMLInputElement> {
  id: string;
  label: string;
  hint?: string;
}

export const AuthField = forwardRef<HTMLInputElement, AuthFieldProps>(function AuthField(
  { id, label, hint, ...rest },
  ref,
) {
  return (
    <div>
      <label htmlFor={id} className="block text-body-sm font-medium text-text-primary">
        {label}
      </label>
      <Input
        id={id}
        ref={ref}
        aria-describedby={hint ? `${id}-hint` : undefined}
        className="mt-1"
        {...rest}
      />
      {hint ? (
        <p id={`${id}-hint`} className="mt-1 text-caption text-text-muted">
          {hint}
        </p>
      ) : null}
    </div>
  );
});
