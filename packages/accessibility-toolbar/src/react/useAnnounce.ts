import { useCallback } from "react";

import { useA11yContext } from "./A11yProvider";

export function useAnnounce() {
  const ctx = useA11yContext();
  return useCallback(
    (message: string, politeness: "polite" | "assertive" = "polite") => {
      ctx.engine.announce(message, politeness);
    },
    [ctx],
  );
}
