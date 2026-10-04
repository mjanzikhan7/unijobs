import { describe, expect, it } from "vitest";

import { groupNav, navFor } from "./nav";
import type { Role } from "@/viewmodels/auth";

const paths = (role: Role | null) => navFor(role).map((item) => item.to);

describe("navFor", () => {
  it("gives a candidate only their own screens", () => {
    expect(paths("CANDIDATE")).toEqual([
      "/",
      "/institutions",
      "/saved",
      "/pipeline",
      "/profile/cv",
      "/profile",
    ]);
  });

  it("shows a candidate nothing under /admin", () => {
    expect(paths("CANDIDATE").some((path) => path.startsWith("/admin"))).toBe(false);
  });

  it("gives a manager the operator screens too", () => {
    expect(paths("MANAGER")).toContain("/admin/crawl");
    expect(paths("MANAGER")).toContain("/admin/review");
    expect(paths("MANAGER")).toContain("/admin/insights");
  });

  it("withholds users and thresholds from a manager", () => {
    expect(paths("MANAGER")).not.toContain("/admin/users");
    expect(paths("MANAGER")).not.toContain("/admin/thresholds");
  });

  it("gives an admin everything", () => {
    expect(paths("ADMIN")).toContain("/admin/users");
    expect(paths("ADMIN")).toContain("/admin/thresholds");
    expect(paths("ADMIN")).toContain("/admin/crawl");
  });

  it("falls back to the candidate nav when the role is not known yet", () => {
    expect(paths(null)).toEqual(paths("CANDIDATE"));
  });

  it("keeps the candidate screens first, in the same order, for every role", () => {
    const candidate = paths("CANDIDATE");
    expect(paths("MANAGER").slice(0, candidate.length)).toEqual(candidate);
    expect(paths("ADMIN").slice(0, candidate.length)).toEqual(candidate);
  });

  it("marks the routes that would otherwise match their own children", () => {
    const exact = navFor("ADMIN").filter((item) => item.end);
    expect(exact.map((item) => item.to)).toEqual(["/", "/profile", "/admin/insights"]);
  });

  it("puts the running-crawl pip and the review badge on one item each", () => {
    const items = navFor("ADMIN");
    expect(items.filter((item) => item.pip).map((item) => item.to)).toEqual(["/admin/crawl"]);
    expect(items.filter((item) => item.badge).map((item) => item.to)).toEqual(["/admin/review"]);
  });

  it("never repeats a destination", () => {
    const all = paths("ADMIN");
    expect(new Set(all).size).toBe(all.length);
  });

  it("gives a recruiter only their own institution's screens", () => {
    expect(paths("RECRUITER")).toEqual([
      "/",
      "/institutions",
      "/admin/jobs",
      "/recruiter/institution",
      "/profile",
    ]);
  });

  it("withholds a manager's estate-wide screens from a recruiter", () => {
    expect(paths("RECRUITER")).not.toContain("/admin/crawl");
    expect(paths("RECRUITER")).not.toContain("/admin/review");
    expect(paths("RECRUITER")).not.toContain("/admin/institutions");
  });
});

describe("groupNav", () => {
  const sections = (role: Role | null) => groupNav(navFor(role)).map((group) => group.section);

  it("leads with the ungrouped daily screens", () => {
    const groups = groupNav(navFor("CANDIDATE"));

    expect(groups[0]?.section).toBeNull();
    expect(groups[0]?.items.map((item) => item.to)).toEqual(["/", "/saved", "/pipeline"]);
  });

  it("drops a group the role has no items in", () => {
    expect(sections("CANDIDATE")).toEqual([null, "Explore", "You"]);
  });

  it("gives an admin every group, in a fixed order", () => {
    expect(sections("ADMIN")).toEqual([
      null,
      "Explore",
      "You",
      "Operations",
      "Analytics",
      "Administration",
    ]);
  });

  it("keeps every destination — grouping hides nothing", () => {
    for (const role of ["CANDIDATE", "MANAGER", "ADMIN", "RECRUITER"] as const) {
      const flat = navFor(role).map((item) => item.to);
      const grouped = groupNav(navFor(role)).flatMap((group) => group.items.map((item) => item.to));

      expect(grouped.slice().sort()).toEqual(flat.slice().sort());
    }
  });

  it("puts no item in two groups at once", () => {
    const grouped = groupNav(navFor("ADMIN")).flatMap((group) => group.items.map((item) => item.to));
    expect(new Set(grouped).size).toBe(grouped.length);
  });
});
