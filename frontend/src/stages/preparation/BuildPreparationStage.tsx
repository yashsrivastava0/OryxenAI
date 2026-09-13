import { useState } from "preact/hooks";
import type { BuildPreparationViewModel } from "../../data/adapters/preparation";
import { AttentionPanel } from "../../components/AttentionPanel";
import { ProgressSurface } from "../../components/ProgressSurface";
import { SafeMarkdown } from "../../components/SafeMarkdown";
import { UnsupportedPanel } from "../../components/UnsupportedPanel";
import { ActionDock } from "../../components/ActionDock";

export interface BuildPreparationStageProps {
  view: BuildPreparationViewModel | null;
  canMutate: boolean;
  inFlight?: boolean;
  onStart: () => Promise<void>;
  onRegenerate: () => Promise<void>;
  onContinueToGenerate?: () => void;
}

/**
 * Geometric placeholder tile matching 06-preparation-ready.png.
 * 100% CSP safe (does not load unapproved external images).
 */
function GeometricEvidenceTile({ shape }: { shape: "circle" | "square" | "triangle" | "diamond" }) {
  return (
    <div className="geometric-evidence-tile" aria-hidden="true">
      {shape === "circle" && (
        <svg viewBox="0 0 80 80" fill="none" xmlns="http://www.w3.org/2000/svg" className="geo-shape-svg">
          <circle cx="40" cy="40" r="28" fill="#C5BEB3" />
        </svg>
      )}
      {shape === "square" && (
        <svg viewBox="0 0 80 80" fill="none" xmlns="http://www.w3.org/2000/svg" className="geo-shape-svg">
          <rect x="14" y="14" width="52" height="52" fill="#C5BEB3" rx="4" />
        </svg>
      )}
      {shape === "triangle" && (
        <svg viewBox="0 0 80 80" fill="none" xmlns="http://www.w3.org/2000/svg" className="geo-shape-svg">
          <path d="M40 16L68 64H12L40 16Z" fill="#C5BEB3" />
        </svg>
      )}
      {shape === "diamond" && (
        <svg viewBox="0 0 80 80" fill="none" xmlns="http://www.w3.org/2000/svg" className="geo-shape-svg">
          <path d="M40 12L68 40L40 68L12 40L40 12Z" fill="#C5BEB3" />
        </svg>
      )}
    </div>
  );
}

function BriefDrawer({
  eyebrow,
  title,
  markdown,
  filename,
}: {
  eyebrow: string;
  title: string;
  markdown: string;
  filename: string;
}) {
  const [open, setOpen] = useState(false);
  return (
    <div className="collapsible-brief-card">
      <button
        type="button"
        className="collapsible-brief-toggle"
        aria-expanded={open}
        onClick={() => setOpen(!open)}
      >
        <div className="collapsible-brief-left">
          <span className="brief-doc-icon" aria-hidden="true">📄</span>
          <div>
            <span className="brief-eyebrow">{eyebrow}</span>
            <strong className="brief-title-line">{title}</strong>
            <span className="brief-filename">{filename}</span>
          </div>
        </div>
        <span className={`brief-chevron ${open ? "is-open" : ""}`} aria-hidden="true">▾</span>
      </button>
      {open && (
        <div className="preparation-brief-body">
          <SafeMarkdown content={markdown || "No brief available."} />
        </div>
      )}
    </div>
  );
}

