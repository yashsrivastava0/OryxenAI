// Content Architect stage adapter (docs/Frontend/05 §6.3).
// Normalizes ContentArchitectState into ContentViewModel.
// Follows the same fail-closed, defensive pattern established by discovery.ts.
//
// The page content tree mirrors the one pinned portfolio template
// (frontend/public/theme/index.html) region for region.

import { selectStageJob } from "./job";
import {
  readAgentOutput,
  readSafeStageError,
  type SafeStageError,
  type StageState,
  type StageViewModel,
} from "./types";

export interface HeroVM {
  name: string;
  eyebrowPrimary: string;
  eyebrowSecondary: string;
  headlinePrefix: string;
  headlineEmphasis: string;
  intro: string;
  location: string;
  primaryCtaLabel: string;
  secondaryCtaLabel: string;
}

export interface PillarVM {
  title: string;
  description: string;
}

export interface SystemsPracticeVM {
  eyebrow: string;
  heading: string;
  intro: string;
  pillars: PillarVM[];
}

export interface CapabilityGroupVM {
  heading: string;
  items: string[];
}

export interface TechnicalCapabilitiesVM {
  eyebrow: string;
  heading: string;
  intro: string;
  groups: CapabilityGroupVM[];
}

export interface ProfessionalContextVM {
  eyebrow: string;
  heading: string;
  intro: string;
  organizations: string[];
}

export interface DestinationVM {
  label: string;
  url: string;
  featured: boolean;
}

export interface ConnectVM {
  eyebrow: string;
  heading: string;
  intro: string;
  destinations: DestinationVM[];
}

export interface PageContentVM {
  hero: HeroVM;
  metadataTitle: string;
  metadataDescription: string;
  marqueeKeywords: string[];
  systemsPractice: SystemsPracticeVM;
  technicalCapabilities: TechnicalCapabilitiesVM;
  professionalContext: ProfessionalContextVM;
  connect: ConnectVM;
  atlas: {
    aboutHeading: string;
    aboutIntro: string;
    aboutQuote: string;
    experience: Array<{ role: string; organization: string; dates: string; description: string }>;
    education: Array<{ credential: string; institution: string; dates: string }>;
    statistics: Array<{ value: string; label: string }>;
    projects: Array<{ kind: string; title: string; summary: string; role: string; period: string; problem: string; approach: string; outcome: string; externalUrl: string }>;
  };
}

export interface ClaimGroundingVM {
  claimId: string;
  statement: string;
  sourceReference: string;
  evidenceStatus: string;
  ownership: string;
  publicationStatus: string;
  confidenceOrWarning: string;
  fieldPaths: string[];
}

export interface CoverageEntryVM {
  sourceId: string;
  disposition: string;
  fieldPaths: string[];
  reason: string;
}

export interface DecisionRecordVM {
  decision: string;
  value: string;
  basis: string;
  rationale: string;
}

export interface StoryStrategyVM {
  positioning: string;
  valueProposition: string;
  primaryAudience: string;
  secondaryAudience: string;
  primaryAction: string;
  narrativeThesis: string;
  leadingEvidence: string[];
  supportingEvidence: string[];
  contentRisks: string[];
  tone: string;
  contentDensity: string;
}

export interface ContentViewModel extends StageViewModel {
  elapsedSeconds: number | null;
  userSummary: string;
  positioning: string;
  storyStrategy: StoryStrategyVM;
  pageContent: PageContentVM;
  claimGrounding: ClaimGroundingVM[];
  coverageLedger: CoverageEntryVM[];
  internalNotes: Record<string, unknown>;
  decisionBasis: DecisionRecordVM[];
  omissions: string[];
  unresolvedIssues: string[];
  warnings: string[];
  safeError: SafeStageError | null;
}

const STATUS_TEXT: Record<string, string> = {
  not_started: "Ready to structure portfolio content",
  build_running: "Structuring your portfolio content",
  content_review: "Your content plan is ready to review",
  approved: "Content plan approved",
  needs_attention: "Content Architect needs attention",
};

const STATE_MAP: Record<string, StageState> = {
  not_started: "available",
  build_running: "working",
  content_review: "review",
  approved: "complete",
  needs_attention: "attention",
};

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}

function str(value: unknown): string {
  return typeof value === "string" ? value : "";
}

function strings(value: unknown): string[] {
  return Array.isArray(value) ? value.filter((v): v is string => typeof v === "string") : [];
}

