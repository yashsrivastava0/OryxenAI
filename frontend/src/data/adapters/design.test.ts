import { describe, it, expect } from "vitest";
import { adaptVisualDesignDirector } from "./design";
import {
  designFixtureNotStarted,
  designFixtureBuildRunning,
  designFixtureReview,
  designFixtureLanguageOnly,
  designFixtureApproved,
  designFixtureNeedsAttention,
} from "./design.fixtures";
// A verbatim copy of the REAL backend fixture
// (src/oryxenai/agents/visual_design_director/samples/01_single_page_output.json).
// Kept in src/ because vitest only includes src/**; this proves the adapter
// parses the genuine backend output shape, not just a hand-written fixture.
import backendSample from "./design.sample.backend.json";

describe("adaptVisualDesignDirector", () => {
  it("locks not_started when Content Architect is not yet approved", () => {
    const view = adaptVisualDesignDirector(designFixtureNotStarted, false);
    expect(view.state).toBe("locked");
    expect(view.statusText).toBe("Locked until Content is approved");
  });

  it("unlocks to available when Content Architect is approved", () => {
    const view = adaptVisualDesignDirector(designFixtureNotStarted, true);
    expect(view.state).toBe("available");
    expect(view.statusText).toBe("Ready to direct visual experience");
  });

  it("maps build_running to working", () => {
    const view = adaptVisualDesignDirector(designFixtureBuildRunning, true);
    expect(view.state).toBe("working");
    expect(view.statusText).toBe("Developing the visual direction");
  });

  it("maps design_review to review and extracts visual language and page directions", () => {
    const view = adaptVisualDesignDirector(designFixtureReview, true);
    expect(view.state).toBe("review");
    expect(view.creativeThesis).toContain("Quiet confidence");
    expect(view.visualLanguage.designKeywords).toContain("swiss");
    expect(view.pages.length).toBe(2);
    expect(view.pages[0]?.routeId).toBe("route_home");
    expect(view.resources.length).toBe(1);
    expect(view.resources[0]?.resourceId).toBe("res_architecture_flow_01");
    expect(view.safeError).toBeNull();
  });

  it("parses scenes[] with all typed fields from the review fixture", () => {
    const view = adaptVisualDesignDirector(designFixtureReview, true);
    const home = view.pages.find((p) => p.routeId === "route_home");
    expect(home).toBeDefined();
    expect(home?.scenes.length).toBe(2);

    const hero = home?.scenes[0];
    expect(hero?.sceneId).toBe("hero_scene");
    expect(hero?.narrativeGoal).toContain("positioning");
    expect(hero?.viewportRole).toBe("above the fold");
    expect(hero?.contentRefs).toEqual(["hero"]);
    expect(hero?.layoutIntent).toContain("asymmetric hero");
    expect(hero?.responsiveBehavior).toContain("mobile");
    expect(hero?.accessibilityIntent).toContain("WCAG AA");
    expect(hero?.acceptanceCriteria.length).toBe(1);

    const project = home?.scenes[1];
    expect(project?.sceneId).toBe("project_scene");
    expect(project?.assetRequirements).toEqual(["project_diagram"]);
    expect(project?.resourceCandidates).toEqual(["res_architecture_flow_01"]);
    // motion_intent is a free prose dict on the backend; flattened to a line.
    expect(project?.motionIntent).toContain("purpose:");
    expect(project?.motionIntent).toContain("scroll into viewport");
    expect(project?.reducedMotionBehavior).toContain("no entrance animation");
    expect(project?.performanceRisk).toContain("low");
    expect(project?.failureSafeStaticState).toContain("legible");
  });

  it("parses top-level asset_briefs[] with typed treatment fields", () => {
    const view = adaptVisualDesignDirector(designFixtureReview, true);
    expect(view.assetBriefs.length).toBe(1);
    const brief = view.assetBriefs[0];
    expect(brief?.assetId).toBe("project_diagram");
    expect(brief?.assetType).toBe("diagram");
    expect(brief?.sourceStatus).toBe("needs_acquisition");
    expect(brief?.importance).toBe("important");
    expect(brief?.desktopTreatment).toContain("framed panel");
    expect(brief?.mobileTreatment).toContain("full-width");
    expect(brief?.decorativeVsInformative).toBe("informative");
    expect(brief?.fallbackStrategy).toContain("bulleted description");
  });

  it("enriches resource_candidates[] with the previously-discarded fields", () => {
    const view = adaptVisualDesignDirector(designFixtureReview, true);
    const res = view.resources[0];
    expect(res?.whereItMayHelp).toBe("route_home/project_scene");
    expect(res?.priority).toBe("primary");
    expect(res?.possibleUse).toContain("process-flow");
    expect(res?.confidence).toBe("high");
  });

  it("flags VISUAL_LANGUAGE_ONLY (pages_included false) and reads fallback prose keys", () => {
    const view = adaptVisualDesignDirector(designFixtureLanguageOnly, true);
    expect(view.state).toBe("review");
    expect(view.visualLanguageOnly).toBe(true);
    expect(view.pages.length).toBe(0);
    expect(view.creativeThesis).toContain("Reliability engineering");
    // color_behavior / typography / motion_character are the real fallback prose keys.
    expect(view.visualLanguage.colorIntent).toContain("confident accent");
    expect(view.visualLanguage.typographyIntent).toContain("calm display");
    expect(view.visualLanguage.motionIntent).toContain("Minimal");
  });

  it("treats a page-bearing run with pages_included true as not language-only", () => {
    const view = adaptVisualDesignDirector(designFixtureReview, true);
    expect(view.visualLanguageOnly).toBe(false);
  });

  it("parses scenes[] and asset_briefs[] correctly from the REAL backend sample JSON", () => {
    // The backend sample is agent OUTPUT; the adapter reads persisted STATE,
    // which shares these field names. Wrap it with a status to feed it in.
    const state = { ...backendSample, status: "design_review" };
    const view = adaptVisualDesignDirector(state, true);

    expect(view.state).toBe("review");
    expect(view.visualLanguageOnly).toBe(false);

    // Creative thesis + prose intent (never literal color/font values).
    expect(view.creativeThesis).toContain("Reliability engineering");
    expect(view.visualLanguage.colorIntent).toContain("confident accent");
    expect(view.visualLanguage.typographyIntent).toContain("calm");
    expect(view.visualLanguage.motionIntent).toContain("Minimal");

    // pages[].scenes[]
    expect(view.pages.length).toBe(1);
    const home = view.pages[0];
    expect(home?.routeId).toBe("home");
    expect(home?.path).toBe("/");
    expect(home?.visitorTakeaway).toContain("Priya");
    expect(home?.scenes.length).toBe(2);
    expect(home?.scenes[0]?.sceneId).toBe("hero_scene");
    expect(home?.scenes[1]?.sceneId).toBe("project_scene");
    expect(home?.scenes[1]?.assetRequirements).toEqual(["project_diagram"]);
    expect(home?.scenes[1]?.motionIntent).toContain("scroll into viewport");
    expect(home?.assetBriefIds).toEqual(["project_diagram"]);

    // top-level asset_briefs[]
    expect(view.assetBriefs.length).toBe(1);
    expect(view.assetBriefs[0]?.assetId).toBe("project_diagram");
    expect(view.assetBriefs[0]?.desktopTreatment).toContain("framed panel");
    expect(view.assetBriefs[0]?.decorativeVsInformative).toBe("informative");

    // resource_candidates[]
    expect(view.resources.length).toBe(1);
    expect(view.resources[0]?.resourceId).toBe("diagram_process_flow");
    expect(view.resources[0]?.whereItMayHelp).toBe("home/project_scene");
    expect(view.resources[0]?.confidence).toBe("high");

    // The scene's referenced asset id resolves against a real top-level brief.
    const projectScene = home?.scenes[1];
    const referenced = view.assetBriefs.filter((b) =>
      projectScene?.assetRequirements.includes(b.assetId),
    );
    expect(referenced.length).toBe(1);
    expect(referenced[0]?.assetId).toBe("project_diagram");
  });

  it("maps approved to complete", () => {
    const view = adaptVisualDesignDirector(designFixtureApproved, true);
    expect(view.state).toBe("complete");
    expect(view.statusText).toBe("Visual direction approved");
  });

  it("maps needs_attention to attention and extracts error", () => {
    const view = adaptVisualDesignDirector(designFixtureNeedsAttention, true);
    expect(view.state).toBe("attention");
    expect(view.safeError?.summary).toBe("Resource catalog resolution failed for custom flow diagram.");
  });

  it("fails closed into unsupported for unknown or malformed status", () => {
    const view = adaptVisualDesignDirector({ status: "future_unsupported_status" }, true);
    expect(view.state).toBe("unsupported");
    expect(view.statusText).toContain("unrecognised state");
  });
});
