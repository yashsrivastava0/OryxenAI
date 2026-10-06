import { useEffect, useRef, useState } from "preact/hooks";
import type { ComponentChildren } from "preact";
import { pageContentIsEmpty, type ContentViewModel } from "../../data/adapters/content";
import { CONTENT_CARD_PREFIX, cardIdForPath } from "../../data/content-paths";
import { ArtifactSurface } from "../../components/ArtifactSurface";
import { AttentionPanel } from "../../components/AttentionPanel";
import { ContentCoverageInspector } from "../../components/ContentCoverageInspector";
import { ProgressSurface } from "../../components/ProgressSurface";
import { elapsedSince } from "../../data/generation-estimates";
import { UnsupportedPanel } from "../../components/UnsupportedPanel";
import { ActionDock } from "../../components/ActionDock";

export interface ContentStageProps {
  view: ContentViewModel | null;
  canMutate: boolean;
  onStart: () => Promise<void>;
  onApproveAndContinue: () => Promise<void>;
  onRevise: (revisionRequest: string) => Promise<void>;
  onStop?: () => Promise<void>;
  inFlight?: boolean;
  /** When set, approval also starts the portfolio build and opens the Studio. */
  approveLabel?: string;
  /** Opens the Studio (starting the build if it has not started) for an approved plan. */
  onOpenStudio?: () => Promise<void>;
  studioInFlight?: boolean;
}

export function ContentStage({
  view,
  canMutate,
  onStart,
  onApproveAndContinue,
  onRevise,
  onStop,
  inFlight = false,
  approveLabel,
  onOpenStudio,
  studioInFlight = false,
}: ContentStageProps) {

  if (!view || view.state === "locked") {
    return (
      <div className="stage-locked-panel" role="region" aria-label="Content Architect locked">
        <p className="eyebrow">Stage 02 / Content Architect</p>
        <h2 className="locked-title">Stage Locked</h2>
        <p className="locked-desc">
          Content Architect requires an approved portfolio brief from Explorer before writing your page copy.
        </p>
      </div>
    );
  }

  if (view.state === "available") {
    return (
      <div className="stage-available-panel" role="region" aria-label="Content Architect available">
        <p className="eyebrow">Stage 02 / Content Architect</p>
        <h1 className="available-title">Ready to structure portfolio content</h1>
        <p className="available-desc">
          Content Architect will consume your approved brief to write the finished copy for every section of your one-page portfolio.
        </p>
        <ActionDock primaryLabel="Start Content Architect" onPrimary={onStart} disabled={!canMutate} busy={inFlight} busyLabel="Starting Content Architect…" note="Your approved brief is ready." />
      </div>
    );
  }

  if (view.state === "unsupported") {
    return <UnsupportedPanel stageName="Content Architect" statusText={view.statusText} />;
  }

  if (view.state === "working") {
    return (
      <ProgressSurface
        stageLabel="Stage 02 / Content Architect"
        title="Structuring the content proof"
        currentMilestone={view.statusText || "Content Architect is working from the approved brief"}
        milestones={[
          { id: "brief", label: "Approved Explorer brief received", state: "complete" },
          { id: "current", label: view.statusText || "Content Architect is working", state: "current" },
        ]}
        elapsedSeconds={view.elapsedSeconds ?? elapsedSince(view.job?.createdAt)}
        estimateKind="content"
        queued={view.job?.status === "queued"}
        onStop={onStop}
        stopLabel="Stop Content Architect"
      />
    );
  }

  if (view.state === "attention") {
    return (
      <AttentionPanel
        stage="content_architect"
        title="Content Architect needs attention"
        summary={view.safeError?.summary || "Content synthesis encountered an issue and can be restarted."}
        preservedWorkNote="Your approved Explorer brief remains intact."
        retryLabel="Retry Content Architect"
        onRetry={onStart}
        errorDetails={view.safeError ?? undefined}
        job={view.job}
      />
    );
  }

  return (
    <div className="content-stage-view">
      <ContentReviewSurface
        view={view}
        canMutate={canMutate}
        onApproveAndContinue={onApproveAndContinue}
        onRevise={onRevise}
        approveLabel={approveLabel}
        onOpenStudio={onOpenStudio}
        studioInFlight={studioInFlight}
      />
    </div>
  );
}

