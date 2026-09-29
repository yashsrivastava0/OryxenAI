import { useEffect, useState } from "preact/hooks";
import type {
  DiscoveryDossierVM,
  DiscoveryQuestionHistoryVM,
  DiscoverySourceDocumentVM,
} from "../data/adapters/discovery";

export interface DiscoveryEvidenceInspectorProps {
  dossier: DiscoveryDossierVM | null;
  sourceDocuments: DiscoverySourceDocumentVM[];
  questionHistory: DiscoveryQuestionHistoryVM[];
}

function humanize(value: string): string {
  return value.replaceAll("_", " ").replace(/\b\w/g, (letter) => letter.toUpperCase());
}

export function DiscoveryEvidenceInspector({
  dossier,
  sourceDocuments,
  questionHistory,
}: DiscoveryEvidenceInspectorProps) {
  const [selectedSpanId, setSelectedSpanId] = useState<string | null>(null);

  useEffect(() => {
    if (!selectedSpanId) return;
    document.getElementById(`discovery-source-span-${encodeURIComponent(selectedSpanId)}`)?.scrollIntoView({
      block: "nearest",
      behavior: "smooth",
    });
  }, [selectedSpanId]);

  const sourceSpanLabels = new Map<string, string>();
  for (const source of sourceDocuments) {
    source.spans.forEach((span, index) => {
      sourceSpanLabels.set(span.id, `${source.label || "Source"} · ${index + 1}`);
    });
  }
  const sourceSpanIds = new Set(sourceSpanLabels.keys());
  const factCount = dossier?.facts.length ?? 0;
  const coverageCount = dossier?.sourceCoverage.length ?? 0;
  const coverageWithoutExcerpt = dossier?.sourceCoverage.filter((item) => !sourceSpanIds.has(item.spanId)) ?? [];

  const sourceLinks = (refs: string[]) => {
    if (!refs.length) {
      return <span className="discovery-evidence-unlinked">No source reference recorded</span>;
    }
    return (
      <div className="discovery-source-links" aria-label="Source references">
        {refs.map((ref) => sourceSpanIds.has(ref) ? (
          <button
            key={ref}
            type="button"
            className={`discovery-source-link ${selectedSpanId === ref ? "is-selected" : ""}`}
            onClick={() => setSelectedSpanId(ref)}
            aria-label={`Open source span ${ref} (${sourceSpanLabels.get(ref)})`}
            title={ref}
          >
            {sourceSpanLabels.get(ref)}
          </button>
        ) : (
          <span key={ref} className="discovery-evidence-unlinked" title="No matching source span is available in this state">
            Unresolved source reference: {ref}
          </span>
        ))}
      </div>
    );
  };

  return (
    <aside className="discovery-evidence-inspector" aria-labelledby="discovery-evidence-heading">
      <div className="discovery-inspector-heading">
        <div>
          <p className="eyebrow">DISCOVERY / REVIEW BASIS</p>
          <h2 id="discovery-evidence-heading">Evidence inspector</h2>
        </div>
        {dossier && <span className="discovery-contract-tag">{dossier.contractVersion}</span>}
      </div>

      {dossier ? (
        <>
          <p className="discovery-inspector-summary">
            {factCount} recorded {factCount === 1 ? "claim" : "claims"} · {coverageCount} source-span dispositions
          </p>

          {(dossier.intent.goal || dossier.intent.audience || dossier.intent.visitorAction || dossier.intent.language || dossier.intent.preferences.length > 0 || dossier.subject.name || dossier.subject.currentTitle || dossier.subject.location || dossier.subject.links.length > 0 || dossier.userChoices.length > 0) && (
            <section className="discovery-inspector-section" aria-labelledby="discovery-intent-heading">
              <h3 id="discovery-intent-heading">Purpose and preferences</h3>
              <dl className="discovery-intent-list">
                {dossier.intent.goal && <div><dt>Goal</dt><dd>{dossier.intent.goal}{sourceLinks(dossier.intent.basisRefs.goal ?? [])}</dd></div>}
                {dossier.intent.audience && <div><dt>Audience</dt><dd>{dossier.intent.audience}{sourceLinks(dossier.intent.basisRefs.audience ?? [])}</dd></div>}
                {dossier.intent.visitorAction && <div><dt>Desired visitor action</dt><dd>{dossier.intent.visitorAction}{sourceLinks(dossier.intent.basisRefs.visitor_action ?? [])}</dd></div>}
                {dossier.intent.language && <div><dt>Language</dt><dd>{dossier.intent.language}{sourceLinks(dossier.intent.basisRefs.language ?? [])}</dd></div>}
                {dossier.intent.preferences.length > 0 && <div><dt>Preferences</dt><dd>{dossier.intent.preferences.join(" · ")}{sourceLinks(dossier.intent.basisRefs.preferences ?? [])}</dd></div>}
                {dossier.subject.name && <div><dt>Subject</dt><dd>{dossier.subject.name}</dd></div>}
                {dossier.subject.currentTitle && <div><dt>Current title</dt><dd>{dossier.subject.currentTitle}</dd></div>}
                {dossier.subject.location && <div><dt>Location</dt><dd>{dossier.subject.location}</dd></div>}
                {dossier.subject.links.map((link, index) => <div key={`${link.label}-${index}`}><dt>{link.label || "Link"}</dt><dd>{link.url}</dd></div>)}
                {dossier.subject.sourceRefs.length > 0 && <div><dt>Identity evidence</dt><dd>{sourceLinks(dossier.subject.sourceRefs)}</dd></div>}
                {dossier.userChoices.length > 0 && <div><dt>User choices</dt><dd>{dossier.userChoices.join(" · ")}</dd></div>}
              </dl>
            </section>
          )}

          <section className="discovery-inspector-section" aria-labelledby="discovery-claims-heading">
            <h3 id="discovery-claims-heading">Claims and evidence</h3>
            {dossier.facts.length ? (
              <ul className="discovery-inspector-list">
                {dossier.facts.map((fact, index) => (
                  <li className="discovery-evidence-entry" key={fact.id || `fact-${index}`}>
                    <div className="discovery-evidence-entry-meta">
                      <span className={`evidence-status evidence-status--${fact.status}`}>{humanize(fact.status)}</span>
                      <span className="evidence-ownership">{humanize(fact.ownership)} ownership</span>
                    </div>
                    <p className="discovery-evidence-statement">{fact.statement || fact.originalWording || "Claim text not provided."}</p>
                    {fact.originalWording && fact.statement && fact.originalWording !== fact.statement && (
                      <details className="discovery-original-wording">
                        <summary>Original wording</summary>
                        <blockquote>{fact.originalWording}</blockquote>
                      </details>
                    )}
                    {fact.qualifiers.length > 0 && (
                      <p className="discovery-evidence-qualifiers">Qualifiers: {fact.qualifiers.join(" · ")}</p>
                    )}
                    {sourceLinks(fact.sourceRefs)}
                  </li>
                ))}
              </ul>
            ) : (
              <p className="discovery-inspector-empty">No structured claims were recorded in this dossier.</p>
            )}

            {[
              { title: "Roles", items: dossier.roles },
              { title: "Projects", items: dossier.projects },
              { title: "Other evidence", items: dossier.otherEvidence },
            ].filter((group) => group.items.length > 0).map((group) => (
              <details className="discovery-evidence-group" key={group.title}>
                <summary>{group.title} <span>{group.items.length}</span></summary>
                <ul className="discovery-inspector-list">
                  {group.items.map((item, index) => (
                    <li className="discovery-evidence-entry" key={item.id || `${group.title}-${index}`}>
                      <strong>{item.title || "Untitled evidence"}</strong>
                      {item.category && <span className="evidence-category">{humanize(item.category)}</span>}
                      {item.details.length ? item.details.map((detail, detailIndex) => (
                        <p className="discovery-evidence-detail" key={`${detail.label}-${detailIndex}`}>
                          <strong>{detail.label}:</strong> {detail.value}
                        </p>
                      )) : item.detail && <p className="discovery-evidence-statement">{item.detail}</p>}
                      {item.factIds.length > 0 && <p className="discovery-evidence-qualifiers">Claims: {item.factIds.join(", ")}</p>}
                      {sourceLinks(item.sourceRefs)}
                    </li>
                  ))}
                </ul>
              </details>
            ))}
          </section>

          <section className="discovery-inspector-section" aria-labelledby="discovery-gaps-heading">
            <h3 id="discovery-gaps-heading">Open gaps</h3>
            {dossier.openItems.length ? (
              <ul className="discovery-inspector-list">
                {dossier.openItems.map((item, index) => (
                  <li className="discovery-gap-entry" key={item.id || `gap-${index}`}>
                    <div className="discovery-evidence-entry-meta">
                      <span className="evidence-status evidence-status--open">{humanize(item.status)}</span>
                      <span className="evidence-ownership">{humanize(item.importance)} importance</span>
                    </div>
                    <p>{item.detail || "Gap details were not supplied."}</p>
                    {item.safeWording && <p className="discovery-gap-safe-wording"><strong>Safe wording:</strong> {item.safeWording}</p>}
                    {item.affectedIds.length > 0 && <p className="discovery-evidence-qualifiers">Related items: {item.affectedIds.join(", ")}</p>}
                    {sourceLinks(item.sourceRefs)}
                  </li>
                ))}
              </ul>
            ) : (
              <p className="discovery-inspector-empty">No open gaps are recorded.</p>
            )}
          </section>

          {dossier.restrictions.length > 0 && (
            <section className="discovery-inspector-section" aria-labelledby="discovery-restrictions-heading">
              <h3 id="discovery-restrictions-heading">Restrictions and exclusions</h3>
              <ul className="discovery-inspector-list">
                {dossier.restrictions.map((item, index) => (
                  <li className="discovery-evidence-entry" key={item.id || `restriction-${index}`}>
                    <div className="discovery-evidence-entry-meta">
                      <span className="evidence-status">{humanize(item.disposition)}</span>
                      {item.scope && <span className="evidence-ownership">{humanize(item.scope)}</span>}
                    </div>
                    <p className="discovery-evidence-statement">{item.instruction || "Restriction detail not provided."}</p>
                    {sourceLinks(item.sourceRefs)}
                  </li>
                ))}
              </ul>
            </section>
          )}

          <section className="discovery-inspector-section" aria-labelledby="discovery-coverage-heading">
            <h3 id="discovery-coverage-heading">Source coverage</h3>
            {sourceDocuments.length ? sourceDocuments.map((source) => (
              <div className="discovery-source-document" key={source.id}>
                <div className="discovery-source-document-heading">
                  <strong>{source.label || source.id}</strong>
                  <span>{humanize(source.sourceKind || source.format)}</span>
                </div>
                {source.spans.length ? (
                  <ol className="discovery-source-span-list">
                    {source.spans.map((span, index) => (
                      <li
                        id={`discovery-source-span-${encodeURIComponent(span.id)}`}
                        key={span.id || `${source.id}-span-${index}`}
                        className={`discovery-source-span ${selectedSpanId === span.id ? "is-selected" : ""}`}
                      >
                        <div className="discovery-source-span-meta">
                          <span>{span.disposition ? humanize(span.disposition) : "No disposition recorded"}</span>
                          <span>{span.start}–{span.end}</span>
                        </div>
                        <blockquote>{span.excerpt || "No excerpt available for this span."}</blockquote>
                        {span.reason && <p>{span.reason}</p>}
                        {span.factIds.length > 0 && <p className="discovery-evidence-qualifiers">Claims: {span.factIds.join(", ")}</p>}
                      </li>
                    ))}
                  </ol>
                ) : source.originalText ? (
                  <div className="discovery-source-without-spans">
                    <p>No span-level coverage was recorded for this source.</p>
                    <blockquote>{source.originalText}</blockquote>
                  </div>
                ) : (
                  <p className="discovery-inspector-empty">Source text is not available in this saved state.</p>
                )}
              </div>
            )) : (
              <p className="discovery-inspector-empty">
                This saved brief has no source documents, so its claims cannot be linked back to excerpts.
              </p>
            )}
            {coverageWithoutExcerpt.length > 0 && (
              <ul className="discovery-source-span-list" aria-label="Coverage records without a saved source excerpt">
                {coverageWithoutExcerpt.map((item, index) => (
                  <li className="discovery-source-span" key={item.spanId || `coverage-${index}`}>
                    <div className="discovery-source-span-meta">
                      <span>{humanize(item.disposition)}</span>
                      <span>{item.spanId || "Source span id unavailable"}</span>
                    </div>
                    <p>{item.reason || "This coverage record has no matching saved source excerpt."}</p>
                    {item.factIds.length > 0 && <p className="discovery-evidence-qualifiers">Claims: {item.factIds.join(", ")}</p>}
                  </li>
                ))}
              </ul>
            )}
          </section>

          <section className="discovery-inspector-section" aria-labelledby="discovery-question-history-heading">
            <h3 id="discovery-question-history-heading">Clarification history</h3>
            {questionHistory.length ? (
              <ol className="discovery-question-history">
                {questionHistory.map((event, index) => (
                  <li key={event.questionId || `question-${index}`}>
                    <div className="discovery-evidence-entry-meta">
                      <span>{humanize(event.status)}</span>
                      {event.gapId && <span className="evidence-ownership">Gap {event.gapId}</span>}
                    </div>
                    <p className="discovery-evidence-statement">{event.question || "Question text unavailable."}</p>
                    {event.reason && <p>{event.reason}</p>}
                    {event.answerHistory.length > 0 ? (
                      <details className="discovery-answer-revisions">
                        <summary>Answer history ({event.answerHistory.length})</summary>
                        <ol>
                          {event.answerHistory.map((revision) => (
                            <li key={`${event.questionId}-${revision.revision}`}>
                              <span className="evidence-status">Revision {revision.revision} · {humanize(revision.status)}</span>
                              {revision.answer && <blockquote>{revision.answer}</blockquote>}
                              {sourceLinks(revision.sourceRefs)}
                            </li>
                          ))}
                        </ol>
                      </details>
                    ) : event.answer && <blockquote>{event.answer}</blockquote>}
                    {event.affectedIds.length > 0 && <p className="discovery-evidence-qualifiers">Related items: {event.affectedIds.join(", ")}</p>}
                  </li>
                ))}
              </ol>
            ) : (
              <p className="discovery-inspector-empty">No clarification history is recorded for this brief.</p>
            )}
          </section>
        </>
      ) : (
        <div className="discovery-legacy-evidence-note">
          <strong>Source links are unavailable for this saved brief.</strong>
          <p>This brief predates the structured evidence record. The workspace does not infer citations or claim provenance from its text.</p>
          {sourceDocuments.length > 0 && (
            <div className="discovery-inspector-section">
              <h3>Saved source material</h3>
              {sourceDocuments.map((source) => (
                <details className="discovery-source-document" key={source.id}>
                  <summary>{source.label || source.id}</summary>
                  {source.spans.length ? source.spans.map((span) => (
                    <blockquote key={span.id}>{span.excerpt || source.originalText.slice(span.start, span.end)}</blockquote>
                  )) : <blockquote>{source.originalText || "Source text is unavailable."}</blockquote>}
                </details>
              ))}
            </div>
          )}
          {questionHistory.length > 0 && (
            <div className="discovery-inspector-section">
              <h3>Clarification history</h3>
              <ol className="discovery-question-history">
                {questionHistory.map((event, index) => (
                  <li key={event.questionId || `legacy-question-${index}`}>
                    <strong>{event.question || "Question text unavailable."}</strong>
                    <p>{event.answer || humanize(event.status)}</p>
                  </li>
                ))}
              </ol>
            </div>
          )}
        </div>
      )}
    </aside>
  );
}
