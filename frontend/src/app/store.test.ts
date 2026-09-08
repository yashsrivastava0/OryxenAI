import { describe, expect, it } from "vitest";
import { adaptContentArchitect } from "../data/adapters/content";
import { contentFixtureReview } from "../data/adapters/content.fixtures";
import { adaptVisualDesignDirector } from "../data/adapters/design";
import { designFixtureReview } from "../data/adapters/design.fixtures";
import { appReducer, initialAppState } from "./store";

describe("five-stage app store", () => {
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

  it("holds the five product-stage projections, uninitialized until each stage responds", () => {
    const content = adaptContentArchitect(contentFixtureReview, true);
    const design = adaptVisualDesignDirector(designFixtureReview, true);
    let state = appReducer(initialAppState, { type: "content/set", view: content });
    state = appReducer(state, { type: "design/set", view: design });
    state = appReducer(state, { type: "stage/select", stage: "content" });
    expect(state.content?.state).toBe("review");
    expect(state.design?.state).toBe("review");
    expect(state.activeStage).toBe("content");
    expect(state.preparation).toBeNull();
    expect(state.generation).toBeNull();
    // "preview" was never a separate store field -- Generate & Preview (D-081)
    // is one merged stage, keyed as "generation".
    expect(Object.keys(state)).not.toContain("preview");
  });

  it("sets the Generate & Preview projection (D-081)", () => {
    const state = appReducer(initialAppState, {
      type: "generation/set",
      view: {
        state: "available",
        statusText: "Ready to generate the portfolio",
        raw: {},
        job: null,
        agentOutput: null,
        status: "not_started",
        stale: false,
        staleReasons: [],
        currentMilestone: "",
        preview: null,
        candidatePreview: null,
        warnings: [],
        safeError: null,
      },
    });
    expect(state.generation?.state).toBe("available");
  });

  it("resets all stages and returns to discover on pipeline/reset", () => {
    const populatedState = {
      ...initialAppState,
      sessionId: "session-123",
      sessionRevision: 5,
      activeStage: "design" as const,
      discovery: { state: "complete" } as any,
      content: { state: "complete" } as any,
      design: { state: "working" } as any,
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
    expect(reset.design).toBeNull();
    expect(reset.preparation).toBeNull();
    expect(reset.generation).toBeNull();
  });
});
