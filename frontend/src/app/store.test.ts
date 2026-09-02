import { describe, expect, it } from "vitest";
import { appReducer, initialAppState } from "./store";
import { adaptDiscovery } from "../data/adapters/discovery";
import * as fixtures from "../data/adapters/discovery.fixtures";

describe("appReducer", () => {
  it("sets read-only from the me projection", () => {
    const next = appReducer(initialAppState, {
      type: "me/set",
      me: { id: "u1", username: "a", role: "user", status: "active", onboarding_required: false, admin_available: false, read_only: true },
    });
    expect(next.readOnly).toBe(true);
    expect(next.me?.id).toBe("u1");
  });

  it("stores the normalized discovery view model", () => {
    const view = adaptDiscovery(fixtures.briefReview);
    const next = appReducer(initialAppState, { type: "discovery/set", view });
    expect(next.discovery?.state).toBe("review");
  });

  it("does not mutate the previous state object", () => {
    const next = appReducer(initialAppState, { type: "connection/set", state: "stale" });
    expect(initialAppState.connection).toBe("checking");
    expect(next.connection).toBe("stale");
    expect(next).not.toBe(initialAppState);
  });
});
