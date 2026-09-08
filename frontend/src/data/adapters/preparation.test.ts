import { describe, expect, it } from "vitest";
import { adaptBuildPreparation } from "./preparation";
import {
  preparationNeedsAttention,
  preparationNotStarted,
  preparationReady,
  preparationRunning,
  preparationStale,
} from "./preparation.fixtures";

describe("adaptBuildPreparation", () => {
  it("keeps the stage locked until both upstream approvals exist", () => {
    expect(adaptBuildPreparation(preparationNotStarted, false, true).state).toBe("locked");
    expect(adaptBuildPreparation(preparationNotStarted, true, true).state).toBe("available");
  });

  it("maps running and ready states into honest product states", () => {
    expect(adaptBuildPreparation(preparationRunning, true, true).state).toBe("working");
    const view = adaptBuildPreparation(preparationReady, true, true);
    expect(view.state).toBe("complete");
    expect(view.routes[0]?.path).toBe("/");
    expect(view.resourceNeedsCount).toBe(1);
    expect(view.agentOutput).toEqual({ stage: "compose_visual_brief", nested: { retained: true } });
  });

  it("requires regeneration for stale output and surfaces retryable errors", () => {
    expect(adaptBuildPreparation(preparationStale, true, true).state).toBe("attention");
    const attention = adaptBuildPreparation(preparationNeedsAttention, true, true);
    expect(attention.state).toBe("attention");
    expect(attention.safeError?.retryable).toBe(true);
  });

  it("fails closed on unknown status", () => {
    expect(adaptBuildPreparation({ status: "future" }, true, true).state).toBe("unsupported");
  });
});
