import { describe, it, expect } from "vitest";
import { parseAppUrlState, serializeAppUrlState } from "./url-state";

describe("parseAppUrlState", () => {
  it("parses valid stage and view", () => {
    const state = parseAppUrlState("?stage=discover&view=work");
    expect(state).toEqual({ stage: "discover", view: "work", route: null, viewport: null });
  });

  it("parses content stage and artifact view", () => {
    const state = parseAppUrlState("?stage=content&view=artifact");
    expect(state).toEqual({ stage: "content", view: "artifact", route: null, viewport: null });
  });

  it("normalizes preview view", () => {
    const state = parseAppUrlState("?view=preview&route=%2Fprojects&viewport=mobile");
    expect(state).toEqual({ stage: "preview", view: "preview", route: "/projects", viewport: "mobile" });
  });

  it("drops unknown stage and view keys", () => {
    const state = parseAppUrlState("?stage=bogus&view=unknown");
    expect(state).toEqual({ stage: null, view: null, route: null, viewport: null });
  });

  it("rejects path-traversal or backslash routes", () => {
    const state = parseAppUrlState("?view=preview&route=..%2Fescape");
    expect(state.route).toBeNull();
  });
});

describe("serializeAppUrlState", () => {
  it("serializes stage and view", () => {
    const qs = serializeAppUrlState({ stage: "content", view: "artifact" });
    expect(qs).toBe("?stage=content&view=artifact");
  });

  it("serializes preview parameters", () => {
    const qs = serializeAppUrlState({ view: "preview", route: "/about", viewport: "tablet" });
    expect(qs).toBe("?view=preview&route=%2Fabout&viewport=tablet");
  });

  it("returns empty string when no allowed keys are set", () => {
    const qs = serializeAppUrlState({});
    expect(qs).toBe("");
  });
});
