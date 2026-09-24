import { describe, expect, it } from "vitest";
import { resolveInitialStage } from "./AppShell";

describe("resolveInitialStage", () => {
  it("keeps Discovery selected while no approved output exists", () => {
    expect(resolveInitialStage("discover", false)).toEqual({
      stage: null,
      corrected: false,
    });
    expect(resolveInitialStage(null, false)).toEqual({
      stage: null,
      corrected: false,
    });
  });

  it("returns to Discovery when a bookmarked content view has no approved brief", () => {
    expect(resolveInitialStage("content", false)).toEqual({
      stage: "discover",
      corrected: true,
    });
  });

  it("continues to Content after an approved Discovery brief", () => {
    expect(resolveInitialStage("discover", true)).toEqual({
      stage: "content",
      corrected: true,
    });
    expect(resolveInitialStage(null, true)).toEqual({
      stage: "content",
      corrected: true,
    });
  });

  it("leaves an available Content view selected", () => {
    expect(resolveInitialStage("content", true)).toEqual({
      stage: null,
      corrected: false,
    });
  });

  it("keeps the final approved Content plan selected", () => {
    expect(resolveInitialStage("discover", true)).toEqual({
      stage: "content",
      corrected: true,
    });
  });
});
