import { useCallback, useSyncExternalStore } from "react";

import type { A11ySettings, ProfileId, SettableKey } from "../core/settings";
import { useA11yContext } from "./A11yProvider";

export interface UseA11yResult<T> {
  value: T;
  set: <K extends SettableKey>(key: K, value: A11ySettings[K]) => void;
  patch: (partial: Partial<Pick<A11ySettings, SettableKey>>) => void;
  applyProfile: (id: ProfileId) => void;
  clearProfile: () => void;
  resetKeys: (keys: readonly SettableKey[]) => void;
  reset: () => void;
}

export function useA11y(): UseA11yResult<Readonly<A11ySettings>>;
export function useA11y<T>(selector: (settings: Readonly<A11ySettings>) => T): UseA11yResult<T>;
export function useA11y<T>(
  selector?: (settings: Readonly<A11ySettings>) => T,
): UseA11yResult<T | Readonly<A11ySettings>> {
  const ctx = useA11yContext();

  const getSnapshot = useCallback(
    () => (selector ? selector(ctx.getSettings()) : ctx.getSettings()),
    [ctx, selector],
  );

  const value = useSyncExternalStore(ctx.subscribe, getSnapshot, getSnapshot);
  const { engine } = ctx;

  return {
    value,
    set: (key, next) => engine.set(key, next),
    patch: (partial) => engine.patch(partial),
    applyProfile: (id) => engine.applyProfile(id),
    clearProfile: () => engine.clearProfile(),
    resetKeys: (keys) => engine.resetKeys(keys),
    reset: () => {
      engine.speech.stop();
      engine.reset();
    },
  };
}
