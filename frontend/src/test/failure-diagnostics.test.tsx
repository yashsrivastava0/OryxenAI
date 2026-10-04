// @vitest-environment jsdom
import { h, render } from "preact";
import { afterEach, describe, expect, it, vi } from "vitest";
import { AttentionPanel } from "../components/AttentionPanel";

afterEach(() => {
  document.body.replaceChildren();
  vi.restoreAllMocks();
});

describe("failure-only diagnostic copy", () => {
  it("copies the failed operation, time and safe issue path", async () => {
    const writeText = vi.fn().mockResolvedValue(undefined);
    Object.defineProperty(navigator, "clipboard", { configurable: true, value: { writeText } });
    const host = document.createElement("div");
    document.body.append(host);
    render(h(AttentionPanel, {
      stage: "content_architect",
      summary: "The model output was invalid.",
      errorDetails: {
        summary: "The model output was invalid.",
        code: "MODEL_OUTPUT_INVALID",
        operationLabel: "content_architect.build",
        suboperation: "approval_readiness",
        occurredAt: "2026-10-04T10:00:42Z",
        supportReference: "model-3a2e7372d0ee",
        issueCount: 12,
        issues: [{ code: "coverage_path_unpopulated", sourceId: "fact/f4", path: "page_content.atlas.education[0]" }],
      },
    }), host);

    (host.querySelector("button.diagnostic-copy-button") as HTMLButtonElement).click();
    await vi.waitFor(() => expect(writeText).toHaveBeenCalledOnce());
    const packet = JSON.parse(writeText.mock.calls[0]![0]);
    expect(packet.stage).toBe("content_architect");
    expect(packet.suboperation).toBe("approval_readiness");
    expect(packet.occurred_at).toBe("2026-10-04T10:00:42Z");
    expect(packet.reference).toBe("model-3a2e7372d0ee");
    expect(packet.issues[0]).toEqual({
      code: "coverage_path_unpopulated",
      sourceId: "fact/f4",
      path: "page_content.atlas.education[0]",
    });
    expect(JSON.stringify(packet)).not.toContain("api_key");
    render(null, host);
  });
});
