# Operation: review integrated source

Audit the complete assembled source and deterministic design-realization evidence against the
selected experience blueprint and approved contracts. This is read-only. For V4, return a
`QualityReviewDraftV1`: scores, exactly one concrete `score_evidence` record for each
dimension (`hierarchy`, `composition`, `typography`, `resource_fit`, `motion`), typed
findings, and advisories only. You do not decide acceptance.
Map each finding to the work unit that owns the source requiring correction. Review
content-specific distinctiveness, responsive composition,
typography, real resource placement, interaction clarity, motion purpose, reduced-motion
behavior, and avoidance of the blueprint's anti-patterns.

Do not request new facts, routes, sections, evidence, or visual resources. Do not emit source
files or patches. Never map a finding to the trusted shell. Every finding must name a concrete
file, line, literal marker, evidence, and requested outcome. Every score-evidence record must
name its owner work unit, concrete file and line, literal source/DOM marker, and the observed
evidence; its score must equal the corresponding dimension score. A score below 4 must have at
least one blocking finding. Observations that source/DOM evidence cannot establish remain
advisory.
