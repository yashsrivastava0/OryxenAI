import { describe, it, expect } from "vitest";
import { DiscoveryStage } from "./discovery/DiscoveryStage";
import { ContentStage } from "./content/ContentStage";
import { DesignStage } from "./design/DesignStage";
import { PreparationStage } from "./preparation/PreparationStage";
import { GenerationStage } from "./generation/GenerationStage";
import { adaptDiscovery } from "../data/adapters/discovery";
import { adaptContentArchitect } from "../data/adapters/content";
import { adaptVisualDesignDirector } from "../data/adapters/design";
import { adaptBuildPreparation } from "../data/adapters/preparation";
import { adaptCodeGenerator } from "../data/adapters/generation";
import {
  notStarted as discoveryFixtureNotStarted,
  questionsReady as discoveryFixtureQuestionsReady,
  briefReview as discoveryFixtureBriefReview,
  approved as discoveryFixtureApproved,
} from "../data/adapters/discovery.fixtures";
import {
  contentFixtureNotStarted,
  contentFixtureReview,
  contentFixtureApproved,
} from "../data/adapters/content.fixtures";
import {
  designFixtureNotStarted,
  designFixtureReview,
  designFixtureApproved,
} from "../data/adapters/design.fixtures";
import {
  preparationFixtureNotStarted,
  preparationFixtureRunningStage2,
  preparationFixtureReadyEligible,
  preparationFixtureNeedsAttention,
} from "../data/adapters/preparation.fixtures";
import {
  generationFixtureNotStarted,
  generationFixtureGenerating,
  generationFixtureReadyWithPreview,
  generationFixtureNeedsAttentionRetryable,
} from "../data/adapters/generation.fixtures";

function getClassName(vnode: any): string | undefined {
  return vnode?.props?.className ?? vnode?.props?.class;
}

