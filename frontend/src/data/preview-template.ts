// Deterministic client-side fill of the pinned portfolio template.
//
// This is a lightweight, UNVERIFIED review convenience: it substitutes the
// Content Architect's page content into the real pinned index.html so the
// reviewer sees roughly what the page will look like. It is not the future
// browser-verified preview pipeline, and no model is involved.
//
// Security: page content traces back to untrusted source material, so every
// substitution uses textContent / createElement / setAttribute with a URL
// scheme allow-list — never innerHTML string concatenation.

import type { PageContentVM } from "./adapters/content";

export const THEME_BASE_PATH = "/static/product/theme/";
const SAFE_LINK_PROTOCOLS = new Set(["https:", "http:", "mailto:"]);
const MARQUEE_MIN_ITEMS = 10;
const PREVIEW_ITEM_COUNT = 4;

const NAV_FALLBACK_LABELS = [
  "Systems practice",
  "Technical capabilities",
  "Professional context",
  "Connect",
];

export function safeLinkUrl(value: string): string | null {
  const trimmed = value.trim();
  if (!trimmed) return null;
  try {
    const parsed = new URL(trimmed);
    return SAFE_LINK_PROTOCOLS.has(parsed.protocol) ? trimmed : null;
  } catch {
    return null;
  }
}

/** Up to three initials from the name, skipping honorifics like "Dr.". */
export function monogramFor(name: string): string {
  const words = name
    .split(/\s+/)
    .map((word) => word.trim())
    .filter((word) => word && !word.endsWith("."));
  const letters = words.slice(0, 3).map((word) => Array.from(word)[0] ?? "");
  const monogram = letters.join("");
  if (monogram) return monogram.toUpperCase();
  return Array.from(name.trim()).slice(0, 2).join("").toUpperCase();
}

export function capabilityPreview(items: string[]): string {
  return items
    .filter((item) => item.trim())
    .slice(0, PREVIEW_ITEM_COUNT)
    .join(" · ");
}

function ordinal(index: number): string {
  return String(index + 1).padStart(2, "0");
}

