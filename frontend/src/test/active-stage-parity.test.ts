import { describe, expect, it } from "vitest";
import { adaptContentArchitect } from "../data/adapters/content";
import { contentFixtureApproved, contentFixtureReview } from "../data/adapters/content.fixtures";
import { adaptDiscovery } from "../data/adapters/discovery";
import { approved, briefReview, questionsReady } from "../data/adapters/discovery.fixtures";
import { JourneyRail } from "../components/JourneyRail";

describe("active-stage contract parity", () => {
  it("covers the Discovery input, review, and approved lifecycle", () => {
    expect(adaptDiscovery(questionsReady).state).toBe("input");
    expect(adaptDiscovery(briefReview).state).toBe("review");
    expect(adaptDiscovery(approved).state).toBe("complete");
  });

  it("preserves Content Architect routes and approval", () => {
    expect(adaptContentArchitect(contentFixtureReview, true).routePlan.length).toBeGreaterThan(0);
    expect(adaptContentArchitect(contentFixtureApproved, true).state).toBe("complete");
  });

  it("renders the two active stages in the journey rail", () => {
    const vnode = JourneyRail({
      journey: [
        { id: "discover", ordinal: 1, label: "Discover", state: "available", isSelectable: true },
        { id: "content", ordinal: 2, label: "Content", state: "locked", isSelectable: false },
      ],
      selectedStageId: "discover",
      onSelect: () => {},
    });
    expect(vnode).toBeDefined();
    expect(vnode.props["aria-label"]).toBe("Portfolio journey");
  });
});
