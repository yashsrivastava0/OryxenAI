import type { ContentViewModel } from "../../data/adapters/content";
import { ArtifactSurface, type ArtifactSectionItem } from "../../components/ArtifactSurface";
import { HandoffPanel } from "../../components/HandoffPanel";
import { AttentionPanel } from "../../components/AttentionPanel";
import { LivingDraftMark } from "../../components/LivingDraftMark";

export interface ContentStageProps {
  view: ContentViewModel | null;
  canMutate: boolean;
  onStart: () => Promise<void>;
  onApprove: () => Promise<void>;
  onRevise: (revisionRequest: string) => Promise<void>;
  onContinueToDesign: () => void;
}

export function ContentStage({
  view,
  canMutate,
  onStart,
  onApprove,
  onRevise,
  onContinueToDesign,
}: ContentStageProps) {
  if (!view || view.state === "locked") {
    return (
      <div className="stage-locked-panel">
        <p className="eyebrow">Stage 02 / Content Architect</p>
        <h2>Stage Locked</h2>
        <p className="stage-desc">
          Content Architect requires an approved portfolio brief from Discovery before building your site architecture and page copy.
        </p>
      </div>
    );
  }

  if (view.state === "available") {
    return (
      <div className="stage-available-panel">
        <p className="eyebrow">Stage 02 / Content Architect</p>
        <h2>Ready to structure portfolio content</h2>
        <p className="stage-desc">
          Content Architect will consume your approved brief to define the site's route structure, positioning statements, and detailed section copy.
        </p>
        <button
          type="button"
          className="btn-primary"
          disabled={!canMutate}
          onClick={onStart}
        >
          Start Content Architect
        </button>
      </div>
    );
  }

  if (view.state === "working") {
    return (
      <div className="stage-working-panel" role="status">
        <LivingDraftMark active={true} />
        <h2>{view.statusText}</h2>
        <p className="stage-desc">
          The agent is structuring routes, deriving positioning, and drafting page content packs.
        </p>
      </div>
    );
  }

  if (view.state === "attention") {
    return (
      <AttentionPanel
        title="Content Architect needs attention"
        summary={view.safeError?.summary || "Content synthesis encountered an issue and can be restarted."}
        preservedWorkNote="Your approved Discovery brief remains intact."
        retryLabel="Retry Content Architect"
        onRetry={onStart}
      />
    );
  }

  // review or complete
  const isApproved = view.state === "complete";

  // Build structured sections for ArtifactSurface
  const structuredSections: ArtifactSectionItem[] = [];

  // Strategy section
  if (view.positioning || view.userSummary) {
    structuredSections.push({
      id: "strategy",
      title: "Core Positioning & Strategy",
      contentMarkdown: view.positioning
        ? `**Positioning:** ${view.positioning}\n\n${view.userSummary}`
        : view.userSummary,
    });
  }

  // Route Plan section
  if (view.routePlan.length > 0) {
    const routeMarkdown = view.routePlan
      .map(
        (r) =>
          `### \`${r.path}\` — ${r.title}\n* **Purpose:** ${r.purpose}\n* **Status:** \`${r.publicationStatus}\`\n* **Audience takeaway:** ${r.audienceTakeaway}\n* **Sections:** ${r.sectionSequence.map((s) => `\`${s}\``).join(", ")}`,
      )
      .join("\n\n---\n\n");

    structuredSections.push({
      id: "routes",
      title: "Site Architecture & Routes",
      badge: `${view.routePlan.length} routes planned`,
      contentMarkdown: routeMarkdown,
    });
  }

  // Page Content Packs section
  if (view.pageContentPacks.length > 0) {
    const packsMarkdown = view.pageContentPacks
      .map((pack) => {
        const sectionsText = pack.sections
          .map((sec) => {
            const headline = (sec.content.headline as string) || (sec.content.title as string) || sec.purpose;
            const subhead = (sec.content.subheadline as string) || (sec.content.body as string) || "";
            return `#### Section: \`${sec.sectionId}\` (${sec.priority || "standard"})\n*Purpose: ${sec.purpose}*\n\n${headline ? `**${headline}**\n\n` : ""}${subhead}`;
          })
          .join("\n\n");
        return `### Route: \`${pack.routeId}\`\n\n${sectionsText}`;
      })
      .join("\n\n---\n\n");

    structuredSections.push({
      id: "sections",
      title: "Page Content Packs",
      contentMarkdown: packsMarkdown,
    });
  }

  // Strategy Decisions section
  if (view.decisionBasis.length > 0) {
    const decisionsMarkdown = view.decisionBasis
      .map(
        (d) =>
          `* **${d.decision.replace(/_/g, " ")}:** \`${d.value}\` (${d.basis.replace(/_/g, " ")}) — *${d.rationale}*`,
      )
      .join("\n");

    structuredSections.push({
      id: "decisions",
      title: "Strategy Decisions",
      contentMarkdown: decisionsMarkdown,
    });
  }

  return (
    <div className="content-stage-view">
      <ArtifactSurface
        title="Content Strategy & Route Architecture"
        artifactTypeName="content plan"
        statusBadge={isApproved ? "Approved" : "Ready for review"}
        isApproved={isApproved}
        canMutate={canMutate}
        structuredSections={structuredSections}
        warnings={view.warnings}
        metadata={[
          { label: "Planned Routes", value: String(view.routePlan.length) },
          { label: "Status", value: isApproved ? "Locked & Approved" : "Under Review" },
        ]}
        onApprove={onApprove}
        onRevise={onRevise}
      />

      {isApproved && (
        <HandoffPanel
          completedStageName="Content Plan"
          nextStageName="Visual Design Director"
          summary="Your site content and route architecture are approved and locked. Visual Design Director will now establish the creative thesis, aesthetic tokens, and page-by-page visual language."
          nextDescription="Visual Design Director directs the typography hierarchy, color intention, motion rules, and resolves adaptable layout components."
          actionLabel="Continue to Design"
          onContinue={onContinueToDesign}
        />
      )}
    </div>
  );
}
