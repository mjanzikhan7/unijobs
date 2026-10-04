import { Button } from "@/components/Button/Button";

export interface PaginationProps {
  page: number;
  totalPages: number;
  hasPrevious: boolean;
  hasNext: boolean;
  onChange: (page: number) => void;
  label?: string;
}

export function Pagination({
  page,
  totalPages,
  hasPrevious,
  hasNext,
  onChange,
  label = "Pagination",
}: PaginationProps) {
  if (totalPages <= 1) return null;

  return (
    <nav
      aria-label={label}
      className="flex items-center justify-center gap-4 border-t border-border-subtle pt-4"
    >
      <Button size="sm" disabled={!hasPrevious} onClick={() => onChange(page - 1)}>
        Previous
      </Button>
      <span aria-live="polite" className="text-body-sm tabular-nums text-text-secondary">
        Page {page} of {totalPages}
      </span>
      <Button size="sm" disabled={!hasNext} onClick={() => onChange(page + 1)}>
        Next
      </Button>
    </nav>
  );
}
