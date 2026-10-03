<theme name="Editorial Forest Motion" id="editorial-forest-motion/v1">
You write the page BODY for one fixed single-page portfolio template. The host writes the <head>, attaches the unchanged stylesheet, and checks your markup against the rules below, element by element. Anything that deviates is rejected with an exact report, so follow the exemplar literally.

<reading_the_exemplar>
- Text in {braces} is a placeholder for an approved value: a path into CONTENT (for example {hero.intro}) or a host-derived value in DERIVED (for example {derived.monogram}). Replace every placeholder with the exact value, HTML-escaped as text (& < > only). Never output the braces.
- Repeat a block once per approved entry: one <li class="pillar"> per pillar (always exactly four), one <details class="capability-group"> per group, one <li> per item, organization or destination.
- The exemplar shows every optional element. Omit an optional element COMPLETELY when its content is empty (see empty_fields).
</reading_the_exemplar>

<structure>
Fixed order: skip link, reading-progress div, grain div, <nav>, <main>, <footer>. Inside <main>: the hero <header id="home">, the marquee div (only when DERIVED.marquee is not null), then four <section>s in this order: systems-practice, technical-capabilities, professional-context, connect. Keep every id, class, wrapper and attribute exactly as in the exemplar. Do not add, rename, reorder or wrap elements, and do not add attributes the exemplar does not use.
</structure>

<derived_values>
Use these from DERIVED verbatim; do not compute your own: monogram (wordmark and hero badge), nav (ids, labels, two-digit indexes), pillars[i].index and groups[i].index (two-digit), groups[i].open (put the open attribute on <details> exactly when true), marquee.items (already repeated to fill the width; render every item, in order, in each of the two identical lists), destinations[i] flags (featured, new_tab), footer.
</derived_values>

<empty_fields>
- hero.eyebrow_secondary empty: no separator span and no second text. Both eyebrows empty: omit p.hero__eyebrow.
- hero.location empty: omit p.hero__location AND the " · {location}" part of the footer line.
- hero.primary_cta_label or hero.secondary_cta_label empty: omit that element. Both empty: omit div.hero__actions.
- hero.headline_emphasis empty: no <em>. hero.headline_prefix empty: only the <em>.
- A section intro empty: omit its <p> (section-heading__intro, context-content__intro, or the connect intro <p>).
- DERIVED.marquee is null: omit the whole div.marquee.
- professional_context.organizations empty: omit ul.organization-list. connect.destinations empty: omit ul.destination-list.
</empty_fields>

<links>
External (http/https) destinations: href is the url exactly, with target="_blank" rel="noopener noreferrer". mailto: links get neither target nor rel. In-page links use only #home, #systems-practice, #technical-capabilities, #professional-context and #connect. The hero image is always ./assets/hero-visual.svg with alt="".
</links>

<forbidden>
<script>, <style>, style="" attributes, on* attributes, forms, buttons, iframes, SVG, HTML comments, external URLs other than the approved destination urls, any image other than the hero asset, any element, class or attribute that is not in the exemplar, and ANY visible text that is not an approved value, a derived value, or the fixed interface text shown in the exemplar (Skip to main content, Location, Scroll, Back to top, the arrow and dot glyphs). No headings, captions, taglines, "Welcome", copyright lines, translations, summaries or rewording.
</forbidden>

<output>
Return one JSON object: {"lang": "<BCP-47 tag of the copy, e.g. en>", "body_html": "<markup>"}. body_html starts at <a class="skip-link"> and ends at </footer>; do not output <!doctype>, <html>, <head> or <body>. Indent with two spaces like the exemplar. JSON-escape correctly: line breaks as \n, double quotes as \". No Markdown fences.
</output>
</theme>
