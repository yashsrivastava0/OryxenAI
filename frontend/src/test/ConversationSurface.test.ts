import { describe, expect, it } from "vitest";
import { h } from "preact";
import { render } from "preact-render-to-string";
import { ConversationSurface } from "../components/ConversationSurface";
import { adaptDiscovery } from "../data/adapters/discovery";
import { questionsMcqReady, questionsReady, questionsTextReady } from "../data/adapters/discovery.fixtures";

const noop = async () => {};

describe("ConversationSurface discovery question rendering", () => {
  it("shows catalog-driven visual looks as one selectable decision", () => {
    const html = render(
      h(ConversationSurface, {
        questions: [{
          id: "visual_palette",
          text: "Which look feels right for your portfolio?",
          helpText: "Each direction pairs its colors with a distinct design style.",
          reason: null,
          gapId: "visual_palette_v1",
          affectedIds: [],
          kind: "palette_select",
          allowSkip: false,
          options: [
            { id: "forest_copper", label: "Forest & copper", description: "Editorial warmth", swatches: ["#14231c", "#f3f1e9", "#9a3f29"] },
            { id: "cobalt_white", label: "Cobalt & white", description: "Minimal clarity", swatches: ["#2849c9", "#f7f9fc", "#17253c"] },
            { id: "obsidian_lime", label: "Obsidian & lime", description: "Bold modernity", swatches: ["#0c0e0d", "#d9fc73", "#f0f2eb"] },
            { id: "cobalt_atlas_interactive", label: "Cobalt & volt", description: "Interactive editorial", swatches: ["#f8f8f5", "#3656d6", "#d7fa76"] },
            { id: "claret_amber", label: "Claret & amber", description: "Cinematic depth", swatches: ["#3b0f1e", "#f6eee3", "#ffb04a"], theme: { collection: "interactive", badge: "Cinematic motion", style: "cinematic", colors: ["#3b0f1e", "#f6eee3", "#ffb04a"] } },
          ],
        }],
        history: [],
        isWorking: false,
        onSubmitAnswer: noop,
      }),
    );

    expect(html.match(/class="palette-choice /g)).toHaveLength(5);
    expect(html).toContain('data-look="claret_amber"');
    expect(html).toContain("Cinematic motion");
    expect(html).toContain("palette-choice__demo");
    expect(html).toContain("Editorial warmth");
    expect(html).toContain("Minimal clarity");
    expect(html).toContain("Bold modernity");
    expect(html).toContain("Optional note for your reference");
    expect(html).not.toContain("cobalt-atlas/v1");
  });

  it("renders three choices and a free-text field for a multi-select question", () => {
    const vm = adaptDiscovery(questionsMcqReady);
    const html = render(
      h(ConversationSurface, {
        questions: vm.currentQuestions,
        history: [],
        isWorking: false,
        onSubmitAnswer: noop,
      }),
    );

    expect(html).toContain('aria-label="Explorer interview"');
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
    expect(html).toContain("Add context or write your own answer");
    expect(html).not.toContain("What primary audience should this portfolio address?");
    expect(html).toContain('aria-label="Explorer question"');
    expect(html).toContain("Question 01 of 02");
  });

  it("shows one question at a time from a three-question batch", () => {
    const two = adaptDiscovery(questionsMcqReady).currentQuestions;
    const third = adaptDiscovery(questionsReady).currentQuestions[0]!;
    const html = render(
      h(ConversationSurface, {
        questions: [...two, third],
        history: [],
        isWorking: false,
        onSubmitAnswer: noop,
      }),
    );

    expect(html).toContain("Which project stories should lead your portfolio?");
    expect(html).not.toContain("What primary audience should this portfolio address?");
    expect(html).not.toContain("What kind of work do you want this portfolio to lead with?");
    expect(html).toContain("Question 01 of 03");
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
    expect(html).toContain("Add context or write your own answer");
    expect(html).toContain("Continue to brief");
  });

  it("renders a text question with an answer field and action", () => {
    const vm = adaptDiscovery(questionsTextReady);
    const html = render(
      h(ConversationSurface, {
        questions: vm.currentQuestions,
        history: [],
        isWorking: false,
        onSubmitAnswer: noop,
      }),
    );

    expect(html).toContain("Your answer");
    expect(html).toContain("What should someone understand after reading your portfolio?");
    expect(html).toContain("A sentence or two is enough. Focus on the change you helped create.");
    expect(html).toContain("composer-textarea");
    expect(html).toContain("Write what feels important");
    expect(html).toContain("Continue to brief");
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
