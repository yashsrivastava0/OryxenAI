import { describe, expect, it } from "vitest";
import { parseAppUrlState, serializeAppUrlState } from "./url-state";

describe("three-stage URL state", () => {
  it("parses valid product stages", () => {
    expect(parseAppUrlState("?stage=discover&view=work")).toEqual({ stage: "discover", view: "work" });
    expect(parseAppUrlState("?stage=content&view=artifact")).toEqual({ stage: "content", view: "artifact" });
    expect(parseAppUrlState("?stage=design&view=progress")).toEqual({ stage: "design", view: "progress" });
  });

  it("drops removed and unknown stage parameters", () => {
    expect(parseAppUrlState("?stage=prepare&view=artifact")).toEqual({ stage: null, view: "artifact" });
    expect(parseAppUrlState("?stage=preview&view=preview&route=%2Fprojects")).toEqual({ stage: null, view: null });
  });

  it("serializes only the product stage and view", () => {
    expect(serializeAppUrlState({ stage: "content", view: "artifact" })).toBe("?stage=content&view=artifact");
    expect(serializeAppUrlState({})).toBe("");
  });
});
