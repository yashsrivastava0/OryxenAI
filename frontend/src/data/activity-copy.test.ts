import { describe, expect, it } from "vitest";
import { formatActivityStatus } from "./activity-copy";

describe("formatActivityStatus", () => {
  it("produces present-tense, ellipsis-terminated working copy for discovery", () => {
    const copy = formatActivityStatus("discovery", "brief_running");
    expect(copy.working).toBe(true);
    expect(copy.complete).toBe(false);
    expect(copy.text.endsWith("…")).toBe(true);
    // Action + Specific-Item, not a generic "Working…".
    expect(copy.text).toBe("Shaping your portfolio brief from your answers…");
    expect(copy.text).not.toMatch(/^Working\.\.\.?$/);
  });

  it("produces past-tense completion copy without an ellipsis for discovery", () => {
    const copy = formatActivityStatus("discovery", "approved");
    expect(copy.working).toBe(false);
    expect(copy.complete).toBe(true);
    expect(copy.text.endsWith("…")).toBe(false);
    expect(copy.text).toBe("Approved your portfolio brief");
  });

  it("covers content_architect working and complete", () => {
    const working = formatActivityStatus("content_architect", "build_running");
    expect(working.working).toBe(true);
    expect(working.text).toBe("Structuring the site plan and page content from your approved brief…");

    const done = formatActivityStatus("content_architect", "approved");
    expect(done.complete).toBe(true);
    expect(done.text).toBe("Approved your content plan across every page");
  });

  it("reports a stale completion as needing a refresh, not as done", () => {
    const copy = formatActivityStatus("content_architect", "approved", { stale: true });
    expect(copy.complete).toBe(false);
    expect(copy.working).toBe(false);
    expect(copy.text).toBe("Your content plan is out of date and needs an update");
  });

  it("refines active work copy with a milestone and retry, keeping one ellipsis", () => {
    const copy = formatActivityStatus("content_architect", "build_running", {
      milestone: "write_pages",
      attempt: 2,
    });
    expect(copy.working).toBe(true);
    expect(copy.text).toBe(
      "Structuring the site plan and page content from your approved brief (write pages) — retry 2…",
    );
    // Exactly one trailing ellipsis character.
    expect(copy.text.match(/…/g)?.length).toBe(1);
  });

  it("emits specific, non-generic idle copy for review and not-started states", () => {
    const review = formatActivityStatus("content_architect", "content_review");
    expect(review.working).toBe(false);
    expect(review.complete).toBe(false);
    expect(review.text).toBe("Waiting for you to review your content plan");

    const idle = formatActivityStatus("content_architect", "not_started");
    expect(idle.text).toBe("Ready to start on your content plan");
    expect(idle.text).not.toMatch(/working/i);
  });

  it("fails safe with specific copy for an unrecognised working status", () => {
    // A newer backend "*_running" status still reads as forward progress.
    const copy = formatActivityStatus("discovery", "polishing_running");
    expect(copy.working).toBe(true);
    expect(copy.text).toBe("Working on your portfolio brief…");
  });
});
