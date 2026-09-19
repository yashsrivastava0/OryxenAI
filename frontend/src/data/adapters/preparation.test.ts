import { describe, expect, it } from "vitest";
import { adaptBuildPreparation } from "./preparation";
import { BuildPreparationStage } from "../../stages/preparation/BuildPreparationStage";
import {
  preparationNeedsAttention,
  preparationNotStarted,
  preparationReady,
  preparationRunning,
  preparationStale,
} from "./preparation.fixtures";

describe("adaptBuildPreparation", () => {
  it("keeps the stage locked until both upstream approvals exist", () => {
    expect(adaptBuildPreparation(preparationNotStarted, false, true).state).toBe("locked");
    expect(adaptBuildPreparation(preparationNotStarted, true, true).state).toBe("available");
  });

  it("maps running and ready states into honest product states", () => {
    expect(adaptBuildPreparation(preparationRunning, true, true).state).toBe("working");
    const view = adaptBuildPreparation(preparationReady, true, true);
    expect(view.state).toBe("complete");
    expect(view.routes[0]?.path).toBe("/");
    expect(view.resourceNeedsCount).toBe(1);
    expect(view.agentOutput).toEqual({ stage: "compose_visual_brief", nested: { retained: true } });
  });

  it("parses resource_index and component_index into structured, renderable fields (previously only counted)", () => {
    const view = adaptBuildPreparation(preparationReady, true, true);
    expect(view.resourceIndexCount).toBe(1);
    expect(view.resourceIndex).toHaveLength(1);
    expect(view.resourceIndex[0]?.roleId).toBe("home-hero-bg");
    expect(view.resourceIndex[0]?.status).toBe("candidates_found");
    expect(view.resourceIndex[0]?.candidates[0]?.previewUrl).toContain("images.unsplash.com");
    expect(view.resourceIndex[0]?.candidates[0]?.attribution).toBe("Photo by John Doe on Unsplash");

    expect(view.componentIndexCount).toBe(1);
    expect(view.componentIndex).toHaveLength(1);
    expect(view.componentIndex[0]?.roleId).toBe("framer-motion-reveal");
    expect(view.componentIndex[0]?.suggestions[0]?.itemUrl).toBe("https://motion.dev/docs/react-quick-start");
  });

  it("requires regeneration for stale output and surfaces retryable errors", () => {
    expect(adaptBuildPreparation(preparationStale, true, true).state).toBe("attention");
    const attention = adaptBuildPreparation(preparationNeedsAttention, true, true);
    expect(attention.state).toBe("attention");
    expect(attention.safeError?.retryable).toBe(true);
  });

  it("fails closed on unknown status", () => {
    expect(adaptBuildPreparation({ status: "future" }, true, true).state).toBe("unsupported");
  });
});

describe("BuildPreparationStage — readiness is the primary view", () => {
  const props = {
    canMutate: true,
    onStart: async () => {},
    onRegenerate: async () => {},
    onStartGeneration: async () => {},
  };

  it("renders the ready state inside the WorkspaceCanvas shell", () => {
    const node = BuildPreparationStage({ ...props, view: adaptBuildPreparation(preparationReady, true, true) });
    expect((node as { props?: { className?: string } }).props?.className).toBe("preparation-stage-shell");
  });

  it("orders readiness signals BEFORE the two collapsed brief drawers", () => {
    const node = BuildPreparationStage({ ...props, view: adaptBuildPreparation(preparationReady, true, true) });
    const serialized = JSON.stringify(node);

    const galleryAt = serialized.indexOf("preparation-asset-gallery");
    const componentDeckAt = serialized.indexOf("preparation-component-deck");
    const routesAt = serialized.indexOf("preparation-routes");
    const briefGridAt = serialized.indexOf("preparation-brief-grid");

    // Every readiness signal is present...
    expect(galleryAt).toBeGreaterThanOrEqual(0);
    expect(componentDeckAt).toBeGreaterThanOrEqual(0);
    expect(routesAt).toBeGreaterThanOrEqual(0);
    expect(briefGridAt).toBeGreaterThanOrEqual(0);

    // ...and each appears BEFORE the brief drawers in the rendered tree.
    expect(galleryAt).toBeLessThan(briefGridAt);
    expect(componentDeckAt).toBeLessThan(briefGridAt);
    expect(routesAt).toBeLessThan(briefGridAt);
  });

  it("keeps the full brief markdown collapsed by default (no expanded brief body in the default tree)", () => {
    const node = BuildPreparationStage({ ...props, view: adaptBuildPreparation(preparationReady, true, true) });
    const serialized = JSON.stringify(node);
    // The full brief text only reaches the DOM through BriefDrawer's own
    // SafeMarkdown render, which is guarded by a `useState(false)` "open"
    // flag. In the default (un-toggled) tree there is no expanded brief body
    // and no SafeMarkdown node — the sole path to the full text is the
    // explicit "Read full brief" toggle.
    expect(serialized).not.toContain("preparation-brief-body");
    expect(serialized).not.toContain("SafeMarkdown");
    // The briefs are still present, but only as collapsed BriefDrawer props
    // carrying the raw markdown (not yet rendered into visible page text).
    expect(serialized).toContain("preparation-brief-grid");
    expect(serialized).toContain('"eyebrow":"CONTENT BRIEF"');
    expect(serialized).toContain('"eyebrow":"VISUAL BRIEF"');
  });

  it("surfaces a compact readiness summary in the rail from real adapter fields", () => {
    const node = BuildPreparationStage({ ...props, view: adaptBuildPreparation(preparationReady, true, true) });
    const serialized = JSON.stringify(node);
    expect(serialized).toContain("Routes bound");
    expect(serialized).toContain("Resource needs");
    expect(serialized).toContain("Resource roles");
    expect(serialized).toContain("Component roles");
    expect(serialized).not.toContain("Brand Positioning Deck");
    expect(serialized).toContain("Start generating portfolio");
  });
});
