export interface FactProps {
  label: string;
  value: string | number | null | undefined;
  danger?: boolean;
}

export function Fact({ label, value, danger = false }: FactProps) {
  const display = value === null || value === undefined || value === "" ? "—" : value;
  return (
    <div>
      <dt className="text-overline uppercase tracking-wide text-text-muted">{label}</dt>
      <dd className={`text-body ${danger ? "text-danger font-semibold" : "text-text-primary"}`}>
        {display}
      </dd>
    </div>
  );
}
