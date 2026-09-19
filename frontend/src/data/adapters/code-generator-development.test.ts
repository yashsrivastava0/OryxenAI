import { describe, expect, it } from "vitest";
import { adaptDevelopmentRun, mapDevelopmentStatus } from "./code-generator-development";

describe("Code Generator development projection adapter", () => {
  it("maps the standalone run lifecycle into product stage vocabulary", () => {
    expect(mapDevelopmentStatus("planning")).toBe("planning");
    expect(mapDevelopmentStatus("generating_routes")).toBe("generating");
    expect(mapDevelopmentStatus("smoke_testing")).toBe("verifying");
    expect(mapDevelopmentStatus("ready")).toBe("ready");
    expect(mapDevelopmentStatus("needs_attention")).toBe("needs_attention");
  });

  it("preserves real preview pointers and exposes a terminal diagnostic", () => {
    const projection = adaptDevelopmentRun(
      {
        run_id: "run-123",
        status: "needs_attention",
        coordinator_stage: "plan",
        pipeline_contract_version: "code-generator-v5",
        trace_id: "trace-123",
        current_attempt: 3,
        job_id: "job-plan-123",
        terminal_failure: {
          terminal_code: "HANDLER_ERROR",
          safe_user_summary: "Code Generator could not complete this stage.",
        },
        issues: [{ code: "HANDLER_ERROR", message: "Code Generator could not complete this stage." }],
      },
      {
        active_preview: { url: "http://127.0.0.1:4174/preview/active/" },
        candidate_preview: { url: "http://127.0.0.1:4174/preview/candidate/", verification_status: "unverified" },
      },
    );

    expect(projection.raw.status).toBe("needs_attention");
    expect(projection.raw.active_preview).toEqual({ url: "http://127.0.0.1:4174/preview/active/" });
    expect(projection.raw.candidate_preview).toEqual({
      url: "http://127.0.0.1:4174/preview/candidate/",
      verification_status: "unverified",
    });
    expect(projection.jobs[0]).toMatchObject({
      id: "job-plan-123",
      kind: "code_generator.v5.plan",
      status: "failed",
    });
  });
});
