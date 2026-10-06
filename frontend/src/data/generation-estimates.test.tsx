// @vitest-environment jsdom
import { afterEach, describe, expect, it } from "vitest";
import { h } from "preact";
import { render } from "preact-render-to-string";
import { GenerationEstimate } from "../components/GenerationEstimate";
import { generationEstimate } from "./generation-estimates";

afterEach(() => { document.head.innerHTML = ""; });

function config(value: string) {
  const meta = document.createElement("meta");
  meta.name = "oryxenai-generation-estimates";
  meta.content = value;
  document.head.append(meta);
}

describe("Generation time estimates", () => {
  it("shows the configured range and real elapsed time without a completion percentage", () => {
    config('{"content":[30,90]}');
    const html = render(h(GenerationEstimate, { kind: "content", elapsedSeconds: 22 }));
    expect(html).toContain("30–90");
    expect(html).toContain("22s");
    expect(html).toContain("An estimate, not a countdown");
    expect(html).not.toContain("%");
  });

  it("explains an overrun but never claims completion", () => {
    config('{"brief":[25,60]}');
    const html = render(h(GenerationEstimate, { kind: "brief", elapsedSeconds: 80 }));
    expect(html).toContain("Taking longer than usual");
    expect(html).toContain("1m 20s");
    expect(html).toContain("still in progress");
    expect(html).not.toContain("complete");
  });

  it("distinguishes queue wait and a paused worker from a slow generation", () => {
    config('{"studio":[25,35]}');
    const html = render(h(GenerationEstimate, { kind: "studio", elapsedSeconds: 90, queued: true }));
    expect(html).toContain("when a worker is free");
    expect(html).not.toContain("Taking longer");
    expect(render(h(GenerationEstimate, { kind: "studio", paused: true }))).toContain("worker to resume");
  });

  it("rejects unavailable or malformed timing configuration", () => {
    expect(generationEstimate("brief")).toBeNull();
    config('{"brief":[60,25]}');
    expect(generationEstimate("brief")).toBeNull();
    expect(render(h(GenerationEstimate, { kind: "brief", elapsedSeconds: 12 }))).toContain("12s elapsed");
  });
});
