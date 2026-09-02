import { describe, expect, it } from "vitest";
import { parseAppUrlState, serializeAppUrlState } from "./url-state";

describe("parseAppUrlState", () => {
  it("parses a valid stage", () => {
    expect(parseAppUrlState("?stage=content")).toEqual({ stage: "content", view: null, route: null, viewport: null });
  });

  it("drops an invalid stage value", () => {
    expect(parseAppUrlState("?stage=nonsense")).toEqual({ stage: null, view: null, route: null, viewport: null });
  });

  it("prefers view=preview over a simultaneous stage", () => {
    const result = parseAppUrlState("?stage=content&view=preview&route=%2Fprojects&viewport=mobile");
    expect(result.stage).toBeNull();
    expect(result.view).toBe("preview");
    expect(result.route).toBe("/projects");
    expect(result.viewport).toBe("mobile");
  });

  it("drops view when stage is present and view is not preview", () => {
    expect(parseAppUrlState("?stage=design&view=work")).toEqual({ stage: "design", view: null, route: null, viewport: null });
  });

  it("rejects a route value that is not an absolute path", () => {
    expect(parseAppUrlState("?view=preview&route=projects").route).toBeNull();
  });

  it("rejects a route value with directory traversal or backslashes", () => {
    expect(parseAppUrlState("?view=preview&route=%2F..%2Fadmin").route).toBeNull();
    expect(parseAppUrlState("?view=preview&route=%5Cadmin").route).toBeNull();
  });

  it("drops an invalid viewport value", () => {
    expect(parseAppUrlState("?view=preview&viewport=huge").viewport).toBeNull();
  });
});

describe("serializeAppUrlState", () => {
  it("serializes a stage", () => {
    expect(serializeAppUrlState({ stage: "prepare" })).toBe("?stage=prepare");
  });

  it("serializes a preview view with route and viewport", () => {
    expect(serializeAppUrlState({ view: "preview", route: "/projects", viewport: "tablet" })).toBe(
      "?view=preview&route=%2Fprojects&viewport=tablet",
    );
  });

  it("returns an empty string for the default view", () => {
    expect(serializeAppUrlState({})).toBe("");
  });

  it("round-trips through parse", () => {
    const original = { stage: "generate" as const, view: null, route: null, viewport: null };
    expect(parseAppUrlState(serializeAppUrlState(original))).toEqual(original);
  });
});
