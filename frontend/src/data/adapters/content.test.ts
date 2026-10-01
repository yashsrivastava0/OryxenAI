import { describe, it, expect } from "vitest";
import { adaptContentArchitect, pageContentIsEmpty } from "./content";
import {
  contentFixtureNotStarted,
  contentFixtureBuildRunning,
  contentFixtureReview,
  contentFixtureApproved,
  contentFixtureNeedsAttention,
} from "./content.fixtures";

describe("adaptContentArchitect", () => {
  it("locks not_started when Discovery is not yet approved", () => {
    const view = adaptContentArchitect(contentFixtureNotStarted, false);
    expect(view.state).toBe("locked");
    expect(view.statusText).toBe("Locked until Discovery is approved");
  });

  it("unlocks to available when Discovery is approved", () => {
    const view = adaptContentArchitect(contentFixtureNotStarted, true);
    expect(view.state).toBe("available");
    expect(view.statusText).toBe("Ready to structure portfolio content");
  });

  it("maps build_running to working", () => {
    const view = adaptContentArchitect(contentFixtureBuildRunning, true);
    expect(view.state).toBe("working");
    expect(view.statusText).toBe("Structuring your portfolio content");
  });

  it("maps content_review to review and extracts the page content tree", () => {
    const view = adaptContentArchitect(contentFixtureReview, true);
    expect(view.state).toBe("review");
    expect(view.positioning).toBe("Staff-level infrastructure engineer leading reliability at scale.");
    expect(view.pageContent.hero.name).toBe("Priya Nandan");
    expect(view.pageContent.hero.headlineEmphasis).toBe("never lose a message.");
    expect(view.pageContent.systemsPractice.pillars).toHaveLength(4);
    expect(view.pageContent.technicalCapabilities.groups[1]?.items).toContain("Kafka");
    expect(view.pageContent.professionalContext.organizations).toEqual(["Example Systems", "Northwind Labs"]);
    expect(view.pageContent.connect.destinations.filter((d) => d.featured)).toHaveLength(2);
    expect(view.claimGrounding[0]?.fieldPaths).toEqual(["systems_practice.pillars[0].description"]);
    expect(view.claimGrounding[1]?.publicationStatus).toBe("pending");
    expect(view.coverageLedger.map((e) => e.disposition)).toEqual(["used", "unresolved"]);
    expect(view.decisionBasis.length).toBe(1);
    expect(view.warnings).toContain("Omitted internal employer metrics per privacy policy.");
    expect(view.safeError).toBeNull();
  });

  it("degrades to an empty page for legacy or malformed content without throwing", () => {
    const view = adaptContentArchitect(
      { status: "content_review", page_content: { hero: "oops", systems_practice: { pillars: [1, null] } } },
      true,
    );
    expect(view.state).toBe("review");
    expect(pageContentIsEmpty(view.pageContent)).toBe(true);
    expect(view.pageContent.systemsPractice.pillars).toEqual([]);
  });

  it("maps approved to complete", () => {
    const view = adaptContentArchitect(contentFixtureApproved, true);
    expect(view.state).toBe("complete");
    expect(view.statusText).toBe("Content plan approved");
  });

  it("maps needs_attention to attention and extracts error", () => {
    const view = adaptContentArchitect(contentFixtureNeedsAttention, true);
    expect(view.state).toBe("attention");
    expect(view.safeError?.summary).toBe("Content model timed out while synthesizing page copy.");
  });

  it("fails closed into unsupported for unknown or malformed status", () => {
    const view = adaptContentArchitect({ status: "some_future_phase" }, true);
    expect(view.state).toBe("unsupported");
    expect(view.statusText).toContain("unrecognised state");
  });
});