describe("Stage Component VNodes", () => {
  describe("DiscoveryStage", () => {
    it("renders available start panel when not started", () => {
      const view = adaptDiscovery(discoveryFixtureNotStarted);
      const vnode = DiscoveryStage({
        view,
        history: [],
        canMutate: true,
        onStartDiscovery: async () => {},
        onSubmitAnswer: async () => {},
        onGenerateBriefNow: async () => {},
        onApproveBrief: async () => {},
        onReviseBrief: async () => {},
        onContinueToContent: () => {},
      });
      expect(vnode).toBeDefined();
      expect(getClassName(vnode)).toBe("stage-available-panel");
    });

    it("renders conversation surface when questions are ready", () => {
      const view = adaptDiscovery(discoveryFixtureQuestionsReady);
      const vnode = DiscoveryStage({
        view,
        history: [],
        canMutate: true,
        onStartDiscovery: async () => {},
        onSubmitAnswer: async () => {},
        onGenerateBriefNow: async () => {},
        onApproveBrief: async () => {},
        onReviseBrief: async () => {},
        onContinueToContent: () => {},
      });
      expect(vnode).toBeDefined();
      expect(vnode.props.questions.length).toBe(1);
    });

    it("renders brief review surface when in brief_review", () => {
      const view = adaptDiscovery(discoveryFixtureBriefReview);
      const vnode = DiscoveryStage({
        view,
        history: [],
        canMutate: true,
        onStartDiscovery: async () => {},
        onSubmitAnswer: async () => {},
        onGenerateBriefNow: async () => {},
        onApproveBrief: async () => {},
        onReviseBrief: async () => {},
        onContinueToContent: () => {},
      });
      expect(vnode).toBeDefined();
      expect(getClassName(vnode)).toBe("discovery-brief-view");
    });

    it("renders handoff to Content when approved", () => {
      const view = adaptDiscovery(discoveryFixtureApproved);
      const vnode = DiscoveryStage({
        view,
        history: [],
        canMutate: true,
        onStartDiscovery: async () => {},
        onSubmitAnswer: async () => {},
        onGenerateBriefNow: async () => {},
        onApproveBrief: async () => {},
        onReviseBrief: async () => {},
        onContinueToContent: () => {},
      });
      expect(vnode).toBeDefined();
      expect(getClassName(vnode)).toBe("discovery-brief-view");
    });
  });

  describe("ContentStage", () => {
    it("renders locked panel when Discovery is not approved", () => {
      const view = adaptContentArchitect(contentFixtureNotStarted, false);
      const vnode = ContentStage({
        view,
        canMutate: true,
        onStart: async () => {},
        onApprove: async () => {},
        onRevise: async () => {},
        onContinueToDesign: () => {},
      });
      expect(getClassName(vnode)).toBe("stage-locked-panel");
    });

    it("renders available start panel when Discovery is approved", () => {
      const view = adaptContentArchitect(contentFixtureNotStarted, true);
      const vnode = ContentStage({
        view,
        canMutate: true,
        onStart: async () => {},
        onApprove: async () => {},
        onRevise: async () => {},
        onContinueToDesign: () => {},
      });
      expect(getClassName(vnode)).toBe("stage-available-panel");
    });

    it("renders artifact review when in content_review", () => {
      const view = adaptContentArchitect(contentFixtureReview, true);
      const vnode = ContentStage({
        view,
        canMutate: true,
        onStart: async () => {},
        onApprove: async () => {},
        onRevise: async () => {},
        onContinueToDesign: () => {},
      });
      expect(getClassName(vnode)).toBe("content-stage-view");
    });

    it("renders handoff to Design when approved", () => {
      const view = adaptContentArchitect(contentFixtureApproved, true);
      const vnode = ContentStage({
        view,
        canMutate: true,
        onStart: async () => {},
        onApprove: async () => {},
        onRevise: async () => {},
        onContinueToDesign: () => {},
      });
      expect(getClassName(vnode)).toBe("content-stage-view");
    });
  });

  describe("DesignStage", () => {
    it("renders locked panel when Content is not approved", () => {
      const view = adaptVisualDesignDirector(designFixtureNotStarted, false);
      const vnode = DesignStage({
        view,
        canMutate: true,
        onStart: async () => {},
        onApprove: async () => {},
        onRevise: async () => {},
        onContinueToPrepare: () => {},
      });
      expect(getClassName(vnode)).toBe("stage-locked-panel");
    });

    it("renders available start panel when Content is approved", () => {
      const view = adaptVisualDesignDirector(designFixtureNotStarted, true);
      const vnode = DesignStage({
        view,
        canMutate: true,
        onStart: async () => {},
        onApprove: async () => {},
        onRevise: async () => {},
        onContinueToPrepare: () => {},
      });
      expect(getClassName(vnode)).toBe("stage-available-panel");
    });

    it("renders visual direction artifact when in design_review", () => {
      const view = adaptVisualDesignDirector(designFixtureReview, true);
      const vnode = DesignStage({
        view,
        canMutate: true,
        onStart: async () => {},
        onApprove: async () => {},
        onRevise: async () => {},
        onContinueToPrepare: () => {},
      });
      expect(getClassName(vnode)).toBe("design-stage-view");
    });

    it("renders handoff to Prepare when approved", () => {
      const view = adaptVisualDesignDirector(designFixtureApproved, true);
      const vnode = DesignStage({
        view,
        canMutate: true,
        onStart: async () => {},
        onApprove: async () => {},
        onRevise: async () => {},
        onContinueToPrepare: () => {},
      });
      expect(getClassName(vnode)).toBe("design-stage-view");
    });
  });

  describe("PreparationStage", () => {
    it("renders locked panel when Design is not approved", () => {
      const view = adaptBuildPreparation(preparationFixtureNotStarted, false);
      const vnode = PreparationStage({
        view,
        canMutate: true,
        onStart: async () => {},
        onRegenerate: async () => {},
        onContinueToGeneration: () => {},
      });
      expect(getClassName(vnode)).toBe("stage-locked-panel");
    });

    it("renders available start panel when Design is approved", () => {
      const view = adaptBuildPreparation(preparationFixtureNotStarted, true);
      const vnode = PreparationStage({
        view,
        canMutate: true,
        onStart: async () => {},
        onRegenerate: async () => {},
        onContinueToGeneration: () => {},
      });
      expect(getClassName(vnode)).toBe("stage-available-panel");
    });

    it("renders progress surface when working", () => {
      const view = adaptBuildPreparation(preparationFixtureRunningStage2, true);
      const vnode = PreparationStage({
        view,
        canMutate: true,
        onStart: async () => {},
        onRegenerate: async () => {},
        onContinueToGeneration: () => {},
      });
      expect(vnode).toBeDefined();
      expect(vnode.props.stageLabel).toContain("Prepare");
      expect(vnode.props.currentMilestone).toBe("Resolving portfolio materials");
    });

    it("renders complete summary and handoff to Generation when ready and eligible", () => {
      const view = adaptBuildPreparation(preparationFixtureReadyEligible, true);
      const vnode = PreparationStage({
        view,
        canMutate: true,
        onStart: async () => {},
        onRegenerate: async () => {},
        onContinueToGeneration: () => {},
      });
      expect(getClassName(vnode)).toBe("preparation-stage-view");
    });

    it("renders attention panel when needs_attention", () => {
      const view = adaptBuildPreparation(preparationFixtureNeedsAttention, true);
      const vnode = PreparationStage({
        view,
        canMutate: true,
        onStart: async () => {},
        onRegenerate: async () => {},
        onContinueToGeneration: () => {},
      });
      expect(getClassName(vnode)).toBe("preparation-stage-view");
    });
  });

  describe("GenerationStage", () => {
    it("renders locked panel when Preparation is not ready", () => {
      const view = adaptCodeGenerator(generationFixtureNotStarted, false, false);
      const vnode = GenerationStage({
        view,
        canMutate: true,
        readOnly: false,
        onStart: async () => {},
        onRetry: async () => {},
        onOpenPreview: () => {},
      });
      expect(getClassName(vnode)).toBe("stage-locked-panel");
    });

    it("renders available start panel when Preparation is ready", () => {
      const view = adaptCodeGenerator(generationFixtureNotStarted, true, false);
      const vnode = GenerationStage({
        view,
        canMutate: true,
        readOnly: false,
        onStart: async () => {},
        onRetry: async () => {},
        onOpenPreview: () => {},
      });
      expect(getClassName(vnode)).toBe("stage-available-panel");
    });

    it("renders progress surface when working", () => {
      const view = adaptCodeGenerator(generationFixtureGenerating, true, false);
      const vnode = GenerationStage({
        view,
        canMutate: true,
        readOnly: false,
        onStart: async () => {},
        onRetry: async () => {},
        onOpenPreview: () => {},
      });
      expect(vnode).toBeDefined();
      expect(vnode.props.stageLabel).toContain("Generate");
      expect(vnode.props.currentMilestone).toBe("Building portfolio routes");
    });

    it("renders complete summary and Open Preview action when ready with preview", () => {
      const view = adaptCodeGenerator(generationFixtureReadyWithPreview, true, false);
      const vnode = GenerationStage({
        view,
        canMutate: true,
        readOnly: false,
        onStart: async () => {},
        onRetry: async () => {},
        onOpenPreview: () => {},
      });
      expect(getClassName(vnode)).toBe("generation-stage-view");
    });

    it("renders attention panel when needs_attention", () => {
      const view = adaptCodeGenerator(generationFixtureNeedsAttentionRetryable, true, false);
      const vnode = GenerationStage({
        view,
        canMutate: true,
        readOnly: false,
        onStart: async () => {},
        onRetry: async () => {},
        onOpenPreview: () => {},
      });
      expect(getClassName(vnode)).toBe("generation-stage-view");
    });
  });
});
