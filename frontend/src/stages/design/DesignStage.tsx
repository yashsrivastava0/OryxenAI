import type { DesignViewModel } from "../../data/adapters/design";
import { ArtifactSurface, type ArtifactSectionItem } from "../../components/ArtifactSurface";
import { AttentionPanel } from "../../components/AttentionPanel";
import { ProgressSurface } from "../../components/ProgressSurface";
import { CompletionPanel } from "../../components/CompletionPanel";
import { UnsupportedPanel } from "../../components/UnsupportedPanel";
import { AsyncActionButton } from "../../components/AsyncActionButton";

export interface DesignStageProps {
  view: DesignViewModel | null;
  canMutate: boolean;
  onStart: () => Promise<void>;
  onApprove: () => Promise<void>;
  onRevise: (revisionRequest: string) => Promise<void>;
  inFlight?: boolean;
}

export function DesignStage({
  view,
  canMutate,
  onStart,
  onApprove,
  onRevise,
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
        <AsyncActionButton
          label="Start Visual Design Director"
          busyLabel="Starting Visual Design Director..."
          onAction={onStart}
          disabled={!canMutate}
          inFlight={inFlight}
        />
      </div>
    );
  }

  if (view.state === "unsupported") {
    return <UnsupportedPanel stageName="Visual Design Director" statusText={view.statusText} />;
  }

  if (view.state === "working") {
    return (
      <ProgressSurface
        stageLabel="Stage 03 / Visual Design Director"
        title="Directing the visual proof"
        currentMilestone={view.statusText || "Visual Design Director is working from the approved content plan"}
        milestones={[
          { id: "content", label: "Approved content plan received", state: "complete" },
          { id: "current", label: view.statusText || "Visual Design Director is working", state: "current" },
        ]}
      />
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
        <CompletionPanel />
      )}
    </div>
  );
}
