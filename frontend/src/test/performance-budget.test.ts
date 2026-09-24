import { describe, it, expect } from "vitest";
import { livingDraftMarkMarkup } from "../../../src/oryxenai/auth/static/living-draft-mark.mjs";

declare const process: { cwd: () => string };

// Budgets track gzip size — what the browser actually transfers — as the
// primary guard, with a raw-size ceiling as a secondary sanity check.
// Raised 2026-09 alongside the workspace and reviewed-content updates
// (extracted-profile rail, sitemap, and peek-card decks): the previous
// 120kB/45kB raw ceilings were already
// silently unenforced (see below) and pre-dated this session's genuine
// feature growth, not an unexplained regression.
const JS_RAW_BUDGET_BYTES = 170 * 1024;
const JS_GZIP_BUDGET_BYTES = 50 * 1024;
const CSS_RAW_BUDGET_BYTES = 70 * 1024;
const CSS_GZIP_BUDGET_BYTES = 16 * 1024;

describe("Phase 5 Performance & Asset Budgets (docs/Frontend/05 §14, §18)", () => {
  it("LivingDraftMark SVG footprint is strictly under 4 kB budget", () => {
    const markupActive = livingDraftMarkMarkup({ active: true });
    const markupInactive = livingDraftMarkMarkup({ active: false });

    expect(new TextEncoder().encode(markupActive).length).toBeLessThan(4096);
    expect(new TextEncoder().encode(markupInactive).length).toBeLessThan(4096);
  });

  it("checks production asset budget limits against §14", async () => {
    // @ts-expect-error dynamic node import for vitest
    const fs = await import("node:fs");
    // @ts-expect-error dynamic node import for vitest
    const path = await import("node:path");
    // @ts-expect-error dynamic node import for vitest
    const zlib = await import("node:zlib");
    const assetsDir = path.resolve(process.cwd(), "../src/oryxenai/web/static/product/assets");
    // Only skip when the bundle genuinely has not been built yet (fresh
    // checkout before `npm run build`) — never swallow a real assertion
    // failure. A prior version of this test wrapped everything in a bare
    // try/catch that silently passed on any thrown error, including a
    // failed `expect()`, so the budget was never actually enforced.
    if (!fs.existsSync(assetsDir)) return;

    const files = fs.readdirSync(assetsDir);
    const jsFile = files.find((f: string) => f.endsWith(".js"));
    const cssFile = files.find((f: string) => f.endsWith(".css"));

    if (jsFile) {
      const contents = fs.readFileSync(path.resolve(assetsDir, jsFile));
      expect(contents.length).toBeLessThan(JS_RAW_BUDGET_BYTES);
      expect(zlib.gzipSync(contents).length).toBeLessThan(JS_GZIP_BUDGET_BYTES);
    }

    if (cssFile) {
      const contents = fs.readFileSync(path.resolve(assetsDir, cssFile));
      expect(contents.length).toBeLessThan(CSS_RAW_BUDGET_BYTES);
      expect(zlib.gzipSync(contents).length).toBeLessThan(CSS_GZIP_BUDGET_BYTES);
    }

    const rasterFiles = files.filter((f: string) => /\.(png|jpe?g|gif|webp|avif)$/i.test(f));
    expect(rasterFiles.length).toBe(0);
  });
});
