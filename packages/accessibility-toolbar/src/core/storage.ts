import type { A11ySettings } from "./settings";

export interface StorageAdapter {
  read(): Promise<Partial<A11ySettings> | null>;
  write(settings: A11ySettings): Promise<void>;
  clear(): Promise<void>;
}

export type RemoteSyncAdapter = StorageAdapter;

const STORAGE_KEY = "unijobs.a11y";

export function createLocalStorageAdapter(key: string = STORAGE_KEY): StorageAdapter {
  return {
    async read() {
      try {
        const raw = window.localStorage.getItem(key);
        if (!raw) return null;
        return JSON.parse(raw) as Partial<A11ySettings>;
      } catch {
        return null;
      }
    },
    async write(settings) {
      try {
        window.localStorage.setItem(key, JSON.stringify(settings));
      } catch {
        // Persistence is best-effort; the in-memory setting still applies for this session.
      }
    },
    async clear() {
      try {
        window.localStorage.removeItem(key);
      } catch {
        // Nothing to do - there was nothing reliably stored to begin with.
      }
    },
  };
}

export function createNoopStorageAdapter(): StorageAdapter {
  return {
    async read() {
      return null;
    },
    async write() {
      // intentionally inert
    },
    async clear() {
      // intentionally inert
    },
  };
}

export { STORAGE_KEY };
