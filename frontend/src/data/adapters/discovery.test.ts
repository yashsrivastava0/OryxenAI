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

  it("shows at most three choices from an older oversized question", () => {
    const raw = structuredClone(fixtures.questionsReady);
    raw.operation_a.items[0]!.options.push({ id: "extra", label: "Extra choice" });
    const vm = adaptDiscovery(raw);
    expect(vm.currentQuestions[0]?.options).toHaveLength(3);
  });

  it("preserves the fixed palette question's visual options", () => {
    const palette = {
      id: "palette",
      text: "Which colors feel right?",
      help_text: "Choose one",
      kind: "palette_select",
      options: [
        { id: "forest_copper", label: "Forest & copper", description: "Warm, editorial", swatches: ["#14231c", "#f3f1e9", "#9a3f29"] },
        { id: "cobalt_white", label: "Cobalt & white", description: "Bright, structured", swatches: ["#2849c9", "#f7f9fc", "#17253c"] },
        { id: "obsidian_lime", label: "Obsidian & lime", description: "Bold, energetic", swatches: ["#0c0e0d", "#d9fc73", "#f0f2eb"] },
        { id: "cobalt_atlas_interactive", label: "Cobalt & volt", description: "Interactive editorial", swatches: ["#f8f8f5", "#3656d6", "#d7fa76"] },
      ],
      allow_skip: false,
    };
    const raw = { status: "questions_ready", operation_a: { items: [palette] }, answers: { items: {} } };
    const question = adaptDiscovery(raw).currentQuestions[0];
    expect(question?.kind).toBe("palette_select");
    expect(question?.options).toHaveLength(4);
    expect(question?.allowSkip).toBe(false);
    expect(question?.options.map((option) => option.swatches)).toEqual(palette.options.map((option) => option.swatches));
  });

  it("keeps the optional Atlas project question kind", () => {
    const raw = { status: "questions_ready", operation_a: { items: [{ id: "work", text: "Feature a project?", kind: "work_detail", options: [], allow_skip: true }] }, answers: { items: {} } };
    const question = adaptDiscovery(raw).currentQuestions[0];
    expect(question?.kind).toBe("work_detail");
    expect(question?.allowSkip).toBe(true);
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

  it("exposes the brief markdown and structured profile facts (previously discarded)", () => {
    const vm = adaptDiscovery(fixtures.briefReview);
    expect(vm.brief?.markdown).toContain("systems-minded engineer");
    expect(vm.brief?.profile.skills).toContain("Python");
    expect(vm.brief?.profile.experience[0]?.organization).toBe("Northwind Systems");
    expect(vm.brief?.profile.projects[0]?.name).toBe("Durable Jobs Rewrite");
    expect(vm.brief?.profile.links[0]?.url).toBe("https://github.com/example");
  });

  it("returns an empty profile shape rather than throwing when profile is missing", () => {
    const vm = adaptDiscovery(fixtures.approved.status === "approved" ? { status: "brief_review", brief: { title: "t" } } : {});
    expect(vm.brief?.profile.skills).toEqual([]);
    expect(vm.brief?.profile.experience).toEqual([]);
  });

  it("maps approved to complete with an approved brief", () => {
    const vm = adaptDiscovery(fixtures.approved);
    expect(vm.state).toBe("complete");
    expect(vm.brief?.approved).toBe(true);
  });

  it("maps needs_attention to attention with a safe error summary", () => {
    const vm = adaptDiscovery(fixtures.needsAttention);
    expect(vm.state).toBe("attention");
    expect(vm.safeError?.summary).toBe("Explorer could not continue.");
  });

  it("tracks the brief job after questions, even when the older question job failed", () => {
    const vm = adaptDiscovery(
      {
        status: "brief_running",
        operation_a: { job_id: "question-job", items: [] },
        brief: { job_id: "brief-job" },
      },
      [
        { id: "question-job", kind: "discovery.understand_and_question", status: "failed" },
        { id: "brief-job", kind: "discovery.build_or_revise_brief", status: "running" },
      ],
    );
    expect(vm.state).toBe("working");
    expect(vm.job?.id).toBe("brief-job");
  });

  it("uses the backend error message and selects the Operation A retry path", () => {
    const vm = adaptDiscovery({
      status: "needs_attention",
      latest_error: {
        message: "Question drafting timed out.",
        operation: "understand_and_question",
      },
    });
    expect(vm.safeError).toEqual({
      summary: "Question drafting timed out.",
      operationLabel: "understand_and_question",
      retryOperation: "questions",
    });
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