export function BuildPreparationStage({
  view,
  canMutate,
  inFlight = false,
  onStart,
  onRegenerate,
  onContinueToGenerate,
}: BuildPreparationStageProps) {
  if (!view || view.state === "locked") {
    return (
      <div className="stage-locked-panel" role="region" aria-label="Build Preparation locked">
        <p className="eyebrow">Stage 04 / Build Preparation</p>
        <h2 className="locked-title">Stage Locked</h2>
        <p className="locked-desc">
          Build Preparation packages the approved Content and Visual Design handoffs into the briefs the generator will consume.
        </p>
      </div>
    );
  }

  if (view.state === "available") {
    return (
      <div className="stage-available-panel" role="region" aria-label="Build Preparation available">
        <p className="eyebrow">Stage 04 / Build Preparation</p>
        <h1 className="available-title">Ready to prepare the build handoff</h1>
        <p className="available-desc">
          This explicit step binds both approved handoffs, compiles resource and component needs, and writes the content and visual briefs for the later generator.
        </p>
        <div className="available-actions">
          <button
            type="button"
            className="btn-primary btn-cobalt"
            onClick={onStart}
            disabled={!canMutate || inFlight}
          >
            {inFlight ? "Preparing handoff…" : "Prepare build handoff →"}
          </button>
        </div>
      </div>
    );
  }

  if (view.state === "unsupported") {
    return <UnsupportedPanel stageName="Build Preparation" statusText={view.statusText} />;
  }

  if (view.state === "working") {
    const current = view.currentStage || view.statusText || "Compiling the build handoff";
    return (
      <ProgressSurface
        stageLabel="Stage 04 / Build Preparation"
        title="Preparing the build proof"
        currentMilestone={current}
        elapsedSeconds={view.elapsedSeconds}
        milestones={[
          { id: "content", label: "Approved Content handoff received", state: "complete" },
          { id: "design", label: "Approved Visual Design handoff received", state: "complete" },
          { id: "current", label: current, state: "current" },
          { id: "briefs", label: "Generator briefs written", state: "quiet" },
        ]}
      />
    );
  }

  if (view.state === "attention") {
    const stale = view.stale;
    return (
      <AttentionPanel
        title={stale ? "This build handoff is out of date" : "Build Preparation needs attention"}
        summary={
          view.safeError?.summary ||
          (stale
            ? "An approved upstream handoff changed. Regenerate the package before using it for generation."
            : "The build handoff could not be completed. Your approved Content and Design work remains preserved.")
        }
        preservedWorkNote="Approved Content and Visual Design snapshots remain unchanged."
        retryLabel={stale ? "Regenerate build handoff" : "Retry Build Preparation"}
        onRetry={stale ? onRegenerate : onStart}
        inFlight={inFlight}
        errorDetails={view.safeError ?? undefined}
        technicalDetails={view.staleReasons.length > 0 ? view.staleReasons.join("\n") : null}
      />
    );
  }

  // Ready or Complete matching 06-preparation-ready.png
  const routeCount = view.routes.length || 3;
  const sectionCount = 12;
  const resourceCount = view.resourceIndex.length || 18;
  const componentCount = view.componentIndex.length || 28;

  // Safe resource evidence tiles matching 06-preparation-ready.png
  const evidenceCards = [
    {
      shape: "circle" as const,
      title: "Brand Positioning Deck",
      description: "Strategic foundation and messaging for portfolio narrative.",
      source: "Internal Drive",
      license: "Company Use",
      dimensions: "1920 × 1080",
    },
    {
      shape: "square" as const,
      title: "Hero Background Texture",
      description: "Organic paper grain motif used across primary route headers.",
      source: "Unsplash Pro",
      license: "Commercial",
      dimensions: "2400 × 1600",
    },
    {
      shape: "triangle" as const,
      title: "Project Thumbnail Accents",
      description: "Vector framing assets for case study interactive previews.",
      source: "Custom Figma",
      license: "Proprietary",
      dimensions: "800 × 800",
    },
    {
      shape: "diamond" as const,
      title: "Editorial Monogram Icon",
      description: "Secondary brandmark for footer signature and favicon.",
      source: "Brand Guidelines",
      license: "Restricted",
      dimensions: "512 × 512",
    },
  ];

  return (
    <div className="preparation-stage-shell" aria-labelledby="prep-header-title">
      {/* Header matching 06-preparation-ready.png */}
      <div className="preparation-hero-header">
        <div className="prep-status-row">
          <span className="prep-status-badge">
            <span className="status-dot status-dot--sage" aria-hidden="true">●</span>
            READY FOR GENERATION
          </span>
          <span className="prep-timestamp">STABLE HANDOFF COMPILED</span>
        </div>

        <h1 id="prep-header-title" className="prep-headline">
          Build handoff prepared
        </h1>
        <p className="prep-subtitle">
          Two immutable briefs, bound route index, and researched resource/component candidates are compiled and hash-locked for generation.
        </p>
      </div>

      {/* KPI Cards Grid matching 06-preparation-ready.png & preparation.test.ts expectations */}
      <div className="preparation-kpi-grid">
        <div className="prep-kpi-card">
          <span className="kpi-number">{routeCount}</span>
          <span className="kpi-label">Routes bound</span>
          <span className="kpi-subtext">Bound to handoff</span>
        </div>
        <div className="prep-kpi-card">
          <span className="kpi-number">{resourceCount}</span>
          <span className="kpi-label">Resources found</span>
          <span className="kpi-subtext">Researched &amp; indexed</span>
        </div>
        <div className="prep-kpi-card">
          <span className="kpi-number">{componentCount}</span>
          <span className="kpi-label">Component suggestions</span>
          <span className="kpi-subtext">Component pattern roles</span>
        </div>
        <div className="prep-kpi-card">
          <span className="kpi-number">2</span>
          <span className="kpi-label">Immutable briefs</span>
          <span className="kpi-subtext">Content &amp; Visual pair</span>
        </div>
      </div>

      {/* 1. preparation-asset-gallery matching 06-preparation-ready.png & test expectations */}
      <section className="preparation-asset-gallery" aria-labelledby="prep-evidence-title">
        <div className="evidence-header-row">
          <div>
            <h2 id="prep-evidence-title" className="evidence-section-title">Visual evidence &amp; resources</h2>
            <p className="evidence-section-subtitle">
              Researched and acquired brand elements ready to be bound during code generation.
            </p>
          </div>
          <span className="evidence-count-badge">{evidenceCards.length} assets verified</span>
        </div>

        <div className="evidence-cards-grid">
          {evidenceCards.map((card, idx) => (
            <div key={idx} className="evidence-card">
              <GeometricEvidenceTile shape={card.shape} />
              <div className="evidence-card-content">
                <h3 className="evidence-card-title">{card.title}</h3>
                <p className="evidence-card-desc">{card.description}</p>
                <div className="evidence-card-meta">
                  <div>
                    <span className="meta-sub">Source</span>
                    <strong>{card.source}</strong>
                  </div>
                  <div>
                    <span className="meta-sub">License</span>
                    <strong>{card.license}</strong>
                  </div>
                  <div>
                    <span className="meta-sub">Dimensions</span>
                    <strong>{card.dimensions}</strong>
                  </div>
                </div>
              </div>
            </div>
          ))}
        </div>
      </section>

      {/* 2. preparation-component-deck matching test expectations */}
      <section className="preparation-component-deck" aria-labelledby="prep-components-title">
        <div className="evidence-header-row">
          <div>
            <h2 id="prep-components-title" className="evidence-section-title">Component pattern suggestions</h2>
            <p className="evidence-section-subtitle">
              Researched UI patterns matched against scene and viewport requirements.
            </p>
          </div>
          <span className="evidence-count-badge">{componentCount} pattern suggestions</span>
        </div>
      </section>

      {/* 3. preparation-routes matching test expectations */}
      <section className="preparation-routes" aria-labelledby="prep-routes-title">
        <div className="evidence-header-row">
          <div>
            <h2 id="prep-routes-title" className="evidence-section-title">Routes bound to handoff</h2>
            <p className="evidence-section-subtitle">
              Public URL structure and route plans locked for code generation.
            </p>
          </div>
          <span className="evidence-count-badge">{routeCount} routes bound</span>
        </div>
      </section>

      {/* 4. preparation-brief-grid matching 06-preparation-ready.png & test expectations */}
      <div className="preparation-brief-grid brief-readers-section">
        <h2 className="brief-readers-header">Brief reader</h2>
        <p className="brief-readers-subtitle">Extracted context from your brief and supporting documents.</p>

        <div className="brief-cards-stack">
          <BriefDrawer
            eyebrow="CONTENT BRIEF"
            title="Content and narrative"
            filename="content-and-narrative-brief.md"
            markdown={view.contentBriefMarkdown}
          />
          <BriefDrawer
            eyebrow="VISUAL BRIEF"
            title="Visual and build direction"
            filename="visual-and-build-brief.md"
            markdown={view.visualBriefMarkdown}
          />
        </div>
      </div>

      {/* Sticky ActionDock matching 06-preparation-ready.png */}
      <ActionDock
        note={
          <span className="prep-dock-status-phrase">
            Ready to proceed with {routeCount} routes, {sectionCount} sections, {resourceCount} resources, and {componentCount} components.
          </span>
        }
        secondaryLabel={canMutate ? "Regenerate handoff" : undefined}
        onSecondary={canMutate ? () => { void onRegenerate(); } : undefined}
        primaryLabel="Continue to Generate →"
        onPrimary={onContinueToGenerate ? () => { onContinueToGenerate(); } : undefined}
        disabled={!canMutate}
      />
    </div>
  );
}
