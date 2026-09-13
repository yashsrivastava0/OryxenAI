// Activity copy — turns a stage's real durable status (the same status
// strings the per-stage adapters map in their STATUS_TEXT tables) into
// honest, specific, human activity copy for the workspace's live status
// line. This is deliberately *not* the adapter's `statusText`: the adapter
// text is a short label ("Structuring your portfolio content"); this module
// produces the fuller live-activity line following a single formula:
//
//   Action-Word + Specific-Item + Limit
//
// e.g. "Structuring the site plan from your approved brief…" instead of a
// generic "Working…". While a stage is actively working the copy is
// present-tense and ends with a single-character ellipsis (…); once the
// stage has finished the copy is past-tense with no ellipsis.
//
// The function is pure: identical inputs always produce identical output,
// and it never reads the DOM, network, clock, or any module-level mutable
// state. Every branch has a deterministic, specific fallback so an
// unrecognised (newer) backend status still yields non-generic copy rather
// than "Working…".

/** The canonical stage keys used across the pipeline. */
export type ActivityStage =
  | "discovery"
  | "content_architect"
  | "visual_design_director"
  | "build_preparation"
  | "code_generator";

/**
 * Optional job/progress fields the caller may already hold (from the shared
 * StageJobViewModel / adapter progress fields). All optional: the function
 * degrades gracefully to status-only copy when they are absent. These only
 * ever *refine* copy (e.g. naming the current milestone); they never change
 * the present-vs-past tense decision, which is driven purely by status.
 */
export interface ActivityContext {
  /** A backend-reported sub-stage / milestone label, if any
   * (e.g. build_preparation `current_stage`, code_generator
   * `progress.coordinator_stage`). Used only to sharpen the Specific-Item. */
  milestone?: string | null;
  /** Retry attempt number for the active job (1-based). When > 1 while
   * working, the copy notes the retry so a stalled-looking line still reads
   * as forward progress rather than a hang. */
  attempt?: number | null;
  /** Whether a completed stage's output is stale and must be re-run. A stale
   * "complete" status is reported as needing a refresh rather than as a
   * finished success. */
  stale?: boolean | null;
}

export interface ActivityCopy {
  /** The rendered activity line. Ends with "…" iff `working` is true. */
  text: string;
  /** True while the stage is actively doing work (present tense, ellipsis). */
  working: boolean;
  /** True once the stage has finished its work successfully (past tense). */
  complete: boolean;
}

/**
 * A single status entry. `working` copy omits the trailing ellipsis — it is
 * appended centrally so every working line ends in exactly one "…". `done`
 * copy is the past-tense form used when the stage has completed.
 */
interface StatusEntry {
  /** Present-tense Action + Specific-Item + Limit, WITHOUT trailing ellipsis. */
  working?: string;
  /** Past-tense completion copy (no ellipsis). */
  done?: string;
  /** If true this status is a working (in-progress) state. */
  isWorking?: boolean;
  /** If true this status is a successful completion state. */
  isComplete?: boolean;
}

const ELLIPSIS = "…";

// Statuses that mean "actively working" per stage but for which we still
// want per-status specific copy live in the maps below with isWorking:true.
// Statuses that mean "done" carry isComplete:true.

const DISCOVERY: Record<string, StatusEntry> = {
  not_started: { working: undefined, done: undefined },
  questions_queued: { working: "Preparing the first few discovery questions from your intake", isWorking: true },
  questions_running: { working: "Reading your material to draft up to a handful of focused questions", isWorking: true },
  questions_ready: { done: undefined },
  answers_in_progress: { done: undefined },
  brief_running: { working: "Shaping your portfolio brief from your answers", isWorking: true },
  brief_review: { done: undefined },
  approved: { done: "Approved your portfolio brief", isComplete: true },
  needs_attention: { done: undefined },
};

const CONTENT_ARCHITECT: Record<string, StatusEntry> = {
  not_started: {},
  build_running: { working: "Structuring the site plan and page content from your approved brief", isWorking: true },
  content_review: {},
  approved: { done: "Approved your content plan across every page", isComplete: true },
  needs_attention: {},
};

const VISUAL_DESIGN_DIRECTOR: Record<string, StatusEntry> = {
  not_started: {},
  build_running: { working: "Developing the visual direction from your approved content plan", isWorking: true },
  design_review: {},
  approved: { done: "Approved your visual direction for the whole site", isComplete: true },
  needs_attention: {},
};

const BUILD_PREPARATION: Record<string, StatusEntry> = {
  not_started: {},
  running: { working: "Compiling the build handoff from your approved content and design", isWorking: true },
  ready: { done: "Prepared the build handoff for generation", isComplete: true },
  needs_attention: {},
};

