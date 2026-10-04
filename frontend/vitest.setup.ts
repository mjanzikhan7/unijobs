import "@testing-library/jest-dom/vitest";
import { cleanup } from "@testing-library/react";
import { afterEach, beforeEach, vi } from "vitest";

import { urlOf } from "./src/models/api/client";

afterEach(() => {
  cleanup();
  vi.restoreAllMocks();
});

beforeEach(() => {
  vi.spyOn(globalThis, "fetch").mockImplementation((input) => {
    throw new Error(`Unstubbed fetch to ${urlOf(input)}. Stub it in the test.`);
  });

  if (!("createObjectURL" in URL)) Object.assign(URL, { createObjectURL: vi.fn(() => "blob:test") });
  if (!("revokeObjectURL" in URL)) Object.assign(URL, { revokeObjectURL: vi.fn() });
});
