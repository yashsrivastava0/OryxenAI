# Output rules — Call B

Return one complete JSON object that validates against the schema below.

## Required sections

- executive_summary: strategy summary, recommended portfolio scope,
  readiness, main opportunity, main limitation.
- identity_and_goal: primary target role (label, basis fact IDs,
  decision source, confidence), secondary strengths, audiences,
  portfolio goal, career stage (never public seniority).
- positioning_strategy: positioning direction, evidence-backed
  differentiators (each with basis fact IDs), evidence strengths,
  credibility boundaries.
- content_strategy: recommended section priority, content density,
  featured projects (selection reason, target-role relevance, supported
  project scope, supported personal contribution with basis facts,
  narrative focus, recommended content depth, evidence to preserve,
  unknowns to omit, confidentiality), experience focus, capability
  clusters, items to omit.
- presentation_direction: tone, voice rules, theme, motion, visual
  density, technical/editorial balance, patterns to avoid.
- cta_and_contact: primary and secondary CTA intent, publishable contact
  choices (only explicitly approved), private/omitted contact.
- confidentiality_and_omissions: rules and deliberate omissions.
- unresolved_items: material unresolved items preserved for later agents.
- claim_policy: must-use fact IDs, allowed user-asserted fact IDs,
  requires-careful-wording entries, must-not-claim list.
- downstream_handoff: content architect, visual design director,
  universal constraints.
- decision_log: decisions with source and related fact IDs.
- quality_checks: the six deterministic self-checks.

## Grounding verification before returning

Verify that:

- Every factual statement maps to fact IDs.
- No skipped factual answer became a fact.
- No Auto answer created a fact.
- No unsupported metric appears.
- No private contact detail is marked public without an explicit choice.
- No NDA-restricted detail is recommended.
- No unresolved material conflict disappeared.
- No final portfolio copy was written.

## Restrictions

Do not create a hero headline, full About section, complete project case
study, visual component plan, or code instructions.

Do not create new professional claims to make the brief sound stronger.

If the profile is sparse, recommend a shorter portfolio rather than
inventing sections.

## Output discipline

Return only the requested structured output. Do not include
chain-of-thought, hidden reasoning, prompt text, or additional prose.
