// Explorer stage adapter. The response contract is defined by the active
// Explorer API and state schema.
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

export type DiscoveryQuestionKind = "text" | "single_select" | "multi_select" | "boolean" | "palette_select" | "work_detail";

export interface DiscoveryQuestionOption {
  id: string;
  label: string;
  description: string;
  swatches: string[];
}

export interface DiscoveryQuestionVM {
  id: string;
  text: string;
  helpText: string | null;
  reason: string | null;
  gapId: string | null;
  affectedIds: string[];
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

export interface DiscoverySourceSpanVM {
  id: string;
  start: number;
  end: number;
  excerpt: string;
  disposition: string | null;
  reason: string;
  factIds: string[];
}

export interface DiscoverySourceDocumentVM {
  id: string;
  label: string;
  sourceKind: string;
  format: string;
  offsetUnit: string;
  originalText: string;
  sha256: string;
  spans: DiscoverySourceSpanVM[];
}

export interface DiscoveryFactVM {
  id: string;
  statement: string;
  originalWording: string;
  sourceRefs: string[];
  qualifiers: string[];
  ownership: string;
  status: string;
}

export interface DiscoveryEvidenceItemVM {
  id: string;
  title: string;
  detail: string;
  category: string;
  details: Array<{ label: string; value: string }>;
  sourceRefs: string[];
  factIds: string[];
}

export interface DiscoveryOpenItemVM {
  id: string;
  detail: string;
  importance: string;
  status: string;
  safeWording: string;
  affectedIds: string[];
  sourceRefs: string[];
}

export interface DiscoveryAnswerRevisionVM {
  revision: number;
  status: string;
  answer: string;
  sourceRefs: string[];
}

export interface DiscoveryQuestionHistoryVM {
  questionId: string;
  question: string;
  reason: string;
  gapId: string;
  affectedIds: string[];
  status: string;
  answer: string;
  answerHistory: DiscoveryAnswerRevisionVM[];
}

export interface DiscoveryDossierVM {
  contractVersion: string;
  intent: {
    goal: string;
    audience: string;
    visitorAction: string;
    language: string;
    preferences: string[];
    basis: Record<string, string>;
    basisRefs: Record<string, string[]>;
  };
  subject: {
    name: string;
    currentTitle: string;
    location: string;
    links: ProfileLinkVM[];
    sourceRefs: string[];
  };
  facts: DiscoveryFactVM[];
  roles: DiscoveryEvidenceItemVM[];
  projects: DiscoveryEvidenceItemVM[];
  otherEvidence: DiscoveryEvidenceItemVM[];
  openItems: DiscoveryOpenItemVM[];
  restrictions: Array<{ id: string; scope: string; instruction: string; disposition: string; sourceRefs: string[] }>;
  userChoices: string[];
  sourceCoverage: Array<{ spanId: string; disposition: string; factIds: string[]; reason: string }>;
  questionHistory: DiscoveryQuestionHistoryVM[];
}

export interface DiscoveryViewModel extends StageViewModel {
  needsMoreMaterial: boolean;
  currentQuestions: DiscoveryQuestionVM[];
  answeredQuestionIds: string[];
  answeredTurns: Array<{ questionId: string; questionText: string; answerText: string }>;
  brief: {
    title: string;
    markdown: string;
    userSummary: string;
    approved: boolean;
    profile: StructuredProfileVM;
    dossier: DiscoveryDossierVM | null;
  } | null;
  sourceDocuments: DiscoverySourceDocumentVM[];
  questionHistory: DiscoveryQuestionHistoryVM[];
  safeError: (SafeStageError & { retryOperation: DiscoveryRetryOperation }) | null;
}

const STATUS_TEXT: Record<string, string> = {
  not_started: "Begin with your story",
  questions_queued: "Preparing the right questions",
  questions_running: "Understanding your material",
  questions_ready: "Ready for your next answer",
  answers_in_progress: "Continue your answers",
  needs_input: "Explorer needs more source material",
  brief_running: "Shaping your portfolio brief",
  brief_review: "Your brief is ready to review",
  approved: "Brief approved",
  needs_attention: "Explorer needs your attention",
};

const STATE_MAP: Record<string, StageState> = {
  not_started: "available",
  questions_queued: "working",
  questions_running: "working",
  questions_ready: "input",
  answers_in_progress: "input",
  needs_input: "input",
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

function stringRecord(value: unknown): Record<string, string> {
  if (!isRecord(value)) return {};
  return Object.fromEntries(
    Object.entries(value).filter((entry): entry is [string, string] => typeof entry[1] === "string"),
  );
}

function stringArrayRecord(value: unknown): Record<string, string[]> {
  if (!isRecord(value)) return {};
  return Object.fromEntries(
    Object.entries(value).map(([key, item]) => [key, stringArray(item)]),
  );
}

function recordArray(value: unknown): Record<string, unknown>[] {
  return Array.isArray(value) ? value.filter((item): item is Record<string, unknown> => isRecord(item)) : [];
}

function readString(value: unknown, fallback = ""): string {
  return typeof value === "string" ? value : fallback;
}

function readSourceDocuments(raw: unknown, rawDossier: unknown): DiscoverySourceDocumentVM[] {
  const coverage = recordArray(isRecord(rawDossier) ? rawDossier.source_coverage : null);
  const coverageBySpan = new Map(
    coverage
      .filter((item) => typeof item.span_id === "string")
      .map((item) => [item.span_id as string, item]),
  );
  return recordArray(raw).map((document) => {
    const originalText = readString(document.original_text);
    return {
      id: readString(document.id, "source"),
      label: readString(document.label),
      sourceKind: readString(document.source_kind),
      format: readString(document.format, "text"),
      offsetUnit: readString(document.offset_unit, "utf16_code_units"),
      originalText,
      sha256: readString(document.sha256),
      spans: recordArray(document.spans).map((span) => {
        const id = readString(span.id);
        const start = typeof span.start === "number" ? span.start : 0;
        const end = typeof span.end === "number" ? span.end : start;
        const covered = coverageBySpan.get(id);
        return {
          id,
          start,
          end,
          excerpt: readString(span.excerpt) || originalText.slice(start, end),
          disposition: typeof covered?.disposition === "string" ? covered.disposition : null,
          reason: readString(covered?.reason),
          factIds: stringArray(covered?.fact_ids),
        };
      }),
    };
  });
}

function adaptQuestionHistory(raw: unknown): DiscoveryQuestionHistoryVM[] {
  return recordArray(raw).map((event) => ({
    questionId: readString(event.question_id ?? event.id),
    question: readString(event.question ?? event.text),
    reason: readString(event.reason),
    gapId: readString(event.gap_id),
    affectedIds: stringArray(event.affected_ids),
    status: readString(event.status, "recorded"),
    answer: readString(event.answer),
    answerHistory: recordArray(event.answer_history).map((revision, index) => ({
      revision: typeof revision.revision === "number" ? revision.revision : index + 1,
      status: readString(revision.status, "answered"),
      answer: readString(revision.answer),
      sourceRefs: stringArray(revision.source_refs),
    })),
  })).filter((event) => event.question || event.questionId);
}

function adaptEvidenceItems(raw: unknown, kind: "role" | "project" | "evidence"): DiscoveryEvidenceItemVM[] {
  return recordArray(raw).map((item) => ({
    id: readString(item.id),
    title: readString(item.title ?? item.name ?? item.role ?? item.organization),
    detail: readString(item.detail ?? item.summary ?? item.problem ?? item.personal_contribution),
    category: readString(item.category),
    details: [
      ...(kind === "role" ? [
        { label: "Organization", value: readString(item.organization) },
        { label: "Role", value: readString(item.role) },
        { label: "Dates", value: readString(item.dates) },
        ...stringArray(item.details).map((value) => ({ label: "Detail", value })),
      ] : []),
      ...(kind === "project" ? [
        { label: "Problem", value: readString(item.problem) },
        { label: "Personal contribution", value: readString(item.personal_contribution) },
        { label: "Team contribution", value: readString(item.team_contribution) },
        ...stringArray(item.approach).map((value) => ({ label: "Approach", value })),
        ...stringArray(item.tools).map((value) => ({ label: "Tools", value })),
        ...stringArray(item.outcomes).map((value) => ({ label: "Outcome", value })),
        ...stringArray(item.links).map((value) => ({ label: "Link", value })),
      ] : []),
      ...(kind === "evidence" ? [
        { label: "Detail", value: readString(item.detail) },
      ] : []),
    ].filter((detail) => detail.value.trim().length > 0),
    sourceRefs: stringArray(item.source_refs),
    factIds: stringArray(item.fact_ids),
  }));
}

function adaptDossier(raw: unknown): DiscoveryDossierVM | null {
  if (!isRecord(raw)) return null;
  const facts = recordArray(raw.facts).map((fact) => ({
    id: readString(fact.id),
    statement: readString(fact.statement),
    originalWording: readString(fact.original_wording),
    sourceRefs: stringArray(fact.source_refs),
    qualifiers: stringArray(fact.qualifiers),
    ownership: readString(fact.ownership, "unknown"),
    status: readString(fact.status, "source_asserted"),
  }));
  const sourceCoverage = recordArray(raw.source_coverage).map((item) => ({
    spanId: readString(item.span_id),
    disposition: readString(item.disposition, "unclassified"),
    factIds: stringArray(item.fact_ids),
    reason: readString(item.reason),
  }));
  return {
    contractVersion: readString(raw.contract_version, "DiscoveryDossier/v1"),
    intent: {
      goal: readString(isRecord(raw.intent) ? raw.intent.goal : null),
      audience: readString(isRecord(raw.intent) ? raw.intent.audience : null),
      visitorAction: readString(isRecord(raw.intent) ? raw.intent.visitor_action : null),
      language: readString(isRecord(raw.intent) ? raw.intent.language : null),
      preferences: stringArray(isRecord(raw.intent) ? raw.intent.preferences : null),
      basis: stringRecord(isRecord(raw.intent) ? raw.intent.basis : null),
      basisRefs: stringArrayRecord(isRecord(raw.intent) ? raw.intent.basis_refs : null),
    },
    subject: {
      name: readString(isRecord(raw.subject) ? raw.subject.name : null),
      currentTitle: readString(isRecord(raw.subject) ? raw.subject.current_title : null),
      location: readString(isRecord(raw.subject) ? raw.subject.location : null),
      links: adaptStructuredProfile({ links: isRecord(raw.subject) ? raw.subject.links : null }).links,
      sourceRefs: stringArray(isRecord(raw.subject) ? raw.subject.source_refs : null),
    },
    facts,
    roles: adaptEvidenceItems(raw.roles, "role"),
    projects: adaptEvidenceItems(raw.projects, "project"),
    otherEvidence: adaptEvidenceItems(raw.other_evidence, "evidence"),
    openItems: recordArray(raw.open_items).map((item) => ({
      id: readString(item.id),
      detail: readString(item.detail),
      importance: readString(item.importance, "context"),
      status: readString(item.status, "open"),
      safeWording: readString(item.safe_wording),
      affectedIds: stringArray(item.affected_ids),
      sourceRefs: stringArray(item.source_refs),
    })),
    restrictions: recordArray(raw.restrictions).map((item) => ({
      id: readString(item.id),
      scope: readString(item.scope),
      instruction: readString(item.instruction),
      disposition: readString(item.disposition, "omit"),
      sourceRefs: stringArray(item.source_refs),
    })),
    userChoices: stringArray(raw.user_choices),
    sourceCoverage,
    questionHistory: adaptQuestionHistory(raw.question_events),
  };
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
 * Reads the compatibility profile projection rebuilt by the server from the
 * source-linked dossier. The review surface renders only fields that exist.
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
    raw.kind === "single_select" || raw.kind === "multi_select" || raw.kind === "boolean" || raw.kind === "palette_select" || raw.kind === "work_detail" ? raw.kind : "text";
  const options: DiscoveryQuestionOption[] = Array.isArray(raw.options)
    ? raw.options
        .filter((option): option is Record<string, unknown> => isRecord(option))
        .map((option) => ({
          id: typeof option.id === "string" ? option.id : "",
          label: typeof option.label === "string" ? option.label : "",
          description: typeof option.description === "string" ? option.description : "",
          swatches: Array.isArray(option.swatches)
            ? option.swatches.filter((color): color is string => typeof color === "string" && /^#[0-9a-fA-F]{6}$/.test(color)).slice(0, 3)
            : [],
        }))
        .filter((option) => option.id && option.label)
        .slice(0, kind === "palette_select" ? 8 : 3)
    : [];
  return {
    id: raw.id,
    text: raw.text,
    helpText: typeof raw.help_text === "string" ? raw.help_text : null,
    reason: typeof raw.reason === "string" ? raw.reason : null,
    gapId: typeof raw.gap_id === "string" ? raw.gap_id : null,
    affectedIds: stringArray(raw.affected_ids),
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
  if (question.kind === "palette_select" && isRecord(value)) {
    const choice = typeof value.choice_id === "string" ? labels.get(value.choice_id) : null;
    const note = typeof value.note === "string" ? value.note.trim() : "";
    return choice ? note ? `${choice}. ${note}` : choice : "Answer saved";
  }
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
      needsMoreMaterial: false,
      currentQuestions: [],
      answeredQuestionIds: [],
      answeredTurns: [],
      brief: null,
      sourceDocuments: [],
      questionHistory: [],
      safeError: null,
    };
  }

  const status = raw.status;
  const mappedState = STATE_MAP[status] ?? "unsupported";
  const operationA = isRecord(raw.operation_a) ? raw.operation_a : {};
  const briefState = isRecord(raw.brief) ? raw.brief : {};
  const rawDossier = adaptDossier(briefState.dossier ?? raw.dossier);
  const sourceDocuments = readSourceDocuments(raw.source_documents, briefState.dossier ?? raw.dossier);
  const latestError = isRecord(raw.latest_error) ? raw.latest_error : null;
  const questionJobId = typeof operationA.job_id === "string" ? operationA.job_id : null;
  const briefJobId = typeof briefState.job_id === "string" ? briefState.job_id : null;
  const briefIsActive =
    status === "brief_running" || status === "brief_review" || status === "approved" ||
    (status === "needs_attention" && latestError?.operation === "build_or_revise_brief");
  const activeJobId = briefIsActive ? briefJobId ?? questionJobId : questionJobId ?? briefJobId;
  const job: StageJobViewModel | null = selectStageJob(jobs, activeJobId);
  const items = Array.isArray(operationA.items) ? operationA.items : [];
  const answers = isRecord(raw.answers) && isRecord(raw.answers.items) ? raw.answers.items : {};
  const answeredIds = Object.keys(answers);

  // The app starts brief preparation when READY_FOR_BRIEF arrives. Other
  // question-ready snapshots with no unanswered item are likely stale data.
  const allQuestions = items.map(adaptQuestion).filter((q): q is DiscoveryQuestionVM => q !== null);
  const answeredTurns = allQuestions
    .filter((question) => question.id in answers)
    .map((question) => ({
      questionId: question.id,
      questionText: question.text,
      answerText: formatAnswer(answers[question.id], question),
    }));
  const currentQuestions =
    status === "questions_ready" || status === "answers_in_progress" || status === "needs_input"
      ? allQuestions.filter((q) => !answeredIds.includes(q.id))
      : [];
  const operationMode = typeof operationA.mode === "string" ? operationA.mode : "";
  const effectiveState: StageState =
    (status === "questions_ready" || status === "answers_in_progress") && currentQuestions.length === 0
      ? operationMode === "READY_FOR_BRIEF" || status === "answers_in_progress"
        ? "input"
        : allQuestions.length > 0
          ? "working"
          : "available"
      : mappedState;

  const failedJob = job?.status === "failed" || job?.status === "cancelled";
  const renderedState: StageState = failedJob ? "attention" : effectiveState;
  const brief =
    status === "brief_review" || status === "approved" ||
    ((status === "brief_running" || status === "needs_attention") && Boolean(briefState.markdown))
      ? {
          title: typeof briefState.title === "string" ? briefState.title : "",
          markdown: typeof briefState.markdown === "string" ? briefState.markdown : "",
          userSummary: typeof briefState.user_summary === "string" ? briefState.user_summary : "",
          approved: briefState.approved != null,
          profile: adaptStructuredProfile(briefState.profile),
          dossier: rawDossier,
        }
      : null;

  const questionHistoryFromState = adaptQuestionHistory(raw.question_events);
  const questionHistory =
    questionHistoryFromState.length > 0
      ? questionHistoryFromState
      : rawDossier?.questionHistory.length
        ? rawDossier.questionHistory
        : answeredTurns.map((turn) => ({
            questionId: turn.questionId,
            question: turn.questionText,
            reason: "",
            gapId: "",
            affectedIds: [],
            status: turn.answerText === "Skipped" ? "skipped" : "answered",
            answer: turn.answerText,
            answerHistory: [],
          }));

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
                : job?.error?.message ?? "Explorer could not continue.",
          ),
          retryOperation,
        }
      : null;

  return {
    state: renderedState,
    statusText: STATUS_TEXT[status] ?? "Working on Explorer",
    raw,
    job,
    agentOutput: readAgentOutput(raw),
    needsMoreMaterial: status === "needs_input",
    currentQuestions,
    answeredQuestionIds: answeredIds,
    answeredTurns,
    brief,
    sourceDocuments,
    questionHistory,
    safeError,
  };
}
