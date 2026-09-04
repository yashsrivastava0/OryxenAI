import { describe, expect, it } from "vitest";
import { adaptDiscovery } from "./discovery";
import * as fixtures from "./discovery.fixtures";

describe("adaptDiscovery", () => {
  it("maps not_started to available", () => {
    expect(adaptDiscovery(fixtures.notStarted).state).toBe("available");
  });

  it("maps questions_ready with an unanswered question to input", () => {
    const vm = adaptDiscovery(fixtures.questionsReady);
    expect(vm.state).toBe("input");
    expect(vm.currentQuestions).toHaveLength(1);
    expect(vm.currentQuestions[0]?.id).toBe("q1");
    expect(vm.currentQuestions[0]?.options).toHaveLength(3);
  });

  it("treats questions_ready with no remaining unanswered question as working, not an empty composer", () => {
    const vm = adaptDiscovery(fixtures.questionsReadyStale);
    expect(vm.state).toBe("working");
    expect(vm.currentQuestions).toHaveLength(0);
    expect(vm.answeredTurns).toEqual([
      { questionId: "q1", questionText: "Answered already", answerText: "engineering" },
    ]);
  });

  it("maps brief_review to review and exposes the curated summary", () => {
    const vm = adaptDiscovery(fixtures.briefReview);
    expect(vm.state).toBe("review");
    expect(vm.brief?.userSummary).toContain("durable-jobs rewrite");
    expect(vm.brief?.approved).toBe(false);
  });

  it("maps approved to complete with an approved brief", () => {
    const vm = adaptDiscovery(fixtures.approved);
    expect(vm.state).toBe("complete");
    expect(vm.brief?.approved).toBe(true);
  });

  it("maps needs_attention to attention with a safe error summary", () => {
    const vm = adaptDiscovery(fixtures.needsAttention);
    expect(vm.state).toBe("attention");
    expect(vm.safeError?.summary).toBe("Discovery could not continue.");
  });

  it("fails closed on an unrecognized status instead of guessing success", () => {
    const vm = adaptDiscovery(fixtures.unknownFutureStatus);
    expect(vm.state).toBe("unsupported");
  });

  it("fails closed on a completely malformed payload", () => {
    expect(adaptDiscovery(null).state).toBe("unsupported");
    expect(adaptDiscovery(undefined).state).toBe("unsupported");
    expect(adaptDiscovery("not an object").state).toBe("unsupported");
  });

  it("never throws on an internally malformed but status-valid payload", () => {
    expect(() => adaptDiscovery(fixtures.malformed)).not.toThrow();
    expect(adaptDiscovery(fixtures.malformed).currentQuestions).toEqual([]);
  });
});
