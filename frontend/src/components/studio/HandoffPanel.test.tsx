// @vitest-environment jsdom
import { h, render } from "preact";
import { act } from "preact/test-utils";
import { afterEach, describe, expect, it, vi } from "vitest";
import { HandoffPanel } from "./HandoffPanel";
import type { ApiClient, ReactHandoff } from "../../data/api-client";

let container: HTMLDivElement;
afterEach(() => {
  if (container) { render(null, container); container.remove(); }
  vi.useRealTimers();
});
const ready: ReactHandoff = { id: "old", source_version_id: "v1", status: "ready", expires_at: new Date(Date.now() + 3600000).toISOString(), share_link: "https://example.test/share/test", mcp_url: "https://example.test/mcp", error: null };
async function mount(api: Partial<ApiClient>, versionId = "v2") {
  container = document.createElement("div");
  document.body.append(container);
  await act(async () => { render(h(HandoffPanel, { api: api as ApiClient, sessionId: "session", versionId, disabled: false }), container); });
}
function prepareButton() { return Array.from(container.querySelectorAll("button")).find(button => button.textContent?.startsWith("Prepare"))!; }

describe("explicit React sharing", () => {
  it("does not prepare automatically and preserves the previous link on replacement failure", async () => {
    const api = { listHandoffs: vi.fn().mockResolvedValue({ handoffs: [ready] }), prepareHandoff: vi.fn().mockRejectedValue(new Error("Storage is temporarily unavailable.")) };
    await mount(api);
    expect(api.prepareHandoff).not.toHaveBeenCalled();
    await act(async () => { prepareButton().click(); });
    expect(api.prepareHandoff).toHaveBeenCalledWith("session", "v2");
    expect(container.querySelector("input")?.value).toBe(ready.share_link);
    expect(container.textContent).toContain("Storage is temporarily unavailable");
  });

  it("disables duplicate preparation and begins progress polling immediately", async () => {
    vi.useFakeTimers();
    const queued = { ...ready, id: "new", source_version_id: "v2", status: "queued", share_link: null };
    const api = { listHandoffs: vi.fn().mockResolvedValueOnce({ handoffs: [] }).mockResolvedValue({ handoffs: [queued] }), prepareHandoff: vi.fn().mockResolvedValue(queued) };
    await mount(api);
    await act(async () => { prepareButton().click(); });
    const button = Array.from(container.querySelectorAll("button")).find(button => button.textContent?.includes("Preparing"));
    expect(button?.disabled).toBe(true);
    const requests = api.listHandoffs.mock.calls.length;
    await act(async () => { await vi.advanceTimersByTimeAsync(2000); });
    expect(api.listHandoffs.mock.calls.length).toBeGreaterThan(requests);
    expect(api.prepareHandoff).toHaveBeenCalledTimes(1);
  });
});