function ContentReviewSurface({
  view,
  canMutate,
  onApproveAndContinue,
  onRevise,
  approveLabel,
  onOpenStudio,
  studioInFlight,
}: {
  view: ContentViewModel;
  canMutate: boolean;
  onApproveAndContinue: () => Promise<void>;
  onRevise: (revisionRequest: string) => Promise<void>;
  approveLabel?: string;
  onOpenStudio?: () => Promise<void>;
  studioInFlight: boolean;
}) {
  const [highlightedId, setHighlightedId] = useState<string | null>(null);
  const highlightTimer = useRef<number | undefined>(undefined);
  const isApproved = view.state === "complete";
  const page = view.pageContent;
  const empty = pageContentIsEmpty(page);

  useEffect(() => () => window.clearTimeout(highlightTimer.current), []);

  const selectPath = (path: string) => {
    const ids = new Set(
      Array.from(document.querySelectorAll(`[id^="${CONTENT_CARD_PREFIX}"]`)).map((el) => el.id),
    );
    const id = cardIdForPath(path, ids);
    if (!id) return;
    document.getElementById(id)?.scrollIntoView({ block: "center", behavior: "smooth" });
    setHighlightedId(id);
    window.clearTimeout(highlightTimer.current);
    highlightTimer.current = window.setTimeout(() => setHighlightedId(null), 2200);
  };

  const cardClass = (id: string, extra = "") =>
    `${extra} ${highlightedId === id ? "is-highlighted" : ""}`.trim();

  const pillarCount = page.systemsPractice.pillars.length;

  return (
    <ArtifactSurface
      title="Your portfolio page content"
      artifactTypeName="content plan"
      statusBadge={isApproved ? "Approved" : "Ready for review"}
      isApproved={isApproved}
      canMutate={canMutate}
      warnings={view.warnings}
      metadata={[
        { label: "Pillars", value: String(pillarCount) },
        { label: "Capability groups", value: String(page.technicalCapabilities.groups.length) },
        { label: "Links", value: String(page.connect.destinations.length) },
        { label: "Claims checked", value: String(view.claimGrounding.length) },
      ]}
      finalJsonOutput={view.agentOutput}
      approveLabel={approveLabel}
      onApproveAndContinue={empty ? undefined : onApproveAndContinue}
      nextStageName={onOpenStudio ? "Studio" : undefined}
      startNextStageLabel="Generate my portfolio"
      onStartNextStage={onOpenStudio}
      nextStageInFlight={studioInFlight}
      onRevise={onRevise}
    >
      {empty && (
        <p className="content-empty-note" role="note">
          This content has no page copy. It was likely created by an earlier version of Content
          Architect. Use Revise to regenerate it.
        </p>
      )}

      <div className="content-review-layout">
          <div className="content-review-main">
            {view.userSummary && (
              <section className="content-summary" aria-label="Summary">
                <p className="eyebrow">SUMMARY</p>
                {view.userSummary.split(/\n{2,}/).map((paragraph, index) => (
                  <p key={index}>{paragraph}</p>
                ))}
              </section>
            )}

            {!empty && (
              <>
                <FieldCard
                  id="content-card-hero"
                  className={cardClass("content-card-hero")}
                  eyebrow="HERO"
                  title={page.hero.name || "Hero"}
                >
                  <FieldList
                    rows={[
                      ["Role", [page.hero.eyebrowPrimary, page.hero.eyebrowSecondary].filter(Boolean).join(" · ")],
                      ["Headline", `${page.hero.headlinePrefix} ${page.hero.headlineEmphasis}`.trim()],
                      ["Introduction", page.hero.intro],
                      ["Location", page.hero.location],
                      ["Primary button", page.hero.primaryCtaLabel],
                      ["Secondary link", page.hero.secondaryCtaLabel],
                    ]}
                  />
                </FieldCard>

                <FieldCard
                  id="content-card-metadata"
                  className={cardClass("content-card-metadata")}
                  eyebrow="PAGE METADATA"
                  title={page.metadataTitle || "Browser title"}
                >
                  <FieldList rows={[["Description", page.metadataDescription]]} />
                </FieldCard>

                {page.marqueeKeywords.length > 0 && (
                  <FieldCard
                    id="content-card-marquee_keywords"
                    className={cardClass("content-card-marquee_keywords")}
                    eyebrow="KEYWORD TICKER"
                    title="Scrolling keywords"
                  >
                    <ul className="content-chip-list">
                      {page.marqueeKeywords.map((word, index) => (
                        <li key={index} className="content-chip">{word}</li>
                      ))}
                    </ul>
                  </FieldCard>
                )}

                <FieldCard
                  id="content-card-systems_practice"
                  className={cardClass("content-card-systems_practice")}
                  eyebrow={`SECTION 01 · ${page.systemsPractice.eyebrow || "SYSTEMS PRACTICE"}`}
                  title={page.systemsPractice.heading || "Pillars"}
                >
                  {page.systemsPractice.intro && (
                    <p className="content-card-intro">{page.systemsPractice.intro}</p>
                  )}
                  {pillarCount !== 4 && (
                    <p className="content-card-warning" role="alert">
                      The page layout needs exactly four pillars; this content has {pillarCount}.
                    </p>
                  )}
                  <ol className="content-pillar-grid">
                    {page.systemsPractice.pillars.map((pillar, index) => {
                      const id = `content-card-systems_practice.pillars.${index}`;
                      return (
                        <li key={index} id={id} className={`content-pillar-card ${cardClass(id)}`}>
                          <span className="content-pillar-index">{String(index + 1).padStart(2, "0")}</span>
                          <h4>{pillar.title}</h4>
                          <p>{pillar.description}</p>
                        </li>
                      );
                    })}
                  </ol>
                </FieldCard>

                <FieldCard
                  id="content-card-technical_capabilities"
                  className={cardClass("content-card-technical_capabilities")}
                  eyebrow={`SECTION 02 · ${page.technicalCapabilities.eyebrow || "TECHNICAL CAPABILITIES"}`}
                  title={page.technicalCapabilities.heading || "Capabilities"}
                >
                  {page.technicalCapabilities.intro && (
                    <p className="content-card-intro">{page.technicalCapabilities.intro}</p>
                  )}
                  <div className="content-capability-groups">
                    {page.technicalCapabilities.groups.map((group, index) => {
                      const id = `content-card-technical_capabilities.groups.${index}`;
                      return (
                        <div key={index} id={id} className={`content-capability-group ${cardClass(id)}`}>
                          <h4>{group.heading}</h4>
                          <ul className="content-chip-list">
                            {group.items.map((item, itemIndex) => (
                              <li key={itemIndex} className="content-chip">{item}</li>
                            ))}
                          </ul>
                        </div>
                      );
                    })}
                  </div>
                </FieldCard>

                <FieldCard
                  id="content-card-professional_context"
                  className={cardClass("content-card-professional_context")}
                  eyebrow={`SECTION 03 · ${page.professionalContext.eyebrow || "PROFESSIONAL CONTEXT"}`}
                  title={page.professionalContext.heading || "Context"}
                >
                  {page.professionalContext.intro && (
                    <p className="content-card-intro">{page.professionalContext.intro}</p>
                  )}
                  {page.professionalContext.organizations.length > 0 ? (
                    <ul className="content-chip-list">
                      {page.professionalContext.organizations.map((org, index) => {
                        const id = `content-card-professional_context.organizations.${index}`;
                        return (
                          <li key={index} id={id} className={`content-chip content-org-chip ${cardClass(id)}`}>
                            {org}
                          </li>
                        );
                      })}
                    </ul>
                  ) : (
                    <p className="content-card-muted">No organizations were named in the profile.</p>
                  )}
                </FieldCard>

                <FieldCard
                  id="content-card-connect"
                  className={cardClass("content-card-connect")}
                  eyebrow={`SECTION 04 · ${page.connect.eyebrow || "CONNECT"}`}
                  title={page.connect.heading || "Connect"}
                >
                  {page.connect.intro && <p className="content-card-intro">{page.connect.intro}</p>}
                  {page.connect.destinations.length > 0 ? (
                    <ul className="content-destination-list">
                      {page.connect.destinations.map((destination, index) => {
                        const id = `content-card-connect.destinations.${index}`;
                        return (
                          <li key={index} id={id} className={`content-destination-item ${cardClass(id)}`}>
                            <span className="content-destination-label">{destination.label}</span>
                            <span className="content-destination-url">{destination.url}</span>
                            {destination.featured && (
                              <span className="content-badge content-badge--featured">Featured</span>
                            )}
                          </li>
                        );
                      })}
                    </ul>
                  ) : (
                    <p className="content-card-muted">No public links were supplied.</p>
                  )}
                </FieldCard>

                {page.atlas.aboutHeading && (
                  <FieldCard id="content-card-atlas" className={cardClass("content-card-atlas")} eyebrow="COBALT ATLAS · ADDITIONAL PAGES" title="About and selected work">
                    <h4>{page.atlas.aboutHeading}</h4>
                    <p>{page.atlas.aboutIntro}</p>
                    {page.atlas.aboutQuote && <blockquote>{page.atlas.aboutQuote}</blockquote>}
                    {page.atlas.experience.map((row, index) => <p key={`role-${index}`}><strong>{row.role}</strong> · {row.organization} · {row.dates}<br />{row.description}</p>)}
                    {page.atlas.education.map((row, index) => <p key={`education-${index}`}><strong>{row.credential}</strong> · {row.institution} · {row.dates}</p>)}
                    {page.atlas.statistics.map((row, index) => <p key={`stat-${index}`}><strong>{row.value}</strong> · {row.label}</p>)}
                    {page.atlas.projects.length === 0 && <p className="content-card-muted">The portfolio will show a designed Work area until a project is added.</p>}
                    {page.atlas.projects.map((project, index) => (
                      <div key={`project-${index}`} className="content-capability-group">
                        <h4>{project.title} {project.kind === "illustrative" && <span className="content-badge">Illustrative concept — not real client work</span>}</h4>
                        <p>{project.summary}</p>
                        {project.role && <p>Role: {project.role}</p>}
                        {project.period && <p>Period: {project.period}</p>}
                        {project.problem && <p>Problem: {project.problem}</p>}
                        {project.approach && <p>Approach: {project.approach}</p>}
                        {project.outcome && <p>Outcome: {project.outcome}</p>}
                        {project.externalUrl && <p>Link: {project.externalUrl}</p>}
                      </div>
                    ))}
                  </FieldCard>
                )}
              </>
            )}

            {view.decisionBasis.length > 0 && (
              <details className="content-decisions">
                <summary>How these choices were made</summary>
                <ul>
                  {view.decisionBasis.map((decision, index) => (
                    <li key={index}>
                      <strong>{decision.decision.replaceAll("_", " ")}:</strong> {decision.value}{" "}
                      <span className="content-badge">{decision.basis.replaceAll("_", " ")}</span>
                      {decision.rationale && <p>{decision.rationale}</p>}
                    </li>
                  ))}
                </ul>
              </details>
            )}
          </div>

          <ContentCoverageInspector
            claims={view.claimGrounding}
            coverage={view.coverageLedger}
            unresolvedIssues={view.unresolvedIssues}
            omissions={view.omissions}
            onSelectPath={selectPath}
          />
        </div>
    </ArtifactSurface>
  );
}

function FieldCard({
  id,
  className,
  eyebrow,
  title,
  children,
}: {
  id: string;
  className: string;
  eyebrow: string;
  title: string;
  children: ComponentChildren;
}) {
  return (
    <section id={id} className={`content-section-card ${className}`}>
      <p className="eyebrow">{eyebrow}</p>
      <h3>{title}</h3>
      {children}
    </section>
  );
}

function FieldList({ rows }: { rows: Array<[string, string]> }) {
  const visible = rows.filter(([, value]) => value.trim());
  if (!visible.length) return null;
  return (
    <dl className="content-field-list">
      {visible.map(([label, value]) => (
        <div key={label} className="content-field-row">
          <dt>{label}</dt>
          <dd>{value}</dd>
        </div>
      ))}
    </dl>
  );
}
