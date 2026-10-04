/// <reference types="node" />
import { readFileSync } from "node:fs";
import { dirname, resolve } from "node:path";
import { fileURLToPath } from "node:url";

import { describe, expect, it } from "vitest";

import { TOOLBAR_HOST_ID } from "../src/core/constants";

const css = readFileSync(resolve(dirname(fileURLToPath(import.meta.url)), "../src/styles/styles.css"), "utf8");

function selectorsOutsideAttributeGates(source: string): string[] {
  const withoutComments = source.replace(/\/\*[\s\S]*?\*\//g, "");
  const selectors = Array.from(withoutComments.matchAll(/([^{};]+)\{/g), (match) => match[1]!.trim());
  return selectors.filter(
    (selector) =>
      selector !== "" &&
      !selector.startsWith("@") &&
      !selector.startsWith("::highlight") &&
      !selector.includes("data-a11y-"),
  );
}

describe("styles.css", () => {
  it("excludes the same toolbar host id the code creates", () => {
    expect(css).toContain(`#${TOOLBAR_HOST_ID}`);
  });

  it("changes nothing on the page until a data-a11y attribute is present", () => {
    expect(selectorsOutsideAttributeGates(css)).toEqual([]);
  });

  it("scales text from the root, so rem-sized text grows too", () => {
    expect(css).toMatch(/html\[data-a11y-text-scale\]\s*\{\s*font-size:\s*calc\(100% \* var\(--a11y-font-scale/);
  });
});
