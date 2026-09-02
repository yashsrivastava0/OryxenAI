import { describe, it, expect } from "vitest";
import { appReducer, initialAppState } from "./store";
import { adaptContentArchitect } from "../data/adapters/content";
import { adaptVisualDesignDirector } from "../data/adapters/design";
import { contentFixtureReview } from "../data/adapters/content.fixtures";
import { designFixtureReview } from "../data/adapters/design.fixtures";

describe("appReducer", () => {
  it("handles me/set action correctly", () => {
    const state = appReducer(initialAppState, {
      type: "me/set",
      me: {
        id: "user_1",
        username: "yash",
        role: "user",
        status: "active",
        onboarding_required: false,
        admin_available: false,
        read_only: true,
      },
    });
    expect(state.me?.username).toBe("yash");
    expect(state.readOnly).toBe(true);
  });

  it("handles session/set action", () => {
    const state = appReducer(initialAppState, {
      type: "session/set",
      sessionId: "session_123",
      revision: 4,
    });
    expect(state.sessionId).toBe("session_123");
    expect(state.sessionRevision).toBe(4);
  });

  it("handles stage/select, content/set, and design/set actions", () => {
    const content = adaptContentArchitect(contentFixtureReview, true);
    const design = adaptVisualDesignDirector(designFixtureReview, true);

    let state = appReducer(initialAppState, { type: "content/set", view: content });
    state = appReducer(state, { type: "design/set", view: design });
    state = appReducer(state, { type: "stage/select", stage: "content" });

    expect(state.content?.state).toBe("review");
    expect(state.design?.state).toBe("review");
    expect(state.activeStage).toBe("content");
  });

  it("handles preparation/set and generation/set actions", () => {
    const prep = {
      state: "working" as const,
      statusText: "Packaging and verifying handoff",
      currentMilestone: "Packaging and verifying handoff",
      milestones: [],
      routeCount: 2,
      warnings: [],
      stale: false,
      staleReasons: [],
      handoffEligible: false,
      safeError: null,
      elapsedSeconds: 15,
      raw: {},
    };

    const gen = {
      state: "working" as const,
      statusText: "Building portfolio routes",
      currentMilestone: "Building portfolio routes",
      milestones: [],
      activePreview: null,
      hasUsablePreview: false,
      safeError: null,
      stale: false,
      retryEligible: false,
      elapsedSeconds: 30,
      supportReference: "trace_123",
      issues: [],
      raw: {},
    };

    let state = appReducer(initialAppState, { type: "preparation/set", view: prep });
    state = appReducer(state, { type: "generation/set", view: gen });

    expect(state.preparation?.state).toBe("working");
    expect(state.preparation?.statusText).toBe("Packaging and verifying handoff");
    expect(state.generation?.state).toBe("working");
    expect(state.generation?.supportReference).toBe("trace_123");
  });
});
