import type { VNode } from "preact";
import { describe, expect, it } from "vitest";
import { ErrorBoundary } from "../components/ErrorBoundary";
import { ApiError, parseApiError } from "../data/errors";
import { safeLocalStorage, safeSessionStorage } from "../data/safe-storage";

describe("product resilience", () => {
  it("maps structured server errors without exposing internal copy", async () => {
    const response = new Response(JSON.stringify({ error: { code: "PORTFOLIO_READ_ONLY", message: "internal" } }), { status: 409, headers: { "Content-Type": "application/json" } });
    const error = await parseApiError(response);
    expect(error).toBeInstanceOf(ApiError);
    expect(error.code).toBe("PORTFOLIO_READ_ONLY");
    expect(error.message).toBe("This portfolio has a verified success and is now read-only.");
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
