import { describe, it, expect } from "vitest";
import { adaptContentArchitect } from "./content";
import {
  contentFixtureNotStarted,
  contentFixtureBuildRunning,
  contentFixtureReview,
  contentFixtureApproved,
  contentFixtureNeedsAttention,
} from "./content.fixtures";

describe("adaptContentArchitect", () => {
  it("locks not_started when Discovery is not yet approved", () => {
    const view = adaptContentArchitect(contentFixtureNotStarted, false);
    expect(view.state).toBe("locked");
    expect(view.statusText).toBe("Locked until Discovery is approved");
  });

  it("unlocks to available when Discovery is approved", () => {
    const view = adaptContentArchitect(contentFixtureNotStarted, true);
    expect(view.state).toBe("available");
    expect(view.statusText).toBe("Ready to structure portfolio content");
  });

  it("maps build_running to working", () => {
    const view = adaptContentArchitect(contentFixtureBuildRunning, true);
    expect(view.state).toBe("working");
    expect(view.statusText).toBe("Structuring your portfolio content");
  });

  it("maps content_review to review and extracts structured sections", () => {
    const view = adaptContentArchitect(contentFixtureReview, true);
    expect(view.state).toBe("review");
    expect(view.routePlan.length).toBe(2);
    expect(view.routePlan[0]?.path).toBe("/");
    expect(view.routePlan[1]?.routeId).toBe("route_case_study_queueguard");
    expect(view.pageContentPacks.length).toBe(1);
    expect(view.pageContentPacks[0]?.sections[0]?.sectionId).toBe("hero");
    expect(view.decisionBasis.length).toBe(1);
    expect(view.warnings).toContain("Omitted internal employer metrics per privacy policy.");
    expect(view.safeError).toBeNull();
  });

  it("maps approved to complete", () => {
    const view = adaptContentArchitect(contentFixtureApproved, true);
    expect(view.state).toBe("complete");
    expect(view.statusText).toBe("Content plan approved");
  });

  it("maps needs_attention to attention and extracts error", () => {
    const view = adaptContentArchitect(contentFixtureNeedsAttention, true);
    expect(view.state).toBe("attention");
    expect(view.safeError?.summary).toBe("Generation model timed out while synthesizing page copy.");
  });

  it("fails closed into unsupported for unknown or malformed status", () => {
    const view = adaptContentArchitect({ status: "some_future_phase" }, true);
    expect(view.state).toBe("unsupported");
    expect(view.statusText).toContain("unrecognised state");
  });
});
