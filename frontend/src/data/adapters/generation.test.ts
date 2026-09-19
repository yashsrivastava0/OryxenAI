import { describe, expect, it } from "vitest";
import { adaptCodeGenerator, friendlyRouteLabel } from "./generation";
import {
  generationNeedsAttentionNoPreview,
  generationNeedsAttentionWithCandidate,
  generationNeedsAttentionWithPreview,
  generationNotStarted,
  generationPlanningWithFailedJob,
  generationReady,
  generationStale,
  generationWorking,
  generationWorkingWithEstimate,
} from "./generation.fixtures";

describe("adaptCodeGenerator", () => {
  it("keeps the stage locked until Build Preparation is approved", () => {
    expect(adaptCodeGenerator(generationNotStarted, false).state).toBe("locked");
    expect(adaptCodeGenerator(generationNotStarted, true).state).toBe("available");
  });

  it("maps working and ready states into honest product states", () => {
    const working = adaptCodeGenerator(generationWorking, true, [
      { id: "job-generate-1", kind: "code_generator.generate", status: "running", attempt: 1 },
    ]);
    expect(working.state).toBe("working");
    expect(working.job?.id).toBe("job-generate-1");
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
    const withPreview = adaptCodeGenerator(generationNeedsAttentionWithPreview, true, [
      {
        id: "job-verify-failed",
        kind: "code_generator.verify_and_preview",
        status: "failed",
        attempt: 3,
        error: { code: "VERIFY_FAILED", message: "safe failure" },
      },
    ]);
    expect(withPreview.state).toBe("attention");
    expect(withPreview.preview?.url).toBe("https://preview.example.test/preview/abc123/");
    expect(withPreview.safeError?.retryable).toBe(true);
    expect(withPreview.retryAvailable).toBe(true);

    const withoutPreview = adaptCodeGenerator(generationNeedsAttentionNoPreview, true, [
      {
        id: "job-verify-failed",
        kind: "code_generator.verify_and_preview",
        status: "cancelled",
        attempt: 3,
      },
    ]);
    expect(withoutPreview.state).toBe("attention");
    expect(withoutPreview.preview).toBeNull();
    expect(withoutPreview.retryAvailable).toBe(false);
  });

  it("converges a planning response with a failed active job to attention", () => {
    const view = adaptCodeGenerator(generationPlanningWithFailedJob, true, [
      {
        id: "job-plan-failed",
        kind: "code_generator.v5.plan",
        status: "failed",
        attempt: 3,
        max_attempts: 3,
        error: { code: "HANDLER_ERROR", message: "The background job handler failed." },
      },
    ]);
    expect(view.state).toBe("attention");
    expect(view.status).toBe("planning");
    expect(view.safeError?.summary).toBe("The background job handler failed.");
    expect(view.safeError?.retryable).toBe(false);
    expect(view.retryAvailable).toBe(false);
  });

  it("does not confuse current_run_id with a job id", () => {
    const view = adaptCodeGenerator(
      {
        ...generationWorking,
        current_run_id: "run-123",
        active_job_id: "job-generate-1",
      },
      true,
      [
        { id: "run-123", kind: "code_generator.plan", status: "completed", attempt: 1 },
        { id: "job-generate-1", kind: "code_generator.generate", status: "running", attempt: 1 },
      ],
    );
    expect(view.job?.id).toBe("job-generate-1");
  });

  it("uses the coordinator stage for legacy responses without active job fields", () => {
    const legacy = { ...generationWorking } as Record<string, unknown>;
    delete legacy.active_job_id;
    delete legacy.active_job_kind;
    const view = adaptCodeGenerator(
      legacy,
      true,
      [
        { id: "job-plan", kind: "code_generator.plan", status: "completed", attempt: 1 },
        { id: "job-generate", kind: "code_generator.generate", status: "running", attempt: 1 },
      ],
    );
    expect(view.job?.id).toBe("job-generate");
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

  it("maps progress.stage_estimate into estimatedRemainingMs/estimatedTotalMs/estimateSource", () => {
    const view = adaptCodeGenerator(generationWorkingWithEstimate, true);
    expect(view.estimatedRemainingMs).toBe(7916000);
    expect(view.estimatedTotalMs).toBe(8100000);
    expect(view.estimateSource).toBe("configured_budget");
  });

  it("leaves estimate fields undefined when progress exists but stage_estimate is absent", () => {
    const view = adaptCodeGenerator(generationWorking, true);
    expect(view.estimatedRemainingMs).toBeUndefined();
    expect(view.estimatedTotalMs).toBeUndefined();
    expect(view.estimateSource).toBeUndefined();
  });

  it("leaves estimate fields undefined when no progress object exists at all", () => {
    const view = adaptCodeGenerator(generationNotStarted, true);
    expect(view.estimatedRemainingMs).toBeUndefined();
    expect(view.estimatedTotalMs).toBeUndefined();
    expect(view.estimateSource).toBeUndefined();
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
