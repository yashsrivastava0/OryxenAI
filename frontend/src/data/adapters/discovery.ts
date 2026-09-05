// Discovery stage adapter — the Phase 1 spike proving the adapter pattern
// end to end (docs/Frontend/05 §19 Phase 1 "adapter fixtures for current
// stage payloads"; status map in §6.2). Content, Design, Build Preparation,
// and Code Generator adapters follow the same shape in their owning phases.
//
// Backend contract (verified against source, not just docs):
// src/oryxenai/agents/discovery/schemas.py::DiscoveryState,
// src/oryxenai/api/routes/discovery.py::DiscoveryStateResponse — the API
// response is { session_id, session_revision, discovery: <dict>, jobs: [] }.

import { selectStageJob, type StageJobViewModel } from "./job";
import type { StageState, StageViewModel } from "./types";

export type DiscoveryQuestionKind = "text" | "single_select" | "multi_select" | "boolean";

export interface DiscoveryQuestionOption {
  id: string;
  label: string;
}

export interface DiscoveryQuestionVM {
  id: string;
  text: string;
  helpText: string | null;
  kind: DiscoveryQuestionKind;
  options: DiscoveryQuestionOption[];
  allowSkip: boolean;
}

export type DiscoveryRetryOperation = "questions" | "brief";

export interface DiscoveryViewModel extends StageViewModel {
  currentQuestions: DiscoveryQuestionVM[];
  answeredQuestionIds: string[];
  answeredTurns: Array<{ questionId: string; questionText: string; answerText: string }>;
  brief: { title: string; userSummary: string; approved: boolean } | null;
  safeError: { summary: string; retryOperation: DiscoveryRetryOperation } | null;
}

const STATUS_TEXT: Record<string, string> = {
  not_started: "Begin with your story",
  questions_queued: "Preparing the right questions",
  questions_running: "Understanding your material",
  questions_ready: "Ready for your next answer",
  answers_in_progress: "Continue your answers",
  brief_running: "Shaping your portfolio brief",
  brief_review: "Your brief is ready to review",
  approved: "Brief approved",
  needs_attention: "Discovery needs your attention",
};

const STATE_MAP: Record<string, StageState> = {
  not_started: "available",
  questions_queued: "working",
  questions_running: "working",
  questions_ready: "input",
  answers_in_progress: "input",
  brief_running: "working",
  brief_review: "review",
  approved: "complete",
  needs_attention: "attention",
};

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null;
}

function adaptQuestion(raw: unknown): DiscoveryQuestionVM | null {
  if (!isRecord(raw) || typeof raw.id !== "string" || typeof raw.text !== "string") return null;
  const kind: DiscoveryQuestionKind =
    raw.kind === "single_select" || raw.kind === "multi_select" || raw.kind === "boolean" ? raw.kind : "text";
  const options: DiscoveryQuestionOption[] = Array.isArray(raw.options)
    ? raw.options
        .filter((option): option is Record<string, unknown> => isRecord(option))
        .map((option) => ({
          id: typeof option.id === "string" ? option.id : "",
          label: typeof option.label === "string" ? option.label : "",
        }))
        .filter((option) => option.id && option.label)
    : [];
  return {
    id: raw.id,
    text: raw.text,
    helpText: typeof raw.help_text === "string" ? raw.help_text : null,
    kind,
    options,
    allowSkip: raw.allow_skip !== false,
  };
}

function formatAnswer(answer: unknown, question: DiscoveryQuestionVM): string {
  if (!isRecord(answer)) return "Answer saved";
  if (answer.mode === "skip") return "Skipped";
  const value = answer.value;
  const labels = new Map(question.options.map((option) => [option.id, option.label]));
  if (Array.isArray(value)) {
    return value.map((item) => labels.get(String(item)) ?? String(item)).join(", ");
  }
  if (typeof value === "boolean") return value ? "Yes" : "No";
  if (typeof value === "string") {
    if (question.kind === "boolean") {
      if (value === "true") return "Yes";
      if (value === "false") return "No";
    }
    return labels.get(value) ?? value;
  }
  return value == null ? "Answer saved" : JSON.stringify(value);
}

