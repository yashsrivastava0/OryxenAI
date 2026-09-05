export type DiscoveryAnswerMode = "answered" | "skipped";

export interface DiscoveryAnswerSubmission {
  questionId: string;
  mode: DiscoveryAnswerMode;
  value: unknown;
}

export function answeredDiscoveryQuestion(
  questionId: string,
  value: unknown,
): DiscoveryAnswerSubmission {
  return { questionId, mode: "answered", value };
}

export function skippedDiscoveryQuestion(questionId: string): DiscoveryAnswerSubmission {
  return { questionId, mode: "skipped", value: null };
}
