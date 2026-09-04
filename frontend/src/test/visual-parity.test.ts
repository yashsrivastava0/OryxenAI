import { describe, expect, it } from "vitest";
import { adaptContentArchitect } from "../data/adapters/content";
import { contentFixtureApproved, contentFixtureReview } from "../data/adapters/content.fixtures";
import { adaptVisualDesignDirector } from "../data/adapters/design";
import { designFixtureApproved, designFixtureReview } from "../data/adapters/design.fixtures";
import { adaptDiscovery } from "../data/adapters/discovery";
import { approved, briefReview, questionsReady } from "../data/adapters/discovery.fixtures";

describe("three-stage contract parity", () => {
  it("covers the Discovery input, review, and approved lifecycle", () => {
    expect(adaptDiscovery(questionsReady).state).toBe("input");
    expect(adaptDiscovery(briefReview).state).toBe("review");
    expect(adaptDiscovery(approved).state).toBe("complete");
  });

  it("preserves Content Architect routes and approval", () => {
    expect(adaptContentArchitect(contentFixtureReview, true).routePlan.length).toBeGreaterThan(0);
    expect(adaptContentArchitect(contentFixtureApproved, true).state).toBe("complete");
  });

  it("preserves Visual Design direction and approval", () => {
    expect(adaptVisualDesignDirector(designFixtureReview, true).resources.length).toBeGreaterThan(0);
    expect(adaptVisualDesignDirector(designFixtureApproved, true).state).toBe("complete");
  });
});
