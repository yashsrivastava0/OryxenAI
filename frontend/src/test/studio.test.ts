import { describe, expect, it } from "vitest";
import { h } from "preact";
import { render } from "preact-render-to-string";
import { adaptStudio, adaptStudioFailure } from "../data/adapters/studio";
import { FailurePanel } from "../components/studio/FailurePanel";
import { ChatPane } from "../components/studio/ChatPane";
import { PreviewPane, previewScale } from "../components/studio/PreviewPane";
import { StudioStage } from "../stages/studio/StudioStage";
import { JourneyRail } from "../components/JourneyRail";
import { appReducer, initialAppState } from "../app/store";
import { parseAppUrlState, serializeAppUrlState } from "../app/url-state";
import { resolveInitialStage } from "../app/AppShell";

const noop = async () => {};
const grant = async () => ({
  url: "/preview/g/token/index.html",
  expires_at: "2026-10-02T12:00:00+00:00",
  expires_in_seconds: 1800,
  version_id: "v2",
  version_number: 2,
});

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
  issue_count: 3,
  reference: "cg-abc123",
  issues: [],
};

function envelope(generator: Record<string, unknown>, extra: Record<string, unknown> = {}) {
  return { session_id: "s", session_revision: 3, code_generator: generator, versions: [], chat: [], jobs: [], ...extra };
}

const liveEnvelope = envelope(
  { status: "ready", active_version_id: "v2", active_version_number: 2 },
  {
    versions: [
      { id: "v2", seq: 2, version_number: 2, origin: "change", status: "ready", instruction: "shorter intro", completed_at: "2026-10-02T10:00:00+00:00" },
      { id: "v1", seq: 1, version_number: 1, origin: "initial", status: "ready", completed_at: "2026-10-02T09:00:00+00:00" },
    ],
    chat: [
      { id: "c1", seq: 1, role: "assistant", kind: "build", body: "Your portfolio is ready (version 1).", version_id: "v1" },
      { id: "c2", seq: 2, role: "user", kind: "message", body: "Make my intro shorter" },
      { id: "c3", seq: 3, role: "assistant", kind: "message", body: "I shortened your intro.", version_id: "v2" },
    ],
  },
);

function stage(view: ReturnType<typeof adaptStudio> | null, overrides: Record<string, unknown> = {}) {
  return h(StudioStage, {
    view,
    contentApproved: true,
    canMutate: true,
    inFlight: false,
    loadPreview: grant,
    onStart: noop,
    onStop: noop,
    onSend: noop,
    onRestore: noop,
    ...overrides,
  });
}

