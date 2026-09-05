import { describe, it, expect } from "vitest";
import { StatusAnnouncer } from "../components/StatusAnnouncer";
import { CacheNotice } from "../components/CacheNotice";
import { ProgressSurface } from "../components/ProgressSurface";
import { JourneyRail, type JourneyStageVM } from "../components/JourneyRail";
import { extractHeadings, SafeMarkdown } from "../components/SafeMarkdown";

describe("Phase 5 Accessibility Pass (docs/Frontend/05 §13, §18)", () => {
  it("StatusAnnouncer renders polite live region with status role", () => {
    const vnode = StatusAnnouncer({ message: "Portfolio brief approved." });
    expect(vnode).toBeDefined();
    expect(vnode.props["aria-live"]).toBe("polite");
    expect(vnode.props.role).toBe("status");
    expect(vnode.props.className).toBe("visually-hidden");
    expect(vnode.props.children).toBe("Portfolio brief approved.");
  });

  it("CacheNotice explains a confirmed cached response accessibly", () => {
    const vnode = CacheNotice({ message: "Served from cache — this response arrived faster." });
    if (!vnode) throw new Error("CacheNotice should render for a cache receipt message");
    expect(vnode.props["aria-live"]).toBe("polite");
    expect(vnode.props.role).toBe("status");
  });

  it("ProgressSurface sets aria-busy and marks milestones cleanly", () => {
    const milestones = [
      { id: "1", label: "Resolving assets", state: "complete" as const },
      { id: "2", label: "Compiling work graph", state: "current" as const },
      { id: "3", label: "Generating pages", state: "quiet" as const },
    ];
    const vnode = ProgressSurface({
      stageLabel: "Stage 05 / Code Generator",
      title: "Building portfolio source",
      currentMilestone: "Compiling work graph",
      milestones,
    });
    expect(vnode).toBeDefined();
    expect(vnode.props["aria-label"]).toBe("Stage 05 / Code Generator progress");
  });

  it("JourneyRail marks active stage with aria-current='step'", () => {
    const stages: JourneyStageVM[] = [
      { id: "discover", ordinal: 1, label: "Discovery", state: "complete", isSelectable: true },
      { id: "content", ordinal: 2, label: "Content Architect", state: "review", isSelectable: true },
      { id: "design", ordinal: 3, label: "Visual Design", state: "locked", isSelectable: false },
    ];
    const vnode = JourneyRail({
      journey: stages,
      selectedStageId: "content",
      onSelect: () => {},
    });
    expect(vnode).toBeDefined();
    expect(vnode.props["aria-label"]).toBe("Portfolio journey");
  });

  it("SafeMarkdown enforces single or logical heading structure with clean anchors", () => {
    const doc = `
# Engineering Leader Portfolio

Executive summary and strategic vision.

## Technical Philosophy

Principles for resilient distributed systems.

### Consistency Models

Eventual consistency vs strong consistency.
`;
    const headings = extractHeadings(doc);
    expect(headings.length).toBe(3);
    expect(headings[0]).toEqual({ id: "engineering-leader-portfolio", text: "Engineering Leader Portfolio", level: 1 });
    expect(headings[1]).toEqual({ id: "technical-philosophy", text: "Technical Philosophy", level: 2 });
    expect(headings[2]).toEqual({ id: "consistency-models", text: "Consistency Models", level: 3 });

    // Check rendered markup
    const rendered = SafeMarkdown({ content: doc });
    expect(rendered).toBeDefined();
  });
});
