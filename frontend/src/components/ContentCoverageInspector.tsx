import { useState } from "preact/hooks";
import type { ClaimGroundingVM, CoverageEntryVM } from "../data/adapters/content";

export const COVERAGE_DISPOSITIONS: Array<{ id: string; label: string; hint: string }> = [
  { id: "used", label: "Used", hint: "Appears in the page copy" },
  { id: "condensed", label: "Condensed", hint: "Shortened or merged into the copy" },
  { id: "retained_internally", label: "Kept internal", hint: "Not needed on this page" },
  { id: "excluded_by_restriction", label: "Excluded by restriction", hint: "A stated restriction applies" },
  { id: "excluded_editorially", label: "Left out editorially", hint: "Considered and not used" },
  { id: "unresolved", label: "Unresolved", hint: "A gap or conflict prevents safe use" },
];

export interface ContentCoverageInspectorProps {
  claims: ClaimGroundingVM[];
  coverage: CoverageEntryVM[];
  unresolvedIssues: string[];
  omissions: string[];
  /** Called with a field path (for example "hero.intro") when a chip is clicked. */
  onSelectPath?: (path: string) => void;
}

function humanize(value: string): string {
  return value.replaceAll("_", " ").replace(/\b\w/g, (letter) => letter.toUpperCase());
}

export function ContentCoverageInspector({
  claims,
  coverage,
  unresolvedIssues,
  omissions,
  onSelectPath,
}: ContentCoverageInspectorProps) {
  const [selectedPath, setSelectedPath] = useState<string | null>(null);

  const pathChips = (paths: string[]) => {
    if (!paths.length) return <span className="content-coverage-unlinked">Not shown on the page</span>;
    return (
      <div className="content-coverage-paths" aria-label="Page fields">
        {paths.map((path) => (
          <button
            key={path}
            type="button"
            className={`content-path-chip ${selectedPath === path ? "is-selected" : ""}`}
            onClick={() => {
              setSelectedPath(path);
              onSelectPath?.(path);
            }}
            title={`Show ${path} in the review`}
          >
            {path}
          </button>
        ))}
      </div>
    );
  };

  const known = new Set(COVERAGE_DISPOSITIONS.map((d) => d.id));
  const groups = [
    ...COVERAGE_DISPOSITIONS,
    ...(coverage.some((entry) => !known.has(entry.disposition))
      ? [{ id: "other", label: "Other", hint: "" }]
      : []),
  ];

  return (
    <aside className="content-coverage-inspector" aria-labelledby="content-coverage-heading">
      <div className="content-coverage-heading">
        <p className="eyebrow">CONTENT / REVIEW BASIS</p>
        <h2 id="content-coverage-heading">Evidence and coverage</h2>
      </div>

      <section className="content-coverage-section">
        <h3>Claims on the page ({claims.length})</h3>
        {claims.length === 0 ? (
          <p className="content-coverage-empty">No individual claims needed grounding.</p>
        ) : (
          <ul className="content-coverage-list">
            {claims.map((claim) => (
              <li key={claim.claimId} className="content-claim-entry">
                <div className="content-claim-badges">
                  <span className={`content-badge content-badge--publication-${claim.publicationStatus}`}>
                    {humanize(claim.publicationStatus)}
                  </span>
                  <span className={`content-badge content-badge--evidence-${claim.evidenceStatus}`}>
                    {humanize(claim.evidenceStatus)}
                  </span>
                  <span className="content-badge">{humanize(claim.ownership)}</span>
                </div>
                <p className="content-claim-statement">{claim.statement || claim.claimId}</p>
                {claim.confidenceOrWarning && (
                  <p className="content-claim-note">{claim.confidenceOrWarning}</p>
                )}
                {pathChips(claim.fieldPaths)}
              </li>
            ))}
          </ul>
        )}
      </section>

      <section className="content-coverage-section">
        <h3>Source coverage ({coverage.length})</h3>
        {coverage.length === 0 ? (
          <p className="content-coverage-empty">No coverage ledger was recorded for this content.</p>
        ) : (
          groups.map((group) => {
            const entries = coverage.filter((entry) =>
              group.id === "other" ? !known.has(entry.disposition) : entry.disposition === group.id,
            );
            if (!entries.length) return null;
            return (
              <details key={group.id} className="content-coverage-group" open={group.id === "used"}>
                <summary>
                  {group.label} <span>{entries.length}</span>
                </summary>
                {group.hint && <p className="content-coverage-hint">{group.hint}</p>}
                <ul className="content-coverage-list">
                  {entries.map((entry) => (
                    <li key={entry.sourceId} className="content-coverage-entry">
                      <code>{entry.sourceId}</code>
                      {entry.reason && <p className="content-claim-note">{entry.reason}</p>}
                      {entry.fieldPaths.length > 0 && pathChips(entry.fieldPaths)}
                    </li>
                  ))}
                </ul>
              </details>
            );
          })
        )}
      </section>

      {(unresolvedIssues.length > 0 || omissions.length > 0) && (
        <section className="content-coverage-section">
          <h3>Open points</h3>
          {unresolvedIssues.length > 0 && (
            <>
              <p className="content-coverage-hint">Needs your attention</p>
              <ul className="content-coverage-bullets">
                {unresolvedIssues.map((issue, index) => (
                  <li key={index}>{issue}</li>
                ))}
              </ul>
            </>
          )}
          {omissions.length > 0 && (
            <>
              <p className="content-coverage-hint">Deliberately left out</p>
              <ul className="content-coverage-bullets">
                {omissions.map((item, index) => (
                  <li key={index}>{item}</li>
                ))}
              </ul>
            </>
          )}
        </section>
      )}
    </aside>
  );
}
