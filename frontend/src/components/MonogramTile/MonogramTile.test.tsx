import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { MonogramTile, initialsOf } from "./MonogramTile";

describe("initialsOf", () => {
  it.each([
    ["University of Test", "UT"],
    ["Northgate University", "NU"],
    ["The Open University", "OU"],
    ["Brackenfield Institute of Technology", "BI"],
    ["Royal Holloway, University of London", "RH"],
    ["Newcastle-upon-Tyne College", "NU"],
  ])("reduces %s to %s", (name, expected) => {
    expect(initialsOf(name)).toBe(expected);
  });

  it("takes two letters from a single-word name", () => {
    expect(initialsOf("Cranfield")).toBe("CR");
  });

  it("does not fall over on a name with nothing usable in it", () => {
    expect(initialsOf("   ")).toBe("?");
    expect(initialsOf("——")).toBe("?");
  });
});

describe("MonogramTile", () => {
  it("stays out of the accessibility tree — the name is beside it as real text", () => {
    render(
      <>
        <MonogramTile name="University of Test" />
        <span>University of Test</span>
      </>,
    );

    expect(screen.getByText("UT")).toHaveAttribute("aria-hidden", "true");
    expect(screen.getAllByText("University of Test")).toHaveLength(1);
  });
});
