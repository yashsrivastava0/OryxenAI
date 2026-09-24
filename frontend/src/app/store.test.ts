import { describe, expect, it } from "vitest";
import { adaptContentArchitect } from "../data/adapters/content";
import { contentFixtureReview } from "../data/adapters/content.fixtures";
import { adaptDiscovery } from "../data/adapters/discovery";
import { approved } from "../data/adapters/discovery.fixtures";
import { appReducer, initialAppState } from "./store";

describe("two-stage app store", () => {
  it("stores the authenticated identity", () => {
    const state = appReducer(initialAppState, {
      type: "me/set",
      me: {
        id: "user_1",
        username: "yash",
        role: "user",
        status: "active",
        onboarding_required: false,
        admin_available: false,
      },
    });
    expect(state.me?.username).toBe("yash");
  });

  it("stores the server session revision", () => {
    const state = appReducer(initialAppState, {
      type: "session/set",
      sessionId: "session_123",
      revision: 4,
    });
    expect(state.sessionId).toBe("session_123");
    expect(state.sessionRevision).toBe(4);
  });

  it("holds the Discovery and Content Architect projections", () => {
    const discovery = adaptDiscovery(approved);
    const content = adaptContentArchitect(contentFixtureReview, true);
    let state = appReducer(initialAppState, { type: "discovery/set", view: discovery });
    state = appReducer(state, { type: "content/set", view: content });
    state = appReducer(state, { type: "stage/select", stage: "content" });
    expect(state.discovery?.state).toBe("complete");
    expect(state.content?.state).toBe("review");
    expect(state.activeStage).toBe("content");
    expect(Object.keys(state)).not.toContain("preview");
  });

  it("resets both stages and returns to Discovery", () => {
    const populatedState = {
      ...initialAppState,
      sessionId: "session-123",
      sessionRevision: 5,
      activeStage: "content" as const,
      discovery: { state: "complete" } as any,
      content: { state: "working" } as any,
    };
    const reset = appReducer(populatedState, {
      type: "pipeline/reset",
      sessionId: "session-123",
      revision: 6,
    });
    expect(reset.sessionId).toBe("session-123");
    expect(reset.sessionRevision).toBe(6);
    expect(reset.activeStage).toBe("discover");
    expect(reset.discovery).toBeNull();
    expect(reset.content).toBeNull();
  });
});
