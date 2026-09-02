import { describe, it, expect } from "vitest";
import { extractHeadings, SafeMarkdown } from "./SafeMarkdown";

describe("SafeMarkdown & extractHeadings", () => {
  it("extracts headings with clean, unique anchor IDs", () => {
    const md = `# Overview\n\nSome text.\n\n## Experience & Impact\n\nMore text.\n\n## Overview\n`;
    const headings = extractHeadings(md);
    expect(headings.length).toBe(3);
    expect(headings[0]).toEqual({ id: "overview", text: "Overview", level: 1 });
    expect(headings[1]).toEqual({ id: "experience-impact", text: "Experience & Impact", level: 2 });
    expect(headings[2]).toEqual({ id: "overview-1", text: "Overview", level: 2 });
  });

  it("renders safe elements as VNodes without errors", () => {
    const md = `
# Main Header

This is a paragraph with **bold**, *italic*, and \`code\` tokens.

- Item one with [Valid Link](https://example.com)
- Item two with [Dangerous Link](javascript:alert(1))

1. Ordered step 1
2. Ordered step 2

---
`;
    const vnode = SafeMarkdown({ content: md });
    expect(vnode).toBeDefined();
    expect(vnode.props.className).toBe("markdown-content");
    expect(vnode.props.children).toBeDefined();
  });

  it("handles empty or null markdown cleanly", () => {
    const vnode = SafeMarkdown({ content: "" });
    expect(vnode).toBeDefined();
    expect(extractHeadings("")).toEqual([]);
  });
});
