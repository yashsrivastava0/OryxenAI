import { describe, expect, it } from "vitest";
import {
  adaptStudio,
  adaptStudioFailure,
  failureDiagnostics,
  readyVersions,
  studioMilestones,
  studioStageLabel,
} from "./studio";

const failure = {
  code: "PAGE_COPY_MISMATCH",
  stage: "validate",
  summary: "The generated page failed 1 check; first: The text for hero.intro differs.",
  cause: "The model changed approved wording.",
  where: [{ kind: "field", ref: "hero.intro", detail: "The text for hero.intro differs." }],
  expected: "Senior engineer",
  found: "Staff engineer",
  owner: "model_output",
  retryable: true,
  action: "Try again.",
  issue_count: 1,
  reference: "cg-abc123",
  issues: [{ code: "COPY_MISMATCH", severity: "error", message: "differs", path: "hero.intro" }],
};

function envelope(generator: Record<string, unknown>, extra: Record<string, unknown> = {}) {
  return {
    session_id: "s1",
    session_revision: 7,
    code_generator: generator,
    versions: [],
    chat: [],
    jobs: [],
    ...extra,
  };
}

describe("adaptStudio", () => {
  it("is locked until the content plan is approved", () => {
    expect(adaptStudio(envelope({ status: "not_started" }), false).state).toBe("locked");
  });

  it("offers generation once content is approved and nothing was built", () => {
    const view = adaptStudio(envelope({ status: "not_started" }), true);
    expect(view.state).toBe("available");
    expect(view.building).toBe(false);
    expect(view.statusText).toContain("Ready to generate");
  });

  it("shows full-page progress for the first build and the workspace for later ones", () => {
    const inFlight = { run_id: "r", job_id: "j", version_id: "v1", origin: "initial", stage: "generating", elapsed_seconds: 12.4 };
    const first = adaptStudio(envelope({ status: "build_running", in_flight: inFlight }), true);
    expect(first.state).toBe("working");
    expect(first.building).toBe(true);
    expect(first.inFlight).toMatchObject({ stage: "generating", origin: "initial", elapsedSeconds: 12.4 });

    const later = adaptStudio(
      envelope({
        status: "build_running",
        active_version_id: "v1",
        active_version_number: 1,
        in_flight: { ...inFlight, version_id: "v2", origin: "change", instruction: "shorter intro", stage: "planning" },
      }),
      true,
    );
    expect(later.state).toBe("complete");
    expect(later.building).toBe(true);
    expect(later.inFlight?.instruction).toBe("shorter intro");
  });

  it("opens the workspace when a page is live, even with a recorded failed edit", () => {
    const view = adaptStudio(
      envelope({ status: "ready", active_version_id: "v1", active_version_number: 3, last_error: failure }),
      true,
    );
    expect(view.state).toBe("complete");
    expect(view.activeVersionNumber).toBe(3);
    expect(view.lastError?.code).toBe("PAGE_COPY_MISMATCH");
  });

  it("needs attention when the first build failed", () => {
    const view = adaptStudio(envelope({ status: "needs_attention", last_error: failure }), true);
    expect(view.state).toBe("attention");
    expect(view.lastError?.where[0]).toEqual({ kind: "field", ref: "hero.intro", detail: "The text for hero.intro differs." });
    expect(view.lastError?.reference).toBe("cg-abc123");
  });

  it("fails closed on an unknown status and on a malformed envelope", () => {
    expect(adaptStudio(envelope({ status: "mystery" }), true).state).toBe("unsupported");
    expect(adaptStudio(null, true).state).toBe("unsupported");
    expect(adaptStudio("nope", false).state).toBe("locked");
    expect(adaptStudio(envelope({ status: "ready" }), true).state).toBe("available"); // no live page
  });

  it("reads versions and chat defensively", () => {
    const view = adaptStudio(
      envelope(
        { status: "ready", active_version_id: "v2", active_version_number: 2 },
        {
          versions: [
            { id: "v2", seq: 2, version_number: 2, origin: "change", status: "ready", instruction: "x", restricted: false, summary: { warning_count: 1, browser: "passed" } },
            { id: "v1", seq: 1, version_number: 1, origin: "initial", status: "ready", restricted: true },
            { id: "v3", seq: 3, version_number: null, origin: "weird", status: "failed", error: failure },
            { nope: true },
          ],
          chat: [
            { id: "c1", seq: 1, role: "user", kind: "message", body: "hello" },
            { id: "c2", seq: 2, role: "alien", kind: "other", body: "x", version_id: "v2" },
            { body: "no id" },
          ],
        },
      ),
      true,
    );
    expect(view.versions.map((item) => item.id)).toEqual(["v2", "v1", "v3"]);
    expect(view.versions[2]).toMatchObject({ origin: "initial", failure: { code: "PAGE_COPY_MISMATCH" } });
    expect(view.versions[0]).toMatchObject({ warningCount: 1, browser: "passed" });
    expect(readyVersions(view.versions).map((item) => item.versionNumber)).toEqual([2, 1]);
    expect(view.chat).toHaveLength(2);
    expect(view.chat[1]).toMatchObject({ role: "system", kind: "message", versionId: "v2" });
  });

  it("bounds oversized text from the server", () => {
    const huge = "x".repeat(10000);
    const view = adaptStudioFailure({ code: "X", summary: huge, cause: huge, where: Array.from({ length: 30 }, () => ({ kind: "field", ref: huge })), issues: Array.from({ length: 50 }, () => ({ code: "c", message: huge })) });
    expect(view?.summary.length).toBeLessThanOrEqual(600);
    expect(view?.where).toHaveLength(8);
    expect(view?.issues).toHaveLength(20);
    expect(adaptStudioFailure({ summary: "no code" })).toBeNull();
    expect(adaptStudioFailure(null)).toBeNull();
  });
});

describe("studio progress copy", () => {
  it("walks the milestones as the server stage advances", () => {
    const states = (stage: Parameters<typeof studioMilestones>[0]) => studioMilestones(stage).map((item) => item.state);
    expect(states("queued")).toEqual(["complete", "current", "quiet", "quiet", "quiet"]);
    expect(states("generating")).toEqual(["complete", "current", "quiet", "quiet", "quiet"]);
    expect(states("validating")).toEqual(["complete", "complete", "current", "quiet", "quiet"]);
    expect(states("verifying")).toEqual(["complete", "complete", "complete", "current", "quiet"]);
  });

  it("describes each stage in plain language", () => {
    expect(studioStageLabel("queued", "initial")).toMatch(/Waiting/);
    expect(studioStageLabel("planning", "change")).toBe("Understanding your request");
    expect(studioStageLabel("generating", "change")).toBe("Rewriting the page");
    expect(studioStageLabel("generating", "initial")).toBe("Writing your page");
    expect(studioStageLabel("verifying", "initial")).toMatch(/browser/);
  });

  it("builds copyable diagnostics without raw page markup", () => {
    const parsed = adaptStudioFailure(failure);
    expect(parsed).not.toBeNull();
    const text = failureDiagnostics(parsed!);
    expect(JSON.parse(text)).toMatchObject({ code: "PAGE_COPY_MISMATCH", reference: "cg-abc123", issue_count: 1 });
    expect(text).not.toContain("<script");
  });
});
