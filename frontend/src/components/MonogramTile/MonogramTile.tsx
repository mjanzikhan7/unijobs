export type MonogramSize = "sm" | "md" | "lg";

export interface MonogramTileProps {
  name: string;
  size?: MonogramSize;
}

const sizes: Record<MonogramSize, string> = {
  sm: "h-8 w-8 text-caption",
  md: "h-11 w-11 text-body",
  lg: "h-16 w-16 text-heading-sm",
};

export function initialsOf(name: string): string {
  const skip = new Set(["of", "the", "and", "for", "at", "in", "de", "la"]);
  const words = name
    .split(/[\s\-–—]+/)
    .map((word) => word.replace(/[^\p{L}\p{N}]/gu, ""))
    .filter((word) => word.length > 0 && !skip.has(word.toLowerCase()));

  if (words.length === 0) return "?";
  if (words.length === 1) return (words[0] ?? "").slice(0, 2).toUpperCase();
  return `${words[0]?.charAt(0) ?? ""}${words[1]?.charAt(0) ?? ""}`.toUpperCase();
}

export function MonogramTile({ name, size = "md" }: MonogramTileProps) {
  return (
    <span
      aria-hidden="true"
      className={`inline-flex shrink-0 items-center justify-center rounded-md bg-brand-subtle font-display font-semibold text-brand ${sizes[size]}`}
    >
      {initialsOf(name)}
    </span>
  );
}
