import { describe, expect, it } from "vitest";
import { h, type VNode } from "preact";
import { renderToString } from "preact-render-to-string";
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
import { GenerationStage } from "./generation/GenerationStage";
import { adaptCodeGenerator } from "../data/adapters/generation";
import {
  generationNeedsAttentionWithPreview,
  generationNotStarted,
  generationReady,
  generationWorking,
} from "../data/adapters/generation.fixtures";

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

  it("renders GenerationStage control room across Available, Working, Attention and Complete", () => {
    const genProps = {
      canMutate: true,
      sessionId: "session-test-456",
      onStart: async () => {},
      onRetry: async () => {},
      onRegenerate: async () => {},
    };

    // 1. Locked when Build Preparation is not complete
    const lockedHtml = renderToString(
      h(GenerationStage, { ...genProps, view: adaptCodeGenerator(generationNotStarted, false) })
    );
    expect(lockedHtml).toContain("stage-locked-panel");
    expect(lockedHtml).toContain("Stage Locked");

    // 2. Available matching Image 13 (split control room, Desktop viewport, 5 milestones)
    const availHtml = renderToString(
      h(GenerationStage, { ...genProps, view: adaptCodeGenerator(generationNotStarted, true) })
    );
    expect(availHtml).toContain("codegen-workspace");
    expect(availHtml).toContain("Ready to build your portfolio.");
    expect(availHtml).toContain("BUILD WORKSPACE");
    expect(availHtml).toContain("Desktop");
    expect(availHtml).toContain("TELL ORYXENAI WHAT TO DO NEXT");
    expect(availHtml).toContain("Generate Portfolio →");
    expect(availHtml).toContain("Plan");
    expect(availHtml).toContain("Acquire");
    expect(availHtml).toContain("Build");
    expect(availHtml).toContain("Verify");
    expect(availHtml).toContain("Preview");

    // 3. Working matching Image 14 (Building pages, real milestone state, stop button)
    const workingHtml = renderToString(
      h(GenerationStage, { ...genProps, view: adaptCodeGenerator(generationWorking, true) })
    );
    expect(workingHtml).toContain("codegen-workspace");
    expect(workingHtml).toContain("Building your site");
    expect(workingHtml).toContain("Building pages...");
    expect(workingHtml).toContain("■ Stop generation");
    expect(workingHtml).toContain("Preview updates after each verified backend milestone");
    expect(workingHtml).not.toContain("62%");
    expect(workingHtml).not.toContain("1m ago");

    // 4. Attention matching Image 15 (Generation needs attention, 3 pillars, preserved preview, retry, open details)
    const attentionHtml = renderToString(
      h(GenerationStage, { ...genProps, view: adaptCodeGenerator(generationNeedsAttentionWithPreview, true) })
    );
    expect(attentionHtml).toContain("codegen-attention-card");
    expect(attentionHtml).toContain("Generation needs attention");
    expect(attentionHtml).toContain("Preview preserved");
    expect(attentionHtml).toContain("Polling stopped");
    expect(attentionHtml).toContain("Retry available");
    expect(attentionHtml).toContain("Retry generation");
    expect(attentionHtml).toContain("Open details");
    expect(attentionHtml).toContain("Previous verified preview");
    expect(attentionHtml).toContain("Verification stopped.");
    expect(attentionHtml).toContain("View technical details");

    // 5. Complete / Ready
    const readyHtml = renderToString(
      h(GenerationStage, { ...genProps, view: adaptCodeGenerator(generationReady, true) })
    );
    expect(readyHtml).toContain("codegen-workspace");
    expect(readyHtml).toContain("Open verified preview");
    expect(readyHtml).toContain("Regenerate portfolio");
    expect(readyHtml).not.toContain("Publish");
    expect(readyHtml).not.toContain("Deploy");
    expect(readyHtml).toContain("preview.example.test");
  });
});
