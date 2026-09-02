import { describe, it, expect } from "vitest";
import { DiscoveryStage } from "./discovery/DiscoveryStage";
import { ContentStage } from "./content/ContentStage";
import { DesignStage } from "./design/DesignStage";
import { adaptDiscovery } from "../data/adapters/discovery";
import { adaptContentArchitect } from "../data/adapters/content";
import { adaptVisualDesignDirector } from "../data/adapters/design";
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
});
