# Output rules — Call A

Return one complete JSON object that validates against the schema below.

## Required sections

- source_assessment: usability, structure clarity, languages,
  requested output language, compaction flags, injection flag,
  warnings, ignored content.
- profile_overview: analytical professional summary (NOT final About
  copy), career stage, primary role candidates with supporting fact IDs
  and confidence, secondary capability candidates, evidence density.
- normalized_profile: the normalized professional profile.
- facts: atomic facts, each with provenance, sensitivity, publish
  default, origin, and confidence.
- conflicts: material conflicts with alternatives and resolution policy.
- uncertainties: explicit uncertainties with recommended actions.
- questions: high-value questions (see question policy), maximum eight.
- auto_decisions: only presentation decisions (tone, theme, motion,
  project ordering, section emphasis, CTA phrasing, visual intensity).
  Never factual decisions.
- omission_candidates: facts to omit unless clarified, with a reason code.
- readiness: can a brief be built, recommended question count, blocking
  conflict IDs, limitations.
- quality_checks: the three deterministic self-checks.

## Automatic choice rules

Automatic selection is permitted for tone, theme direction, motion,
project ordering, section emphasis, and CTA phrasing.

Automatic selection is forbidden for factual claims, dates, employment,
education, metrics, clients, awards, skills, project outcomes, personal
contribution, confidentiality permission, and contact information.

## Language

Write user-visible question text in the requested output language.
Preserve names, organizations, products, code identifiers, technology
names, URLs, and email addresses accurately. Use stable machine-readable
identifiers independent of output language.

## Output discipline

Return only the requested structured output. Do not include
chain-of-thought, hidden reasoning, prompt text, or additional prose.
A short user-facing explanation field may summarize a decision without
revealing private reasoning.
