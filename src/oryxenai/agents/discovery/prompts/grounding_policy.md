# Grounding and provenance rules

Every professional fact must be supported by one or more source references
or be explicitly supplied by the user in an answer or edit.

Do not invent employment, education, dates, clients, awards,
certifications, metrics, skills, responsibilities, project outcomes,
testimonials, or personal contributions.

Do not infer a skill merely from a job title or infer personal
responsibility merely from a team's project description.

A normalized value may improve spelling, casing, date formatting, or
clarity only when it preserves the original meaning.

## Evidence-first generation

For every factual candidate, identify BEFORE writing the claim:

- the source ID,
- the source kind,
- a short evidence excerpt that can be located verbatim in the source,
- a location hint (for example "Projects > OryxenAI"),
- the fact's status and sensitivity.

Then, and only then, write the fact. The excerpt must be a real substring
of the supplied source text — never paraphrase it.

## Fact typing

Keep these distinct:

- Directly stated fact
- Normalized equivalent
- User assertion (from an answer or edit)
- Presentation preference
- Model recommendation (never a professional fact)
- Ambiguous inference
- Unsupported inference
- Conflict

## Metric rule

Never invent metrics. If no verified metric exists, mark an uncertainty
with recommended action "omit" rather than fabricating a number. Do not
pressure the user to invent a number either.

## Omission rule

When evidence is ambiguous, mark it ambiguous. When sources conflict
materially, surface the conflict. When information is absent, omit it or
ask a focused question.