describe("StudioStage states", () => {
  it("is locked until the content plan is approved", () => {
    const html = render(stage(adaptStudio(envelope({ status: "not_started" }), false), { contentApproved: false }));
    expect(html).toContain("Stage Locked");
    expect(html).toContain("Approve your content plan first");
  });

  it("offers one explicit Generate button, and shows why an automatic start did not begin", () => {
    const view = adaptStudio(envelope({ status: "not_started" }), true);
    const html = render(stage(view, { startError: "Your content cannot be built into a page yet (1 problem)." }));
    expect(html).toContain("Generate my portfolio");
    expect(html).toContain("Your content cannot be built into a page yet");
    expect(render(stage(view, { inFlight: true }))).toContain("Starting…");
  });

  it("shows plain-language progress for the first build with a stop control", () => {
    const view = adaptStudio(
      envelope({ status: "build_running", in_flight: { run_id: "r", job_id: "j", version_id: "v1", origin: "initial", stage: "validating", elapsed_seconds: 31 } }),
      true,
    );
    const html = render(stage(view));
    expect(html).toContain("Your page is taking shape");
    expect(html).toContain("Illustrative view");
    expect(html).toContain("Checking every word, link and section");
    expect(html).toContain("Stop building");
    expect(html).toContain("Elapsed:");
    expect(html).toContain("31s");
    expect(html).toContain('aria-busy="true"');
  });

  it("explains a queued build instead of looking frozen", () => {
    const view = adaptStudio(
      envelope({ status: "build_running", in_flight: { run_id: "r", job_id: "j", version_id: "v1", origin: "initial", stage: "queued" } }),
      true,
    );
    expect(render(stage(view))).toContain("Waiting for a free builder");
  });

  it("reports a failed first build exactly: what, where, why, what to do, with a retry", () => {
    const view = adaptStudio(envelope({ status: "needs_attention", last_error: failure }), true);
    const html = render(stage(view));
    for (const text of [
      "Your portfolio could not be built yet",
      "What happened",
      "Where",
      "hero.intro",
      "Why",
      "The model changed approved wording.",
      "Expected",
      "Found",
      "What you can do",
      "cg-abc123",
      "Try building again",
      "Copy diagnostics",
      "approved content is safe",
    ]) {
      expect(html).toContain(text);
    }
    expect(html).toContain("and 2 more in the diagnostics");
  });

  it("opens the workspace with chat on the left and the preview on the right", () => {
    const html = render(stage(adaptStudio(liveEnvelope, true)));
    expect(html.indexOf("studio-pane--chat")).toBeLessThan(html.indexOf("studio-pane--preview"));
    expect(html).toContain('aria-label="Portfolio preview"'.replace("Portfolio preview", "Live portfolio preview"));
    expect(html).toContain("Version 2");
    expect(html).toContain("Make my intro shorter");
    expect(html).toContain("I shortened your intro.");
    expect(html).toContain("Versions (2)");
    expect(html).toContain("Restore");
    expect(html).toContain('role="tablist"');
  });

  it("calls a user-stopped build stopped, not failed", () => {
    const stopped = { ...failure, code: "JOB_CANCELLED", summary: "The build was stopped.", cause: "You stopped this build." };
    const html = render(stage(adaptStudio(envelope({ status: "needs_attention", last_error: stopped }), true)));
    expect(html).toContain("The build was stopped");
    expect(html).not.toContain("could not be built yet");
  });

  it("fails closed on an unrecognised status", () => {
    expect(render(stage(adaptStudio(envelope({ status: "mystery" }), true)))).toContain("Studio");
  });
});

describe("ChatPane", () => {
  const base = {
    chat: [],
    versions: [],
    activeVersionId: "v1",
    inFlight: null,
    lastError: null,
    busy: false,
    onSend: noop,
    onStop: noop,
    onRestore: noop,
  };

  it("starts with suggestions and an enabled composer", () => {
    const html = render(h(ChatPane, base));
    expect(html).toContain("Make my introduction a bit shorter");
    expect(html).toContain('id="studio-message"');
    expect(html).toContain("Describe the change you want");
    expect(html).toContain("Colors and layout are not available yet");
    const composer = /<textarea[^>]*>/.exec(html)?.[0] ?? "";
    expect(composer).not.toContain("disabled");
    expect(html).toContain('<button type="submit" class="btn-primary" disabled>'); // nothing typed yet
  });

  it("locks the composer and offers Stop while a change is being built", () => {
    const html = render(
      h(ChatPane, {
        ...base,
        inFlight: { stage: "planning", origin: "change", instruction: "x", elapsedSeconds: 2, versionId: "v3" },
      }),
    );
    expect(html).toContain("Understanding your request…");
    expect(html).toContain(">Stop<");
    expect(html).toContain("Wait for the current change to finish");
    expect(html).toContain("disabled");
    expect(html).not.toContain("studio-suggestion");
  });

  it("does not show a failure link after the owner stopped a change", () => {
    const stopped = adaptStudioFailure({ ...failure, code: "JOB_CANCELLED" });
    expect(render(h(ChatPane, { ...base, lastError: stopped }))).not.toContain("See exactly what went wrong");
  });

  it("keeps the failed-edit details one click away", () => {
    const parsed = adaptStudioFailure(failure);
    const html = render(h(ChatPane, { ...base, lastError: parsed }));
    expect(html).toContain("See exactly what went wrong");
    expect(html).toContain('aria-expanded="false"');
  });

  it("marks the live version and hides restore for it", () => {
    const view = adaptStudio(liveEnvelope, true);
    const html = render(h(ChatPane, { ...base, chat: view.chat, versions: view.versions }));
    expect(html).toContain("studio-pill");
    expect(html).toContain(">Live<");
    expect(html).toContain("v2");
  });
});

