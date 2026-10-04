import type { CSSProperties, MouseEvent } from "react";

export interface SkipLink {
  targetId: string;
  label: string;
}

export interface SkipLinksProps {
  links: SkipLink[];
  className?: string;
}

function focusTarget(targetId: string) {
  return (event: MouseEvent<HTMLAnchorElement>) => {
    event.preventDefault();
    const el = document.getElementById(targetId);
    if (!el) return;
    if (!el.hasAttribute("tabindex")) el.setAttribute("tabindex", "-1");
    el.focus();
    el.scrollIntoView();
  };
}

const linkStyle: CSSProperties = {
  position: "absolute",
  top: 0,
  left: 0,
  transform: "translateY(-150%)",
  transition: "transform 0.15s ease-out",
  background: "var(--a11y-focus-ring, #0b57d0)",
  color: "#fff",
  padding: "0.5rem 1rem",
  zIndex: 2147483000,
  borderRadius: "0 0 4px 0",
  textDecoration: "none",
};

export function SkipLinks({ links, className }: SkipLinksProps) {
  return (
    <nav aria-label="Skip links" className={className}>
      {links.map((link) => (
        <a
          key={link.targetId}
          href={`#${link.targetId}`}
          onClick={focusTarget(link.targetId)}
          style={linkStyle}
          onFocus={(e) => (e.currentTarget.style.transform = "translateY(0)")}
          onBlur={(e) => (e.currentTarget.style.transform = "translateY(-150%)")}
        >
          {link.label}
        </a>
      ))}
    </nav>
  );
}
