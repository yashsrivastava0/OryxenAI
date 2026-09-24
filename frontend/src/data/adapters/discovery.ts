// Discovery stage adapter. The response contract is defined by the active
// Discovery API and state schema.
//
// Backend contract (verified against source, not just docs):
// src/oryxenai/agents/discovery/schemas.py::DiscoveryState,
// src/oryxenai/api/routes/discovery.py::DiscoveryStateResponse — the API
// response is { session_id, session_revision, discovery: <dict>, jobs: [] }.

import { selectStageJob, type StageJobViewModel } from "./job";
import {
  readAgentOutput,
  readSafeStageError,
  type SafeStageError,
  type StageState,
  type StageViewModel,
} from "./types";

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

export interface ProfileLinkVM {
  label: string;
  url: string;
}

export interface ExperienceEntryVM {
  organization: string;
  role: string;
  dates: string;
  highlights: string[];
}

export interface EducationEntryVM {
  institution: string;
  credential: string;
  dates: string;
}

export interface ProjectEntryVM {
  name: string;
  summary: string;
  contribution: string;
  tech: string[];
  link: string;
}

export interface StructuredProfileVM {
  name: string;
  currentTitle: string;
  location: string;
  links: ProfileLinkVM[];
  experience: ExperienceEntryVM[];
  education: EducationEntryVM[];
  projects: ProjectEntryVM[];
  skills: string[];
  spokenLanguages: string[];
}

export interface DiscoveryViewModel extends StageViewModel {
  currentQuestions: DiscoveryQuestionVM[];
  answeredQuestionIds: string[];
  answeredTurns: Array<{ questionId: string; questionText: string; answerText: string }>;
  brief: { title: string; markdown: string; userSummary: string; approved: boolean; profile: StructuredProfileVM } | null;
  safeError: (SafeStageError & { retryOperation: DiscoveryRetryOperation }) | null;
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

function stringArray(value: unknown): string[] {
  return Array.isArray(value) ? value.filter((item): item is string => typeof item === "string") : [];
}

const EMPTY_PROFILE: StructuredProfileVM = {
  name: "",
  currentTitle: "",
  location: "",
  links: [],
  experience: [],
  education: [],
  projects: [],
  skills: [],
  spokenLanguages: [],
};

/**
 * Reads the StructuredProfile facts the Discovery model already extracted
 * (agents/discovery/schemas.py::StructuredProfile) — skills, experience,
 * education, projects, links. These are computed by the backend on every
 * brief but were previously discarded on the client; the extracted-profile
 * rail is what actually renders this now (see ExtractedProfileRail.tsx).
 */
function adaptStructuredProfile(raw: unknown): StructuredProfileVM {
  if (!isRecord(raw)) return EMPTY_PROFILE;
  const links: ProfileLinkVM[] = Array.isArray(raw.links)
    ? raw.links
        .filter((item): item is Record<string, unknown> => isRecord(item))
        .map((item) => ({
          label: typeof item.label === "string" ? item.label : "",
          url: typeof item.url === "string" ? item.url : "",
        }))
        .filter((item) => item.label || item.url)
    : [];
  const experience: ExperienceEntryVM[] = Array.isArray(raw.experience)
    ? raw.experience
        .filter((item): item is Record<string, unknown> => isRecord(item))
        .map((item) => ({
          organization: typeof item.organization === "string" ? item.organization : "",
          role: typeof item.role === "string" ? item.role : "",
          dates: typeof item.dates === "string" ? item.dates : "",
          highlights: stringArray(item.highlights),
        }))
    : [];
  const education: EducationEntryVM[] = Array.isArray(raw.education)
    ? raw.education
        .filter((item): item is Record<string, unknown> => isRecord(item))
        .map((item) => ({
          institution: typeof item.institution === "string" ? item.institution : "",
          credential: typeof item.credential === "string" ? item.credential : "",
          dates: typeof item.dates === "string" ? item.dates : "",
        }))
    : [];
  const projects: ProjectEntryVM[] = Array.isArray(raw.projects)
    ? raw.projects
        .filter((item): item is Record<string, unknown> => isRecord(item))
        .map((item) => ({
          name: typeof item.name === "string" ? item.name : "",
          summary: typeof item.summary === "string" ? item.summary : "",
          contribution: typeof item.contribution === "string" ? item.contribution : "",
          tech: stringArray(item.tech),
          link: typeof item.link === "string" ? item.link : "",
        }))
    : [];
  return {
    name: typeof raw.name === "string" ? raw.name : "",
    currentTitle: typeof raw.current_title === "string" ? raw.current_title : "",
    location: typeof raw.location === "string" ? raw.location : "",
    links,
    experience,
    education,
    projects,
    skills: stringArray(raw.skills),
    spokenLanguages: stringArray(raw.spoken_languages),
  };
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
  if (answer.mode === "skipped") return "Skipped";
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
      agentOutput: null,
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
          markdown: typeof briefState.markdown === "string" ? briefState.markdown : "",
          userSummary: typeof briefState.user_summary === "string" ? briefState.user_summary : "",
          approved: briefState.approved != null,
          profile: adaptStructuredProfile(briefState.profile),
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
          ...readSafeStageError(
            latestError,
            typeof latestError?.message === "string"
              ? latestError.message
              : typeof latestError?.summary === "string"
                ? latestError.summary
                : job?.error?.message ?? "Discovery could not continue.",
          ),
          retryOperation,
        }
      : null;

  return {
    state: renderedState,
    statusText: STATUS_TEXT[status] ?? "Working on Discovery",
    raw,
    job,
    agentOutput: readAgentOutput(raw),
    currentQuestions,
    answeredQuestionIds: answeredIds,
    answeredTurns,
    brief,
    safeError,
  };
}
