import { describe, it, expect } from "vitest";
import { adaptVisualDesignDirector } from "./design";
import {
  designFixtureNotStarted,
  designFixtureBuildRunning,
  designFixtureReview,
  designFixtureApproved,
  designFixtureNeedsAttention,
} from "./design.fixtures";

describe("adaptVisualDesignDirector", () => {
  it("locks not_started when Content Architect is not yet approved", () => {
    const view = adaptVisualDesignDirector(designFixtureNotStarted, false);
    expect(view.state).toBe("locked");
    expect(view.statusText).toBe("Locked until Content is approved");
  });

  it("unlocks to available when Content Architect is approved", () => {
    const view = adaptVisualDesignDirector(designFixtureNotStarted, true);
    expect(view.state).toBe("available");
    expect(view.statusText).toBe("Ready to direct visual experience");
  });

  it("maps build_running to working", () => {
    const view = adaptVisualDesignDirector(designFixtureBuildRunning, true);
    expect(view.state).toBe("working");
    expect(view.statusText).toBe("Developing the visual direction");
  });

  it("maps design_review to review and extracts visual language and page directions", () => {
    const view = adaptVisualDesignDirector(designFixtureReview, true);
    expect(view.state).toBe("review");
    expect(view.creativeThesis).toContain("Quiet confidence");
    expect(view.visualLanguage.designKeywords).toContain("swiss");
    expect(view.pages.length).toBe(2);
    expect(view.pages[0]?.routeId).toBe("route_home");
    expect(view.resources.length).toBe(1);
    expect(view.resources[0]?.resourceId).toBe("res_architecture_flow_01");
    expect(view.safeError).toBeNull();
  });

  it("maps approved to complete", () => {
    const view = adaptVisualDesignDirector(designFixtureApproved, true);
    expect(view.state).toBe("complete");
    expect(view.statusText).toBe("Visual direction approved");
  });

  it("maps needs_attention to attention and extracts error", () => {
    const view = adaptVisualDesignDirector(designFixtureNeedsAttention, true);
    expect(view.state).toBe("attention");
    expect(view.safeError?.summary).toBe("Resource catalog resolution failed for custom flow diagram.");
  });

  it("fails closed into unsupported for unknown or malformed status", () => {
    const view = adaptVisualDesignDirector({ status: "future_unsupported_status" }, true);
    expect(view.state).toBe("unsupported");
    expect(view.statusText).toContain("unrecognised state");
  });
});