const CODE_GENERATOR: Record<string, StatusEntry> = {
  not_started: {},
  queued: { working: "Queuing the portfolio generation from your build handoff", isWorking: true },
  planning: { working: "Planning the site structure from your build handoff", isWorking: true },
  acquiring: { working: "Acquiring the pinned images and fonts for your portfolio", isWorking: true },
  generating: { working: "Generating your portfolio source across every page", isWorking: true },
  verifying: { working: "Verifying the built site across desktop and mobile viewports", isWorking: true },
  preview_pending: { working: "Finishing the verified preview of your portfolio", isWorking: true },
  ready: { done: "Generated and verified your portfolio", isComplete: true },
  needs_attention: {},
};

const STAGE_MAPS: Record<ActivityStage, Record<string, StatusEntry>> = {
  discovery: DISCOVERY,
  content_architect: CONTENT_ARCHITECT,
  visual_design_director: VISUAL_DESIGN_DIRECTOR,
  build_preparation: BUILD_PREPARATION,
  code_generator: CODE_GENERATOR,
};

/** Human-readable per-stage subject used in deterministic fallback copy. */
const STAGE_SUBJECT: Record<ActivityStage, string> = {
  discovery: "your portfolio brief",
  content_architect: "your content plan",
  visual_design_director: "your visual direction",
  build_preparation: "your build handoff",
  code_generator: "your portfolio",
};

/** Statuses that always mean "working" even if not explicitly listed. */
function looksLikeWorkingStatus(status: string): boolean {
  return (
    status.endsWith("_running") ||
    status.endsWith("_queued") ||
    status === "running" ||
    status === "queued" ||
    status === "planning" ||
    status === "acquiring" ||
    status === "generating" ||
    status === "verifying" ||
    status === "preview_pending"
  );
}

/** Statuses that always mean "complete" even if not explicitly listed. */
function looksLikeCompleteStatus(status: string): boolean {
  return status === "approved" || status === "ready" || status === "complete";
}

function withMilestone(base: string, milestone?: string | null): string {
  const trimmed = typeof milestone === "string" ? milestone.trim() : "";
  if (!trimmed) return base;
  // Keep it human: turn "generate_pages" / "generate-pages" into "generate pages".
  const readable = trimmed.replace(/[-_]+/g, " ").trim();
  return `${base} (${readable})`;
}

function withAttempt(base: string, attempt?: number | null): string {
  if (typeof attempt === "number" && Number.isFinite(attempt) && attempt > 1) {
    return `${base} — retry ${attempt}`;
  }
  return base;
}

/**
 * Format honest activity copy for a stage's real durable status.
 *
 * - While the stage is working: present tense, Action + Specific-Item +
 *   Limit, ending in exactly one "…".
 * - When the stage has completed successfully (and is not stale): past tense,
 *   no ellipsis.
 * - Otherwise (idle/review/attention/unknown): a specific, non-generic
 *   present-tense line for the stage, without an ellipsis, and neither
 *   working nor complete.
 *
 * Pure: output depends only on the arguments.
 */
export function formatActivityStatus(
  stage: ActivityStage,
  status: string,
  context: ActivityContext = {},
): ActivityCopy {
  const map = STAGE_MAPS[stage];
  const subject = STAGE_SUBJECT[stage];
  const entry: StatusEntry | undefined = map ? map[status] : undefined;

  const isWorking =
    entry?.isWorking === true || (entry === undefined && looksLikeWorkingStatus(status));
  const isComplete =
    entry?.isComplete === true || (entry === undefined && looksLikeCompleteStatus(status));

  // A stale completion is not a clean "done": surface it as needing a refresh.
  if (isComplete && context.stale === true) {
    return {
      text: `${capitalize(subject)} is out of date and needs to be prepared again`,
      working: false,
      complete: false,
    };
  }

  if (isWorking) {
    const base = entry?.working ?? `Working on ${subject}`;
    const text = withAttempt(withMilestone(base, context.milestone), context.attempt) + ELLIPSIS;
    return { text, working: true, complete: false };
  }

  if (isComplete) {
    const text = entry?.done ?? `Completed ${subject}`;
    return { text, working: false, complete: true };
  }

  // Idle / input / review / attention / unknown — specific, no ellipsis,
  // neither working nor complete.
  return { text: idleCopy(stage, status, subject), working: false, complete: false };
}

function capitalize(value: string): string {
  return value.length === 0 ? value : value[0]!.toUpperCase() + value.slice(1);
}

/**
 * Deterministic, specific idle/non-working copy per stage+status. Never a
 * bare "Working…" — every branch names the stage's subject.
 */
function idleCopy(stage: ActivityStage, status: string, subject: string): string {
  switch (status) {
    case "not_started":
      return `Ready to start on ${subject}`;
    case "questions_ready":
      return "Waiting for your next answer";
    case "answers_in_progress":
      return "Waiting for you to finish your answers";
    case "brief_review":
    case "content_review":
    case "design_review":
      return `Waiting for you to review ${subject}`;
    case "needs_attention":
      return `${capitalize(stage.replace(/_/g, " "))} needs your attention`;
    default:
      return `Working through ${subject}`;
  }
}
