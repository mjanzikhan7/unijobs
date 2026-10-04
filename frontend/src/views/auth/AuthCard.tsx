import type { FormEvent, ReactNode } from "react";

import { SiteFooterLinks } from "@/components/SiteFooter/SiteFooter";

interface AuthCardProps {
  title: string;
  children: ReactNode;
  onSubmit?: (event: FormEvent) => void;
  footer?: ReactNode;
}

export function AuthCard({ title, children, onSubmit, footer }: AuthCardProps) {
  const inner = (
    <>
      <h1 className="font-display text-heading-lg font-bold">{title}</h1>
      <div className="mt-5 space-y-4">{children}</div>
      {footer ? (
        <div className="mt-6 border-t border-border-subtle pt-4 text-body-sm text-text-secondary">
          {footer}
        </div>
      ) : null}
    </>
  );

  const className =
    "mx-auto w-full max-w-form rounded-lg border border-border-subtle bg-surface p-6 shadow-sm sm:p-8";

  return (
    <div className="flex min-h-screen flex-col items-center justify-center gap-6 bg-bg px-4 py-10">
      <main id="main" className="w-full">
        {onSubmit ? (
          <form className={className} onSubmit={onSubmit} noValidate={false}>
            {inner}
          </form>
        ) : (
          <div className={className}>{inner}</div>
        )}
      </main>
      <SiteFooterLinks className="text-body-sm text-text-secondary" />
    </div>
  );
}