function records(value: unknown): Record<string, unknown>[] {
  return Array.isArray(value) ? value.filter(isRecord) : [];
}

function adaptHero(raw: Record<string, unknown>): HeroVM {
  return {
    name: str(raw.name),
    eyebrowPrimary: str(raw.eyebrow_primary),
    eyebrowSecondary: str(raw.eyebrow_secondary),
    headlinePrefix: str(raw.headline_prefix),
    headlineEmphasis: str(raw.headline_emphasis),
    intro: str(raw.intro),
    location: str(raw.location),
    primaryCtaLabel: str(raw.primary_cta_label),
    secondaryCtaLabel: str(raw.secondary_cta_label),
  };
}

function region(raw: Record<string, unknown>, key: string): Record<string, unknown> {
  const value = raw[key];
  return isRecord(value) ? value : {};
}

export function emptyPageContent(): PageContentVM {
  return adaptPageContent({});
}

export function adaptPageContent(raw: unknown): PageContentVM {
  const page = isRecord(raw) ? raw : {};
  const systems = region(page, "systems_practice");
  const capabilities = region(page, "technical_capabilities");
  const context = region(page, "professional_context");
  const connect = region(page, "connect");
  const metadata = region(page, "metadata");
  const atlas = region(page, "atlas");
  return {
    hero: adaptHero(region(page, "hero")),
    metadataTitle: str(metadata.title),
    metadataDescription: str(metadata.description),
    marqueeKeywords: strings(page.marquee_keywords),
    systemsPractice: {
      eyebrow: str(systems.eyebrow),
      heading: str(systems.heading),
      intro: str(systems.intro),
      pillars: records(systems.pillars).map((p) => ({
        title: str(p.title),
        description: str(p.description),
      })),
    },
    technicalCapabilities: {
      eyebrow: str(capabilities.eyebrow),
      heading: str(capabilities.heading),
      intro: str(capabilities.intro),
      groups: records(capabilities.groups).map((g) => ({
        heading: str(g.heading),
        items: strings(g.items),
      })),
    },
    professionalContext: {
      eyebrow: str(context.eyebrow),
      heading: str(context.heading),
      intro: str(context.intro),
      organizations: strings(context.organizations),
    },
    connect: {
      eyebrow: str(connect.eyebrow),
      heading: str(connect.heading),
      intro: str(connect.intro),
      destinations: records(connect.destinations).map((d) => ({
        label: str(d.label),
        url: str(d.url),
        featured: d.featured === true,
      })),
    },
    atlas: {
      aboutHeading: str(atlas.about_heading),
      aboutIntro: str(atlas.about_intro),
      aboutQuote: str(atlas.about_quote),
      experience: records(atlas.experience).map((row) => ({ role: str(row.role), organization: str(row.organization), dates: str(row.dates), description: str(row.description) })),
      education: records(atlas.education).map((row) => ({ credential: str(row.credential), institution: str(row.institution), dates: str(row.dates) })),
      statistics: records(atlas.statistics).map((row) => ({ value: str(row.value), label: str(row.label) })),
      projects: records(atlas.projects).map((row) => ({ kind: str(row.kind), title: str(row.title), summary: str(row.summary), role: str(row.role), period: str(row.period), problem: str(row.problem), approach: str(row.approach), outcome: str(row.outcome), externalUrl: str(row.external_url) })),
    },
  };
}

/** True when the model produced no page copy at all (e.g. legacy persisted state). */
export function pageContentIsEmpty(page: PageContentVM): boolean {
  return (
    !page.hero.name &&
    !page.hero.intro &&
    page.systemsPractice.pillars.length === 0 &&
    page.technicalCapabilities.groups.length === 0
  );
}

function adaptClaim(raw: Record<string, unknown>): ClaimGroundingVM | null {
  if (typeof raw.claim_id !== "string") return null;
  return {
    claimId: raw.claim_id,
    statement: str(raw.statement),
    sourceReference: str(raw.source_reference),
    evidenceStatus: str(raw.evidence_status) || "unresolved",
    ownership: str(raw.ownership) || "unclear",
    publicationStatus: str(raw.publication_status) || "pending",
    confidenceOrWarning: str(raw.confidence_or_warning),
    fieldPaths: strings(raw.field_paths),
  };
}

function adaptCoverage(raw: Record<string, unknown>): CoverageEntryVM | null {
  if (typeof raw.source_id !== "string") return null;
  return {
    sourceId: raw.source_id,
    disposition: str(raw.disposition),
    fieldPaths: strings(raw.field_paths),
    reason: str(raw.reason),
  };
}

