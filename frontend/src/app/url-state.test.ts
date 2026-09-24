import { describe, expect, it } from "vitest";
import { parseAppUrlState, serializeAppUrlState } from "./url-state";

describe("portfolio URL state", () => {
  it("parses the active journey stages", () => {
    expect(parseAppUrlState("?stage=discover&view=work")).toEqual({
      stage: "discover",
      view: "work",
    });
    expect(parseAppUrlState("?stage=content&view=artifact")).toEqual({
      stage: "content",
      view: "artifact",
    });
  });

  it("drops unknown stage parameters", () => {
    expect(parseAppUrlState("?stage=retired&view=artifact")).toEqual({
      stage: null,
      view: "artifact",
    });
    expect(parseAppUrlState("?stage=unknown&view=unknown")).toEqual({
      stage: null,
      view: null,
    });
  });

  it("serializes the selected stage and view", () => {
    expect(serializeAppUrlState({ stage: "content", view: "artifact" })).toBe(
      "?stage=content&view=artifact",
    );
    expect(serializeAppUrlState({})).toBe("");
  });
});
