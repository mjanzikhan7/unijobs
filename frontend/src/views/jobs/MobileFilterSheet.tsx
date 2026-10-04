import Drawer from "@mui/material/Drawer";
import { useRef, useState } from "react";
import type { ReactNode } from "react";

import { Button } from "@/components/Button/Button";

export interface MobileFilterSheetProps {
  activeCount: number;
  children: ReactNode;
}

export function MobileFilterSheet({ activeCount, children }: MobileFilterSheetProps) {
  const [open, setOpen] = useState(false);
  const triggerRef = useRef<HTMLButtonElement>(null);

  return (
    <div className="lg:hidden">
      <Button
        ref={triggerRef}
        onClick={() => setOpen(true)}
        aria-expanded={open}
        className="w-full"
      >
        {activeCount > 0 ? `Filters (${activeCount})` : "Filters"}
      </Button>

      <Drawer
        anchor="bottom"
        open={open}
        onClose={() => setOpen(false)}
        variant="temporary"
        onTransitionExited={() => triggerRef.current?.focus()}
        slotProps={{ paper: { sx: { maxHeight: "85vh", backgroundImage: "none" } } }}
      >
        <div className="flex items-center justify-between border-b border-border-subtle px-4 py-3">
          <h2 className="font-display text-heading-sm font-semibold">Filters</h2>
          <Button size="sm" onClick={() => setOpen(false)}>
            Show results
          </Button>
        </div>
        <div className="overflow-y-auto px-4 py-4">{children}</div>
      </Drawer>
    </div>
  );
}
