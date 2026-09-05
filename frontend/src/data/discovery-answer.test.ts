import { describe, expect, it } from "vitest";
import { answeredDiscoveryQuestion, skippedDiscoveryQuestion } from "./discovery-answer";

describe("Discovery answer transport contract", () => {
  it.each([
    ["free text", "A detailed answer"],
    ["single choice", "staff-engineering"],
    ["boolean choice", "true"],
    ["multiple choices", ["architecture", "leadership"]],
  ])("maps %s values to the API's answered action", (_label, value) => {
    expect(answeredDiscoveryQuestion("question-1", value)).toEqual({
      questionId: "question-1",
      mode: "answered",
      value,
    });
  });

  it("maps skip to the API's skipped action", () => {
    expect(skippedDiscoveryQuestion("question-2")).toEqual({
      questionId: "question-2",
      mode: "skipped",
      value: null,
    });
  });
});
