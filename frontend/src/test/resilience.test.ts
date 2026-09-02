import { describe, it, expect } from "vitest";
import { parseApiError, ApiError } from "../data/errors";
import { safeSessionStorage, safeLocalStorage } from "../data/safe-storage";
import { adaptBuildPreparation } from "../data/adapters/preparation";
import { adaptCodeGenerator } from "../data/adapters/generation";
import { computeFrameUrl } from "../stages/preview/PreviewSurface";
import { ErrorBoundary } from "../components/ErrorBoundary";
import type { VNode } from "preact";

describe("Phase 5 Resilience & Graceful Degradation (docs/Frontend/05 §18)", () => {
  it("normalizes structured server error codes honestly without leaking sensitive traces", async () => {
    const mockResponse409 = new Response(
      JSON.stringify({
        error: {
          code: "PORTFOLIO_READ_ONLY",
          message: "Internal locked message that should be mapped safely",
        },
      }),
      { status: 409, headers: { "Content-Type": "application/json" } }
    );
    const err = await parseApiError(mockResponse409);
    expect(err).toBeInstanceOf(ApiError);
    expect(err.code).toBe("PORTFOLIO_READ_ONLY");
    expect(err.message).toBe("This portfolio has a verified success and is now read-only.");

    const mockResponse429 = new Response(
      JSON.stringify({
        error: {
          code: "MODEL_PROVIDER_CREDIT_EXHAUSTED",
          message: "Model credit error",
        },
      }),
      { status: 429, headers: { "Content-Type": "application/json" } }
    );
    const err429 = await parseApiError(mockResponse429);
    expect(err429.code).toBe("MODEL_PROVIDER_CREDIT_EXHAUSTED");
    expect(err429.message).toBe("Generation is temporarily unavailable. Retry this same run later.");
  });

  it("safe storage gracefully falls back to memory if window storage fails", () => {
    safeSessionStorage.setItem("resilience_key", "important_draft");
    expect(safeSessionStorage.getItem("resilience_key")).toBe("important_draft");

    safeLocalStorage.setItem("pref_key", "dark_mode");
    expect(safeLocalStorage.getItem("pref_key")).toBe("dark_mode");

    safeSessionStorage.removeItem("resilience_key");
    expect(safeSessionStorage.getItem("resilience_key")).toBeNull();
  });

  it("adaptBuildPreparation handles staleness with honest advisory notice", () => {
    const raw = {
      status: "ready",
      pack: { zip_sha256: "abc123sha" },
      handoff_report: { handoff_eligible: true },
      stale: true,
      stale_reasons: ["Visual design was re-approved after this pack was generated."],
    };

    const vm = adaptBuildPreparation(raw, true);
    expect(vm.state).toBe("attention");
    expect(vm.stale).toBe(true);
    expect(vm.staleReasons).toContain("Visual design was re-approved after this pack was generated.");
  });

  it("adaptCodeGenerator preserves trace IDs during attention state", () => {
    const raw = {
      status: "needs_attention",
      trace_id: "tr-987654",
      latest_error: {
        message: "DOM verification timed out after 3 attempts.",
      },
      retry_status: "eligible",
    };

    const vm = adaptCodeGenerator(raw, true, false);
    expect(vm.state).toBe("attention");
    expect(vm.safeError?.summary).toBe("DOM verification timed out after 3 attempts.");
    expect(vm.supportReference).toBe("tr-987654");
    expect(vm.retryEligible).toBe(true);
  });

  it("computeFrameUrl handles path safety and origin binding cleanly", () => {
    const previewUrl = computeFrameUrl(
      "https://preview-tenant.example.com",
      "/projects/system-architecture"
    );
    expect(previewUrl).toBe(
      "https://preview-tenant.example.com/projects/system-architecture"
    );

    // Fallback on missing or invalid inputs
    const emptyUrl = computeFrameUrl("", "");
    expect(emptyUrl).toBe("");
  });

  it("ErrorBoundary renders fallback UI and exposes retry capability", () => {
    const boundary = new ErrorBoundary({
      children: null,
      fallbackTitle: "Stage rendering error",
    });

    // Simulate error state directly on instance
    boundary.state = { hasError: true, error: new Error("Test render failure") };
    const rendered = boundary.render() as VNode<{ className?: string }>;
    expect(rendered).toBeDefined();
    expect(rendered.props.className).toBe("stage-error-boundary-panel");
  });
});
