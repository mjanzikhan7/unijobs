import { createContext, useContext, useEffect, useMemo, useRef, useSyncExternalStore } from "react";
import type { ReactNode } from "react";

import { A11yEngine, type A11yEngineOptions } from "../core/engine";
import type { A11ySettings } from "../core/settings";
import { createLiveAnnouncer } from "./liveRegion";

export interface A11yContextValue {
  engine: A11yEngine;
  getSettings: () => Readonly<A11ySettings>;
  subscribe: (onChange: () => void) => () => void;
}

export const A11yContext = createContext<A11yContextValue | null>(null);

export interface A11yProviderProps {
  children: ReactNode;
  options?: Omit<A11yEngineOptions, "announce">;
}

export function A11yProvider({ children, options }: A11yProviderProps) {
  const engineRef = useRef<A11yEngine | null>(null);
  if (!engineRef.current) {
    const { announce } = createLiveAnnouncer();
    engineRef.current = new A11yEngine({ ...options, announce });
  }
  const engine = engineRef.current;

  useEffect(() => {
    void engine.init();
    return () => engine.destroy();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const value = useMemo<A11yContextValue>(
    () => ({
      engine,
      getSettings: () => engine.settings,
      subscribe: (onChange) => engine.subscribe(onChange),
    }),
    [engine],
  );

  return <A11yContext.Provider value={value}>{children}</A11yContext.Provider>;
}

export function useA11yContext(): A11yContextValue {
  const ctx = useContext(A11yContext);
  if (!ctx) throw new Error("useA11y() must be used inside <A11yProvider>");
  return ctx;
}

export function useA11ySnapshot(): Readonly<A11ySettings> {
  const ctx = useA11yContext();
  return useSyncExternalStore(ctx.subscribe, ctx.getSettings, ctx.getSettings);
}
