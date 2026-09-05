import { describe, expect, it } from "vitest";
import type { VNode } from "preact";
import { adaptContentArchitect } from "../data/adapters/content";
import { contentFixtureApproved, contentFixtureNotStarted, contentFixtureReview } from "../data/adapters/content.fixtures";
import { adaptVisualDesignDirector } from "../data/adapters/design";
import { designFixtureApproved, designFixtureNotStarted, designFixtureReview } from "../data/adapters/design.fixtures";
import { adaptDiscovery } from "../data/adapters/discovery";
import { approved, briefReview, questionsReady, unknownFutureStatus } from "../data/adapters/discovery.fixtures";
import { ContentStage } from "./content/ContentStage";
import { DesignStage } from "./design/DesignStage";
import { DiscoveryStage } from "./discovery/DiscoveryStage";

const className = (node: VNode<{ className?: string }>) => node.props.className;
const discoveryProps = {
  history: [],
  canMutate: true,
  onStartDiscovery: async () => {},
  onSubmitAnswer: async () => {},
  onGenerateBriefNow: async () => {},
  onRetryDiscovery: async () => {},
  onApproveBrief: async () => {},
  onReviseBrief: async () => {},
  onContinueToContent: () => {},
};

describe("authenticated product stages", () => {
  it("renders Discovery input, artifact, approval, and fail-closed states", () => {
    expect(DiscoveryStage({ ...discoveryProps, view: adaptDiscovery(questionsReady) })).toBeDefined();
    expect(className(DiscoveryStage({ ...discoveryProps, view: adaptDiscovery(briefReview) }))).toBe("discovery-brief-view");
    expect(className(DiscoveryStage({ ...discoveryProps, view: adaptDiscovery(approved) }))).toBe("discovery-brief-view");
    const unsupported = DiscoveryStage({ ...discoveryProps, view: adaptDiscovery(unknownFutureStatus) });
    expect(unsupported.type).toBeDefined();
  });

  it("keeps Content locked until Discovery approval and renders approved handoff", () => {
    const props = { canMutate: true, onStart: async () => {}, onApprove: async () => {}, onRevise: async () => {}, onContinueToDesign: () => {} };
    expect(className(ContentStage({ ...props, view: adaptContentArchitect(contentFixtureNotStarted, false) }))).toBe("stage-locked-panel");
    expect(className(ContentStage({ ...props, view: adaptContentArchitect(contentFixtureReview, true) }))).toBe("content-stage-view");
    expect(className(ContentStage({ ...props, view: adaptContentArchitect(contentFixtureApproved, true) }))).toBe("content-stage-view");
  });

  it("ends the product at an approved Visual Direction", () => {
    const props = { canMutate: true, onStart: async () => {}, onApprove: async () => {}, onRevise: async () => {} };
    expect(className(DesignStage({ ...props, view: adaptVisualDesignDirector(designFixtureNotStarted, false) }))).toBe("stage-locked-panel");
    expect(className(DesignStage({ ...props, view: adaptVisualDesignDirector(designFixtureReview, true) }))).toBe("design-stage-view");
    const approvedNode = DesignStage({ ...props, view: adaptVisualDesignDirector(designFixtureApproved, true) });
    expect(className(approvedNode)).toBe("design-stage-view");
    expect(JSON.stringify(approvedNode)).not.toContain("Prepare the build");
  });
});
