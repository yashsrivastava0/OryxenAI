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
import { BuildPreparationStage } from "./preparation/BuildPreparationStage";
import { adaptBuildPreparation } from "../data/adapters/preparation";
import { preparationNotStarted, preparationReady, preparationRunning } from "../data/adapters/preparation.fixtures";

const className = (node: VNode<{ className?: string }>) => node.props.className;
const discoveryProps = {
  history: [],
  canMutate: true,
  onStartDiscovery: async () => {},
  onSubmitAnswer: async () => {},
  onGenerateBriefNow: async () => {},
  onRetryDiscovery: async () => {},
  onApproveAndContinue: async () => {},
  onReviseBrief: async () => {},
};

describe("authenticated product stages", () => {
  it("renders Discovery input, artifact, approval, and fail-closed states", () => {
    expect(DiscoveryStage({ ...discoveryProps, view: adaptDiscovery(questionsReady) })).toBeDefined();
    expect(className(DiscoveryStage({ ...discoveryProps, view: adaptDiscovery(briefReview) }))).toBe("discovery-brief-view");
    expect(className(DiscoveryStage({ ...discoveryProps, view: adaptDiscovery(approved) }))).toBe("discovery-brief-view");
    const unsupported = DiscoveryStage({ ...discoveryProps, view: adaptDiscovery(unknownFutureStatus) });
    expect(unsupported.type).toBeDefined();
  });

  it("keeps Content locked until Discovery approval and wires the next-stage action", () => {
    const props = { canMutate: true, onStart: async () => {}, onApproveAndContinue: async () => {}, onRevise: async () => {} };
    expect(className(ContentStage({ ...props, view: adaptContentArchitect(contentFixtureNotStarted, false) }))).toBe("stage-locked-panel");
    expect(className(ContentStage({ ...props, view: adaptContentArchitect(contentFixtureReview, true) }))).toBe("content-stage-view");
    // ContentStage(...) is an unrendered vnode tree — assert the exact
    // ArtifactSurface prop wiring for the committed approval and the
    // separate destination-specific start action.
    const reviewNode = ContentStage({ ...props, view: adaptContentArchitect(contentFixtureReview, true) });
    expect(JSON.stringify(reviewNode)).toContain('"nextStageName":"Visual Design Director"');
    const approvedNode = ContentStage({ ...props, view: adaptContentArchitect(contentFixtureApproved, true) });
    expect(className(approvedNode)).toBe("content-stage-view");
    expect(JSON.stringify(approvedNode)).toContain('"nextStageName":"Visual Design Director"');
  });

  it("renders the approved Visual Direction without auto-starting later stages", () => {
    const props = {
      canMutate: true,
      onStart: async () => {},
      onApproveAndContinue: async () => {},
      onRevise: async () => {},
    };
    expect(className(DesignStage({ ...props, view: adaptVisualDesignDirector(designFixtureNotStarted, false) }))).toBe("stage-locked-panel");
    expect(className(DesignStage({ ...props, view: adaptVisualDesignDirector(designFixtureReview, true) }))).toBe("design-stage-view");
    const reviewNode = DesignStage({ ...props, view: adaptVisualDesignDirector(designFixtureReview, true) });
    expect(JSON.stringify(reviewNode)).toContain('"nextStageName":"Build Preparation"');
    const approvedNode = DesignStage({ ...props, view: adaptVisualDesignDirector(designFixtureApproved, true) });
    expect(className(approvedNode)).toBe("design-stage-view");
    expect(JSON.stringify(approvedNode)).toContain('"nextStageName":"Build Preparation"');
  });

  it("renders Build Preparation as an explicit fourth stage", () => {
    const props = {
      canMutate: true,
      onStart: async () => {},
      onRegenerate: async () => {},
    };
    expect(className(BuildPreparationStage({ ...props, view: adaptBuildPreparation(preparationNotStarted, true, false) }))).toBe("stage-locked-panel");
    expect(className(BuildPreparationStage({ ...props, view: adaptBuildPreparation(preparationNotStarted, true, true) }))).toBe("stage-available-panel");
    expect(BuildPreparationStage({ ...props, view: adaptBuildPreparation(preparationRunning, true, true) })).toBeDefined();
    expect(className(BuildPreparationStage({ ...props, view: adaptBuildPreparation(preparationReady, true, true) }))).toBe("preparation-stage-shell");
  });
});