function adaptDecision(raw: Record<string, unknown>): DecisionRecordVM | null {
  if (typeof raw.decision !== "string") return null;
  return {
    decision: raw.decision,
    value: str(raw.value),
    basis: str(raw.basis) || "safe_default",
    rationale: str(raw.rationale),
  };
}

function adaptStrategy(raw: unknown): StoryStrategyVM {
  const s = isRecord(raw) ? raw : {};
  return {
    positioning: str(s.positioning),
    valueProposition: str(s.value_proposition),
    primaryAudience: str(s.primary_audience),
    secondaryAudience: str(s.secondary_audience),
    primaryAction: str(s.primary_action),
    narrativeThesis: str(s.narrative_thesis),
    leadingEvidence: strings(s.leading_evidence),
    supportingEvidence: strings(s.supporting_evidence),
    contentRisks: strings(s.content_risks),
    tone: str(s.tone),
    contentDensity: str(s.content_density),
  };
}

function unsupportedView(raw: unknown, jobs: unknown[]): ContentViewModel {
  return {
    state: "unsupported",
    statusText: "Content Architect returned an unrecognised state. Refresh to continue.",
    raw,
    job: selectStageJob(jobs),
    agentOutput: null,
    userSummary: "",
    elapsedSeconds: null,
    positioning: "",
    storyStrategy: adaptStrategy({}),
    pageContent: emptyPageContent(),
    claimGrounding: [],
    coverageLedger: [],
    internalNotes: {},
    decisionBasis: [],
    omissions: [],
    unresolvedIssues: [],
    warnings: [],
    safeError: null,
  };
}

/**
 * Accepts the raw `content_architect` dict from ContentArchitectStateResponse
 * and whether Discovery has been approved.
 */
export function adaptContentArchitect(
  raw: unknown,
  discoveryApproved = false,
  jobs: unknown[] = [],
): ContentViewModel {
  if (!isRecord(raw) || typeof raw.status !== "string" || !(raw.status in STATE_MAP)) {
    return unsupportedView(raw, jobs);
  }

  const status = raw.status;
  const job = selectStageJob(jobs, typeof raw.job_id === "string" ? raw.job_id : null);
  const failedJob = job?.status === "failed" || job?.status === "cancelled";
  let state: StageState = failedJob ? "attention" : STATE_MAP[status] ?? "unsupported";

  // Upstream gating: if not started and Discovery is not yet approved, this stage is locked.
  if (status === "not_started" && !discoveryApproved) {
    state = "locked";
  }

  const storyStrategy = adaptStrategy(raw.site_story_strategy);

  const latestError = isRecord(raw.latest_error) ? raw.latest_error : null;
  const safeError =
    (status === "needs_attention" && latestError) || failedJob
      ? readSafeStageError(
          latestError,
          typeof latestError?.message === "string"
            ? latestError.message
            : typeof latestError?.summary === "string"
              ? latestError.summary
              : job?.error?.message ?? "Content Architect needs attention.",
        )
      : null;

  return {
    state,
    statusText: status === "not_started" && !discoveryApproved
      ? "Locked until Discovery is approved"
      : STATUS_TEXT[status] ?? "Working on Content",
    raw,
    job,
    agentOutput: readAgentOutput(raw),
    userSummary: str(raw.user_summary),
    elapsedSeconds: typeof raw.elapsed_seconds === "number" && Number.isFinite(raw.elapsed_seconds)
      ? Math.max(0, raw.elapsed_seconds)
      : null,
    positioning: storyStrategy.positioning,
    storyStrategy,
    pageContent: adaptPageContent(raw.page_content),
    claimGrounding: records(raw.claim_grounding)
      .map(adaptClaim)
      .filter((c): c is ClaimGroundingVM => c !== null),
    coverageLedger: records(raw.coverage_ledger)
      .map(adaptCoverage)
      .filter((c): c is CoverageEntryVM => c !== null),
    internalNotes: isRecord(raw.internal_notes) ? raw.internal_notes : {},
    decisionBasis: records(raw.decision_basis)
      .map(adaptDecision)
      .filter((d): d is DecisionRecordVM => d !== null),
    omissions: strings(raw.omissions),
    unresolvedIssues: strings(raw.unresolved_issues),
    warnings: strings(raw.warnings),
    safeError,
  };
}
