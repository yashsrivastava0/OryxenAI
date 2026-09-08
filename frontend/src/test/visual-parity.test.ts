import { describe, expect, it } from "vitest";
import { adaptContentArchitect } from "../data/adapters/content";
import { contentFixtureApproved, contentFixtureReview } from "../data/adapters/content.fixtures";
import { adaptVisualDesignDirector } from "../data/adapters/design";
import { designFixtureApproved, designFixtureReview } from "../data/adapters/design.fixtures";
import { adaptDiscovery } from "../data/adapters/discovery";
import { approved, briefReview, questionsReady } from "../data/adapters/discovery.fixtures";
import { JourneyRail } from "../components/JourneyRail";

describe("four-stage contract parity", () => {
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

  it("renders the 6-stage Living Draft rail with all 6 pipeline stages", () => {
    const vnode = JourneyRail({
      journey: [
        { id: "discover", ordinal: 1, label: "Discover", state: "available", isSelectable: true },
        { id: "content", ordinal: 2, label: "Content", state: "locked", isSelectable: false },
        { id: "design", ordinal: 3, label: "Design", state: "locked", isSelectable: false },
        { id: "prepare", ordinal: 4, label: "Prepare", state: "locked", isSelectable: false },
        { id: "generate", ordinal: 5, label: "Generate", state: "locked", isSelectable: false },
        { id: "preview", ordinal: 6, label: "Preview", state: "locked", isSelectable: false },
      ],
      selectedStageId: "discover",
      onSelect: () => {},
    });
    expect(vnode).toBeDefined();
    expect(vnode.props["aria-label"]).toBe("Portfolio journey");
  });
});
