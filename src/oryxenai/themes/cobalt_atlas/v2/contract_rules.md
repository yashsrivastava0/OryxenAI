<theme name="Cobalt Atlas Interactive" id="cobalt-atlas/v2">
Return JSON with only lang and body_html. Generate the visible body markup from
approved page_content, using the exemplar's structure and class names. The host
adds the fixed style.css and theme.js. Never write a script, stylesheet, inline
style, event handler, external resource, form, iframe, or invented claim.

Every route is one article.route-view with id, data-view, data-title and exactly
one h1. Home and About always exist. Case routes exist only for projects with a
specific approved problem and approach. Home has a #work section even when it
has a designed empty state. Internal hrefs must resolve to existing ids.

Use CSS artwork in project cards and case pages, with data-art from
orbit|grid|waves|stack|bars|dots and data-tone from 1|2|3|4. Do not add image
URLs. Illustrative projects must visibly say "Illustrative concept — not real
client work" on both card and case page; leave outcomes and metrics empty.
Every person-specific visible string must match an approved field exactly.
</theme>
