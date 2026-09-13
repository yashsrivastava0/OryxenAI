import { describe, expect, it } from "vitest";
import { h } from "preact";
import { render } from "preact-render-to-string";
import { ConversationSurface } from "../components/ConversationSurface";
import { adaptDiscovery } from "../data/adapters/discovery";
import { questionsMcqReady, questionsReady, questionsTextReady } from "../data/adapters/discovery.fixtures";

const noop = async () => {};

describe("ConversationSurface discovery question rendering", () => {
  it("renders multi-select question with SELECT ALL THAT APPLY group hint and stacked tiles", () => {
    const vm = adaptDiscovery(questionsMcqReady);
    const html = render(
      h(ConversationSurface, {
        questions: vm.currentQuestions,
        history: [],
        isWorking: false,
        onSubmitAnswer: noop,
      }),
    );

    expect(html).toContain('aria-label="Discovery interview"');
    expect(html).toContain("SELECT ALL THAT APPLY");
    expect(html).toContain("Which project stories should lead your portfolio?");
    expect(html).toContain("A focused selection helps your strongest contribution come through.");
    expect(html).toContain("AlphaMesh-Core");
    expect(html).toContain("Chronos-Tick-Fabric");
    expect(html).toContain("NanoSecure-Risk");
    expect(html).toContain("choice-tile");
    expect(html).toContain("choice-indicator--checkbox");
    expect(html).toContain("Next question");
    expect(html).toContain("Skip question");
  });

  it("renders single-select question with SELECT ONE group hint and radio options", () => {
    const vm = adaptDiscovery(questionsReady);
    const html = render(
      h(ConversationSurface, {
        questions: vm.currentQuestions,
        history: [],
        isWorking: false,
        onSubmitAnswer: noop,
      }),
    );

    expect(html).toContain("SELECT ONE");
    expect(html).toContain("What kind of work do you want this portfolio to lead with?");
    expect(html).toContain("choice-indicator--radio");
    expect(html).toContain("Design");
    expect(html).toContain("Engineering");
    expect(html).toContain("Writing");
    // questionsReady has 1 question, so the CTA is "Submit answer"
    expect(html).toContain("Submit answer");
  });

  it("renders text question with YOUR ANSWER label, textarea, and action", () => {
    const vm = adaptDiscovery(questionsTextReady);
    const html = render(
      h(ConversationSurface, {
        questions: vm.currentQuestions,
        history: [],
        isWorking: false,
        onSubmitAnswer: noop,
      }),
    );

    expect(html).toContain("YOUR ANSWER");
    expect(html).toContain("What should someone understand after reading your portfolio?");
    expect(html).toContain("A sentence or two is enough. Focus on the change you helped create.");
    expect(html).toContain("composer-textarea");
    expect(html).toContain("Describe the outcome, your contribution, or the decision behind the work");
    // Since questionsTextReady has only 1 question in currentQuestions, CTA is "Submit answer"
    expect(html).toContain("Submit answer");
  });

  it("renders compact earlier answers disclosure when history is present", () => {
    const vm = adaptDiscovery(questionsMcqReady);
    const html = render(
      h(ConversationSurface, {
        questions: vm.currentQuestions,
        history: [
          {
            questionId: "q_prior",
            questionText: "What was your most recent principal engineering impact?",
            answerText: "Designed and rolled out a zero-downtime ledger engine handling $4B daily volume.",
          },
        ],
        isWorking: false,
        onSubmitAnswer: noop,
      }),
    );

    expect(html).toContain("Earlier answers");
    expect(html).toContain("prior-answers-accordion");
    expect(html).toContain("Designed and rolled out a zero-downtime ledger engine handling $4B daily volume.");
  });
});
