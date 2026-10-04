import { describe, expect, it } from "vitest";
import { parseAppUrlState, serializeAppUrlState } from "./url-state";

describe("portfolio URL state", () => {
  it("parses the active journey stages", () => {
    expect(parseAppUrlState("?stage=discover&view=work")).toEqual({
      stage: "discover",
      view: "work",
      screen: null,
    });
    expect(parseAppUrlState("?stage=content&view=artifact")).toEqual({
      stage: "content",
      view: "artifact",
      screen: null,
    });
  });

  it("drops unknown stage parameters", () => {
    expect(parseAppUrlState("?stage=retired&view=artifact")).toEqual({
      stage: null,
      view: "artifact",
      screen: null,
    });
    expect(parseAppUrlState("?stage=unknown&view=unknown")).toEqual({
      stage: null,
      view: null,
      screen: null,
    });
  });

  it("serializes the selected stage and view", () => {
    expect(serializeAppUrlState({ stage: "content", view: "artifact" })).toBe(
      "?stage=content&view=artifact",
    );
    expect(serializeAppUrlState({})).toBe("");
  });

  it("routes private pages without a stale stage and rejects unknown pages", () => {
    expect(parseAppUrlState("?screen=guide&stage=studio")).toEqual({ screen: "guide", stage: null, view: null });
    expect(serializeAppUrlState({ screen: "home", stage: "studio" })).toBe("?screen=home");
    expect(parseAppUrlState("?screen=unknown").screen).toBeNull();
  });
});
