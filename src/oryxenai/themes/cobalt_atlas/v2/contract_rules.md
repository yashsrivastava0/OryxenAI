<theme name="Cobalt Atlas Interactive" id="cobalt-atlas/v2">
Return JSON with only lang and body_html. Generate the visible body markup from
approved page_content, using the exemplar's structure and class names. The host
adds the fixed style.css and theme.js. Never write a script, stylesheet, inline
style, event handler, external resource, form, iframe, or invented claim.

Every route is one article.route-view with id, data-view, data-title and exactly
one h1. Home and About always exist. Case routes exist only for projects with a
specific approved problem and approach. Home has a #work section even when it
has a designed empty state. A case route id is the project's position among ALL
projects (case-3 for the third project, even when case-2 does not exist). Internal
hrefs must resolve to existing ids.

Use CSS artwork in project cards and case pages, with data-art from
orbit|grid|waves|stack|bars|dots and data-tone from 1|2|3|4. Do not add image
URLs. Illustrative projects must visibly say "Illustrative concept — not real
client work" on both card and case page; leave outcomes and metrics empty.
Every person-specific visible string must match an approved field exactly.

Every {path} in the exemplar is a placeholder, never text: replace it with the exact
value at that path in CONTENT (or DERIVED). Output no braces and none of the
exemplar's words except fixed interface text. Composed values such as data-title and
aria-label (for example "{atlas.projects[0].title} case study") are built from the
approved fields exactly as the exemplar shows, once per route or project.
</theme>
