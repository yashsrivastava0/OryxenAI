import { describe, expect, it } from "vitest";
import { adaptCodeGenerator, friendlyRouteLabel } from "./generation";
import {
  generationNeedsAttentionNoPreview,
  generationNeedsAttentionWithCandidate,
  generationNeedsAttentionWithPreview,
  generationNotStarted,
  generationReady,
  generationStale,
  generationWorking,
} from "./generation.fixtures";

describe("adaptCodeGenerator", () => {
  it("keeps the stage locked until Build Preparation is approved", () => {
    expect(adaptCodeGenerator(generationNotStarted, false).state).toBe("locked");
    expect(adaptCodeGenerator(generationNotStarted, true).state).toBe("available");
  });

  it("maps working and ready states into honest product states", () => {
    expect(adaptCodeGenerator(generationWorking, true).state).toBe("working");
    const view = adaptCodeGenerator(generationReady, true);
    expect(view.state).toBe("complete");
    expect(view.preview?.url).toBe("https://preview.example.test/preview/abc123/");
    expect(view.preview?.routeIds).toEqual(["home"]);
    expect(view.agentOutput).toEqual({ stage: "verify_and_preview", nested: { retained: true } });
  });

  it("requires regeneration for stale output", () => {
    expect(adaptCodeGenerator(generationStale, true).state).toBe("attention");
  });

  it("retains the last verified preview alongside a needs_attention error, when one exists", () => {
    const withPreview = adaptCodeGenerator(generationNeedsAttentionWithPreview, true);
    expect(withPreview.state).toBe("attention");
    expect(withPreview.preview?.url).toBe("https://preview.example.test/preview/abc123/");
    expect(withPreview.safeError?.retryable).toBe(true);

    const withoutPreview = adaptCodeGenerator(generationNeedsAttentionNoPreview, true);
    expect(withoutPreview.state).toBe("attention");
    expect(withoutPreview.preview).toBeNull();
  });

  it("exposes an unverified candidate separately from the active preview", () => {
    const view = adaptCodeGenerator(generationNeedsAttentionWithCandidate, true);
    expect(view.candidatePreview?.verificationStatus).toBe("unverified");
    expect(view.candidatePreview?.routePaths).toEqual(["/", "/about"]);
    expect(view.warnings).toEqual(["Optional composition spacing differs."]);
    expect(view.preview).toBeNull();
  });

  it("fails closed on unknown status", () => {
    expect(adaptCodeGenerator({ status: "future" }, true).state).toBe("unsupported");
  });
});

describe("friendlyRouteLabel", () => {
  it("renders a human-friendly page name instead of the raw route id", () => {
    expect(friendlyRouteLabel("home", "/")).toBe("Home");
    expect(friendlyRouteLabel("case_study_queueguard", "/case-studies/queueguard")).toBe("Case Study Queueguard");
    expect(friendlyRouteLabel("about-me", "/about")).toBe("About Me");
  });

  it("falls back to the bare path when no route id is available", () => {
    expect(friendlyRouteLabel("", "/contact")).toBe("/contact");
    expect(friendlyRouteLabel("", "")).toBe("/");
  });
});
