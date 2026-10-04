import Drawer from "@mui/material/Drawer";
import { useRef, useState } from "react";
import type { MouseEvent } from "react";
import { Link, Outlet, useLocation } from "react-router-dom";
import { useRouteAnnouncer } from "@unijobs/a11y/react";

import { Button } from "@/components/Button/Button";
import { Icon } from "@/components/Icon/Icon";
import { Sidebar } from "@/components/Sidebar/Sidebar";
import { SiteFooterLinks } from "@/components/SiteFooter/SiteFooter";
import { ThemeToggle } from "@/components/ThemeToggle";
import { navFor } from "@/components/nav";
import { useAuth } from "@/viewmodels/auth";
import { routeTitle } from "@/utilities/routeTitle";
import { useSidebarCollapsed } from "@/hooks/useSidebarCollapsed";

function Brand() {
  return <p className="font-display text-heading-sm font-semibold text-text-primary">UniJobs</p>;
}

const SKIP_LINK_CLASSNAME =
  "sr-only focus:not-sr-only focus:absolute focus:top-2 focus:left-2 focus:z-50 focus:rounded-md focus:bg-surface focus:px-4 focus:py-2 focus:shadow-md";

function focusAndScroll(targetId: string) {
  return (event: MouseEvent<HTMLAnchorElement>) => {
    const el = document.getElementById(targetId);
    if (!el) return;
    event.preventDefault();
    el.focus();
    el.scrollIntoView({ block: "start" });
  };
}

export function AppShell() {
  const { user, role, isStaff, signOut } = useAuth();
  const location = useLocation();
  const items = navFor(role);
  const { collapsed, toggleCollapsed } = useSidebarCollapsed();
  const [drawerOpen, setDrawerOpen] = useState(false);
  const hamburgerRef = useRef<HTMLButtonElement>(null);
  const mainRef = useRef<HTMLElement>(null);
  const isJobList = location.pathname === "/";

  useRouteAnnouncer({
    routeKey: location.pathname,
    title: routeTitle(location.pathname),
    focusTarget: mainRef,
  });

  return (
    <div className="min-h-screen bg-bg text-text-primary">
      <a href="#main" className={SKIP_LINK_CLASSNAME} onClick={focusAndScroll("main")}>
        Skip to content
      </a>
      {isJobList ? (
        <>
          <a href="#job-search" className={SKIP_LINK_CLASSNAME} onClick={focusAndScroll("job-search")}>
            Skip to search
          </a>
          <a href="#job-filters" className={SKIP_LINK_CLASSNAME} onClick={focusAndScroll("job-filters")}>
            Skip to filters
          </a>
        </>
      ) : null}
      <a href="#footer" className={SKIP_LINK_CLASSNAME} onClick={focusAndScroll("footer")}>
        Skip to footer
      </a>

      <div className="flex">
        <aside
          className={`sticky top-0 hidden h-screen shrink-0 overflow-y-auto border-r border-border-subtle bg-surface px-2 lg:block ${collapsed ? "w-[72px]" : "w-[264px]"}`}
        >
          <div
            className={`flex items-center gap-2 px-2 py-4 ${collapsed ? "justify-center" : "justify-between"}`}
          >
            {collapsed ? null : <Brand />}
            <Button
              variant="quiet"
              size="sm"
              onClick={toggleCollapsed}
              aria-expanded={!collapsed}
              aria-label={collapsed ? "Expand navigation" : "Collapse navigation"}
              title={collapsed ? "Expand navigation" : "Collapse navigation"}
            >
              <Icon name={collapsed ? "chevron-right" : "chevron-left"} />
            </Button>
          </div>
          <Sidebar items={items} collapsed={collapsed} isStaff={isStaff} />
        </aside>

        <div className="flex min-w-0 flex-1 flex-col">
          <header className="sticky top-0 z-20 flex items-center gap-3 border-b border-border-subtle bg-surface px-4 py-3">
            <Button
              ref={hamburgerRef}
              variant="quiet"
              size="sm"
              className="lg:hidden"
              onClick={() => setDrawerOpen(true)}
              aria-label="Open navigation"
              aria-expanded={drawerOpen}
            >
              <span className="relative block h-5 w-5">
                <Icon
                  name="menu"
                  className={`absolute inset-0 transition-[opacity,transform] duration-[var(--duration-base)] ease-[var(--ease-out)] ${
                    drawerOpen ? "rotate-90 opacity-0" : "rotate-0 opacity-100"
                  }`}
                />
                <Icon
                  name="close"
                  className={`absolute inset-0 transition-[opacity,transform] duration-[var(--duration-base)] ease-[var(--ease-out)] ${
                    drawerOpen ? "rotate-0 opacity-100" : "-rotate-90 opacity-0"
                  }`}
                />
              </span>
            </Button>
            <div className="lg:hidden">
              <Brand />
            </div>

            <div className="ml-auto flex items-center gap-3">
              {user ? (
                <Link
                  to="/profile"
                  title={`Signed in as ${user.username}`}
                  className="hidden rounded-sm px-1 text-body-sm text-text-secondary transition-colors duration-[var(--duration-fast)] ease-[var(--ease-out)] hover:text-text-primary hover:underline focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[var(--color-focus-ring)] sm:inline"
                >
                  {user.username}
                </Link>
              ) : null}
              <ThemeToggle />
              <Button variant="quiet" size="sm" onClick={() => void signOut()}>
                Sign out
              </Button>
            </div>
          </header>

          <main id="main" ref={mainRef} tabIndex={-1} className="min-w-0 flex-1 px-4 py-6">
            <div
              key={location.pathname}
              className="motion-safe:animate-[page-in_var(--duration-slow)_var(--ease-out)]"
            >
              <Outlet />
            </div>
          </main>

          <footer
            id="footer"
            tabIndex={-1}
            className="border-t border-border-subtle px-4 py-4 text-body-sm text-text-secondary"
          >
            <p>
              This tool never submits anything to an employer. Every Apply link opens the
              employer&apos;s own posting.
            </p>
            <SiteFooterLinks className="mt-1" />
          </footer>
        </div>
      </div>

      <Drawer
        open={drawerOpen}
        onClose={() => setDrawerOpen(false)}
        variant="temporary"
        onTransitionExited={() => hamburgerRef.current?.focus()}
        slotProps={{ paper: { sx: { width: 264, backgroundImage: "none" } } }}
      >
        <div className="flex items-center justify-between px-4 py-4">
          <Brand />
          <Button
            variant="quiet"
            size="sm"
            onClick={() => setDrawerOpen(false)}
            aria-label="Close navigation"
          >
            <Icon name="close" />
          </Button>
        </div>
        <div className="px-2">
          <Sidebar items={items} isStaff={isStaff} onNavigate={() => setDrawerOpen(false)} />
        </div>
      </Drawer>
    </div>
  );
}
