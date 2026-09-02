# Home — Arjun Mehta

## Purpose and audience
Present Arjun as a Senior UI/UX Designer based in Bengaluru who simplifies complex product workflows through research, iteration, accessible interaction design, usability testing, and scalable systems. The primary audience is hiring teams and product leaders; the secondary audience is design and engineering collaborators.

## Required section coverage
Cover, in order, `home:hero`, `home:selected-work`, `home:approach`, `home:experience`, `home:design-systems`, and `home:about-connect`. Preserve the approved generalized copy and approved link targets. The selected-work section should give greatest emphasis to payments and checkout, while logistics and healthcare broaden the range. Do not imply full case-study depth.

## Content and interaction
The hero uses the approved headline, introduction, Explore selected work anchor, and LinkedIn action. Selected work contains four generalized entries: payments and onboarding, e-commerce checkout, logistics operations, and healthcare appointments. Optional detail exploration may expose only those approved summaries and must remain reachable by keyboard, touch, and non-hover interaction. Experience contains the two supplied roles, organizations, dates, and concise summaries; a native semantic list/timeline is the safe fallback. Approach contains Understand, Shape, Test, and Scale. Systems and craft contains the approved capabilities, tools, and Nova Design System description. About/connect contains the approved Bengaluru context, education, languages, LinkedIn, portfolio, and resume links.

## Responsive, accessibility, and motion
Preserve document order and essential content. Stack dense compositions on narrow screens. Keep the hero headline, introduction, primary action, payments, and checkout prominent; shorten contributions, tools, and education only according to the supplied mobile condensation guidance. Do not require hover. Use semantic headings, landmarks, lists, descriptive link labels, visible focus, sufficient contrast, keyboard-operable controls, and correct dialog focus management if detail exploration is used. Decorative imagery uses empty alt text; never let it carry evidence. Provide a complete static reduced-motion state without sequencing, parallax, or essential information hidden in motion.

## Resource bindings and fallbacks
Selected route resources are listed in `resource_ids`. Bind them by their Stage 2 metadata, placement, accessibility, responsive, reduced-motion, export, license, and provenance fields. Selected image roles are decorative and non-evidentiary: hero uses the selected Pixabay copper architectural resource; experience uses the selected Pixabay pipe resource; approach uses the selected Pexels abstract data-flow resource; design systems uses the selected Pexels abstract data-flow resource; selected work uses the selected Pexels abstract data-flow resource. About/connect has no selected image and must use its text-led fallback. The selected-work detail resource is optional and may fall back to semantic content. The selected experience resource may fall back to a semantic accessible static timeline/list. Local path/hash/provenance materialization is not present in this packet and is an execution gap; do not claim those resources are build-ready until resolved.

## Acceptance criteria

- Route `/` renders the approved `home` route and covers all six approved section IDs in approved order.
- Approved generalized copy, approved claims, CTA targets, and public links are preserved without pending metrics or private contact details.
- Payments and checkout receive the greatest selected-work emphasis while logistics and healthcare remain represented.
- No section implies full case-study depth, screenshots, project visuals, testimonials, awards, client details, or unsupported ownership.
- Responsive layouts stack dense groups on narrow screens and retain essential content without hover.
- Keyboard focus, semantic headings and lists, link names, contrast, touch targets, and any dialog focus behavior are accessible.
- Reduced-motion mode is a complete static equivalent with no essential sequencing, parallax, or hidden content.
- Decorative image roles use only their selected executable bindings when available, with empty alt text and no evidentiary interpretation.
- About/connect renders without an image because Stage 2 selected nothing for that role.
- No runtime provider/network asset calls are used; unresolved local materialization is reported as an execution gap.
- Selected resource licenses, provenance, hashes, exports, and dependencies are validated before release.

## Free to change

- Choose the visual composition and layout within the technical-editorial direction.
- Choose the number of internal scenes and responsive groupings while covering every approved section ID.
- Choose semantic HTML structure, spacing values, type scale, and component boundaries.
- Choose whether to use the optional selected-work detail resource or its semantic fallback.
- Choose the exact accessible static presentation of the experience entries.
- Choose whether decorative selected images are omitted when their executable local bindings are unavailable, using the specified text-led fallbacks.
