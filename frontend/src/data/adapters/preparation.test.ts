import { describe, it, expect } from "vitest";
import { adaptBuildPreparation } from "./preparation";
import {
  preparationFixtureNotStarted,
  preparationFixtureRunningStage0,
  preparationFixtureRunningStage2,
  preparationFixtureRunningStage4,
  preparationFixtureRunningMaterialize,
  preparationFixtureRunningUnknown,
  preparationFixtureReadyEligible,
  preparationFixtureReadyStale,
  preparationFixtureNeedsAttention,
  preparationFixtureUnsupported,
} from "./preparation.fixtures";

describe("adaptBuildPreparation", () => {
  it("locks not_started when upstream Content/Design are not approved", () => {
    const view = adaptBuildPreparation(preparationFixtureNotStarted, false);
    expect(view.state).toBe("locked");
    expect(view.statusText).toContain("Requires approved Content Plan");
  });

  it("unlocks to available when upstream Content/Design are approved", () => {
    const view = adaptBuildPreparation(preparationFixtureNotStarted, true);
    expect(view.state).toBe("available");
    expect(view.statusText).toContain("Ready to prepare");
  });

  it("maps running at stage_0 to milestone 1 active", () => {
    const view = adaptBuildPreparation(preparationFixtureRunningStage0, true);
    expect(view.state).toBe("working");
    expect(view.currentMilestone).toBe("Checking the approved plan");
    expect(view.milestones[0]?.state).toBe("current");
    expect(view.milestones[1]?.state).toBe("quiet");
    expect(view.routeCount).toBe(1);
    expect(view.elapsedSeconds).toBe(4.2);
  });

  it("maps running at stage_2 to milestone 2 active and milestone 1 complete", () => {
    const view = adaptBuildPreparation(preparationFixtureRunningStage2, true);
    expect(view.state).toBe("working");
    expect(view.currentMilestone).toBe("Resolving portfolio materials");
    expect(view.milestones[0]?.state).toBe("complete");
    expect(view.milestones[1]?.state).toBe("current");
    expect(view.milestones[2]?.state).toBe("quiet");
  });

  it("maps running at stage_4 to milestone 3 active and milestones 1-2 complete", () => {
    const view = adaptBuildPreparation(preparationFixtureRunningStage4, true);
    expect(view.state).toBe("working");
    expect(view.currentMilestone).toBe("Compiling the build context");
    expect(view.milestones[0]?.state).toBe("complete");
    expect(view.milestones[1]?.state).toBe("complete");
    expect(view.milestones[2]?.state).toBe("current");
    expect(view.milestones[3]?.state).toBe("quiet");
  });

  it("maps running at materialize to milestone 4 active and milestones 1-3 complete", () => {
    const view = adaptBuildPreparation(preparationFixtureRunningMaterialize, true);
    expect(view.state).toBe("working");
    expect(view.currentMilestone).toBe("Packaging and verifying the handoff");
    expect(view.milestones[0]?.state).toBe("complete");
    expect(view.milestones[1]?.state).toBe("complete");
    expect(view.milestones[2]?.state).toBe("complete");
    expect(view.milestones[3]?.state).toBe("current");
    expect(view.warnings).toContain("Omitted external font fetch; fallback used.");
  });

  it("maps running unknown substage to honest safe fallback", () => {
    const view = adaptBuildPreparation(preparationFixtureRunningUnknown, true);
    expect(view.state).toBe("working");
    expect(view.currentMilestone).toBe("Preparing the build package");
  });

  it("maps ready and eligible to complete with all milestones complete", () => {
    const view = adaptBuildPreparation(preparationFixtureReadyEligible, true);
    expect(view.state).toBe("complete");
    expect(view.handoffEligible).toBe(true);
    expect(view.stale).toBe(false);
    expect(view.milestones.every((m) => m.state === "complete")).toBe(true);
    expect(view.statusText).toContain("verified and ready");
  });

  it("maps ready but stale to attention with explanation", () => {
    const view = adaptBuildPreparation(preparationFixtureReadyStale, true);
    expect(view.state).toBe("attention");
    expect(view.stale).toBe(true);
    expect(view.handoffEligible).toBe(false);
    expect(view.statusText).toContain("Upstream inputs changed");
  });

  it("maps needs_attention to attention and extracts error and technical details", () => {
    const view = adaptBuildPreparation(preparationFixtureNeedsAttention, true);
    expect(view.state).toBe("attention");
    expect(view.safeError?.summary).toBe("Failed to assemble route context from approved specifications.");
    expect(view.safeError?.technicalDetails).toContain("BUILD_PREPARATION_FAILED");
  });

  it("fails closed into unsupported for unrecognized status", () => {
    const view = adaptBuildPreparation(preparationFixtureUnsupported, true);
    expect(view.state).toBe("unsupported");
    expect(view.statusText).toContain("unrecognized status");
  });
});
