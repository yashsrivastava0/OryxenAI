## Task: compose the Visual & Build Brief

Write `visual_brief_prose` -- the full Markdown body (headings, paragraphs,
short lists) that becomes the "Visual & Build Brief" Code Generator reads
before generating a portfolio. Cover, in this order:

1. **Design language.** Synthesize `visual_language`, `shared_visual_systems`,
   `motion_system`, and `interaction_system` into a short, concrete
   description of the intended look and feel: typography roles, color
   relationships, spacing rhythm, motion character, and interaction
   personality. If the input is sparse (`visual_input_mode` is
   `assumed_from_content` or `merged_vdd_assumptions`), say so honestly and
   give Code Generator sound, professional defaults instead of inventing
   specifics that were never actually approved.
2. **Per-route direction.** For every route in `routes`, describe the
   intended storyboard and section rhythm, primary and secondary emphasis,
   how scenes should transition, and how the layout should adapt on mobile.
   Reference each route's `scenes` (layout_intent, motion_intent,
   interaction_states) when present.
3. **Component and layout patterns.** For every entry in
   `layout_pattern_needs` (Visual Design Director's own local pattern-catalogue
   suggestions that have no fetchable resource -- hero/background/diagram
   patterns), describe when and how to use the suggested pattern, grounded in
   its `why_it_matches`/`adaptation_notes`. These are adaptable suggestions,
   never a mandate.
4. **Resource guidance.** For every entry in `resource_roles`, pick a
   `primary_candidate_index` (or `null`) and write one or two sentences of
   crop, treatment, or fallback guidance. For every entry in
   `component_roles`, pick a `primary_suggestion_index` (or `null`) with a
   short usage note.
5. **Accessibility and performance.** Restate `accessibility_and_performance`
   and any responsive risks as concrete, actionable guidance.
6. **Explicit authority statement.** End with an unambiguous statement that
   Code Generator has final authority to adapt, replace, combine, or ignore
   any suggestion in this brief -- nothing here is a hard constraint except
   the approved content itself, which this brief does not repeat.

Also return, in the structured fields (not inside the prose):

- `resource_guidance` / `component_guidance` -- your index picks, one entry
  per role you have an opinion on. Omit a role entirely rather than guessing
  if you are unsure; an omitted role simply has no primary pick.
- `seo_suggestions` -- an optional one-line meta description per `route_id`,
  grounded only in the approved content already given to you, never a
  fabricated claim.
- `warnings` -- anything Code Generator should know before generating: thin
  visual direction, no candidates found for an important role, a tension
  between the visual language and the available content density.

Never restate raw approved copy verbatim at length -- Code Generator already
receives the full approved content in a separately assembled content brief.
Never write JSX, TSX, CSS, or any code.
