import { useEffect, useState } from "react";

export function useMinimumVisible(active: boolean, minMs = 400): boolean {
  const [previousActive, setPreviousActive] = useState(active);
  const [activation, setActivation] = useState(active ? 1 : 0);
  const [elapsedFor, setElapsedFor] = useState(0);

  if (active !== previousActive) {
    setPreviousActive(active);
    if (active) setActivation((count) => count + 1);
  }

  useEffect(() => {
    if (activation === 0) return;
    const timer = window.setTimeout(() => setElapsedFor(activation), minMs);
    return () => window.clearTimeout(timer);
  }, [activation, minMs]);

  return active || (activation > 0 && elapsedFor !== activation);
}
