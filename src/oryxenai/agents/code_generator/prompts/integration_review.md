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

Treat `trusted_build_runtime` as host authority. In this Vite scaffold, admitted
`/resources/pack/` URLs in source CSS are deliberately root-public inputs and `base: "./"`
rewrites them to mount-safe relative URLs in the built CSS. Build/runtime verification checks
the resulting artifacts; do not lower `resource_fit` from the source prefix alone. Blocking
findings may target only non-terminal work units from `work_graph`; host-owned foundation and
trusted-shell observations remain advisory.

Do not request new facts, routes, sections, evidence, or visual resources. Do not emit source
files or patches. Never map a finding to the trusted shell. Every finding must name a concrete
file, line, literal marker, evidence, and requested outcome. Every score-evidence record must
name its owner work unit, concrete file and line, literal source/DOM marker, and the observed
evidence; its score must equal the corresponding dimension score. A score below 4 must have at
least one blocking finding on the same owner and file as that dimension's score evidence, so
the bounded polish pass receives the defect that caused the low score. Every evidence `file`
must be an exact key in `assembled_source`, and every `marker` must be copied literally from that
file. Give the best one-based source line for the marker. The host deterministically stamps the
exact line from the literal marker, using your approximate line to disambiguate repeated markers.
Prefer a longer unique marker whenever possible. Observations that source/DOM evidence cannot
establish remain advisory and must not lower a dimension below 4.
