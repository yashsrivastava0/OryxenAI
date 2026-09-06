import { describe, expect, it } from "vitest";
import { finalAgentOutput } from "./final-agent-output";

describe("persisted final agent output", () => {
  it("exports Discovery's final artifact without raw intake or job state", () => {
    const output = finalAgentOutput("discovery", {
      intake: { document_text: "private raw source" },
      job_id: "job-1",
      brief: {
        title: "Portfolio Brief",
        markdown: "# Final brief",
        user_summary: "Ready",
        profile: { role: "Engineer" },
        open_items: ["Confirm CTA"],
      },
    });

    expect(output).toMatchObject({
      operation: "build_or_revise_brief",
      brief_title: "Portfolio Brief",
      brief_markdown: "# Final brief",
    });
    expect(JSON.stringify(output)).not.toContain("private raw source");
    expect(output).not.toHaveProperty("job_id");
  });

  it("exports Content and Design artifacts without operational state", () => {
    const content = finalAgentOutput("content_architect", {
      status: "content_review",
      intake: { profile: "private" },
      route_plan: [{ route_id: "home" }],
      page_content_packs: [{ route_id: "home" }],
    });
    const design = finalAgentOutput("visual_design_director", {
      status: "design_review",
      source_ref: { content_hash: "internal" },
      visual_language: { creative_thesis: "Systems made visible" },
      pages: [{ route_id: "home" }],
    });

    expect(content).toEqual({
      route_plan: [{ route_id: "home" }],
      page_content_packs: [{ route_id: "home" }],
    });
    expect(design).toEqual({
      visual_language: { creative_thesis: "Systems made visible" },
      pages: [{ route_id: "home" }],
    });
  });

  it("keeps Build Preparation's copyable brief pair in its final projection", () => {
    expect(finalAgentOutput("build_preparation", {
      status: "ready",
      content_brief_markdown: "# Content brief",
      visual_brief_markdown: "# Visual brief",
      routes: [{ route_id: "home" }],
    })).toEqual({
      routes: [{ route_id: "home" }],
      content_brief_markdown: "# Content brief",
      visual_brief_markdown: "# Visual brief",
    });
  });
});