export function buildPreviewHtml(
  templateHtml: string,
  page: PageContentVM,
  themeBasePath: string = THEME_BASE_PATH,
): string {
  const doc = new DOMParser().parseFromString(templateHtml, "text/html");
  const q = <T extends Element = Element>(selector: string): T | null =>
    doc.querySelector<T>(selector);
  const create = (tag: string, className?: string, text?: string): HTMLElement => {
    const el = doc.createElement(tag);
    if (className) el.className = className;
    if (text !== undefined) el.textContent = text;
    return el;
  };
  const decorative = (el: HTMLElement): HTMLElement => {
    el.setAttribute("aria-hidden", "true");
    return el;
  };
  const setText = (selector: string, text: string, removeWhenEmpty = false): void => {
    const el = q(selector);
    if (!el) return;
    if (!text.trim() && removeWhenEmpty) el.remove();
    else el.textContent = text;
  };

  const { hero } = page;
  const name = hero.name.trim();

  // Head: title, description, stylesheet. Preloads point at font files the
  // theme does not ship yet, and a <base> would turn in-page #anchors into
  // navigations inside the iframe, so the stylesheet gets an absolute path.
  doc.title = page.metadataTitle || name || "Portfolio preview";
  q("meta[name=description]")?.setAttribute("content", page.metadataDescription);
  doc.querySelectorAll("link[rel=preload]").forEach((link) => link.remove());
  q("link[rel=stylesheet]")?.setAttribute("href", `${themeBasePath}styles.css`);

  // Identity
  const monogram = monogramFor(name);
  setText(".wordmark__monogram", monogram);
  setText(".wordmark__name", name);
  q(".wordmark")?.setAttribute("aria-label", `${name} — home`);

  // Navigation labels follow the section eyebrows; the 01-04 index spans stay.
  const sectionEyebrows = [
    page.systemsPractice.eyebrow,
    page.technicalCapabilities.eyebrow,
    page.professionalContext.eyebrow,
    page.connect.eyebrow,
  ];
  doc.querySelectorAll(".site-nav__links li a").forEach((link, index) => {
    const label = link.querySelector("span:not(.site-nav__index)");
    if (label) label.textContent = sectionEyebrows[index]?.trim() || NAV_FALLBACK_LABELS[index] || "";
  });

  // Hero
  const eyebrow = q(".hero__eyebrow");
  if (eyebrow) {
    eyebrow.textContent = "";
    eyebrow.append(doc.createTextNode(hero.eyebrowPrimary));
    if (hero.eyebrowSecondary.trim()) {
      eyebrow.append(
        doc.createTextNode(" "),
        decorative(create("span", undefined, "·")),
        doc.createTextNode(` ${hero.eyebrowSecondary}`),
      );
    }
  }
  setText(".hero h1", name);
  const headline = q(".hero__headline");
  if (headline) {
    headline.textContent = "";
    if (hero.headlinePrefix.trim()) headline.append(doc.createTextNode(`${hero.headlinePrefix} `));
    if (hero.headlineEmphasis.trim()) headline.append(create("em", undefined, hero.headlineEmphasis));
  }
  setText(".hero__intro", hero.intro);
  const locationValue = q(".hero__location span:not(.eyebrow)");
  if (hero.location.trim() && locationValue) locationValue.textContent = hero.location;
  else q(".hero__location")?.remove();
  setText(".button__label", hero.primaryCtaLabel.trim() || "Explore the work");
  const textLink = q(".text-link");
  const textLinkArrow = textLink?.querySelector("span");
  if (textLink && textLinkArrow) {
    textLink.textContent = "";
    textLink.append(doc.createTextNode(`${hero.secondaryCtaLabel.trim() || "View links"} `), textLinkArrow);
  }
  // No portrait or asset binding exists yet; the template's stock photo would
  // read as the user's own photo, so the visual is dropped and the copy widens.
  q(".hero__visual")?.remove();
  const heroGrid = q<HTMLElement>(".hero__grid");
  if (heroGrid) heroGrid.style.gridTemplateColumns = "minmax(0, 1fr)";

  // Marquee: two identical lists for the seamless loop; repeat short lists so
  // each copy is wider than the viewport.
  const keywords = page.marqueeKeywords.map((word) => word.trim()).filter(Boolean);
  if (keywords.length === 0) {
    q(".marquee")?.remove();
  } else {
    const loop: string[] = [];
    while (loop.length < Math.max(MARQUEE_MIN_ITEMS, keywords.length)) loop.push(...keywords);
    doc.querySelectorAll(".marquee__list").forEach((list) => {
      list.textContent = "";
      for (const word of loop) list.append(create("li", undefined, word));
    });
  }

  // Section headings
  const sections: Array<{
    eyebrowSelector: string;
    headingSelector: string;
    introSelector: string;
    data: { eyebrow: string; heading: string; intro: string };
    removeEmptyIntro: boolean;
  }> = [
    {
      eyebrowSelector: "#systems-practice .eyebrow",
      headingSelector: "#systems-title",
      introSelector: "#systems-practice .section-heading__intro",
      data: page.systemsPractice,
      removeEmptyIntro: true,
    },
    {
      eyebrowSelector: "#technical-capabilities .eyebrow",
      headingSelector: "#capabilities-title",
      introSelector: "#technical-capabilities .section-heading__intro",
      data: page.technicalCapabilities,
      removeEmptyIntro: true,
    },
    {
      eyebrowSelector: "#professional-context .section-heading .eyebrow",
      headingSelector: "#context-title",
      introSelector: ".context-content__intro",
      data: page.professionalContext,
      removeEmptyIntro: true,
    },
    {
      eyebrowSelector: "#connect .connect-copy .eyebrow",
      headingSelector: "#connect-title",
      introSelector: "#connect .connect-copy > p:last-child",
      data: page.connect,
      removeEmptyIntro: true,
    },
  ];
  sections.forEach((section, index) => {
    setText(section.eyebrowSelector, section.data.eyebrow.trim() || NAV_FALLBACK_LABELS[index] || "");
    setText(section.headingSelector, section.data.heading);
    setText(section.introSelector, section.data.intro, section.removeEmptyIntro);
  });

  // Pillars
  const pillarGrid = q(".pillar-grid");
  if (pillarGrid) {
    pillarGrid.textContent = "";
    page.systemsPractice.pillars.forEach((pillar, index) => {
      const li = create("li", "pillar");
      li.setAttribute("data-index", ordinal(index));
      li.append(
        decorative(create("span", "pillar__index", ordinal(index))),
        create("h3", undefined, pillar.title),
        create("p", undefined, pillar.description),
      );
      pillarGrid.append(li);
    });
    if (page.systemsPractice.pillars.length === 0) pillarGrid.remove();
  }

  // Capability groups
  const inventory = q(".inventory-grid");
  if (inventory) {
    inventory.textContent = "";
    page.technicalCapabilities.groups.forEach((group, index) => {
      const details = create("details", "capability-group");
      if (index === 0) details.setAttribute("open", "");
      const summary = create("summary");
      const content = create("span", "capability-group__content");
      const heading = create("span", "capability-group__heading");
      heading.append(
        decorative(create("span", "capability-group__index", ordinal(index))),
        create("span", undefined, group.heading),
      );
      content.append(heading);
      const preview = capabilityPreview(group.items);
      if (preview) content.append(create("span", "capability-group__preview", preview));
      summary.append(content, decorative(create("span", "disclosure-icon")));
      const list = create("ul", "capability-list");
      for (const item of group.items) if (item.trim()) list.append(create("li", undefined, item));
      details.append(summary, list);
      inventory.append(details);
    });
    if (page.technicalCapabilities.groups.length === 0) inventory.remove();
  }

  // Organizations (names only)
  const orgList = q(".organization-list");
  if (orgList) {
    orgList.textContent = "";
    for (const org of page.professionalContext.organizations) {
      if (org.trim()) orgList.append(create("li", undefined, org));
    }
    if (!orgList.firstChild) orgList.remove();
  }

  // Destinations: unsafe URL schemes are dropped, never rendered.
  const destinationList = q(".destination-list");
  if (destinationList) {
    destinationList.textContent = "";
    for (const destination of page.connect.destinations) {
      const href = safeLinkUrl(destination.url);
      if (!href || !destination.label.trim()) continue;
      const li = create("li", destination.featured ? "destination-list__featured" : undefined);
      const anchor = create("a");
      anchor.setAttribute("href", href);
      anchor.setAttribute("target", "_blank");
      anchor.setAttribute("rel", "noopener noreferrer");
      anchor.append(
        create("span", undefined, destination.label),
        decorative(create("span", "destination-arrow", "↗")),
      );
      li.append(anchor);
      destinationList.append(li);
    }
    if (!destinationList.firstChild) destinationList.remove();
  }

  // Footer
  const footerLine = q(".site-footer__inner p");
  if (footerLine) {
    footerLine.textContent = "";
    footerLine.append(doc.createTextNode(name));
    if (hero.location.trim()) {
      footerLine.append(
        doc.createTextNode(" "),
        decorative(create("span", undefined, "·")),
        doc.createTextNode(` ${hero.location}`),
      );
    }
  }

  return `<!doctype html>\n${doc.documentElement.outerHTML}`;
}
