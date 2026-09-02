import { describe, it, expect } from "vitest";
import { adaptCodeGenerator } from "./generation";
import {
  generationFixtureNotStarted,
  generationFixtureQueued,
  generationFixturePlanning,
  generationFixtureAcquiring,
  generationFixtureGenerating,
  generationFixtureVerifying,
  generationFixturePreviewPending,
  generationFixtureReadyWithPreview,
  generationFixtureReadyWithoutPreview,
  generationFixtureNeedsAttentionRetryable,
  generationFixtureNeedsAttentionNonRetryable,
  generationFixtureWithPreviousPreview,
  generationFixtureUnsupported,
} from "./generation.fixtures";

describe("adaptCodeGenerator", () => {
  it("locks not_started when Build Preparation is not ready", () => {
    const view = adaptCodeGenerator(generationFixtureNotStarted, false);
    expect(view.state).toBe("locked");
    expect(view.statusText).toContain("Requires completed Build Preparation");
  });

  it("unlocks to available when Build Preparation is ready", () => {
    const view = adaptCodeGenerator(generationFixtureNotStarted, true);
    expect(view.state).toBe("available");
    expect(view.statusText).toContain("Ready to generate");
  });

  it("locks not_started if user is read-only even if prepared", () => {
    const view = adaptCodeGenerator(generationFixtureNotStarted, true, true);
    expect(view.state).toBe("locked");
  });

  it("maps queued to working with milestone 0 active", () => {
    const view = adaptCodeGenerator(generationFixtureQueued, true);
    expect(view.state).toBe("working");
    expect(view.currentMilestone).toBe("Waiting for the generation lane");
    expect(view.milestones[0]?.state).toBe("current");
    expect(view.milestones[1]?.state).toBe("quiet");
    expect(view.supportReference).toBe("trace_lane_wait_123");
  });

  it("maps planning to working with milestone 0 complete, milestone 1 current", () => {
    const view = adaptCodeGenerator(generationFixturePlanning, true);
    expect(view.state).toBe("working");
    expect(view.milestones[0]?.state).toBe("complete");
    expect(view.milestones[1]?.state).toBe("current");
    expect(view.milestones[2]?.state).toBe("quiet");
  });

  it("maps acquiring to working with milestones 0-1 complete, milestone 2 current", () => {
    const view = adaptCodeGenerator(generationFixtureAcquiring, true);
    expect(view.state).toBe("working");
    expect(view.milestones[0]?.state).toBe("complete");
    expect(view.milestones[1]?.state).toBe("complete");
    expect(view.milestones[2]?.state).toBe("current");
  });

  it("maps generating to working with milestones 0-2 complete, milestone 3 current", () => {
    const view = adaptCodeGenerator(generationFixtureGenerating, true);
    expect(view.state).toBe("working");
    expect(view.milestones[2]?.state).toBe("complete");
    expect(view.milestones[3]?.state).toBe("current");
    expect(view.milestones[4]?.state).toBe("quiet");
  });

  it("maps verifying to working with milestones 0-3 complete, milestone 4 current", () => {
    const view = adaptCodeGenerator(generationFixtureVerifying, true);
    expect(view.state).toBe("working");
    expect(view.milestones[3]?.state).toBe("complete");
    expect(view.milestones[4]?.state).toBe("current");
    expect(view.milestones[5]?.state).toBe("quiet");
  });

  it("maps preview_pending to working with milestone 5 current", () => {
    const view = adaptCodeGenerator(generationFixturePreviewPending, true);
    expect(view.state).toBe("working");
    expect(view.milestones[4]?.state).toBe("complete");
    expect(view.milestones[5]?.state).toBe("current");
  });

  it("maps ready with valid active Preview to complete", () => {
    const view = adaptCodeGenerator(generationFixtureReadyWithPreview, true);
    expect(view.state).toBe("complete");
    expect(view.hasUsablePreview).toBe(true);
    expect(view.activePreview?.origin).toBe("https://preview.oryxenai.local");
    expect(view.activePreview?.routePaths).toContain("/projects");
    expect(view.milestones.every((m) => m.state === "complete")).toBe(true);
  });

  it("maps ready without active Preview to attention", () => {
    const view = adaptCodeGenerator(generationFixtureReadyWithoutPreview, true);
    expect(view.state).toBe("attention");
    expect(view.hasUsablePreview).toBe(false);
    expect(view.statusText).toContain("Preview is currently unavailable");
  });

  it("maps needs_attention to attention with retry eligibility", () => {
    const view = adaptCodeGenerator(generationFixtureNeedsAttentionRetryable, true, false);
    expect(view.state).toBe("attention");
    expect(view.retryEligible).toBe(true);
    expect(view.safeError?.summary).toBe("TypeScript compiler error during verification round.");
    expect(view.issues.length).toBe(1);
    expect(view.issues[0]?.code).toBe("BUILD_LINT_ERROR");
  });

  it("suppresses retry eligibility when user is read-only", () => {
    const view = adaptCodeGenerator(generationFixtureNeedsAttentionRetryable, true, true);
    expect(view.state).toBe("attention");
    expect(view.retryEligible).toBe(false);
  });

  it("suppresses retry eligibility when retry_status is ineligible", () => {
    const view = adaptCodeGenerator(generationFixtureNeedsAttentionNonRetryable, true, false);
    expect(view.state).toBe("attention");
    expect(view.retryEligible).toBe(false);
  });

  it("preserves previous verified preview when current attempt failed", () => {
    const view = adaptCodeGenerator(generationFixtureWithPreviousPreview, true, false);
    expect(view.state).toBe("attention");
    expect(view.hasUsablePreview).toBe(true);
    expect(view.activePreview?.path).toBe("/p/run_gen_1/");
    expect(view.milestones.every((m) => m.state === "complete")).toBe(true);
  });

  it("fails closed into unsupported for unrecognized status", () => {
    const view = adaptCodeGenerator(generationFixtureUnsupported, true);
    expect(view.state).toBe("unsupported");
    expect(view.statusText).toContain("unrecognized status");
  });
});
