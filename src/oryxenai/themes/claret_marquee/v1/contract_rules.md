<theme name="Claret Marquee" id="claret-marquee/v1">
This theme is rendered by the host from approved page_content; no model writes its markup.
If a body is ever model-written, return JSON with only lang and body_html, using the
exemplar's structure and class names. The host adds the fixed style.css and theme.js.
Never write a script, stylesheet, inline style, event handler, external resource, form,
iframe, image or invented claim.

Every route is one article.route-view with id, data-view, data-title and exactly one h1.
Home and About always exist. Case routes exist only for projects with a specific approved
problem and approach; a case route id is the project's position among ALL projects
(case-3 for the third project, even when case-2 does not exist). Home has #work and
#contact sections even when Work shows its designed empty state. Internal hrefs must
resolve to existing ids.

Project artwork is CSS only: data-art from aperture|reel|strata|ribbon|grid|halftone and
data-tone from 1|2|3|4. Do not add image URLs. Illustrative projects must visibly say
"Illustrative concept — not real client work" on both the card and the case page and leave
outcomes and metrics empty. Every person-specific visible string must match an approved
field exactly. When any row of experience, education or statistics has kind "sample",
print "Sample content — replace with your own details." once in that section's head block,
as the exemplar shows. Numerals and indices are drawn by CSS, never typed.

Every {path} in the exemplar is a placeholder, never text: replace it with the exact value
at that path in CONTENT (or DERIVED). Output no braces and none of the exemplar's words
except fixed interface text. Composed values such as data-title and aria-label (for example
"{atlas.projects[0].title} case study") are built from the approved fields exactly as the
exemplar shows, once per route or project.
</theme>
