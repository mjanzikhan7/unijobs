import type { JSX, ReactNode } from "react";

export function VisuallyHidden({
  children,
  as: Component = "span",
}: {
  children: ReactNode;
  as?: keyof JSX.IntrinsicElements;
}) {
  return (
    <Component
      style={{
        position: "absolute",
        width: "1px",
        height: "1px",
        padding: 0,
        margin: "-1px",
        overflow: "hidden",
        clip: "rect(0, 0, 0, 0)",
        whiteSpace: "nowrap",
        border: 0,
      }}
    >
      {children}
    </Component>
  );
}
