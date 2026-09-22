import { describe, expect, it } from "vitest";
import {
  getPreviewOrigin,
  isPreviewReadyMessage,
  isPreviewRouteMessage,
  PREVIEW_BRIDGE_VERSION,
  previewLoadMatchesSelection,
  previewRouteFromMessage,
  withPreviewReloadToken,
} from "./preview-bridge";

describe("preview bridge contract", () => {
  it("derives exact origins and adds a deterministic reload token", () => {
    expect(getPreviewOrigin("http://preview.test/portfolio/")).toBe("http://preview.test");
    expect(getPreviewOrigin("javascript:alert(1)")).toBeNull();
    expect(withPreviewReloadToken("http://preview.test/portfolio?route=home", 42)).toBe(
      "http://preview.test/portfolio?route=home&_preview_reload=42",
    );
  });

  it("matches a reload attempt only to its selected preview identity", () => {
    expect(
      previewLoadMatchesSelection(
        "https://preview.test/site/?route=home&_preview_reload=42",
        "https://preview.test/site/?route=home",
      ),
    ).toBe(true);
    expect(
      previewLoadMatchesSelection(
        "https://preview.test/old/?_preview_reload=42",
        "https://preview.test/new/",
      ),
    ).toBe(false);
  });

  it("accepts only the expected frame, origin, and protocol version", () => {
    const frame = {} as Window;
    const ready = {
      source: frame,
      origin: "http://preview.test",
      data: { type: "preview:ready", version: PREVIEW_BRIDGE_VERSION },
    };
    expect(isPreviewReadyMessage(ready, frame, "http://preview.test")).toBe(true);
    expect(isPreviewReadyMessage({ ...ready, origin: "http://attacker.test" }, frame, "http://preview.test")).toBe(false);
    expect(isPreviewReadyMessage({ ...ready, source: {} as Window }, frame, "http://preview.test")).toBe(false);
    expect(isPreviewReadyMessage({ ...ready, data: { type: "preview:ready", version: "old" } }, frame, "http://preview.test")).toBe(false);
  });

  it("supports bounded route telemetry from the same trusted frame", () => {
    const frame = {} as Window;
    const event = {
      source: frame,
      origin: "http://preview.test",
      data: { type: "preview:route", version: PREVIEW_BRIDGE_VERSION, path: "/about" },
    };
    expect(isPreviewRouteMessage(event, frame, "http://preview.test")).toBe(true);
    expect(previewRouteFromMessage(event.data)).toBe("/about");
    expect(previewRouteFromMessage({ route: " /work " })).toBe(" /work ");
  });
});
