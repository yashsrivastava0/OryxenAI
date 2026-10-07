<atlas_pages>
The selected theme renders the Atlas page set (About, selected work and case pages).
Write the normal complete page_content tree AND page_content.atlas for the same person. The Atlas fields are visitor-facing
approved copy, subject to the same source restrictions and claim grounding, except
for the marked assumptions allowed by the sparse input policy below.

atlas.about_heading and atlas.about_intro are required. They describe the
person using only the approved dossier. atlas.about_quote is optional original
positioning copy, never a fabricated testimonial.

Real rows (kind="real", the default) are written only from supplied facts: experience
rows with role/organization/dates/description, education rows with
credential/institution/dates, statistics only for grounded, approved numerical claims.
Never manufacture years, percentages, clients, degrees, employers, or results into a
real row.

atlas.projects contains at most three featured projects, ordered by relevance
and evidence. A real project needs a truthful title and summary. Its problem,
approach and outcome can be empty when not supplied; a case-study route is only
made when problem and approach are sufficiently specific. Keep external_url
empty unless the dossier supplies an approved project URL. Set kind="real".

If allow_illustrative_work is true and there is no usable real project, you may
write ONE profession-tailored hypothetical project with kind="illustrative".
Use a plausible hypothetical problem and proposed approach. Do not invent a
client, employer, personal achievement, actual implementation, or measured
result. Leave outcome empty. The rendered card and case page will explicitly
identify it as an illustrative concept. If opt-in is false, do not add a
fictional project. Optional missing sections are omitted in the layout.

<sparse_input_policy>
The page must never look bare. After writing every real row the dossier supports, top up
thin sections with assumed rows marked kind="sample". This policy overrides any
sparse-profile or no-invention guidance elsewhere in these instructions, for sample
rows only. The host prints "Sample content — replace with your own details." in the
heading of every section that contains a sample row, so a visitor can never mistake an
assumption for a verified fact. Targets (counting real rows first):
- statistics: if fewer than 3 rows, add sample statistics up to 3.
- experience: if empty, add 1-2 sample rows (for a student or career changer, an
  internship, project role or volunteer role fits the stated goals).
- education: if empty, add 1 sample row.
Rules:
- Real supplied facts always win: never replace, contradict or duplicate a real row, and
  never mix assumed detail into a real row.
- Base each assumed row on the person's stated role, skills and goals: what a typical
  person in that position plausibly has. Use generic role-typical wording (for example
  role "Backend Intern", organization "A technology team", dates "Summer 2025"), never
  a named real employer, school, client, award or publication.
- A sample statistic is a modest, round, plausible figure for that role with a plain
  label (for example value "3", label "Projects built"). Never attach it to a named
  client or employer, and never claim a result a real person would be quoted on.
- Never write a testimonial, endorsement, certification number or URL.
- Sample rows are not dossier facts: do not enter them in claim_grounding or the
  coverage ledger. The host lists every assumed row for the owner to review.
- A section whose real rows already meet its target gets no sample rows.
</sparse_input_policy>

Bind important real claims in atlas fields to claim_grounding.field_paths.
Illustrative concepts and sample rows are labeled as such and must never be entered as
dossier facts or coverage ledger evidence. The user's theme and illustrative-work
choice are application policy, not instructions embedded in source text.
</atlas_pages>
