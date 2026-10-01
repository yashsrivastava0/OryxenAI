import { describe, expect, it } from "vitest";
import { cardIdForPath, normalizeFieldPath } from "./content-paths";

describe("content field paths", () => {
  it("normalizes bracket and dotted indexes alike", () => {
    expect(normalizeFieldPath("a.b[2].c")).toEqual(["a", "b", "2", "c"]);
    expect(normalizeFieldPath("a.b.2.c")).toEqual(["a", "b", "2", "c"]);
  });

  it("resolves to the most specific existing card", () => {
    const ids = new Set(["content-card-systems_practice", "content-card-systems_practice.pillars.1"]);
    expect(cardIdForPath("systems_practice.pillars[1].description", ids)).toBe(
      "content-card-systems_practice.pillars.1",
    );
    expect(cardIdForPath("systems_practice.heading", ids)).toBe("content-card-systems_practice");
    expect(cardIdForPath("unknown.path", ids)).toBeNull();
  });
});
