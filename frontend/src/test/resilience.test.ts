import type { VNode } from "preact";
import { describe, expect, it } from "vitest";
import { ErrorBoundary } from "../components/ErrorBoundary";
import { ApiError, parseApiError } from "../data/errors";
import { safeLocalStorage, safeSessionStorage } from "../data/safe-storage";

describe("product resilience", () => {
  it("maps structured server errors without exposing internal copy", async () => {
    const response = new Response(JSON.stringify({ error: { code: "PORTFOLIO_SESSION_STALE", message: "internal" } }), { status: 409, headers: { "Content-Type": "application/json" } });
    const error = await parseApiError(response);
    expect(error).toBeInstanceOf(ApiError);
    expect(error.code).toBe("PORTFOLIO_SESSION_STALE");
    expect(error.message).toBe("This portfolio changed in another tab. Refresh to see the latest state.");
  });

  it("keeps only safe provider attribution and retry guidance", async () => {
    const response = new Response(
      JSON.stringify({
        error: {
          code: "PROVIDER_RATE_LIMIT_ERROR",
          message: "internal provider body",
          request_id: "request-123",
          details: {
            provider_label: "Google Gemini",
            operation_label: "discovery.understand_and_question",
            retry_after_seconds: 12,
            support_reference: "model-abcdef123456",
            credential_alias: "GEMINI_2",
            api_key: "must-not-escape",
          },
        },
      }),
      { status: 429, headers: { "Content-Type": "application/json" } },
    );
    const error = await parseApiError(response);
    expect(error.providerLabel).toBe("Google Gemini");
    expect(error.operationLabel).toBe("discovery.understand_and_question");
    expect(error.retryAfterSeconds).toBe(12);
    expect(error.supportReference).toBe("model-abcdef123456");
    expect(String(error)).not.toContain("GEMINI_2");
    expect(String(error)).not.toContain("must-not-escape");
  });

  it("preserves drafts when browser storage is available", () => {
    safeSessionStorage.setItem("resilience_key", "saved draft");
    safeLocalStorage.setItem("preference_key", "saved preference");
    expect(safeSessionStorage.getItem("resilience_key")).toBe("saved draft");
    expect(safeLocalStorage.getItem("preference_key")).toBe("saved preference");
    safeSessionStorage.removeItem("resilience_key");
    safeLocalStorage.removeItem("preference_key");
  });

  it("renders a recoverable stage error boundary", () => {
    const boundary = new ErrorBoundary({ children: null, fallbackTitle: "Stage rendering error" });
    boundary.state = { hasError: true, error: new Error("render failed") };
    const rendered = boundary.render() as VNode<{ className?: string }>;
    expect(rendered.props.className).toBe("stage-error-boundary-panel");
  });
});
