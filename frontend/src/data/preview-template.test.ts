// @vitest-environment jsdom
import { describe, expect, it } from "vitest";
import template from "../../public/theme/index.html?raw";
import { adaptPageContent, emptyPageContent } from "./adapters/content";
import { contentPageFixture } from "./adapters/content.fixtures";
import {
  buildPreviewHtml,
  capabilityPreview,
  monogramFor,
  safeLinkUrl,
} from "./preview-template";

function render(raw: unknown = contentPageFixture): Document {
  const html = buildPreviewHtml(template, adaptPageContent(raw));
  return new DOMParser().parseFromString(html, "text/html");
}

describe("preview helpers", () => {
  it("derives monograms without honorifics", () => {
    expect(monogramFor("Dr. Aditya Vikram Joshi")).toBe("AVJ");
    expect(monogramFor("Priya Nandan")).toBe("PN");
    expect(monogramFor("Cher")).toBe("C");
  });

  it("only allows http, https, and mailto links", () => {
    expect(safeLinkUrl("https://github.com/x")).toBe("https://github.com/x");
    expect(safeLinkUrl("mailto:a@b.co")).toBe("mailto:a@b.co");
    expect(safeLinkUrl("javascript:alert(1)")).toBeNull();
    expect(safeLinkUrl("data:text/html,x")).toBeNull();
    expect(safeLinkUrl("not a url")).toBeNull();
  });

  it("builds a short preview from the first items", () => {
    expect(capabilityPreview(["a", "b", "c", "d", "e"])).toBe("a · b · c · d");
  });
});

describe("buildPreviewHtml", () => {
  it("fills the hero, metadata, and monogram from the content", () => {
    const doc = render();
    expect(doc.title).toBe("Priya Nandan — Senior Backend Engineer");
    expect(doc.querySelector("h1")?.textContent).toBe("Priya Nandan");
    expect(doc.querySelector(".hero__headline em")?.textContent).toBe("never lose a message.");
    expect(doc.querySelector(".wordmark__monogram")?.textContent).toBe("PN");
    expect(doc.querySelector(".hero__location span:not(.eyebrow)")?.textContent).toBe("Bengaluru, India");
    expect(doc.querySelector(".hero__visual")).toBeNull();
  });

  it("renders exactly the supplied pillars with derived indexes", () => {
    const doc = render();
    const pillars = doc.querySelectorAll(".pillar-grid .pillar");
    expect(pillars).toHaveLength(4);
    expect(pillars[2]?.getAttribute("data-index")).toBe("03");
    expect(pillars[0]?.querySelector("h3")?.textContent).toBe("Durable queues");
  });

  it("duplicates the marquee identically and repeats short lists", () => {
    const doc = render();
    const lists = doc.querySelectorAll(".marquee__list");
    expect(lists).toHaveLength(2);
    expect(lists[0]?.innerHTML).toBe(lists[1]?.innerHTML);
    expect(lists[0]?.querySelectorAll("li").length).toBeGreaterThanOrEqual(10);
  });

  it("builds capability groups with a derived preview and the first group open", () => {
    const doc = render();
    const groups = doc.querySelectorAll(".capability-group");
    expect(groups).toHaveLength(2);
    expect(groups[0]?.hasAttribute("open")).toBe(true);
    expect(groups[1]?.querySelector(".capability-group__preview")?.textContent).toBe(
      "Kafka · PostgreSQL · Redis · ClickHouse",
    );
  });

  it("marks featured destinations and keeps only safe links", () => {
    const raw = structuredClone(contentPageFixture);
    raw.connect.destinations.push({ label: "Bad", url: "javascript:alert(1)", featured: false });
    const doc = render(raw);
    const items = doc.querySelectorAll(".destination-list li");
    expect(items).toHaveLength(3);
    expect(doc.querySelectorAll(".destination-list__featured")).toHaveLength(2);
    expect(doc.querySelector(".destination-list a")?.getAttribute("href")).toBe("https://github.com/example");
    expect(doc.body.innerHTML).not.toContain("javascript:");
  });

  it("never interprets model text as markup", () => {
    const raw = structuredClone(contentPageFixture);
    raw.hero.intro = '<img src=x onerror="alert(1)"><script>alert(2)</script>';
    raw.hero.name = "<b>Eve</b>";
    const doc = render(raw);
    expect(doc.querySelector(".hero__intro img")).toBeNull();
    expect(doc.querySelector("script")).toBeNull();
    expect(doc.querySelector("h1 b")).toBeNull();
    expect(doc.querySelector("h1")?.textContent).toBe("<b>Eve</b>");
  });

  it("uses an absolute stylesheet path and no <base> so in-page anchors keep working", () => {
    const doc = render();
    expect(doc.querySelector("link[rel=stylesheet]")?.getAttribute("href")).toBe(
      "/static/product/theme/styles.css",
    );
    expect(doc.querySelector("base")).toBeNull();
    expect(doc.querySelector("link[rel=preload]")).toBeNull();
  });

  it("degrades gracefully for empty content without leaving broken nodes", () => {
    const html = buildPreviewHtml(template, emptyPageContent());
    const doc = new DOMParser().parseFromString(html, "text/html");
    expect(doc.querySelector(".marquee")).toBeNull();
    expect(doc.querySelector(".hero__location")).toBeNull();
    expect(doc.querySelector(".organization-list")).toBeNull();
    expect(doc.querySelector(".destination-list")).toBeNull();
    expect(doc.querySelector(".inventory-grid")).toBeNull();
    expect(html).not.toContain("undefined");
    expect(html).not.toContain("[object");
  });

  it("derives nav labels from section eyebrows and keeps four indexed links", () => {
    const doc = render();
    const links = doc.querySelectorAll(".site-nav__links a");
    expect(links).toHaveLength(4);
    expect(links[1]?.textContent).toContain("Technical capabilities");
    expect(links[3]?.querySelector(".site-nav__index")?.textContent).toBe("04");
  });
});
