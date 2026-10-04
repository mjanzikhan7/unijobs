import { NavLink } from "react-router-dom";

import { CrawlRunningPip, ReviewQueueBadge } from "@/components/AdminNavBadges";
import { Icon } from "@/components/Icon/Icon";
import { groupNav } from "@/components/nav";
import type { NavItem } from "@/components/nav";

export interface SidebarProps {
  items: readonly NavItem[];
  collapsed?: boolean;
  isStaff?: boolean;
  onNavigate?: () => void;
}

const linkBase =
  "group flex items-center gap-2.5 rounded-sm px-3 py-2 text-body-sm font-medium " +
  "transition-[background-color,color,transform] duration-[var(--duration-fast)] ease-[var(--ease-out)] " +
  "hover:translate-x-0.5 motion-reduce:hover:translate-x-0 " +
  "focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 " +
  "focus-visible:outline-[var(--color-focus-ring)]";

export function Sidebar({ items, collapsed = false, isStaff = false, onNavigate }: SidebarProps) {
  const groups = groupNav(items);

  return (
    <nav aria-label="Primary" className="flex flex-col gap-5 py-4">
      {groups.map((group) => (
        <div key={group.section ?? "primary"}>
          {group.section ? (
            <h2
              className={`px-3 pb-1 text-overline font-semibold tracking-wide text-text-muted uppercase ${collapsed ? "sr-only" : ""}`}
            >
              {group.section}
            </h2>
          ) : null}
          <ul aria-label={group.section ?? undefined} className="flex flex-col gap-0.5">
            {group.items.map((item) => (
              <li key={item.to}>
                <NavLink
                  to={item.to}
                  end={item.end ?? false}
                  title={collapsed ? item.label : undefined}
                  onClick={onNavigate}
                  className={({ isActive }) =>
                    [
                      linkBase,
                      collapsed ? "justify-center px-0" : "",
                      isActive
                        ? "bg-brand-subtle text-brand"
                        : "text-text-secondary hover:bg-surface-sunken hover:text-text-primary",
                    ]
                      .filter(Boolean)
                      .join(" ")
                  }
                >
                  <Icon
                    name={item.icon}
                    className="transition-transform duration-[var(--duration-fast)] ease-[var(--ease-out)] group-hover:scale-110 motion-reduce:group-hover:scale-100"
                  />
                  <span className={collapsed ? "sr-only" : "truncate"}>{item.label}</span>
                  {isStaff && item.pip ? <CrawlRunningPip /> : null}
                  {isStaff && item.badge === "review" ? <ReviewQueueBadge /> : null}
                </NavLink>
              </li>
            ))}
          </ul>
        </div>
      ))}
    </nav>
  );
}
