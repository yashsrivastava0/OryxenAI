import { describe, expect, it } from "vitest";
import { adaptContentArchitect } from "../data/adapters/content";
import { contentFixtureReview } from "../data/adapters/content.fixtures";
import { adaptVisualDesignDirector } from "../data/adapters/design";
import { designFixtureReview } from "../data/adapters/design.fixtures";
import { appReducer, initialAppState } from "./store";

describe("three-stage app store", () => {
  it("stores authenticated identity and read-only state", () => {
    const state = appReducer(initialAppState, {
      type: "me/set",
      me: { id: "user_1", username: "yash", role: "user", status: "active", onboarding_required: false, admin_available: false, read_only: true },
    });
    expect(state.me?.username).toBe("yash");
    expect(state.readOnly).toBe(true);
  });

  it("stores a server session revision", () => {
    const state = appReducer(initialAppState, { type: "session/set", sessionId: "session_123", revision: 4 });
    expect(state.sessionId).toBe("session_123");
    expect(state.sessionRevision).toBe(4);
  });

  it("holds only Discovery, Content, and Design projections", () => {
    const content = adaptContentArchitect(contentFixtureReview, true);
    const design = adaptVisualDesignDirector(designFixtureReview, true);
    let state = appReducer(initialAppState, { type: "content/set", view: content });
    state = appReducer(state, { type: "design/set", view: design });
    state = appReducer(state, { type: "stage/select", stage: "content" });
    expect(state.content?.state).toBe("review");
    expect(state.design?.state).toBe("review");
    expect(state.activeStage).toBe("content");
    expect(Object.keys(state)).not.toContain("preparation");
    expect(Object.keys(state)).not.toContain("generation");
    expect(Object.keys(state)).not.toContain("preview");
  });
});