/**
 * Accepts the raw `discovery` dict from DiscoveryStateResponse. Returns
 * state "unsupported" (never silently "complete"/"available") for a status
 * this adapter does not recognize, per the adapter fail-closed rule.
 */
export function adaptDiscovery(raw: unknown, jobs: unknown[] = []): DiscoveryViewModel {
  if (!isRecord(raw) || typeof raw.status !== "string" || !(raw.status in STATE_MAP)) {
    return {
      state: "unsupported",
      statusText: "This stage returned a newer state. Refresh to continue.",
      raw,
      job: selectStageJob(jobs),
      currentQuestions: [],
      answeredQuestionIds: [],
      answeredTurns: [],
      brief: null,
      safeError: null,
    };
  }

  const status = raw.status;
  const mappedState = STATE_MAP[status] ?? "unsupported";
  const operationA = isRecord(raw.operation_a) ? raw.operation_a : {};
  const briefState = isRecord(raw.brief) ? raw.brief : {};
  const activeJobId =
    typeof operationA.job_id === "string"
      ? operationA.job_id
      : typeof briefState.job_id === "string"
        ? briefState.job_id
        : null;
  const job: StageJobViewModel | null = selectStageJob(jobs, activeJobId);
  const items = Array.isArray(operationA.items) ? operationA.items : [];
  const answers = isRecord(raw.answers) && isRecord(raw.answers.items) ? raw.answers.items : {};
  const answeredIds = Object.keys(answers);

  // questions_ready with no remaining answerable question is stale client
  // data, not an empty composer (docs/Frontend/05 §6.2).
  const allQuestions = items.map(adaptQuestion).filter((q): q is DiscoveryQuestionVM => q !== null);
  const answeredTurns = allQuestions
    .filter((question) => question.id in answers)
    .map((question) => ({
      questionId: question.id,
      questionText: question.text,
      answerText: formatAnswer(answers[question.id], question),
    }));
  const currentQuestions =
    status === "questions_ready" || status === "answers_in_progress"
      ? allQuestions.filter((q) => !answeredIds.includes(q.id))
      : [];
  const effectiveState: StageState =
    (status === "questions_ready" || status === "answers_in_progress") && currentQuestions.length === 0
      ? (allQuestions.length > 0 ? "working" : "available")
      : mappedState;

  const failedJob = job?.status === "failed" || job?.status === "cancelled";
  const renderedState: StageState = failedJob ? "attention" : effectiveState;
  const brief =
    status === "brief_review" || status === "approved"
      ? {
          title: typeof briefState.title === "string" ? briefState.title : "",
          userSummary: typeof briefState.user_summary === "string" ? briefState.user_summary : "",
          approved: briefState.approved != null,
        }
      : null;

  const latestError = isRecord(raw.latest_error) ? raw.latest_error : null;
  const operation = typeof latestError?.operation === "string" ? latestError.operation : "";
  const retryOperation: DiscoveryRetryOperation =
    operation === "understand_and_question" ||
    operation === "prepare_questions" ||
    job?.kind.includes("understand") === true ||
    job?.kind.includes("prepare_questions") === true ||
    status === "questions_queued" ||
    status === "questions_running"
      ? "questions"
      : "brief";
  const safeError =
    (status === "needs_attention" && latestError) || failedJob
      ? {
          summary:
            typeof latestError?.message === "string"
              ? latestError.message
              : typeof latestError?.summary === "string"
                ? latestError.summary
                : job?.error?.message ?? "Discovery could not continue.",
          retryOperation,
        }
      : null;

  return {
    state: renderedState,
    statusText: STATUS_TEXT[status] ?? "Working on Discovery",
    raw,
    job,
    currentQuestions,
    answeredQuestionIds: answeredIds,
    answeredTurns,
    brief,
    safeError,
  };
}
