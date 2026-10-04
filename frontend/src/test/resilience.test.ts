import type { VNode } from "preact";
import { h } from "preact";
import render from "preact-render-to-string";
import { describe, expect, it } from "vitest";
import { ErrorBoundary } from "../components/ErrorBoundary";
import { ApiError, parseApiError } from "../data/errors";
import { safeLocalStorage, safeSessionStorage } from "../data/safe-storage";
import { captureFailure, formatFailureDiagnostics } from "../data/failure-diagnostics";
import { AttentionPanel } from "../components/AttentionPanel";
import { ConnectionBanner } from "../components/ConnectionBanner";

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
    boundary.state = { hasError: true, error: new Error("render failed"), occurredAt: "2026-10-04T10:00:00Z" };
    const rendered = boundary.render() as VNode<{ className?: string }>;
    expect(rendered.props.className).toBe("stage-error-boundary-panel");
  });

  it("copies failure location and safe API metadata without unknown error text", () => {
    const error = new ApiError("The request failed safely.", {
      code: "MODEL_OUTPUT_INVALID",
      status: 409,
      requestId: "request-123",
      details: { support_reference: "model-abcdef123456" },
    });
    const report = JSON.parse(formatFailureDiagnostics(captureFailure(error, "content_architect", "start", "fallback")));
    expect(report.stage).toBe("content_architect");
    expect(report.code).toBe("MODEL_OUTPUT_INVALID");
    expect(report.http_status).toBe(409);
    expect(report.request_id).toBe("request-123");
    expect(report.reference).toBe("model-abcdef123456");
    expect(report.occurred_at).toMatch(/^\d{4}-\d{2}-\d{2}T/);
    const unknown = formatFailureDiagnostics(captureFailure(new Error("secret portfolio text"), "studio", "preview", "Preview failed."));
    expect(unknown).toContain("Preview failed.");
    expect(unknown).not.toContain("secret portfolio text");
  });

  it("shows Copy diagnostics only for a failed workflow or connection state", () => {
    const failed = render(h(AttentionPanel, { stage: "content_architect", summary: "Build failed." }));
    expect(failed).toContain("Copy diagnostics");
    expect(render(h(ConnectionBanner, { state: "confirmed" }))).not.toContain("Copy diagnostics");
    expect(render(h(ConnectionBanner, { state: "checking" }))).not.toContain("Copy diagnostics");
    expect(render(h(ConnectionBanner, { state: "offline" }))).toContain("Copy diagnostics");
  });
});
