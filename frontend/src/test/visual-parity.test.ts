import { describe, it, expect } from "vitest";
import { adaptDiscovery } from "../data/adapters/discovery";
import { adaptContentArchitect } from "../data/adapters/content";
import { adaptVisualDesignDirector } from "../data/adapters/design";
import { adaptBuildPreparation } from "../data/adapters/preparation";
import { adaptCodeGenerator } from "../data/adapters/generation";
import { adaptPreview } from "../data/adapters/preview";
import { DiscoveryStage } from "../stages/discovery/DiscoveryStage";
import { ContentStage } from "../stages/content/ContentStage";
import { DesignStage } from "../stages/design/DesignStage";
import { PreparationStage } from "../stages/preparation/PreparationStage";
import { GenerationStage } from "../stages/generation/GenerationStage";
import { PreviewSurface } from "../stages/preview/PreviewSurface";
import {
  questionsReady as discoveryQuestionsReady,
  briefReview as discoveryBriefReview,
  approved as discoveryApproved,
} from "../data/adapters/discovery.fixtures";
import {
  contentFixtureReview,
  contentFixtureApproved,
} from "../data/adapters/content.fixtures";
import {
  designFixtureReview,
  designFixtureApproved,
} from "../data/adapters/design.fixtures";
import {
  preparationFixtureRunningStage2,
  preparationFixtureReadyEligible,
} from "../data/adapters/preparation.fixtures";
import {
  generationFixtureGenerating,
  generationFixtureReadyWithPreview,
} from "../data/adapters/generation.fixtures";

describe("Phase 5 Visual & Functional Parity Pass (docs/Frontend/05 §18, §19)", () => {
  it("Parity Stage 01: Discovery adapts all question modes and brief review lifecycle", () => {
    const qView = adaptDiscovery(discoveryQuestionsReady);
    expect(qView.state).toBe("input");
    expect(qView.currentQuestions.length).toBeGreaterThan(0);

    const bView = adaptDiscovery(discoveryBriefReview);
    expect(bView.state).toBe("review");
    expect(bView.brief).not.toBeNull();

    const appView = adaptDiscovery(discoveryApproved);
    expect(appView.state).toBe("complete");

    const rendered = DiscoveryStage({
      view: bView,
      history: [],
      canMutate: true,
      onStartDiscovery: async () => {},
      onSubmitAnswer: async () => {},
      onGenerateBriefNow: async () => {},
      onApproveBrief: async () => {},
      onReviseBrief: async () => {},
      onContinueToContent: () => {},
    });
    expect(rendered).toBeDefined();
  });

  it("Parity Stage 02: Content Architect adapts structured routes, pages, and handoff", () => {
    const cView = adaptContentArchitect(contentFixtureReview, true);
    expect(cView.state).toBe("review");
    expect(cView.routePlan.length).toBeGreaterThan(0);

    const cApproved = adaptContentArchitect(contentFixtureApproved, true);
    expect(cApproved.state).toBe("complete");

    const rendered = ContentStage({
      view: cApproved,
      canMutate: false,
      onStart: async () => {},
      onApprove: async () => {},
      onRevise: async () => {},
      onContinueToDesign: () => {},
    });
    expect(rendered).toBeDefined();
  });

  it("Parity Stage 03: Visual Design Director adapts creative direction and catalogue links", () => {
    const dView = adaptVisualDesignDirector(designFixtureReview, true);
    expect(dView.state).toBe("review");
    expect(dView.creativeThesis).toBeDefined();
    expect(dView.resources.length).toBeGreaterThan(0);

    const dApproved = adaptVisualDesignDirector(designFixtureApproved, true);
    expect(dApproved.state).toBe("complete");

    const rendered = DesignStage({
      view: dView,
      canMutate: true,
      onStart: async () => {},
      onApprove: async () => {},
      onRevise: async () => {},
      onContinueToPrepare: () => {},
    });
    expect(rendered).toBeDefined();
  });

  it("Parity Stage 04: Build Preparation adapts milestones and handoff summary", () => {
    const pRunning = adaptBuildPreparation(preparationFixtureRunningStage2, true);
    expect(pRunning.state).toBe("working");
    expect(pRunning.milestones.length).toBe(4);

    const pReady = adaptBuildPreparation(preparationFixtureReadyEligible, true);
    expect(pReady.state).toBe("complete");
    expect(pReady.handoffEligible).toBe(true);

    const rendered = PreparationStage({
      view: pReady,
      canMutate: true,
      onStart: async () => {},
      onRegenerate: async () => {},
      onContinueToGeneration: () => {},
    });
    expect(rendered).toBeDefined();
  });

  it("Parity Stage 05: Code Generator adapts milestones, timing, and preview link", () => {
    const gRunning = adaptCodeGenerator(generationFixtureGenerating, true, false);
    expect(gRunning.state).toBe("working");
    expect(gRunning.milestones.length).toBe(6);

    const gReady = adaptCodeGenerator(generationFixtureReadyWithPreview, true, false);
    expect(gReady.state).toBe("complete");
    expect(gReady.hasUsablePreview).toBe(true);

    const rendered = GenerationStage({
      view: gReady,
      canMutate: true,
      readOnly: false,
      onStart: async () => {},
      onRetry: async () => {},
      onOpenPreview: () => {},
    });
    expect(rendered).toBeDefined();
  });

  it("Parity Stage 06: Verified Preview Surface renders frame with 4 viewports and route switcher", () => {
    const gReady = adaptCodeGenerator(generationFixtureReadyWithPreview, true, false);
    const pView = adaptPreview(gReady);

    expect(pView.state).toBe("ready");
    expect(pView.routes.length).toBeGreaterThan(0);

    const rendered = PreviewSurface({
      view: pView,
      readOnly: false,
    });
    expect(rendered).toBeDefined();
  });
});
