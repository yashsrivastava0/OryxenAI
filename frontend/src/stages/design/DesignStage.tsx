import type { DesignViewModel } from "../../data/adapters/design";
import { ArtifactSurface, type ArtifactSectionItem } from "../../components/ArtifactSurface";
import { HandoffPanel } from "../../components/HandoffPanel";
import { AttentionPanel } from "../../components/AttentionPanel";
import { LivingDraftMark } from "../../components/LivingDraftMark";

export interface DesignStageProps {
  view: DesignViewModel | null;
  canMutate: boolean;
  onStart: () => Promise<void>;
  onApprove: () => Promise<void>;
  onRevise: (revisionRequest: string) => Promise<void>;
  onContinueToPrepare: () => void;
  inFlight?: boolean;
}

export function DesignStage({
  view,
  canMutate,
  onStart,
  onApprove,
  onRevise,
  onContinueToPrepare,
  inFlight = false,
}: DesignStageProps) {
  if (!view || view.state === "locked") {
    return (
      <div className="stage-locked-panel">
        <p className="eyebrow">Stage 03 / Visual Design Director</p>
        <h2>Stage Locked</h2>
        <p className="stage-desc">
          Visual Design Director requires an approved site content plan before establishing the aesthetic systems, visual language, and page layouts.
        </p>
      </div>
    );
  }

  if (view.state === "available") {
    return (
      <div className="stage-available-panel">
        <p className="eyebrow">Stage 03 / Visual Design Director</p>
        <h2>Ready to direct visual experience</h2>
        <p className="stage-desc">
          Visual Design Director will consume your approved content plan to derive the creative thesis, typography hierarchy, color intention, and page-by-page visual language.
        </p>
        <button
          type="button"
          className="btn-primary"
          disabled={!canMutate || inFlight}
          onClick={onStart}
        >
          {inFlight ? "Starting Visual Design Director..." : "Start Visual Design Director"}
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
          The agent is establishing visual language, styling systems, and page-level layouts.
        </p>
      </div>
    );
  }

  if (view.state === "attention") {
    return (
      <AttentionPanel
        title="Visual Design Director needs attention"
        summary={view.safeError?.summary || "Design direction synthesis encountered an issue and can be restarted."}
        preservedWorkNote="Your approved Content Plan remains safe."
        retryLabel="Retry Visual Design Director"
        onRetry={onStart}
      />
    );
  }

  // review or complete
  const isApproved = view.state === "complete";

  // Build structured sections for ArtifactSurface
  const structuredSections: ArtifactSectionItem[] = [];

  // Creative Thesis & Language
  const lang = view.visualLanguage;
  const thesisMarkdown = [
    lang.creativeThesis ? `### Creative Thesis\n${lang.creativeThesis}` : "",
    lang.designKeywords.length > 0 ? `\n\n**Keywords:** ${lang.designKeywords.join(", ")}` : "",
    lang.colorIntent ? `\n\n**Color Intention:** ${lang.colorIntent}` : "",
    lang.typographyIntent ? `\n\n**Typography Intention:** ${lang.typographyIntent}` : "",
    lang.motionIntent ? `\n\n**Motion Rules:** ${lang.motionIntent}` : "",
  ].join("");

  structuredSections.push({
    id: "thesis",
    title: "Creative Thesis & Visual Language",
    contentMarkdown: thesisMarkdown,
  });

  // Page Visual Directions
  if (view.pages.length > 0) {
    const pagesMarkdown = view.pages
      .map(
        (p) =>
          `### Route: \`${p.routeId}\` — ${p.title}\n* **Mood:** ${p.mood}\n* **Layout intent:** ${p.layoutIntent}\n* **Desktop treatment:** ${p.desktopTreatment}\n* **Mobile treatment:** ${p.mobileTreatment}`,
      )
      .join("\n\n---\n\n");

    structuredSections.push({
      id: "pages",
      title: "Page Visual Directions",
      badge: `${view.pages.length} page directions`,
      contentMarkdown: pagesMarkdown,
    });
  }

  // Catalogue Candidates
  if (view.resources.length > 0) {
    const resourcesMarkdown = view.resources
      .map(
        (r) =>
          `* **\`${r.resourceId}\`** (${r.category}): ${r.whyItMatches} — *Adaptation: ${r.adaptationNotes}*`,
      )
      .join("\n");

    structuredSections.push({
      id: "resources",
      title: "Adapted Layout Candidates",
      contentMarkdown: resourcesMarkdown,
    });
  }

  return (
    <div className="design-stage-view">
      <ArtifactSurface
        title="Visual Direction & Experience Architecture"
        artifactTypeName="visual direction"
        statusBadge={isApproved ? "Approved" : "Ready for review"}
        isApproved={isApproved}
        canMutate={canMutate}
        structuredSections={structuredSections}
        warnings={view.warnings}
        metadata={[
          { label: "Styled Routes", value: String(view.pages.length) },
          { label: "Status", value: isApproved ? "Locked & Approved" : "Under Review" },
        ]}
        onApprove={onApprove}
        onRevise={onRevise}
      />

      {isApproved && (
        <HandoffPanel
          completedStageName="Visual Direction"
          nextStageName="Build Preparation"
          summary="Both your Content Plan and Visual Direction are approved and verified. Build Preparation can now resolve verified assets, compile route context, and package the deterministic ZIP."
          nextDescription="Build Preparation compiles public scope, resolves curated assets with fallbacks, builds deterministic ZIP packages, and verifies storage readiness."
          actionLabel="Prepare the build"
          onContinue={onContinueToPrepare}
        />
      )}
    </div>
  );
}
