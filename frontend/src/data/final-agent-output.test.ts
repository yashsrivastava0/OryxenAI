import { describe, expect, it } from "vitest";
import { finalAgentOutput } from "./final-agent-output";

describe("persisted final agent output", () => {
  it("returns Discovery's complete persisted output without rebuilding a field allowlist", () => {
    const output = finalAgentOutput("discovery", {
      agent_output: {
        operation: "build_or_revise_brief",
        brief_markdown: "# Final brief",
        unknown_future_field: { nested: ["kept", { value: true }] },
      },
      intake: { document_text: "private raw source" },
      job_id: "job-1",
    });

    expect(output).toMatchObject({
      operation: "build_or_revise_brief",
      brief_markdown: "# Final brief",
      unknown_future_field: { nested: ["kept", { value: true }] },
    });
    expect(output).not.toHaveProperty("intake");
  });

  it("keeps Content and Design artifacts exact when the server provides them", () => {
    const content = finalAgentOutput("content_architect", {
      agent_output: {
        route_plan: [{ route_id: "home" }],
        page_content_packs: [{ route_id: "home" }],
        custom: { score: 0.8 },
      },
    });
    const design = finalAgentOutput("visual_design_director", {
      agent_output: {
        visual_language: { creative_thesis: "Systems made visible" },
        pages: [{ route_id: "home" }],
        custom: { density: "high" },
      },
    });

    expect(content).toEqual({
      route_plan: [{ route_id: "home" }],
      page_content_packs: [{ route_id: "home" }],
      custom: { score: 0.8 },
    });
    expect(design).toEqual({
      visual_language: { creative_thesis: "Systems made visible" },
      pages: [{ route_id: "home" }],
      custom: { density: "high" },
    });
  });

  it("keeps Build Preparation's complete handoff output", () => {
    expect(finalAgentOutput("build_preparation", {
      agent_output: {
        content_brief_markdown: "# Content brief",
        visual_brief_markdown: "# Visual brief",
        routes: [{ route_id: "home" }],
        target_contract: "react-vite-v1",
      },
    })).toEqual({
      content_brief_markdown: "# Content brief",
      visual_brief_markdown: "# Visual brief",
      routes: [{ route_id: "home" }],
      target_contract: "react-vite-v1",
    });
  });
});
