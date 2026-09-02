import { describe, it, expect } from "vitest";
import { adaptPreview } from "./preview";
import {
  previewFixtureAbsent,
  previewFixtureReady,
  previewFixtureServerReady,
  previewFixtureWorkingWithPrevious,
  previewFixtureNeedsAttentionWithPrevious,
  previewFixtureNeedsAttentionWithoutPrevious,
  previewFixtureInvalidScheme,
  previewFixtureInvalidTraversal,
  previewFixtureStale,
} from "./preview.fixtures";
import { adaptCodeGenerator } from "./generation";
import { generationFixtureReadyWithPreview } from "./generation.fixtures";

describe("adaptPreview", () => {
  it("adapts absent preview when not started or active preview is null", () => {
    const vm = adaptPreview(previewFixtureAbsent);
    expect(vm.state).toBe("absent");
    expect(vm.routes).toEqual([]);
    expect(vm.isPreviousVerifiedResult).toBe(false);
    expect(vm.stableOrigin).toBeUndefined();
    expect(vm.currentUrl).toBeUndefined();
  });

  it("adapts ready preview with explicit origin, path, and routes", () => {
    const vm = adaptPreview(previewFixtureReady);
    expect(vm.state).toBe("ready");
    expect(vm.stableOrigin).toBe("https://preview.oryxenai.local");
    expect(vm.stableBaseUrl).toBe("https://preview.oryxenai.local/p/run_gen_1/");
    expect(vm.currentUrl).toBe("https://preview.oryxenai.local/p/run_gen_1/");
    expect(vm.isPreviousVerifiedResult).toBe(false);
    expect(vm.selectedPath).toBe("/");
    expect(vm.routes).toHaveLength(4);
    expect(vm.routes[0]).toEqual({ id: "/", path: "/", label: "Home" });
    expect(vm.routes[1]).toEqual({ id: "/about", path: "/about", label: "About" });
    expect(vm.routes[2]).toEqual({ id: "/projects", path: "/projects", label: "Projects" });
    expect(vm.routes[3]).toEqual({ id: "/contact", path: "/contact", label: "Contact" });
  });

  it("adapts server-shaped active preview using url property", () => {
    const vm = adaptPreview(previewFixtureServerReady);
    expect(vm.state).toBe("ready");
    expect(vm.stableOrigin).toBe("https://preview.oryxenai.local");
    expect(vm.currentUrl).toBe("https://preview.oryxenai.local/p/run_server_1/");
    expect(vm.routes).toHaveLength(3);
    expect(vm.routes[0]).toEqual({ id: "/", path: "/", label: "Home" });
    expect(vm.routes[1]).toEqual({ id: "/experience", path: "/experience", label: "Experience" });
    expect(vm.routes[2]).toEqual({ id: "/work-samples", path: "/work-samples", label: "Work Samples" });
  });

  it("respects selectedPath and builds composite currentUrl", () => {
    const vm = adaptPreview(previewFixtureReady, { selectedPath: "/projects" });
    expect(vm.selectedPath).toBe("/projects");
    expect(vm.currentUrl).toBe("https://preview.oryxenai.local/p/run_gen_1/projects");
  });

  it("falls back to first promoted route when selectedPath is absent from declared routes", () => {
    const vm = adaptPreview(previewFixtureReady, { selectedPath: "/unknown-page" });
    expect(vm.selectedPath).toBe("/");
    expect(vm.currentUrl).toBe("https://preview.oryxenai.local/p/run_gen_1/");
  });

  it("rejects path traversal in selectedPath and falls back to first route", () => {
    const vm = adaptPreview(previewFixtureReady, { selectedPath: "/../../secret" });
    expect(vm.selectedPath).toBe("/");
    expect(vm.currentUrl).toBe("https://preview.oryxenai.local/p/run_gen_1/");
  });

  it("marks isPreviousVerifiedResult when generation is in progress", () => {
    const vm = adaptPreview(previewFixtureWorkingWithPrevious);
    expect(vm.state).toBe("ready");
    expect(vm.isPreviousVerifiedResult).toBe(true);
    expect(vm.stableOrigin).toBe("https://preview.oryxenai.local");
  });

  it("marks isPreviousVerifiedResult when generation needs attention but older preview exists", () => {
    const vm = adaptPreview(previewFixtureNeedsAttentionWithPrevious);
    expect(vm.state).toBe("ready");
    expect(vm.isPreviousVerifiedResult).toBe(true);
  });

  it("returns absent when generation needs attention and no preview exists", () => {
    const vm = adaptPreview(previewFixtureNeedsAttentionWithoutPrevious);
    expect(vm.state).toBe("absent");
    expect(vm.isPreviousVerifiedResult).toBe(false);
  });

  it("rejects invalid javascript: scheme and returns unavailable without navigable URL", () => {
    const vm = adaptPreview(previewFixtureInvalidScheme);
    expect(vm.state).toBe("unavailable");
    expect(vm.stableOrigin).toBeUndefined();
    expect(vm.currentUrl).toBeUndefined();
  });

  it("rejects path traversal in base URL and returns unavailable", () => {
    const vm = adaptPreview(previewFixtureInvalidTraversal);
    expect(vm.state).toBe("unavailable");
    expect(vm.stableOrigin).toBeUndefined();
    expect(vm.currentUrl).toBeUndefined();
  });

  it("reflects stale state when input or options are stale", () => {
    const vm1 = adaptPreview(previewFixtureStale);
    expect(vm1.state).toBe("stale");

    const vm2 = adaptPreview(previewFixtureReady, { isStale: true });
    expect(vm2.state).toBe("stale");
  });

  it("reflects loadStatus opening, failed, and timed_out", () => {
    const opening = adaptPreview(previewFixtureReady, { loadStatus: "opening" });
    expect(opening.state).toBe("opening");

    const failed = adaptPreview(previewFixtureReady, { loadStatus: "failed" });
    expect(failed.state).toBe("unavailable");
    expect(failed.loadErrorMessage).toContain("could not load");

    const timedOut = adaptPreview(previewFixtureReady, { loadStatus: "timed_out" });
    expect(timedOut.state).toBe("unavailable");
    expect(timedOut.loadErrorMessage).toContain("timed out");
  });

  it("adapts a GenerationViewModel instance directly", () => {
    const genVM = adaptCodeGenerator(generationFixtureReadyWithPreview, true, false);
    const vm = adaptPreview(genVM);
    expect(vm.state).toBe("ready");
    expect(vm.stableOrigin).toBe("https://preview.oryxenai.local");
    expect(vm.routes.length).toBeGreaterThanOrEqual(2);
  });
});
