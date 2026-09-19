import { describe, expect, it } from "vitest";
import {
  resolveInitialStage,
  shouldExposeGenerationAfterPreparation,
  shouldFetchGenerationState,
} from "./AppShell";

// Covers the initial-load stage normalization performed once inside
// refetchCurrentSession's `initialNormalizationDone` guard. Backward
// correction (requested stage ahead of approved progress) already existed;
// forward correction (requested/default "discover" while later stages are
// already approved) was the missing branch that left users stranded on
// stale Discovery content after a full page reload.
describe("resolveInitialStage", () => {
  it("does not correct when nothing is approved and discover was requested", () => {
    expect(resolveInitialStage("discover", false, false, false, false)).toEqual({
      stage: null,
      corrected: false,
    });
    expect(resolveInitialStage(null, false, false, false, false)).toEqual({
      stage: null,
      corrected: false,
    });
  });

  it("falls back from content to discover when discovery is not approved (existing backward case)", () => {
    expect(resolveInitialStage("content", false, false, false, false)).toEqual({
      stage: "discover",
      corrected: true,
    });
  });

  it("falls back from design to content when only discovery is approved (existing backward case)", () => {
    expect(resolveInitialStage("design", true, false, false, false)).toEqual({
      stage: "content",
      corrected: true,
    });
  });

  it("falls back from prepare to design when content/design are not both approved (existing backward case)", () => {
    expect(resolveInitialStage("prepare", true, true, false, false)).toEqual({
      stage: "design",
      corrected: true,
    });
  });

  it("falls back from generate to prepare when preparation is not approved (existing backward case)", () => {
    expect(resolveInitialStage("generate", true, true, true, false)).toEqual({
      stage: "prepare",
      corrected: true,
    });
  });

  it("advances from discover to content when only discovery is approved (new forward case)", () => {
    expect(resolveInitialStage("discover", true, false, false, false)).toEqual({
      stage: "content",
      corrected: true,
    });
  });

  it("advances from discover to prepare when discovery, content, and design are approved but preparation is not (new forward case)", () => {
    expect(resolveInitialStage("discover", true, true, true, false)).toEqual({
      stage: "prepare",
      corrected: true,
    });
    // Same result whether the URL explicitly asked for "discover" or omitted
    // the stage param entirely (both default to the same starting point).
    expect(resolveInitialStage(null, true, true, true, false)).toEqual({
      stage: "prepare",
      corrected: true,
    });
  });

  it("advances from discover all the way to generate when every prior stage is approved (new forward case)", () => {
    expect(resolveInitialStage("discover", true, true, true, true)).toEqual({
      stage: "generate",
      corrected: true,
    });
  });

  it("never fires the forward branch when a later stage was explicitly requested and is already reachable", () => {
    // requested === "content" with discoveryApproved true is neither behind
    // nor ahead -- no correction needed either direction.
    expect(resolveInitialStage("content", true, false, false, false)).toEqual({
      stage: null,
      corrected: false,
    });
  });
});

// F04/ISSUE-01/ISSUE-02 regression: refetchCurrentSession used to fetch
// Code Generator state unconditionally on every refresh, even for a session
// where it had never been started. The backend correctly rejects that with
// 409 ENTITLEMENT_BINDING_CONFLICT, which made the *whole* refetch report
// connection state "stale" -- visible to the user as "The latest check did
// not complete" immediately after approving Content Architect, long before
// Build Preparation (let alone Code Generator) was ever reachable.
describe("shouldFetchGenerationState", () => {
  it("does not fetch for a session with no prior generation activity and preparation not yet approved", () => {
    expect(shouldFetchGenerationState(false, null, "session-a")).toBe(false);
  });

  it("fetches once preparation is approved, regardless of prior generation state", () => {
    expect(shouldFetchGenerationState(true, null, "session-a")).toBe(true);
  });

  it("keeps fetching a session's already-started generation even if preparation looks momentarily unapproved", () => {
    expect(
      shouldFetchGenerationState(false, { sessionId: "session-a", status: "verifying" }, "session-a"),
    ).toBe(true);
  });

  it("does not fetch when the known generation state belongs to a different session", () => {
    expect(
      shouldFetchGenerationState(false, { sessionId: "session-b", status: "ready" }, "session-a"),
    ).toBe(false);
  });

  it("does not fetch when the only known prior state for this session was itself not_started", () => {
    expect(
      shouldFetchGenerationState(false, { sessionId: "session-a", status: "not_started" }, "session-a"),
    ).toBe(false);
  });
});

describe("shouldExposeGenerationAfterPreparation", () => {
  it("unlocks the generator when preparation polling completes", () => {
    expect(shouldExposeGenerationAfterPreparation("locked")).toBe(true);
    expect(shouldExposeGenerationAfterPreparation(null)).toBe(true);
  });

  it("does not erase an existing generation run or preview", () => {
    expect(shouldExposeGenerationAfterPreparation("working")).toBe(false);
    expect(shouldExposeGenerationAfterPreparation("complete")).toBe(false);
    expect(shouldExposeGenerationAfterPreparation("attention")).toBe(false);
  });
});