describe("PreviewPane", () => {
  it("renders the device and zoom controls and a placeholder before the page loads", () => {
    const html = render(h(PreviewPane, { versionId: "v2", versionNumber: 2, loadPreview: grant }));
    for (const label of ["Desktop", "Tablet", "Mobile", "Fit", "100%", "Reload"]) expect(html).toContain(label);
    expect(html).toContain("Version 2");
    expect(html).not.toContain("<iframe");
  });

  it("shows an Updating pill while the next version is being built", () => {
    expect(render(h(PreviewPane, { versionId: "v2", versionNumber: 2, loadPreview: grant, updating: true }))).toContain("Updating…");
  });

  it("scales a wide device down to fit the pane but never up", () => {
    expect(previewScale(1000, 1280, true)).toBeCloseTo((1000 - 24) / 1280);
    expect(previewScale(2000, 1280, true)).toBe(1);
    expect(previewScale(500, 1280, false)).toBe(1);
    expect(previewScale(0, 1280, true)).toBe(1);
    expect(previewScale(100, 1280, true)).toBeGreaterThanOrEqual(0.2);
  });
});

describe("FailurePanel", () => {
  it("never offers a retry for a failure the person cannot fix by retrying", () => {
    const parsed = adaptStudioFailure({ ...failure, retryable: false })!;
    const html = render(h(FailurePanel, { failure: parsed, onRetry: noop }));
    expect(html).not.toContain(">Try again<");
    expect(html).toContain("Copy diagnostics");
  });
});

describe("journey, url and store integration", () => {
  it("renders three stages in the journey rail", () => {
    const vnode = JourneyRail({
      journey: [
        { id: "discover", ordinal: 1, label: "Discover", state: "complete", isSelectable: true },
        { id: "content", ordinal: 2, label: "Content", state: "complete", isSelectable: true },
        { id: "studio", ordinal: 3, label: "Studio", state: "available", isSelectable: true },
      ],
      selectedStageId: "studio",
      onSelect: () => {},
    });
    const html = render(vnode as never);
    expect(html).toContain("Studio");
    expect(html.match(/journey-step /g)?.length).toBe(3);
  });

  it("round-trips the studio stage in the URL", () => {
    expect(parseAppUrlState("?stage=studio&view=work")).toEqual({ stage: "studio", view: "work", screen: null });
    expect(serializeAppUrlState({ stage: "studio", view: "work" })).toBe("?stage=studio&view=work");
  });

  it("keeps the Studio view model in the store and clears it on reset", () => {
    const view = adaptStudio(liveEnvelope, true);
    let state = appReducer(initialAppState, { type: "studio/set", view });
    expect(state.studio?.activeVersionNumber).toBe(2);
    expect(Object.keys(state)).not.toContain("preview");
    state = appReducer({ ...state, sessionId: "s" }, { type: "pipeline/reset", sessionId: "s", revision: 9 });
    expect(state.studio).toBeNull();
  });

  it("lands on the furthest actionable stage and never on a locked Studio", () => {
    expect(resolveInitialStage(null, true, true)).toEqual({ stage: "studio", corrected: true });
    expect(resolveInitialStage("discover", true, true)).toEqual({ stage: "studio", corrected: true });
    expect(resolveInitialStage("content", true, true)).toEqual({ stage: null, corrected: false });
    expect(resolveInitialStage("studio", true, true)).toEqual({ stage: null, corrected: false });
    expect(resolveInitialStage("studio", true, false)).toEqual({ stage: "content", corrected: true });
    expect(resolveInitialStage("studio", false, false)).toEqual({ stage: "discover", corrected: true });
  });
});
