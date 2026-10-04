interface Props {
  data: { label: string; value: number }[];
  emptyMessage?: string;
}

export function Sparkbars({ data, emptyMessage = "Nothing recorded in this window." }: Props) {
  const max = Math.max(...data.map((point) => point.value), 0);
  if (data.length === 0 || max === 0) {
    return (
      <p
        role="status"
        className="rounded-md border border-dashed border-border-subtle px-4 py-8 text-center text-body-sm text-text-muted"
      >
        {emptyMessage}
      </p>
    );
  }

  return (
    <ol className="flex h-32 items-end gap-0.5">
      {data.map((point) => (
        <li key={point.label} className="flex h-full min-w-0 flex-1 items-end">
          <span
            className="w-full rounded-t-xs bg-brand"
            style={{ height: `${Math.max(2, (point.value / max) * 100)}%` }}
            title={`${point.label}: ${point.value}`}
          />
          <span className="sr-only">
            {point.label}: {point.value}
          </span>
        </li>
      ))}
    </ol>
  );
}
