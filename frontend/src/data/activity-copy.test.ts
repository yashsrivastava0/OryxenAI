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

  it("covers visual_design_director working and complete", () => {
    const working = formatActivityStatus("visual_design_director", "build_running");
    expect(working.working).toBe(true);
    expect(working.text).toBe("Developing the visual direction from your approved content plan…");

    const done = formatActivityStatus("visual_design_director", "approved");
    expect(done.complete).toBe(true);
    expect(done.text).toBe("Approved your visual direction for the whole site");
  });

  it("covers build_preparation working and complete", () => {
    const working = formatActivityStatus("build_preparation", "running");
    expect(working.working).toBe(true);
    expect(working.text.endsWith("…")).toBe(true);
    expect(working.text).toBe("Compiling the build handoff from your approved content and design…");

    const done = formatActivityStatus("build_preparation", "ready");
    expect(done.complete).toBe(true);
    expect(done.text).toBe("Prepared the build handoff for generation");
  });

  it("covers code_generator across several working statuses and completion", () => {
    const generating = formatActivityStatus("code_generator", "generating");
    expect(generating.working).toBe(true);
    expect(generating.text).toBe("Generating your portfolio source across every page…");

    const verifying = formatActivityStatus("code_generator", "verifying");
    expect(verifying.working).toBe(true);
    expect(verifying.text).toBe("Verifying the built site across desktop and mobile viewports…");

    const done = formatActivityStatus("code_generator", "ready");
    expect(done.complete).toBe(true);
    expect(done.text).toBe("Generated and verified your portfolio");
  });

  it("reports a stale completion as needing a refresh, not as done", () => {
    const copy = formatActivityStatus("code_generator", "ready", { stale: true });
    expect(copy.complete).toBe(false);
    expect(copy.working).toBe(false);
    expect(copy.text).toBe("Your portfolio is out of date and needs to be prepared again");
  });

  it("refines working copy with a milestone and retry, keeping one ellipsis", () => {
    const copy = formatActivityStatus("code_generator", "generating", {
      milestone: "generate_pages",
      attempt: 2,
    });
    expect(copy.working).toBe(true);
    expect(copy.text).toBe(
      "Generating your portfolio source across every page (generate pages) — retry 2…",
    );
    // Exactly one trailing ellipsis character.
    expect(copy.text.match(/…/g)?.length).toBe(1);
  });

  it("emits specific, non-generic idle copy for review and not-started states", () => {
    const review = formatActivityStatus("content_architect", "content_review");
    expect(review.working).toBe(false);
    expect(review.complete).toBe(false);
    expect(review.text).toBe("Waiting for you to review your content plan");

    const idle = formatActivityStatus("build_preparation", "not_started");
    expect(idle.text).toBe("Ready to start on your build handoff");
    expect(idle.text).not.toMatch(/working/i);
  });

  it("fails safe with specific copy for an unrecognised working status", () => {
    // A newer backend "*_running" status still reads as forward progress.
    const copy = formatActivityStatus("discovery", "polishing_running");
    expect(copy.working).toBe(true);
    expect(copy.text).toBe("Working on your portfolio brief…");
  });
});
